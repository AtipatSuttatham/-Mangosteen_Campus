from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import UserAdminChangeForm, UserAdminCreationForm
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """หน้าจัดการผู้ใช้ใน Django admin (ใช้ชั่วคราวจนกว่าจะมีหน้าจัดการผู้ใช้จริงของ Admin)"""

    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    list_display = (
        "email",
        "student_or_staff_id",
        "first_name",
        "last_name",
        "role",
        "is_email_verified",
        "is_active",
    )
    list_filter = ("role", "is_email_verified", "is_active")
    search_fields = ("email", "student_or_staff_id", "first_name", "last_name")
    ordering = ("email",)
    # ฟิลด์ที่ระบบตั้งเอง แก้ในหน้านี้ไม่ได้
    readonly_fields = ("last_login", "date_joined", "created_at", "updated_at")
    # เลือกผู้สร้างด้วยช่องกรอก id แทน dropdown (ผู้ใช้อาจมีจำนวนมาก)
    raw_id_fields = ("created_by",)

    # หน้าแก้ไขผู้ใช้เดิม
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "ข้อมูลส่วนตัว",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "first_name_en",
                    "last_name_en",
                    "student_or_staff_id",
                    "avatar_url",
                )
            },
        ),
        ("บทบาทและสถานะ", {"fields": ("role", "is_email_verified", "is_active")}),
        (
            "สิทธิ์ Django admin",
            {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        (
            "ข้อมูลระบบ",
            {"fields": ("created_by", "last_login", "date_joined", "created_at", "updated_at")},
        ),
    )
    # หน้าเพิ่มผู้ใช้ใหม่ (usable_password = เลือกว่าจะตั้งรหัสผ่านตอนนี้หรือให้เจ้าของตั้งเอง)
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "student_or_staff_id",
                    "is_email_verified",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
