"""จัดการบัญชีผู้ใช้โดย Admin: สร้าง / แก้ไข / ปิด-เปิดใช้งาน / ส่งลิงก์ตั้งรหัสผ่านซ้ำ (ก้อน d3)

ทุกฟังก์ชันไม่รู้จัก HTTP — view เรียกใช้ แล้วแปลง error เป็นคำตอบของ API (สัญญาอยู่ที่ docs/api-admin-users.md)
หลักการร่วม:
- การเปลี่ยนข้อมูล + Audit Log อยู่ใน "ธุรกรรมเดียวกัน" ล้มพร้อมกัน: ไม่มี log ของสิ่งที่ไม่เคยเกิด
  และถ้าเขียน log ไม่ได้ ตัวการกระทำก็ล้มด้วย
- อีเมลส่ง "หลังธุรกรรมสำเร็จ" เท่านั้น ถ้าธุรกรรมล้ม จะไม่มีลิงก์ที่ชี้ไปหาบัญชีที่ไม่มีอยู่จริงหลุดออกไป
- ต่างจาก endpoint สาธารณะที่ต้องกลืน error การส่งอีเมล (กันการเดาอีเมล) ฝั่ง Admin ต้องรู้ความจริง
  จึงคืน email_sent ให้ view ตอบ (บัญชียังถูกสร้าง/แก้แล้ว Admin กดส่งลิงก์ซ้ำได้)
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ErrorDetail, ValidationError

from audit.models import AuditAction
from audit.services import field_changes, log_action

from .email_tokens import (
    INVITE_LIFETIME,
    VERIFY_EMAIL_LIFETIME,
    cancel_unused_tokens,
    issue_token,
    seconds_until_resend,
)
from .emails import send_account_invite_email, send_verification_email
from .exceptions import (
    CannotDeactivateSelf,
    CannotDemoteSelf,
    InviteNotApplicable,
    LastAdmin,
    ResendTooSoon,
)
from .models import TokenPurpose, User
from .roles import Role
from .user_status import UserStatus, status_of

logger = logging.getLogger(__name__)

# ฟิลด์ที่ Admin แก้ได้ผ่าน API (รหัสผ่านและสิทธิ์อื่นแก้ผ่านทางนี้ไม่ได้เลย)
PROFILE_FIELDS = (
    "email",
    "role",
    "first_name",
    "last_name",
    "first_name_en",
    "last_name_en",
    "student_or_staff_id",
)
# ฟิลด์ที่เทียบและบันทึกลง Audit Log (whitelist — ห้ามมีรหัสผ่านหรือโทเคน)
AUDITED_FIELDS = (*PROFILE_FIELDS, "is_active")


@dataclass(frozen=True)
class Outcome:
    """ผลของการกระทำที่อาจส่งอีเมล: email_sent = True/False ตามที่ส่งจริง, None = ไม่ต้องส่งอีเมลเลย"""

    user: User
    email_sent: bool | None


# ---------- ตรวจซ้ำ (อีเมล / รหัส) ----------


def email_in_use(email: str, *, exclude_pk: int | None = None) -> bool:
    """มีบัญชีอื่นใช้อีเมลนี้อยู่แล้วหรือไม่ (อีเมลในฐานข้อมูลเป็นตัวพิมพ์เล็กเสมอ ผู้เรียกต้องแปลงก่อน)"""
    queryset = User.objects.filter(email=email)
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.exists()


def staff_id_in_use(staff_id: str, *, exclude_pk: int | None = None) -> bool:
    """มีบัญชีอื่นใช้รหัสนักศึกษา/พนักงานนี้อยู่แล้วหรือไม่ (แยกตัวพิมพ์เล็ก/ใหญ่)"""
    queryset = User.objects.filter(student_or_staff_id=staff_id)
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.exists()


def _taken_errors(email: str, staff_id: str | None, exclude_pk: int | None = None) -> dict:
    """ข้อผิดพลาดรายช่องของอีเมล/รหัสที่ซ้ำ (ว่าง = ไม่ซ้ำ) — ใช้แปลง IntegrityError กรณีสองคำขอแข่งกัน"""
    errors = {}
    if email_in_use(email, exclude_pk=exclude_pk):
        errors["email"] = [ErrorDetail("อีเมลนี้ถูกใช้แล้ว", code="email_taken")]
    if staff_id and staff_id_in_use(staff_id, exclude_pk=exclude_pk):
        errors["student_or_staff_id"] = [ErrorDetail("รหัสนี้ถูกใช้แล้ว", code="staff_id_taken")]
    return errors


# ---------- ตัวช่วยภายใน ----------


def _snapshot(user: User) -> dict:
    """ค่าของฟิลด์ที่บันทึกลง Audit Log ณ ตอนนี้ (สตริงว่างนับเป็น None: "ไม่มีค่า" เหมือนกันทุกที่)"""
    return {
        name: (None if getattr(user, name) == "" else getattr(user, name))
        for name in AUDITED_FIELDS
    }


def _send_safely(send: Callable[[User, str], None], user: User, raw_token: str) -> bool:
    """ส่งอีเมล แล้วคืนว่าสำเร็จไหม — ไม่ปล่อยให้คำขอล้มเป็น 500 (การกระทำหลักสำเร็จไปแล้ว)"""
    try:
        send(user, raw_token)
    except Exception:
        logger.exception("ส่งอีเมลให้ผู้ใช้ไม่สำเร็จ (user id=%s)", user.pk)
        return False
    return True


def _lock_active_admins() -> set[int]:
    """ล็อกแถว Admin ที่ใช้งานอยู่ทั้งหมดจนจบธุรกรรม แล้วคืน pk ของพวกเขา

    ล็อก "ก่อน" ล็อกแถวเป้าหมายเสมอ (เรียงตาม pk): ถ้า Admin สองคนลดบทบาท/ปิดใช้งานกันเองพร้อมกัน
    คำขอที่สองต้องรอคำขอแรกจบแล้วเห็นผลของมัน (ไม่เหลือ Admin เป็นศูนย์) และลำดับล็อกที่คงที่ทำให้ไม่เกิด deadlock
    """
    return set(
        User.objects.select_for_update()
        .filter(role=Role.ADMIN, is_active=True)
        .order_by("pk")
        .values_list("pk", flat=True)
    )


def _ensure_another_admin(user: User, active_admin_ids: set[int]) -> None:
    """ถ้าผู้ใช้นี้เป็น Admin ที่ใช้งานอยู่ ต้องเหลือ Admin คนอื่นที่ใช้งานอยู่อย่างน้อย 1 คน ไม่งั้นโยน LastAdmin"""
    if user.pk in active_admin_ids and not (active_admin_ids - {user.pk}):
        raise LastAdmin


# ---------- สร้างบัญชี ----------


def create_user_by_admin(
    *,
    actor: User,
    role: str,
    email: str,
    first_name: str,
    last_name: str,
    student_or_staff_id: str | None = None,
    first_name_en: str = "",
    last_name_en: str = "",
    audit_context: dict | None = None,
) -> Outcome:
    """สร้างบัญชีให้ผู้ใช้ (ยังไม่มีรหัสผ่าน) แล้วส่งลิงก์ตั้งรหัสผ่านอายุ 7 วันไปที่อีเมลนั้น

    - ยืนยันอีเมลแล้วตั้งแต่สร้าง (docs/database.md W2) ความเป็นเจ้าของอีเมลพิสูจน์ตอนกดลิงก์ตั้งรหัสผ่าน
    - created_by = actor; ไม่ได้สิทธิ์ Django admin (is_staff เป็น False เสมอ แม้บทบาทเป็น admin)
    - อีเมล/รหัสซ้ำ → ValidationError รายช่อง (รวมกรณีสองคำขอแข่งกันชน unique ในฐานข้อมูล)
    """
    with transaction.atomic():
        try:
            # savepoint แยก: ชน unique แล้วธุรกรรมหลักต้องยังใช้งานต่อได้
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    password=None,
                    role=role,
                    first_name=first_name,
                    last_name=last_name,
                    student_or_staff_id=student_or_staff_id,
                    first_name_en=first_name_en,
                    last_name_en=last_name_en,
                    is_email_verified=True,
                    created_by=actor,
                )
        except IntegrityError as exc:
            errors = _taken_errors(
                email.strip().lower(), (student_or_staff_id or "").strip() or None
            )
            if errors:
                raise ValidationError(errors) from exc
            raise

        raw_token = issue_token(user, TokenPurpose.RESET_PASSWORD, INVITE_LIFETIME)
        log_action(
            actor=actor,
            action=AuditAction.CREATE,
            target=user,
            changes=field_changes(dict.fromkeys(AUDITED_FIELDS), _snapshot(user), AUDITED_FIELDS),
            context=audit_context,
        )

    return Outcome(user, _send_safely(send_account_invite_email, user, raw_token))


# ---------- แก้ไขข้อมูล ----------


def update_user_by_admin(
    *, actor: User, user_id: int, updates: dict, audit_context: dict | None = None
) -> Outcome:
    """แก้ข้อมูลของผู้ใช้ (เฉพาะฟิลด์ใน PROFILE_FIELDS ที่อยู่ใน updates)

    - ไม่มีอะไรเปลี่ยนจริง → ไม่บันทึก ไม่เขียน log ไม่ส่งอีเมล
    - เปลี่ยนบทบาทของตัวเองไม่ได้ (CannotDemoteSelf) และห้ามทำให้ไม่เหลือ Admin (LastAdmin)
    - เปลี่ยนอีเมลได้ทุกบัญชี: ยกเลิกโทเคนที่ยังไม่ใช้ทั้งหมดก่อน (โทเคนผูกกับผู้ใช้ ไม่ใช่อีเมล ลิงก์ที่เคยส่ง
      ไปอีเมลเดิมต้องใช้ไม่ได้) แล้วส่งลิงก์ใหม่ไป "อีเมลใหม่" ตามสถานะ: รอตั้งรหัสผ่าน → ลิงก์ตั้งรหัส 7 วัน,
      รอยืนยันอีเมล → ลิงก์ยืนยัน 24 ชั่วโมง, ใช้งานอยู่/ปิดใช้งาน → ไม่ส่งอะไร (คงสถานะยืนยันไว้)
    """
    with transaction.atomic():
        active_admin_ids = _lock_active_admins()
        user = get_object_or_404(User.objects.select_for_update(), pk=user_id)
        before = _snapshot(user)

        new_role = updates.get("role", user.role)
        if new_role != user.role:
            if user.pk == actor.pk:
                raise CannotDemoteSelf
            if new_role != Role.ADMIN:
                _ensure_another_admin(user, active_admin_ids)

        for name in PROFILE_FIELDS:
            if name in updates:
                setattr(user, name, updates[name])
        # ทำให้เป็นรูปแบบเดียวกับที่จะบันทึก (อีเมลตัวพิมพ์เล็ก, รหัสว่าง = None) ก่อนเทียบว่ามีอะไรเปลี่ยนไหม
        user.normalize_fields()

        changes = field_changes(before, _snapshot(user), AUDITED_FIELDS)
        if not changes:
            return Outcome(user, None)

        try:
            with transaction.atomic():
                user.save(update_fields=[*changes, "updated_at"])
        except IntegrityError as exc:
            errors = _taken_errors(user.email, user.student_or_staff_id, exclude_pk=user.pk)
            if errors:
                raise ValidationError(errors) from exc
            raise

        raw_token = None
        send = None
        if "email" in changes:
            cancel_unused_tokens(user)
            new_status = status_of(user)
            if new_status == UserStatus.PENDING_PASSWORD:
                raw_token = issue_token(user, TokenPurpose.RESET_PASSWORD, INVITE_LIFETIME)
                send = send_account_invite_email
            elif new_status == UserStatus.PENDING_VERIFICATION:
                raw_token = issue_token(user, TokenPurpose.VERIFY_EMAIL, VERIFY_EMAIL_LIFETIME)
                send = send_verification_email

        log_action(
            actor=actor,
            action=AuditAction.UPDATE,
            target=user,
            changes=changes,
            context=audit_context,
        )

    email_sent = None if raw_token is None else _send_safely(send, user, raw_token)
    return Outcome(user, email_sent)


# ---------- ปิด / เปิดใช้งาน ----------


def set_user_active(
    *, actor: User, user_id: int, is_active: bool, audit_context: dict | None = None
) -> User:
    """ปิดหรือเปิดใช้งานบัญชี (ทำซ้ำได้: สถานะเป็นอย่างนั้นอยู่แล้วก็ไม่บันทึก ไม่เขียน log ซ้ำ)

    ปิดตัวเองไม่ได้ (CannotDeactivateSelf) และห้ามปิด Admin คนสุดท้าย (LastAdmin)
    ปิดแล้ว: เข้าสู่ระบบ/ใช้ token/ต่ออายุเซสชันไม่ได้ทันที และลิงก์ตั้งรหัสที่ค้างอยู่ใช้ไม่ได้
    """
    with transaction.atomic():
        active_admin_ids = _lock_active_admins()
        user = get_object_or_404(User.objects.select_for_update(), pk=user_id)
        if user.is_active == is_active:
            return user

        if not is_active:
            if user.pk == actor.pk:
                raise CannotDeactivateSelf
            _ensure_another_admin(user, active_admin_ids)

        before = _snapshot(user)
        user.is_active = is_active
        user.save(update_fields=["is_active", "updated_at"])
        log_action(
            actor=actor,
            action=AuditAction.UPDATE,
            target=user,
            changes=field_changes(before, _snapshot(user), AUDITED_FIELDS),
            context=audit_context,
        )
    return user


# ---------- ส่งลิงก์ตั้งรหัสผ่านซ้ำ ----------


def resend_invite(*, actor: User, user_id: int, audit_context: dict | None = None) -> Outcome:
    """ส่งลิงก์ตั้งรหัสผ่านครั้งแรก (7 วัน) ซ้ำให้บัญชีที่ยังไม่ได้ตั้งรหัส — ลิงก์ฉบับเก่าใช้ไม่ได้ทันที

    - เฉพาะสถานะรอตั้งรหัสผ่าน (InviteNotApplicable ถ้าเป็นสถานะอื่น รวมถึงบัญชีที่ปิดใช้งานอยู่)
    - ต้องพ้น 60 วินาทีจากลิงก์ล่าสุด (ResendTooSoon พร้อมเวลาที่ต้องรอ) โดยไม่ส่งอีเมลและลิงก์เดิมยังใช้ได้
    - บันทึก Audit Log เป็น update ที่ไม่มี changes แต่มี context.event = "resend_invite"
    - ล็อกแถวผู้ใช้: กดซ้ำพร้อมกันหลายคำขอ คำขอหลังเห็นกฎรอ 60 วินาทีแล้วถูกปฏิเสธ (ไม่ออกลิงก์ซ้อน)
    """
    with transaction.atomic():
        user = get_object_or_404(User.objects.select_for_update(), pk=user_id)
        if status_of(user) != UserStatus.PENDING_PASSWORD:
            raise InviteNotApplicable
        wait = seconds_until_resend(user, TokenPurpose.RESET_PASSWORD)
        if wait > 0:
            raise ResendTooSoon(wait)

        raw_token = issue_token(user, TokenPurpose.RESET_PASSWORD, INVITE_LIFETIME)
        log_action(
            actor=actor,
            action=AuditAction.UPDATE,
            target=user,
            context={**(audit_context or {}), "event": "resend_invite"},
        )

    return Outcome(user, _send_safely(send_account_invite_email, user, raw_token))
