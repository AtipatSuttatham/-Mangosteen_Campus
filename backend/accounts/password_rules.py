from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ErrorDetail

from .models import User


def password_rule_errors(password: str, user: User) -> list[ErrorDetail]:
    """ตรวจรหัสผ่านตามกฎของระบบ (AUTH_PASSWORD_VALIDATORS) แล้วคืนรายการข้อผิดพลาด (ว่าง = ผ่าน)

    ใช้ร่วมกันทั้งตอนสมัครและตอนตั้งรหัสผ่านใหม่ เพื่อให้กฎเหมือนกันเป๊ะ
    ส่งผู้ใช้เข้ามาด้วย เพื่อให้กฎ "ไม่คล้ายชื่อหรืออีเมลของคุณ" ตรวจกับข้อมูลของผู้ใช้จริง
    แต่ละข้อผิดพลาดมี code ของกฎ (เช่น password_too_short) ให้ frontend ใช้แปลข้อความรายกฎ
    """
    try:
        validate_password(password, user=user)
    except DjangoValidationError as error:
        return [ErrorDetail(item.messages[0], code=item.code) for item in error.error_list]
    return []
