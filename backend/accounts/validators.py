from django.core.exceptions import ValidationError


def validate_staff_id(value: str) -> None:
    """ตรวจรหัสนักศึกษา/พนักงาน: ห้ามมีอักขระ @

    หน้า login ช่องเดียวใช้ @ แยกอีเมลออกจากรหัส (มี @ = อีเมล) ถ้ารหัสมี @ ระบบจะเข้าใจผิดว่าเป็นอีเมล
    """
    if "@" in value:
        raise ValidationError(
            "รหัสห้ามมีเครื่องหมาย @",
            code="staff_id_contains_at_sign",
        )
