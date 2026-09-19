from .exceptions import EmailNotVerified, InvalidCredentials
from .models import User


def find_user_by_identifier(identifier: str) -> User | None:
    """หาผู้ใช้จากช่อง login ช่องเดียว: มีอักขระ @ = อีเมล, ไม่มี = รหัสนักศึกษา/พนักงาน

    - อีเมล: ไม่สนตัวพิมพ์เล็ก/ใหญ่ (ในฐานข้อมูลเก็บเป็นตัวพิมพ์เล็กเสมอ)
    - รหัส: แยกตัวพิมพ์เล็ก/ใหญ่ ตรงตามที่พิมพ์ (ตัดช่องว่างหัวท้ายให้)
    รหัสห้ามมี @ จึงไม่มีทางกำกวมว่าเป็นอีเมลหรือรหัส
    """
    identifier = identifier.strip()
    if "@" in identifier:
        return User.objects.filter(email=identifier.lower()).first()
    return User.objects.filter(student_or_staff_id=identifier).first()


def authenticate_identifier(identifier: str, password: str) -> User:
    """ตรวจรหัส/อีเมล + รหัสผ่าน แล้วคืนผู้ใช้ ถ้าไม่ผ่านจะโยน error

    - ไม่พบผู้ใช้ / รหัสผ่านผิด / บัญชีถูกปิด / ยังไม่มีรหัสผ่าน → InvalidCredentials (ข้อความเดียวกันหมด)
    - รหัสผ่านถูกและบัญชีเปิดอยู่ แต่ยังไม่ยืนยันอีเมล → EmailNotVerified
    """
    user = find_user_by_identifier(identifier)
    if user is None:
        # ไม่พบผู้ใช้ก็ต้องเสียเวลาแฮชรหัสผ่านเท่ากับกรณีที่พบ ไม่งั้นวัดเวลาตอบเพื่อเดาได้ว่ามีบัญชีหรือไม่
        User().set_password(password)
        raise InvalidCredentials

    if not user.check_password(password) or not user.is_active:
        raise InvalidCredentials

    if not user.is_email_verified:
        raise EmailNotVerified

    return user
