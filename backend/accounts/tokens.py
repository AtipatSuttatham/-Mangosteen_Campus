from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .exceptions import InvalidRefreshToken
from .models import User

# ชื่อ cookie ที่เก็บ refresh token และ path ที่เบราว์เซอร์ยอมส่ง cookie นี้ไป (เฉพาะ /api/auth/)
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth/"


def issue_refresh_token(user: User) -> RefreshToken:
    """สร้าง refresh token ใหม่ให้ผู้ใช้ โดยใส่ role ปัจจุบันเป็น claim

    ตั้งใจไม่ใช้ RefreshToken.for_user เพราะมันบันทึกตัว token เต็ม ๆ ลงตาราง OutstandingToken
    ถ้าฐานข้อมูลรั่วจะได้ token ที่ยังใช้งานได้ไปด้วย — สร้างเองแล้ว token ที่ยังใช้อยู่จะไม่อยู่ในฐานข้อมูลเลย
    (จะถูกบันทึกเฉพาะตอนถูกเพิกถอนแล้ว ซึ่งใช้ไม่ได้อยู่แล้ว)
    access token ที่ได้จาก refresh.access_token จะคัดลอก claim (รวม role) ไปด้วย
    """
    refresh = RefreshToken()
    refresh[api_settings.USER_ID_CLAIM] = user.pk
    refresh["role"] = user.role
    return refresh


def load_refresh_token(raw_token: str) -> tuple[RefreshToken, User]:
    """ตรวจ refresh token ที่รับมา แล้วคืน (token, ผู้ใช้เจ้าของ)

    ตรวจลายเซ็น วันหมดอายุ ชนิดของ token และว่าถูกเพิกถอน (blacklist) แล้วหรือไม่ รวมทั้งผู้ใช้ต้องยังเปิดใช้งานอยู่
    """
    try:
        token = RefreshToken(raw_token)
    except TokenError as exc:
        raise InvalidRefreshToken from exc

    user_id = token.get(api_settings.USER_ID_CLAIM)
    user = User.objects.filter(pk=user_id, is_active=True).first() if user_id else None
    if user is None:
        raise InvalidRefreshToken
    return token, user


def set_refresh_cookie(response, refresh: RefreshToken) -> None:
    """ตั้ง cookie เก็บ refresh token

    httpOnly (โค้ดหน้าเว็บอ่านไม่ได้), SameSite=Lax, จำกัด path, Secure ตอน production
    """
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        str(refresh),
        max_age=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        httponly=True,
        # ตอน dev (DEBUG) ใช้ http ธรรมดาได้ แต่ production ต้องเป็น https เท่านั้น
        secure=not settings.DEBUG,
        samesite="Lax",
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response) -> None:
    """สั่งให้เบราว์เซอร์ลบ cookie refresh token"""
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH, samesite="Lax")
