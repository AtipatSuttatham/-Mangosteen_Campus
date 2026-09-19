from django.contrib.auth.models import BaseUserManager

from .roles import Role


class UserManager(BaseUserManager):
    """ตัวสร้างผู้ใช้ — ใช้อีเมลเป็นตัวระบุตัวตนหลักแทน username"""

    # ให้ migration เก็บ manager นี้ไว้ด้วย (จำเป็นกับโมเดลผู้ใช้แบบกำหนดเอง)
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("ต้องระบุอีเมล")
        user = self.model(email=email, **extra_fields)
        # password=None จะตั้งเป็น "ยังไม่มีรหัสผ่าน" — ใช้กับบัญชีที่ Admin สร้างให้ก่อนเจ้าของกดลิงก์ตั้งรหัส
        user.set_password(password)
        # การ normalize อีเมล/รหัสทำใน User.save()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """สร้างผู้ใช้ทั่วไป (ไม่มีสิทธิ์เข้า Django admin)"""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """สร้างผู้ดูแลระบบ (ใช้กับคำสั่ง createsuperuser) — บทบาท admin และถือว่ายืนยันอีเมลแล้ว"""
        extra_fields.setdefault("role", Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_email_verified", True)

        if extra_fields["is_staff"] is not True:
            raise ValueError("superuser ต้องตั้ง is_staff=True")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("superuser ต้องตั้ง is_superuser=True")
        return self._create_user(email, password, **extra_fields)
