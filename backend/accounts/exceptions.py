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


class TokenInvalid(APIException):
    """โทเคนในลิงก์อีเมลใช้ไม่ได้: ไม่มีในระบบ / ใช้ไปแล้ว / ผิดจุดประสงค์"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "ลิงก์ไม่ถูกต้องหรือถูกใช้ไปแล้ว"
    default_code = "token_invalid"


class TokenExpired(APIException):
    """โทเคนในลิงก์อีเมลถูกต้อง แต่หมดอายุแล้ว — หน้าเว็บควรเสนอให้ขอลิงก์ใหม่"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "ลิงก์หมดอายุแล้ว"
    default_code = "token_expired"


class CannotDeactivateSelf(APIException):
    """Admin พยายามปิดใช้งานบัญชีของตัวเอง — ห้าม กันตัวเองล็อกตัวเองออกจากระบบ"""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "ปิดใช้งานบัญชีของตัวเองไม่ได้"
    default_code = "cannot_deactivate_self"


class CannotDemoteSelf(APIException):
    """Admin พยายามเปลี่ยนบทบาทของตัวเอง — ห้าม ให้ผู้ดูแลระบบคนอื่นทำแทน"""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "เปลี่ยนบทบาทของตัวเองไม่ได้"
    default_code = "cannot_demote_self"


class LastAdmin(APIException):
    """การกระทำนี้จะทำให้ไม่เหลือผู้ดูแลระบบที่ใช้งานอยู่เลย — ห้าม (ระบบต้องมี Admin อย่างน้อย 1 คนเสมอ)"""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "ต้องเหลือผู้ดูแลระบบที่ใช้งานอยู่อย่างน้อย 1 คน"
    default_code = "last_admin"


class InviteNotApplicable(APIException):
    """ส่งลิงก์ตั้งรหัสผ่านซ้ำได้เฉพาะบัญชีที่ Admin สร้างให้และเจ้าของยังไม่ตั้งรหัส (สถานะ pending_password)"""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "บัญชีนี้ไม่ได้อยู่ในสถานะรอตั้งรหัสผ่าน"
    default_code = "invite_not_applicable"


class ResendTooSoon(APIException):
    """ขอส่งลิงก์ใหม่เร็วกว่ากฎรอ 60 วินาที — บอกเวลาที่ต้องรอ (วินาที) ใน `wait`

    ไม่สืบทอดจาก Throttled ของ DRF เพราะมันต่อข้อความอังกฤษ "Expected available in N seconds" ท้าย detail
    ตัวจัดการ error กลางอ่าน `wait` แล้วใส่ header Retry-After และ `retry_after` ใน body ให้เอง
    """

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "ขอลิงก์ได้อีกครั้งเมื่อครบเวลารอ"
    default_code = "resend_too_soon"

    def __init__(self, wait: int):
        super().__init__()
        self.wait = wait


class EmailTaken(APIException):
    """สมัครด้วยอีเมลที่มีบัญชีใช้งานอยู่แล้ว (ยืนยันแล้ว หรือถูก Admin ปิดบัญชีไว้)

    บอกตรง ๆ ตามที่ผู้ใช้ตัดสินใจ (ตัวเลือก ก): ผู้สมัครรู้ทันทีว่าต้องเข้าสู่ระบบหรือกดลืมรหัสผ่านแทน
    แลกกับการที่คนนอกใช้หน้าสมัครไล่เช็กได้ว่าอีเมลไหนมีบัญชี (บันทึกใน docs/api-auth.md)
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "อีเมลนี้ถูกใช้สมัครแล้ว"
    default_code = "email_taken"
