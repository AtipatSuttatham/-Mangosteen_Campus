"""ลืมรหัสผ่าน / ตั้งรหัสผ่านใหม่ด้วยลิงก์ในอีเมล (ก้อน c3)

ทุกฟังก์ชันไม่รู้จัก HTTP — view เรียกใช้ แล้วแปลง error เป็นคำตอบของ API
บัญชีที่ Admin สร้างให้และยังไม่มีรหัสผ่านก็ใช้เส้นทางเดียวกันนี้ตั้งรหัสครั้งแรกได้
"""

import logging

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .email_tokens import (
    RESET_PASSWORD_LIFETIME,
    consume_token,
    issue_token,
    peek_token,
    seconds_until_resend,
)
from .emails import send_password_reset_email
from .exceptions import TokenInvalid
from .models import TokenPurpose, User
from .password_rules import password_rule_errors
from .registration import normalize_email

logger = logging.getLogger(__name__)


def request_password_reset(email: str) -> None:
    """ขอลิงก์ตั้งรหัสผ่านใหม่ — ไม่โยน error ทุกกรณี (API ตอบเหมือนกันเสมอ ไม่บอกว่ามีอีเมลนี้หรือไม่)

    ส่งเฉพาะบัญชีที่มีจริง ยืนยันอีเมลแล้ว เปิดใช้งานอยู่ และพ้น 60 วินาทีจากลิงก์ล่าสุด
    บัญชีที่ยังไม่ยืนยันอีเมลไม่ได้ลิงก์นี้ (ต้องยืนยันอีเมลก่อน กันใช้เส้นทางนี้ข้ามขั้นตอนยืนยัน)
    ลิงก์ฉบับก่อนหน้าจะใช้ไม่ได้ทันทีที่ออกฉบับใหม่
    """
    with transaction.atomic():
        # ล็อกแถวกันขอลิงก์พร้อมกันหลายคำขอแล้วออกโทเคนซ้อนกัน
        user = User.objects.select_for_update().filter(email=normalize_email(email)).first()
        if user is None or not user.is_email_verified or not user.is_active:
            return
        if seconds_until_resend(user, TokenPurpose.RESET_PASSWORD) > 0:
            return
        raw_token = issue_token(user, TokenPurpose.RESET_PASSWORD, RESET_PASSWORD_LIFETIME)

    # ส่งอีเมลหลังจบธุรกรรม ถ้าส่งไม่สำเร็จแค่บันทึก error (คำตอบของ API ต้องเหมือนกันทุกกรณี ห้ามล้มเป็น 500)
    try:
        send_password_reset_email(user, raw_token)
    except Exception:
        logger.exception("ส่งอีเมลตั้งรหัสผ่านไม่สำเร็จ (user id=%s)", user.pk)


def check_reset_token(raw_token: str) -> User:
    """ตรวจลิงก์ตั้งรหัสผ่านโดยไม่ใช้ทิ้ง แล้วคืนผู้ใช้เจ้าของ (ให้หน้าเว็บแสดงว่าตั้งรหัสให้บัญชีไหน)

    ผิดเงื่อนไขโยน TokenInvalid / TokenExpired บัญชีที่ถูกปิดแล้วถือว่าลิงก์ใช้ไม่ได้
    """
    user = peek_token(raw_token, TokenPurpose.RESET_PASSWORD)
    if not user.is_active:
        raise TokenInvalid
    return user


def reset_password(raw_token: str, new_password: str) -> User:
    """ตั้งรหัสผ่านใหม่จากลิงก์ (ใช้โทเคนได้ครั้งเดียว)

    ทำทั้งหมดในธุรกรรมเดียว ลำดับ: ใช้โทเคน → ตรวจกฎรหัสผ่าน → บันทึก
    ถ้ารหัสผ่านไม่ผ่านกฎ ธุรกรรมย้อนกลับ ทำให้โทเคน **ไม่ถูกใช้ทิ้ง** ผู้ใช้กรอกใหม่ด้วยลิงก์เดิมได้
    ตั้งรหัสสำเร็จแล้วเซสชันเดิมทั้งหมดใช้ไม่ได้ (refresh token ผูกกับรหัสผ่าน — ดู tokens.py)
    ไม่ล็อกอินให้ (หน้าเว็บพาไปหน้า login)
    """
    with transaction.atomic():
        user = consume_token(raw_token, TokenPurpose.RESET_PASSWORD)
        if not user.is_active:
            raise TokenInvalid
        errors = password_rule_errors(new_password, user)
        if errors:
            raise ValidationError({"password": errors})
        user.set_password(new_password)
        # update_fields ไม่อัปเดต updated_at ให้เอง ต้องระบุเพิ่ม
        user.save(update_fields=["password", "updated_at"])
    return user
