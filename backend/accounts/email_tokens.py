"""ออก/ตรวจ/ใช้โทเคนแบบครั้งเดียวในลิงก์อีเมล (ยืนยันอีเมล, ตั้งรหัสผ่าน)

หลักการ: ตัวโทเคนจริงส่งทางอีเมลเท่านั้น ในฐานข้อมูลเก็บแค่แฮช SHA-256 ของมัน
"""

import hashlib
import math
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .exceptions import TokenExpired, TokenInvalid
from .models import EmailVerificationToken, User

# อายุของลิงก์แต่ละแบบ (docs/database.md §3) — ลิงก์ตั้งรหัสครั้งแรก 7 วันของบัญชีที่ Admin สร้าง
# จะเพิ่มพร้อมฟีเจอร์จัดการผู้ใช้
VERIFY_EMAIL_LIFETIME = timedelta(hours=24)
RESET_PASSWORD_LIFETIME = timedelta(hours=1)

# ขอลิงก์ใหม่ของบัญชีเดียวกัน (จุดประสงค์เดียวกัน) ได้ไม่ถี่กว่านี้ — กันคนกดรัวเพื่อสแปมอีเมลของคนอื่น
RESEND_COOLDOWN = timedelta(seconds=60)


def hash_token(raw_token: str) -> str:
    """แฮช SHA-256 (hex 64 ตัว) ของโทเคน — ใช้ทั้งตอนเก็บและตอนค้นหาจากลิงก์"""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def issue_token(user: User, purpose: str, lifetime: timedelta) -> str:
    """ออกโทเคนใหม่ให้ผู้ใช้ แล้วคืน "ตัวโทเคนจริง" เพื่อใส่ในลิงก์อีเมล (ไม่มีเก็บที่ไหนอีก)

    โทเคนเก่าของบัญชีนี้ในจุดประสงค์เดียวกันที่ยังไม่ถูกใช้จะถูกยกเลิกทันที
    ผู้ใช้กด "ส่งลิงก์อีกครั้ง" แล้วลิงก์ฉบับเก่าที่ค้างในกล่องอีเมลจึงใช้ไม่ได้
    """
    # 32 ไบต์สุ่มจากตัวสร้างเลขสุ่มที่ปลอดภัย (256 บิต) เดาไม่ได้
    raw_token = secrets.token_urlsafe(32)
    now = timezone.now()
    with transaction.atomic():
        # ยกเลิกใบเก่าด้วยการทำเครื่องหมายว่า "ใช้แล้ว" (ไม่ต้องมีสถานะเพิ่ม)
        EmailVerificationToken.objects.filter(
            user=user, purpose=purpose, used_at__isnull=True
        ).update(used_at=now)
        EmailVerificationToken.objects.create(
            user=user,
            token_hash=hash_token(raw_token),
            purpose=purpose,
            expires_at=now + lifetime,
        )
    return raw_token


def seconds_until_resend(user: User, purpose: str) -> int:
    """ต้องรออีกกี่วินาทีจึงจะออกโทเคนใหม่ได้ (0 = ออกได้เลย)"""
    latest = (
        EmailVerificationToken.objects.filter(user=user, purpose=purpose)
        .order_by("-created_at")
        .first()
    )
    if latest is None:
        return 0
    remaining = (latest.created_at + RESEND_COOLDOWN - timezone.now()).total_seconds()
    # ปัดขึ้นเป็นวินาทีเต็ม เพื่อไม่ให้บอกว่า "รอ 0 วินาที" ทั้งที่ยังไม่ถึงเวลา
    return max(0, math.ceil(remaining))


def consume_token(raw_token: str, purpose: str) -> User:
    """ตรวจโทเคนจากลิงก์และ "ใช้" มัน (ใช้ได้ครั้งเดียว) แล้วคืนผู้ใช้เจ้าของ

    - ไม่พบ / ใช้ไปแล้ว / ผิดจุดประสงค์ → TokenInvalid
    - พบและยังไม่ใช้ แต่หมดอายุ → TokenExpired (ไม่ถือว่าใช้แล้ว)
    ผู้เรียกต้องตรวจเองว่าบัญชียังเปิดใช้งาน (is_active) ก่อนทำต่อ
    """
    with transaction.atomic():
        # ล็อกแถวไว้ตลอดธุรกรรม: ถ้ากดลิงก์เดียวกัน 2 คำขอพร้อมกัน คำขอที่สองจะรอแล้วเห็นว่า "ใช้แล้ว"
        token = (
            EmailVerificationToken.objects.select_for_update()
            .select_related("user")
            .filter(token_hash=hash_token(raw_token), purpose=purpose)
            .first()
        )
        if token is None or token.used_at is not None:
            raise TokenInvalid
        now = timezone.now()
        if token.expires_at <= now:
            raise TokenExpired
        token.used_at = now
        token.save(update_fields=["used_at"])
        return token.user
