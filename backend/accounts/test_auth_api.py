import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from accounts.roles import Role
from accounts.tokens import REFRESH_COOKIE_NAME

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres)
pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"
LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/refresh/"
LOGOUT_URL = "/api/auth/logout/"
ME_URL = "/api/auth/me/"
# header ที่ frontend ต้องส่งทุกครั้งที่เรียก refresh / logout (ดู MissingRequestedWithHeader)
XHR = {"HTTP_X_REQUESTED_WITH": "fetch"}


def make_user(email="teacher@example.com", **extra):
    """สร้างผู้ใช้ที่ยืนยันอีเมลแล้ว (ระบุเฉพาะส่วนที่ต่างในแต่ละ test)"""
    extra.setdefault("is_email_verified", True)
    return User.objects.create_user(
        email=email, password=PASSWORD, first_name="สมชาย", last_name="ใจดี", **extra
    )


def login(client, identifier="teacher@example.com", password=PASSWORD):
    return client.post(LOGIN_URL, {"identifier": identifier, "password": password}, format="json")


@pytest.fixture
def client():
    return APIClient()


class TestLogin:
    def test_login_with_email_ignores_case_and_spaces(self, client):
        make_user(role=Role.TEACHER)

        response = login(client, identifier="  Teacher@EXAMPLE.com ")

        assert response.status_code == 200
        assert response.json()["user"]["email"] == "teacher@example.com"
        assert response.json()["user"]["role"] == Role.TEACHER

    def test_login_with_staff_id(self, client):
        make_user(student_or_staff_id="T0042")

        response = login(client, identifier=" T0042 ")

        assert response.status_code == 200
        assert response.json()["user"]["student_or_staff_id"] == "T0042"

    def test_staff_id_is_case_sensitive(self, client):
        make_user(student_or_staff_id="T0042")

        response = login(client, identifier="t0042")

        assert response.status_code == 401
        assert response.json()["code"] == "invalid_credentials"

    def test_access_token_carries_role_and_user_id(self, client):
        user = make_user(role=Role.TEACHER)

        access = AccessToken(login(client).json()["access"])

        assert access["role"] == Role.TEACHER
        assert access["user_id"] == user.pk

    def test_refresh_token_is_stored_in_httponly_cookie_not_in_body(self, client):
        make_user()

        response = login(client)

        cookie = response.cookies[REFRESH_COOKIE_NAME]
        assert cookie.value
        assert cookie["httponly"]
        assert cookie["samesite"] == "Lax"
        assert cookie["path"] == "/api/auth/"
        assert cookie["max-age"] == 7 * 24 * 60 * 60
        # ตัว refresh token ต้องไม่อยู่ในเนื้อหาที่โค้ดหน้าเว็บอ่านได้
        assert "refresh" not in response.json()
        assert cookie.value not in response.content.decode()

    def test_cookie_is_secure_unless_debug(self, client, settings):
        make_user()

        settings.DEBUG = False
        assert login(client).cookies[REFRESH_COOKIE_NAME]["secure"]

        settings.DEBUG = True
        assert not login(client).cookies[REFRESH_COOKIE_NAME]["secure"]

    def test_login_response_is_not_cacheable(self, client):
        make_user()

        assert login(client)["Cache-Control"] == "no-store"

    def test_login_updates_last_login(self, client):
        user = make_user()
        assert user.last_login is None

        login(client)

        user.refresh_from_db()
        assert user.last_login is not None

    def test_login_does_not_store_live_refresh_token_in_database(self, client):
        # ตาราง OutstandingToken เก็บ token เต็ม ๆ — ต้องไม่มี token ที่ยังใช้งานได้อยู่ในนั้น
        make_user()

        login(client)

        assert OutstandingToken.objects.count() == 0

    def test_user_payload_has_no_secrets(self, client):
        make_user()

        payload = login(client).json()["user"]

        assert "password" not in payload
        assert "is_superuser" not in payload
        assert set(payload) == {
            "id",
            "email",
            "student_or_staff_id",
            "role",
            "first_name",
            "last_name",
            "first_name_en",
            "last_name_en",
            "is_email_verified",
            "avatar_url",
        }


class TestLoginFailures:
    def test_wrong_password_and_unknown_user_look_identical(self, client):
        make_user()

        wrong_password = login(client, password="wrong-password")
        unknown_user = login(client, identifier="nobody@example.com")

        assert wrong_password.status_code == unknown_user.status_code == 401
        assert wrong_password.json() == unknown_user.json()
        assert wrong_password.json()["code"] == "invalid_credentials"

    def test_unverified_email_is_reported_only_with_correct_password(self, client):
        make_user(email="new@example.com", is_email_verified=False)

        correct = login(client, identifier="new@example.com")
        wrong = login(client, identifier="new@example.com", password="wrong-password")

        assert correct.status_code == 403
        assert correct.json()["code"] == "email_not_verified"
        # รหัสผ่านผิดต้องไม่บอกว่าบัญชีนี้มีอยู่และยังไม่ยืนยัน
        assert wrong.status_code == 401
        assert wrong.json()["code"] == "invalid_credentials"
        assert REFRESH_COOKIE_NAME not in correct.cookies

    def test_inactive_user_gets_generic_error(self, client):
        make_user(is_active=False)

        response = login(client)

        assert response.status_code == 401
        assert response.json()["code"] == "invalid_credentials"

    def test_user_without_password_cannot_login(self, client):
        # บัญชีที่ Admin สร้างให้ยังไม่ได้ตั้งรหัสผ่าน
        User.objects.create_user(email="pending@example.com", password=None, is_email_verified=True)

        response = login(client, identifier="pending@example.com", password="anything")

        assert response.status_code == 401
        assert response.json()["code"] == "invalid_credentials"

    def test_missing_fields_are_validation_errors(self, client):
        response = client.post(LOGIN_URL, {}, format="json")

        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"
        assert set(response.json()["errors"]) == {"identifier", "password"}

    def test_failed_login_sets_no_cookie(self, client):
        make_user()

        response = login(client, password="wrong-password")

        assert REFRESH_COOKIE_NAME not in response.cookies


class TestMe:
    def test_returns_current_user(self, client):
        make_user(role=Role.TEACHER)
        access = login(client).json()["access"]

        response = client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {access}")

        assert response.status_code == 200
        assert response.json()["email"] == "teacher@example.com"

    def test_requires_token(self, client):
        response = client.get(ME_URL)

        assert response.status_code == 401
        assert response.json()["code"] == "not_authenticated"

    def test_rejects_invalid_token(self, client):
        response = client.get(ME_URL, HTTP_AUTHORIZATION="Bearer not-a-real-token")

        assert response.status_code == 401
        assert response.json()["code"] == "token_not_valid"

    def test_rejects_refresh_token_used_as_access_token(self, client):
        make_user()
        refresh_value = login(client).cookies[REFRESH_COOKIE_NAME].value

        response = client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {refresh_value}")

        assert response.status_code == 401

    def test_deactivated_user_loses_access_immediately(self, client):
        user = make_user()
        access = login(client).json()["access"]
        user.is_active = False
        user.save()

        response = client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {access}")

        assert response.status_code == 401


class TestRefresh:
    def test_requires_requested_with_header(self, client):
        make_user()
        login(client)

        response = client.post(REFRESH_URL)

        assert response.status_code == 403
        assert response.json()["code"] == "missing_requested_with_header"

    def test_without_cookie_is_rejected(self, client):
        response = client.post(REFRESH_URL, **XHR)

        assert response.status_code == 401
        assert response.json()["code"] == "invalid_refresh_token"

    def test_returns_new_access_token_and_rotates_cookie(self, client):
        make_user()
        first = login(client)
        first_cookie = first.cookies[REFRESH_COOKIE_NAME].value

        response = client.post(REFRESH_URL, **XHR)

        assert response.status_code == 200
        assert response.json()["access"]
        new_cookie = response.cookies[REFRESH_COOKIE_NAME].value
        assert new_cookie and new_cookie != first_cookie
        assert response["Cache-Control"] == "no-store"

    def test_new_access_token_works(self, client):
        make_user()
        login(client)

        access = client.post(REFRESH_URL, **XHR).json()["access"]

        assert client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {access}").status_code == 200

    def test_used_refresh_token_cannot_be_reused(self, client):
        make_user()
        old_cookie = login(client).cookies[REFRESH_COOKIE_NAME].value
        client.post(REFRESH_URL, **XHR)

        # ผู้โจมตีที่ขโมยใบเก่าไว้ ใช้หลังจากผู้ใช้จริงแลกไปแล้วไม่ได้
        client.cookies[REFRESH_COOKIE_NAME] = old_cookie
        response = client.post(REFRESH_URL, **XHR)

        assert response.status_code == 401
        assert response.json()["code"] == "invalid_refresh_token"

    def test_role_change_takes_effect_on_next_refresh(self, client):
        user = make_user(role=Role.TEACHER)
        login(client)
        user.role = Role.STUDENT
        user.save()

        response = client.post(REFRESH_URL, **XHR)

        assert AccessToken(response.json()["access"])["role"] == Role.STUDENT
        assert response.json()["user"]["role"] == Role.STUDENT

    def test_deactivated_user_cannot_refresh_and_cookie_is_cleared(self, client):
        user = make_user()
        login(client)
        user.is_active = False
        user.save()

        response = client.post(REFRESH_URL, **XHR)

        assert response.status_code == 401
        cleared = response.cookies[REFRESH_COOKIE_NAME]
        assert cleared.value == ""
        assert cleared["max-age"] == 0

    def test_garbage_cookie_is_rejected(self, client):
        client.cookies[REFRESH_COOKIE_NAME] = "garbage"

        response = client.post(REFRESH_URL, **XHR)

        assert response.status_code == 401
        assert response.json()["code"] == "invalid_refresh_token"

    def test_live_refresh_token_is_never_stored_in_database(self, client):
        make_user()
        login(client)

        response = client.post(REFRESH_URL, **XHR)

        # ในฐานข้อมูลมีเฉพาะใบเก่าที่ถูกเพิกถอนแล้ว ใบใหม่ที่ยังใช้งานได้ต้องไม่อยู่ที่นั่น
        live_cookie = response.cookies[REFRESH_COOKIE_NAME].value
        stored = OutstandingToken.objects.get()
        assert live_cookie != stored.token
        assert BlacklistedToken.objects.filter(token=stored).exists()


class TestLogout:
    def test_requires_requested_with_header(self, client):
        response = client.post(LOGOUT_URL)

        assert response.status_code == 403
        assert response.json()["code"] == "missing_requested_with_header"

    def test_revokes_refresh_token_and_clears_cookie(self, client):
        make_user()
        cookie_value = login(client).cookies[REFRESH_COOKIE_NAME].value

        response = client.post(LOGOUT_URL, **XHR)

        assert response.status_code == 204
        assert response.cookies[REFRESH_COOKIE_NAME]["max-age"] == 0
        # ต่อให้มีคนถือใบแลกเดิมไว้ ก็ใช้ต่อไม่ได้แล้ว
        client.cookies[REFRESH_COOKIE_NAME] = cookie_value
        assert client.post(REFRESH_URL, **XHR).status_code == 401

    def test_is_safe_to_call_without_cookie(self, client):
        response = client.post(LOGOUT_URL, **XHR)

        assert response.status_code == 204

    def test_is_safe_to_call_with_garbage_cookie(self, client):
        client.cookies[REFRESH_COOKIE_NAME] = "garbage"

        response = client.post(LOGOUT_URL, **XHR)

        assert response.status_code == 204
