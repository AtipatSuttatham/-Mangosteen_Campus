from rest_framework import status
from rest_framework.exceptions import APIException


class InvalidCredentials(APIException):
    """รหัส/อีเมล หรือรหัสผ่านไม่ถูกต้อง

    ตอบข้อความเดียวกันทุกกรณี (ไม่พบผู้ใช้ / รหัสผ่านผิด / บัญชีถูกปิด / ยังไม่มีรหัสผ่าน)
    เพื่อไม่ให้ใครใช้หน้า login เดาว่าอีเมลหรือรหัสไหนมีบัญชีอยู่จริง
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "ข้อมูลเข้าสู่ระบบไม่ถูกต้อง"
    default_code = "invalid_credentials"


class EmailNotVerified(APIException):
    """บัญชีถูกต้อง แต่ยังไม่ได้ยืนยันอีเมล (บอกเฉพาะเมื่อรหัสผ่านถูกต้องเท่านั้น)"""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "บัญชีนี้ยังไม่ได้ยืนยันอีเมล"
    default_code = "email_not_verified"


class InvalidRefreshToken(APIException):
    """refresh token ไม่มี / หมดอายุ / ถูกเพิกถอนแล้ว / ผู้ใช้ถูกปิด — ต้องเข้าสู่ระบบใหม่"""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "เซสชันหมดอายุหรือไม่ถูกต้อง กรุณาเข้าสู่ระบบใหม่"
    default_code = "invalid_refresh_token"


class MissingRequestedWithHeader(APIException):
    """คำขอที่ใช้ cookie (refresh / logout) ต้องมี header X-Requested-With เสมอ

    เว็บอื่นแอบส่งคำขอโดยพ่วง cookie ของผู้ใช้มาได้ แต่เพิ่ม header กำหนดเองข้ามเว็บไม่ได้ (เบราว์เซอร์
    ต้องขออนุญาต CORS ก่อน ซึ่งเราไม่เปิดให้) จึงใช้ header นี้แยกคำขอจริงจากเว็บของเราออกจากคำขอปลอม
    """

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "คำขอไม่ถูกต้อง"
    default_code = "missing_requested_with_header"
