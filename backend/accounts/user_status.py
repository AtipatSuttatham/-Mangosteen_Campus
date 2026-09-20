"""สถานะบัญชี 4 แบบที่ Admin เห็นในหน้าจัดการผู้ใช้ (docs/design.md หัวข้อ "หน้าจัดการผู้ใช้ของ Admin")

สถานะไม่ได้เก็บเป็นคอลัมน์ แต่คำนวณจากฟิลด์ที่มีอยู่แล้ว กฎเดียวจึงมี 2 รูปแบบที่ "ต้องตรงกันเสมอ":
- status_of      คำนวณจากผู้ใช้ 1 คน (ใช้ตอนแสดงผล)
- status_filter  เงื่อนไขของฐานข้อมูล (ใช้ตอนกรองรายชื่อ)
มี test เทียบสองแบบนี้ทุกชุดเงื่อนไขใน test_user_status.py

ลำดับความสำคัญเมื่อเข้าข่ายหลายข้อ: ปิดใช้งาน → รอตั้งรหัสผ่าน → รอยืนยันอีเมล → ใช้งานอยู่
"""

from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX
from django.db import models
from django.db.models import Q

from .models import User


class UserStatus(models.TextChoices):
    """ค่าที่ API ส่ง/รับ (หน้าเว็บแปลเป็นไทย/อังกฤษเอง เหมือนที่ใช้ `code` ของ error)"""

    ACTIVE = "active", "ใช้งานอยู่"
    PENDING_PASSWORD = "pending_password", "รอตั้งรหัสผ่าน"
    PENDING_VERIFICATION = "pending_verification", "รอยืนยันอีเมล"
    DISABLED = "disabled", "ปิดใช้งาน"


def has_no_password(password: str) -> bool:
    """บัญชียังไม่มีรหัสผ่าน (Admin สร้างให้แล้วเจ้าของยังไม่กดลิงก์ตั้งรหัส) = ขึ้นต้นด้วย "!"

    ตั้งใจไม่ใช้ has_usable_password() ของ Django: มันตอบว่า "ใช้ได้" กับรหัสผ่านที่เป็นสตริงว่าง
    ต่างจากเงื่อนไขขึ้นต้นด้วย "!" ที่ใช้กรองในฐานข้อมูล ใช้กฎเดียวกันทั้งสองฝั่งจึงไม่เหลื่อมกัน
    """
    return password.startswith(UNUSABLE_PASSWORD_PREFIX)


def status_of(user: User) -> str:
    """สถานะของผู้ใช้ 1 คน (คืนค่าเป็นข้อความของ UserStatus)"""
    if not user.is_active:
        return UserStatus.DISABLED
    if has_no_password(user.password):
        return UserStatus.PENDING_PASSWORD
    if not user.is_email_verified:
        return UserStatus.PENDING_VERIFICATION
    return UserStatus.ACTIVE


def status_filter(status: str) -> Q:
    """เงื่อนไขกรองผู้ใช้ตามสถานะ — ต้องให้ผลตรงกับ status_of เสมอ

    ทุกสถานะที่ไม่ใช่ "ปิดใช้งาน" ระบุ is_active=True ชัดเจน เพื่อให้ 4 สถานะไม่ซ้อนทับกัน
    (ผู้ใช้ 1 คนอยู่ในสถานะเดียวเท่านั้น)
    """
    no_password = Q(password__startswith=UNUSABLE_PASSWORD_PREFIX)
    if status == UserStatus.DISABLED:
        return Q(is_active=False)
    if status == UserStatus.PENDING_PASSWORD:
        return Q(is_active=True) & no_password
    if status == UserStatus.PENDING_VERIFICATION:
        return Q(is_active=True, is_email_verified=False) & ~no_password
    if status == UserStatus.ACTIVE:
        return Q(is_active=True, is_email_verified=True) & ~no_password
    raise ValueError(f"สถานะไม่ถูกต้อง: {status!r}")
