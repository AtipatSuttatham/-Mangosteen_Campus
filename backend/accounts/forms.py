from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import User


class UserAdminCreationForm(AdminUserCreationForm):
    """ฟอร์มสร้างผู้ใช้ในหน้า Django admin

    ใช้ AdminUserCreationForm เพราะเว้นรหัสผ่านได้ (ตัวเลือก "ไม่ใช้รหัสผ่านตอนนี้")
    ตรงกับ flow: Admin สร้างบัญชีก่อน แล้วเจ้าของกดลิงก์ตั้งรหัสผ่านเอง
    """

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "role",
            "student_or_staff_id",
            "is_email_verified",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # บัญชีที่ Admin สร้างถือว่ายืนยันอีเมลแล้วตั้งแต่สร้าง (docs/database-guide.md W2)
        self.fields["is_email_verified"].initial = True


class UserAdminChangeForm(UserChangeForm):
    """ฟอร์มแก้ไขผู้ใช้ในหน้า Django admin (แสดงทุกฟิลด์ตาม fieldsets ที่กำหนดใน admin.py)"""

    class Meta:
        model = User
        fields = "__all__"
