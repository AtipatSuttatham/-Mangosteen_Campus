"""สมัครสมาชิกด้วยอีเมล, ยืนยันอีเมล และขอลิงก์ยืนยันใหม่ (ก้อน c2)

ทุกฟังก์ชันไม่รู้จัก HTTP — view เรียกใช้ แล้วแปลง error เป็นคำตอบของ API
"""

import logging

from django.db import IntegrityError, transaction

from .email_tokens import (
    VERIFY_EMAIL_LIFETIME,
    consume_token,
    issue_token,
    seconds_until_resend,
)
from .emails import send_verification_email
from .exceptions import EmailTaken, TokenInvalid
from .models import TokenPurpose, User
from .roles import Role

logger = logging.getLogger(__name__)


def normalize_email(email: str) -> str:
    """อีเมลในฐานข้อมูลเก็บเป็นตัวพิมพ์เล็กเสมอ (ตัดช่องว่างหัวท้ายด้วย)"""
    return email.strip().lower()


def _lock_user(email: str) -> User | None:
    """หาผู้ใช้จากอีเมลพร้อมล็อกแถวไว้จนจบธุรกรรม (ไม่พบ = None)

    ล็อกกันคนสมัครซ้ำ/ขอลิงก์ซ้ำด้วยอีเมลเดียวกันพร้อมกันแล้วแก้ข้อมูลทับกันมั่ว
    """
    return User.objects.select_for_update().filter(email=email).first()


def _send_verification_safely(user: User, raw_token: str) -> None:
    """ส่งอีเมลยืนยัน ถ้าส่งไม่สำเร็จ (เช่น ระบบอีเมลล่ม) แค่บันทึก error แล้วไปต่อ

    ไม่ปล่อยให้คำขอล้มเป็น 500: ผู้ใช้กด "ส่งอีกครั้ง" ได้ และคำตอบของ API
    จะไม่ต่างกันระหว่างอีเมลที่มี/ไม่มีในระบบ (ไม่ต้องบอกเหตุผลที่ส่งไม่ออก)
    """
    try:
        send_verification_email(user, raw_token)
    except Exception:
        logger.exception("ส่งอีเมลยืนยันไม่สำเร็จ (user id=%s)", user.pk)


def _issue_verification_if_allowed(user: User) -> str | None:
    """ออกโทเคนยืนยันอีเมลใหม่ถ้าพ้น 60 วินาทีจากครั้งก่อน (ยังไม่พ้น = None ไม่ส่งซ้ำ)"""
    if seconds_until_resend(user, TokenPurpose.VERIFY_EMAIL) > 0:
        return None
    return issue_token(user, TokenPurpose.VERIFY_EMAIL, VERIFY_EMAIL_LIFETIME)


def register_student(*, email: str, password: str, first_name: str, last_name: str) -> None:
    """สมัครเองด้วยอีเมล: สร้างบัญชีผู้เรียนที่ยังไม่ยืนยันอีเมล แล้วส่งลิงก์ยืนยัน

    - role เป็น student เสมอ (Teacher/Admin ต้อง Admin สร้าง) ไม่มีรหัสนักศึกษา ไม่มี created_by
    - อีเมลที่มีบัญชียืนยันแล้ว หรือบัญชีถูกปิด → EmailTaken
    - อีเมลที่สมัครค้างไว้แต่ยังไม่ยืนยัน → เขียนทับรหัสผ่านและชื่อด้วยค่าที่ส่งมาล่าสุด แล้วส่งลิงก์ใหม่
      (กันคนร้ายสมัครล่วงหน้าด้วยอีเมลเหยื่อ + รหัสของตัวเอง: พอเจ้าของอีเมลสมัครจริงทับ รหัสของคนร้ายใช้ไม่ได้ทันที)
    """
    email = normalize_email(email)

    with transaction.atomic():
        user = _lock_user(email)
        if user is None:
            try:
                # savepoint แยก เพราะถ้าชน unique (มีคนสมัครอีเมลนี้พร้อมกัน) ธุรกรรมหลักต้องไม่พัง
                with transaction.atomic():
                    user = User.objects.create_user(
                        email=email,
                        password=password,
                        role=Role.STUDENT,
                        first_name=first_name,
                        last_name=last_name,
                    )
            except IntegrityError:
                # อีกคำขอสร้างแถวนี้ตัดหน้าไปแล้ว → กลับไปใช้เส้นทางเดียวกับ "มีบัญชีอยู่แล้ว" ด้านล่าง
                user = _lock_user(email)
                if user is not None:
                    user = _overwrite_pending_registration(user, password, first_name, last_name)
        else:
            user = _overwrite_pending_registration(user, password, first_name, last_name)
        if user is None:
            raise EmailTaken
        raw_token = _issue_verification_if_allowed(user)

    # ส่งอีเมลหลังจบธุรกรรม: ถ้าธุรกรรมล้ม จะไม่มีลิงก์ที่ชี้ไปหาบัญชีที่ไม่มีอยู่จริงหลุดออกไป
    if raw_token is not None:
        _send_verification_safely(user, raw_token)


def _overwrite_pending_registration(
    user: User, password: str, first_name: str, last_name: str
) -> User | None:
    """อีเมลนี้มีบัญชีอยู่แล้ว: ถ้ายังสมัครค้าง (ไม่ยืนยัน + เปิดอยู่) เขียนทับด้วยข้อมูลล่าสุด

    คืน None เมื่อบัญชียืนยันแล้วหรือถูกปิด (ผู้เรียกจะโยน EmailTaken) — ไม่แก้ข้อมูลของบัญชีเหล่านั้นเด็ดขาด
    """
    if user.is_email_verified or not user.is_active:
        return None
    user.set_password(password)
    user.first_name = first_name
    user.last_name = last_name
    user.save()
    return user


def verify_email(raw_token: str) -> User:
    """ยืนยันอีเมลจากโทเคนในลิงก์ (ใช้ได้ครั้งเดียว)

    - โทเคนไม่ถูกต้อง/ใช้แล้ว/ผิดจุดประสงค์ → TokenInvalid, หมดอายุ → TokenExpired
    - บัญชีที่ถูกปิดแล้ว → TokenInvalid โดยไม่ถือว่าใช้โทเคน (อยู่ในธุรกรรมเดียวกัน จึงย้อนกลับได้)
    """
    with transaction.atomic():
        user = consume_token(raw_token, TokenPurpose.VERIFY_EMAIL)
        if not user.is_active:
            raise TokenInvalid
        if not user.is_email_verified:
            user.is_email_verified = True
            # update_fields ไม่อัปเดต updated_at ให้เอง ต้องระบุเพิ่ม
            user.save(update_fields=["is_email_verified", "updated_at"])
    return user


def resend_verification(email: str) -> None:
    """ส่งลิงก์ยืนยันอีเมลอีกครั้ง — ไม่โยน error ทุกกรณี (API ตอบเหมือนกันเสมอ ไม่บอกว่ามีอีเมลนี้หรือไม่)

    ส่งเฉพาะเมื่อมีบัญชีนี้จริง ยังไม่ยืนยัน เปิดใช้งานอยู่ และพ้น 60 วินาทีจากลิงก์ล่าสุด
    ลิงก์ฉบับก่อนหน้าจะใช้ไม่ได้ทันทีที่ออกฉบับใหม่
    """
    with transaction.atomic():
        user = _lock_user(normalize_email(email))
        if user is None or user.is_email_verified or not user.is_active:
            return
        raw_token = _issue_verification_if_allowed(user)

    if raw_token is not None:
        _send_verification_safely(user, raw_token)
