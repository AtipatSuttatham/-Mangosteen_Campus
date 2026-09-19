import pytest
from django.core.management import call_command

from accounts.models import User
from accounts.roles import Role

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres)
pytestmark = pytest.mark.django_db


def test_changelist_page_loads(admin_client):
    response = admin_client.get("/admin/accounts/user/")

    assert response.status_code == 200


def test_add_page_loads(admin_client):
    response = admin_client.get("/admin/accounts/user/add/")

    assert response.status_code == 200


def test_admin_can_create_user_without_password(admin_client):
    """Admin สร้างบัญชีโดยไม่ตั้งรหัสผ่าน (เจ้าของบัญชีตั้งเองภายหลังผ่านลิงก์)"""
    response = admin_client.post(
        "/admin/accounts/user/add/",
        {
            "email": "New.User@Example.com",
            "first_name": "มานี",
            "last_name": "ใจตรง",
            "role": Role.STUDENT,
            "student_or_staff_id": " 650612001 ",
            "is_email_verified": "on",
            "usable_password": "false",
            "password1": "",
            "password2": "",
        },
    )

    assert response.status_code == 302
    user = User.objects.get(email="new.user@example.com")
    assert user.student_or_staff_id == "650612001"
    assert user.role == Role.STUDENT
    assert user.is_email_verified is True
    assert user.has_usable_password() is False


def test_createsuperuser_command_works_with_email_login(monkeypatch):
    """คำสั่ง createsuperuser ใช้กับ User แบบกำหนดเองได้ (ตัวระบุตัวตน = อีเมล)"""
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "Str0ng-pass-123")

    call_command(
        "createsuperuser",
        interactive=False,
        email="Root@Example.com",
        first_name="ราก",
        last_name="ระบบ",
    )

    user = User.objects.get(email="root@example.com")
    assert user.role == Role.ADMIN
    assert user.is_staff and user.is_superuser
    assert user.is_email_verified is True
    assert user.check_password("Str0ng-pass-123")
