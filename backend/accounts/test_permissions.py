from types import SimpleNamespace

import pytest
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from .models import User
from .permissions import IsAdminRole
from .roles import Role
from .tokens import issue_refresh_token

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres)
pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"


class AdminOnlyView(APIView):
    """view ทดสอบที่ใช้ IsAdminRole เท่านั้น (ใช้ตัวยืนยันตัวตนตาม settings คือ JWT จริง)"""

    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response({"ok": True})


factory = APIRequestFactory()
view = AdminOnlyView.as_view()


def make_user(role, email=None):
    return User.objects.create_user(
        email=email or f"{role}@example.com",
        password=PASSWORD,
        first_name="สมชาย",
        last_name="ใจดี",
        role=role,
    )


def call(user=None, token=None):
    """เรียก view ด้วย access token ของ user (หรือ token ที่ระบุ) — ไม่ใส่อะไรเลย = ไม่ล็อกอิน"""
    extra = {}
    if user is not None:
        token = str(issue_refresh_token(user).access_token)
    if token is not None:
        extra["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return view(factory.get("/admin-only/", **extra))


class TestIsAdminRole:
    def test_admin_is_allowed(self):
        response = call(make_user(Role.ADMIN))

        assert response.status_code == 200

    @pytest.mark.parametrize("role", [Role.TEACHER, Role.STUDENT])
    def test_other_roles_get_403_with_code(self, role):
        response = call(make_user(role))

        assert response.status_code == 403
        assert response.data["code"] == "permission_denied"

    def test_anonymous_gets_401(self):
        response = call()

        assert response.status_code == 401

    def test_invalid_token_gets_401(self):
        response = call(token="not-a-real-token")

        assert response.status_code == 401

    def test_demoted_admin_with_old_token_is_denied(self):
        # token ออกตอนเป็น admin (role ใน token = admin) แต่ตอนนี้ฐานข้อมูลบอกว่าเป็นผู้เรียนแล้ว
        # ต้องโดนปฏิเสธทันที ไม่ต้องรอ token หมดอายุ — พิสูจน์ว่าไม่เชื่อ role ใน token
        admin = make_user(Role.ADMIN)
        token = str(issue_refresh_token(admin).access_token)
        User.objects.filter(pk=admin.pk).update(role=Role.STUDENT)

        response = call(token=token)

        assert response.status_code == 403

    def test_promoted_user_with_old_token_is_allowed(self):
        # กลับด้านของข้อบน: token ออกตอนเป็นผู้เรียน แต่ฐานข้อมูลบอกว่าเป็น admin แล้ว ผ่านตามฐานข้อมูล
        student = make_user(Role.STUDENT)
        token = str(issue_refresh_token(student).access_token)
        User.objects.filter(pk=student.pk).update(role=Role.ADMIN)

        response = call(token=token)

        assert response.status_code == 200

    def test_deactivated_admin_is_denied(self):
        admin = make_user(Role.ADMIN)
        token = str(issue_refresh_token(admin).access_token)
        User.objects.filter(pk=admin.pk).update(is_active=False)

        response = call(token=token)

        assert response.status_code == 401

    def test_permission_itself_rejects_inactive_admin(self):
        # ผ่าน API จะไม่มีทางถึงจุดนี้ (ตัวยืนยันตัวตนตัดบัญชีที่ปิดไปก่อน) แต่ตัวตรวจสิทธิ์ตั้งใจตรวจซ้ำ
        # เป็นชั้นป้องกันที่ไม่พึ่งพฤติกรรมของชั้นอื่น จึงทดสอบเรียกตรง ๆ ไม่ผ่านตัวยืนยันตัวตน
        inactive_admin = User(email="off@example.com", role=Role.ADMIN, is_active=False)

        assert IsAdminRole().has_permission(SimpleNamespace(user=inactive_admin), None) is False
