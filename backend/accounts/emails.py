"""ส่งอีเมลที่มีลิงก์โทเคน (ยืนยันอีเมล, ตั้งรหัสผ่านใหม่)

ส่งผ่าน send_mail ของ Django จึงไม่ผูกกับ provider ใด (ตอน dev พิมพ์ลงคอนโซล — ดู settings.EMAIL_BACKEND)
อีเมลหนึ่งฉบับมีทั้งภาษาไทยและอังกฤษ เพราะระบบยังไม่เก็บว่าผู้ใช้เลือกภาษาไหน
"""

from urllib.parse import quote

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .email_tokens import RESET_PASSWORD_LIFETIME, VERIFY_EMAIL_LIFETIME
from .models import User

# หัวข้อสองภาษาในบรรทัดเดียว (ไทย / อังกฤษ)
VERIFY_EMAIL_SUBJECT = "ยืนยันอีเมลของคุณ / Verify your email"
RESET_PASSWORD_SUBJECT = "ตั้งรหัสผ่านใหม่ / Reset your password"


def _send_link_email(user: User, subject: str, template: str, path: str, raw_token: str, lifetime):
    """ประกอบลิงก์ {FRONTEND_URL}{path}?token=... แล้วส่งอีเมลจาก template ให้ผู้ใช้"""
    body = render_to_string(
        template,
        {
            "first_name": user.first_name,
            # โทเคนเป็นอักขระที่ปลอดภัยใน URL อยู่แล้ว (token_urlsafe) แต่ quote ไว้เผื่อรูปแบบเปลี่ยนภายหลัง
            "link": f"{settings.FRONTEND_URL}{path}?token={quote(raw_token, safe='')}",
            # อายุลิงก์เป็นชั่วโมงเต็ม (24 / 1) ให้ผู้ใช้อ่านง่าย
            "hours": int(lifetime.total_seconds() // 3600),
        },
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


def send_verification_email(user: User, raw_token: str) -> None:
    """ส่งลิงก์ยืนยันอีเมลตอนสมัคร (หน้า /verify-email ของเว็บ)"""
    _send_link_email(
        user,
        VERIFY_EMAIL_SUBJECT,
        "accounts/email/verify_email.txt",
        "/verify-email",
        raw_token,
        VERIFY_EMAIL_LIFETIME,
    )


def send_password_reset_email(user: User, raw_token: str) -> None:
    """ส่งลิงก์ตั้งรหัสผ่านใหม่ตอนลืมรหัสผ่าน (หน้า /reset-password ของเว็บ)"""
    _send_link_email(
        user,
        RESET_PASSWORD_SUBJECT,
        "accounts/email/reset_password.txt",
        "/reset-password",
        raw_token,
        RESET_PASSWORD_LIFETIME,
    )
