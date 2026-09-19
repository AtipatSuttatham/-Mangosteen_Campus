import logging
import re
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from accounts import password_reset
from accounts.email_tokens import (
    RESET_PASSWORD_LIFETIME,
    VERIFY_EMAIL_LIFETIME,
    issue_token,
)
from accounts.models import EmailVerificationToken, TokenPurpose, User
from accounts.roles import Role
from accounts.tokens import PASSWORD_FINGERPRINT_CLAIM, REFRESH_COOKIE_NAME

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres); pytest-django ใช้กล่องอีเมลจำลอง (mail.outbox) ให้เอง
pytestmark = pytest.mark.django_db

FORGOT_URL = "/api/auth/forgot-password/"
CHECK_URL = "/api/auth/reset-password/check/"
RESET_URL = "/api/auth/reset-password/"
LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/refresh/"
ME_URL = "/api/auth/me/"
XHR = {"HTTP_X_REQUESTED_WITH": "fetch"}

OLD_PASSWORD = "Old-Str0ng-pass-1"
NEW_PASSWORD = "New-Str0ng-pass-2"


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user():
    """ผู้ใช้ที่ยืนยันอีเมลแล้ว (กรณีปกติของการลืมรหัสผ่าน)"""
    return User.objects.create_user(
        email="manee@example.com",
        password=OLD_PASSWORD,
        first_name="มานี",
        last_name="ใจดี",
        is_email_verified=True,
    )


def token_in(message) -> str:
    """ดึงโทเคนจากลิงก์ในอีเมล (เหมือนที่หน้าเว็บอ่านจาก URL)"""
    return re.search(r"token=([\w-]+)", message.body).group(1)


def age_tokens(seconds=61):
    """ทำให้โทเคนทุกใบดูเก่าลง เพื่อข้ามกฎรอ 60 วินาที โดยไม่ต้องรอจริง"""
    EmailVerificationToken.objects.update(created_at=timezone.now() - timedelta(seconds=seconds))


def forgot(client, email="manee@example.com"):
    return client.post(FORGOT_URL, {"email": email}, format="json")


def check(client, token):
    return client.post(CHECK_URL, {"token": token}, format="json")


def reset(client, token, password=NEW_PASSWORD):
    return client.post(RESET_URL, {"token": token, "password": password}, format="json")


def login(client, identifier="manee@example.com", password=OLD_PASSWORD):
    return client.post(LOGIN_URL, {"identifier": identifier, "password": password}, format="json")


def reset_link_token(user):
    """ออกโทเคนตั้งรหัสผ่านตรง ๆ (ข้ามขั้นขออีเมล) ใช้ใน test ที่สนใจแค่ขั้นตั้งรหัส"""
    return issue_token(user, TokenPurpose.RESET_PASSWORD, RESET_PASSWORD_LIFETIME)


class TestForgotPassword:
    def test_sends_a_reset_link_to_a_verified_account(self, client, user):
        response = forgot(client)

        assert response.status_code == 202
        assert response.json() == {}
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["manee@example.com"]
        assert "/reset-password?token=" in mail.outbox[0].body
        stored = EmailVerificationToken.objects.get()
        assert stored.purpose == TokenPurpose.RESET_PASSWORD
        # ลิงก์ลืมรหัสผ่านอายุ 1 ชั่วโมง
        assert abs((stored.expires_at - stored.created_at) - RESET_PASSWORD_LIFETIME) < timedelta(
            seconds=5
        )

    def test_the_link_in_the_email_really_resets_the_password(self, client, user):
        forgot(client)

        assert reset(client, token_in(mail.outbox[0])).status_code == 200
        assert login(client, password=NEW_PASSWORD).status_code == 200

    def test_email_case_and_spaces_do_not_matter(self, client, user):
        forgot(client, email="  MANEE@Example.com ")

        assert len(mail.outbox) == 1

    def test_answers_identically_whether_or_not_a_link_is_sent(self, client, user):
        User.objects.create_user(
            email="pending@example.com", password=OLD_PASSWORD, first_name="ก", last_name="ข"
        )  # ยังไม่ยืนยันอีเมล
        User.objects.create_user(
            email="disabled@example.com",
            password=OLD_PASSWORD,
            first_name="ค",
            last_name="ง",
            is_email_verified=True,
            is_active=False,
        )

        answers = [
            forgot(client, email="manee@example.com"),  # ส่งจริง
            forgot(client, email="nobody@example.com"),  # ไม่มีในระบบ
            forgot(client, email="pending@example.com"),  # ยังไม่ยืนยันอีเมล
            forgot(client, email="disabled@example.com"),  # ถูกปิด
            forgot(client, email="manee@example.com"),  # ซ้ำภายใน 60 วินาที
        ]

        assert {(r.status_code, r.content) for r in answers} == {(202, b"{}")}
        # ส่งจริงฉบับเดียว ให้บัญชีที่ยืนยันแล้วและเปิดอยู่
        assert [m.to for m in mail.outbox] == [["manee@example.com"]]

    def test_second_request_within_60_seconds_sends_nothing(self, client, user):
        forgot(client)
        forgot(client)

        assert len(mail.outbox) == 1

    def test_after_60_seconds_a_new_link_replaces_the_old_one(self, client, user):
        forgot(client)
        old_token = token_in(mail.outbox[0])
        age_tokens()

        forgot(client)

        assert len(mail.outbox) == 2
        assert reset(client, old_token).json()["code"] == "token_invalid"
        assert reset(client, token_in(mail.outbox[1])).status_code == 200

    def test_a_pending_verification_link_does_not_block_a_reset_request(self, client, user):
        # cooldown แยกตามจุดประสงค์: ขอลิงก์ยืนยันอีเมลไว้ ไม่กระทบการขอลิงก์ตั้งรหัสผ่าน
        issue_token(user, TokenPurpose.VERIFY_EMAIL, VERIFY_EMAIL_LIFETIME)

        forgot(client)

        assert len(mail.outbox) == 1

    def test_admin_created_account_without_a_password_can_set_its_first_password(self, client):
        teacher = User.objects.create_user(
            email="teacher@example.com",
            password=None,
            role=Role.TEACHER,
            student_or_staff_id="T0042",
            first_name="อาจารย์",
            last_name="ผู้สอน",
            is_email_verified=True,
        )
        assert login(client, identifier="T0042", password="anything").status_code == 401

        forgot(client, email="teacher@example.com")
        reset(client, token_in(mail.outbox[0]), password="Teacher-Str0ng-9")

        response = login(client, identifier="T0042", password="Teacher-Str0ng-9")
        assert response.status_code == 200
        teacher.refresh_from_db()
        assert teacher.role == Role.TEACHER

    @pytest.mark.parametrize("body", [{}, {"email": ""}, {"email": "not-an-email"}])
    def test_invalid_email_is_a_validation_error(self, client, body):
        response = client.post(FORGOT_URL, body, format="json")

        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"

    def test_still_accepts_the_request_when_sending_fails_and_logs_it(
        self, client, user, monkeypatch, caplog
    ):
        def broken(user, raw_token):
            raise RuntimeError("smtp down")

        monkeypatch.setattr(password_reset, "send_password_reset_email", broken)

        with caplog.at_level(logging.ERROR, logger="accounts.password_reset"):
            response = forgot(client)

        assert response.status_code == 202
        assert "ส่งอีเมลตั้งรหัสผ่านไม่สำเร็จ" in caplog.text

    def test_does_not_touch_the_current_password(self, client, user):
        forgot(client)

        user.refresh_from_db()
        assert user.check_password(OLD_PASSWORD)
        assert login(client).status_code == 200


class TestCheckResetLink:
    def test_valid_link_shows_the_account_and_is_not_consumed(self, client, user):
        token = reset_link_token(user)

        first = check(client, token)
        second = check(client, token)

        assert first.status_code == 200
        assert first.json() == {"email": "manee@example.com"}
        assert second.status_code == 200
        # ตรวจกี่รอบก็ยังไม่ถูกใช้ทิ้ง — ตั้งรหัสได้ตามปกติ
        assert reset(client, token).status_code == 200

    def test_expired_link_is_reported_as_expired(self, client, user):
        token = reset_link_token(user)
        EmailVerificationToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

        response = check(client, token)

        assert response.status_code == 400
        assert response.json()["code"] == "token_expired"

    def test_used_link_is_invalid(self, client, user):
        token = reset_link_token(user)
        reset(client, token)

        assert check(client, token).json()["code"] == "token_invalid"

    @pytest.mark.parametrize("bad", ["garbage", "x" * 256, "abc' OR '1'='1"])
    def test_garbage_tokens_are_invalid(self, client, user, bad):
        reset_link_token(user)

        response = check(client, bad)

        assert response.status_code == 400
        assert response.json()["code"] == "token_invalid"

    @pytest.mark.parametrize("body", [{}, {"token": ""}, {"token": "   "}, {"token": "x" * 257}])
    def test_missing_or_oversized_token_is_a_validation_error(self, client, body):
        response = client.post(CHECK_URL, body, format="json")

        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"

    def test_an_email_verification_link_is_not_a_reset_link(self, client, user):
        verify_token = issue_token(user, TokenPurpose.VERIFY_EMAIL, VERIFY_EMAIL_LIFETIME)

        assert check(client, verify_token).json()["code"] == "token_invalid"

    def test_disabled_account_link_is_invalid(self, client, user):
        token = reset_link_token(user)
        user.is_active = False
        user.save()

        assert check(client, token).json()["code"] == "token_invalid"

    def test_get_is_not_allowed(self, client, user):
        token = reset_link_token(user)

        assert client.get(f"{CHECK_URL}?token={token}").status_code == 405


class TestResetPassword:
    def test_sets_the_new_password_and_the_old_one_stops_working(self, client, user):
        token = reset_link_token(user)

        response = reset(client, token)

        assert response.status_code == 200
        assert response.json() == {}
        assert login(client, password=OLD_PASSWORD).status_code == 401
        assert login(client, password=NEW_PASSWORD).status_code == 200

    def test_does_not_log_the_user_in(self, client, user):
        response = reset(client, reset_link_token(user))

        assert REFRESH_COOKIE_NAME not in response.cookies
        assert "access" not in response.json()

    def test_link_works_only_once(self, client, user):
        token = reset_link_token(user)
        reset(client, token)

        again = reset(client, token, password="Third-Str0ng-pass-3")

        assert again.status_code == 400
        assert again.json()["code"] == "token_invalid"
        # รหัสผ่านยังเป็นของรอบแรก
        assert login(client, password=NEW_PASSWORD).status_code == 200

    def test_expired_link_is_rejected_and_the_password_is_unchanged(self, client, user):
        token = reset_link_token(user)
        EmailVerificationToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

        response = reset(client, token)

        assert response.json()["code"] == "token_expired"
        assert login(client, password=OLD_PASSWORD).status_code == 200

    @pytest.mark.parametrize(
        ("password", "expected_code"),
        [
            ("Ab1!", "password_too_short"),
            ("password1234", "password_too_common"),
            ("83920175", "password_entirely_numeric"),
            # เกือบเหมือนอีเมลของเจ้าของบัญชี (ตัวตรวจต้องรู้ผู้ใช้จากโทเคน)
            ("manee@example.cm", "password_too_similar"),
        ],
    )
    def test_weak_password_is_rejected_with_a_code_per_rule(
        self, client, user, password, expected_code
    ):
        token = reset_link_token(user)

        response = reset(client, token, password=password)

        assert response.status_code == 400
        body = response.json()
        assert body["code"] == "validation_error"
        assert expected_code in body["error_codes"]["password"]
        assert login(client, password=OLD_PASSWORD).status_code == 200

    def test_a_rejected_weak_password_does_not_burn_the_link(self, client, user):
        token = reset_link_token(user)

        assert reset(client, token, password="12345678").status_code == 400

        # ลิงก์เดิมยังใช้ได้ กรอกรหัสที่ดีกว่าแล้วผ่าน
        assert check(client, token).status_code == 200
        assert reset(client, token, password=NEW_PASSWORD).status_code == 200

    def test_a_bad_link_is_reported_before_the_password_is_judged(self, client, user):
        # โทเคนมั่ว + รหัสอ่อน → บอกแค่ว่าลิงก์ใช้ไม่ได้ (ไม่ให้ลองกฎรหัสผ่านโดยไม่มีลิงก์จริง)
        response = reset(client, "garbage", password="12345678")

        assert response.json()["code"] == "token_invalid"

    @pytest.mark.parametrize(
        "body",
        [
            {"password": NEW_PASSWORD},
            {"token": "abc"},
            {"token": "abc", "password": ""},
            {"token": "abc", "password": "x" * 1025},
        ],
    )
    def test_missing_or_oversized_fields_are_validation_errors(self, client, body):
        response = client.post(RESET_URL, body, format="json")

        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"

    def test_password_with_spaces_is_kept_exactly(self, client, user):
        reset(client, reset_link_token(user), password="  spaced Str0ng pass  ")

        user.refresh_from_db()
        assert user.check_password("  spaced Str0ng pass  ")

    def test_an_email_verification_link_cannot_reset_a_password(self, client, user):
        verify_token = issue_token(user, TokenPurpose.VERIFY_EMAIL, VERIFY_EMAIL_LIFETIME)

        response = reset(client, verify_token)

        assert response.json()["code"] == "token_invalid"
        assert login(client, password=OLD_PASSWORD).status_code == 200

    def test_disabled_account_cannot_reset_and_the_link_is_not_consumed(self, client, user):
        token = reset_link_token(user)
        user.is_active = False
        user.save()

        response = reset(client, token)

        assert response.json()["code"] == "token_invalid"
        user.refresh_from_db()
        assert user.check_password(OLD_PASSWORD)
        assert EmailVerificationToken.objects.get().used_at is None

    def test_get_is_not_allowed(self, client, user):
        assert client.get(RESET_URL).status_code == 405

    def test_does_not_change_role_or_verification_status(self, client, user):
        reset(client, reset_link_token(user))

        user.refresh_from_db()
        assert user.role == Role.STUDENT
        assert user.is_email_verified is True
        assert user.is_active is True


class TestSessionsDieWhenThePasswordChanges:
    def logged_in_client(self):
        client = APIClient()
        response = login(client)
        assert response.status_code == 200
        return client, response.json()["access"]

    def test_old_refresh_cookie_stops_working_after_a_reset(self, user):
        client, _ = self.logged_in_client()
        # ก่อนเปลี่ยนรหัส แลก token ได้ตามปกติ (ยืนยันว่า test นี้ตั้งต้นถูก)
        assert client.post(REFRESH_URL, **XHR).status_code == 200

        reset(APIClient(), reset_link_token(user))

        response = client.post(REFRESH_URL, **XHR)
        assert response.status_code == 401
        assert response.json()["code"] == "invalid_refresh_token"
        # ระบบสั่งลบ cookie ที่ใช้ไม่ได้ให้ด้วย
        assert response.cookies[REFRESH_COOKIE_NAME].value == ""

    def test_every_device_is_signed_out_not_just_one(self, user):
        laptop, _ = self.logged_in_client()
        phone, _ = self.logged_in_client()

        reset(APIClient(), reset_link_token(user))

        assert laptop.post(REFRESH_URL, **XHR).status_code == 401
        assert phone.post(REFRESH_URL, **XHR).status_code == 401

    def test_logging_in_again_with_the_new_password_works_and_refreshes(self, user):
        reset(APIClient(), reset_link_token(user))
        client = APIClient()

        assert login(client, password=NEW_PASSWORD).status_code == 200
        assert client.post(REFRESH_URL, **XHR).status_code == 200

    def test_access_token_already_issued_lives_until_it_expires(self, user):
        # ข้อจำกัดที่บันทึกไว้ใน docs/api-auth.md: access token อายุสั้น (15 นาที) ยังใช้ได้จนหมดอายุ
        # แต่แลกต่ออายุไม่ได้แล้ว
        client, access = self.logged_in_client()
        reset(APIClient(), reset_link_token(user))

        response = APIClient().get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {access}")

        assert response.status_code == 200
        assert client.post(REFRESH_URL, **XHR).status_code == 401

    def test_any_password_change_kills_sessions_not_only_the_reset_flow(self, user):
        # เช่น Admin เปลี่ยนรหัสให้ในหน้า Django admin หรือฟีเจอร์เปลี่ยนรหัสในอนาคต
        client, _ = self.logged_in_client()

        user.set_password("Changed-By-Admin-77")
        user.save()

        assert client.post(REFRESH_URL, **XHR).status_code == 401

    def test_unrelated_saves_do_not_sign_anyone_out(self, user):
        client, _ = self.logged_in_client()

        user.first_name = "ชื่อใหม่"
        user.save()

        assert client.post(REFRESH_URL, **XHR).status_code == 200

    def test_refresh_token_without_the_fingerprint_claim_is_rejected(self, user):
        # token รูปแบบเก่า (ออกก่อนมีกลไกนี้) ต้องเข้าสู่ระบบใหม่
        old_style = RefreshToken()
        old_style[api_settings.USER_ID_CLAIM] = user.pk
        old_style["role"] = user.role
        client = APIClient()
        client.cookies[REFRESH_COOKIE_NAME] = str(old_style)

        assert client.post(REFRESH_URL, **XHR).status_code == 401

    def test_refresh_token_with_a_wrong_fingerprint_is_rejected(self, user):
        forged = RefreshToken()
        forged[api_settings.USER_ID_CLAIM] = user.pk
        forged["role"] = user.role
        forged[PASSWORD_FINGERPRINT_CLAIM] = "0" * 64
        client = APIClient()
        client.cookies[REFRESH_COOKIE_NAME] = str(forged)

        assert client.post(REFRESH_URL, **XHR).status_code == 401

    def test_the_fingerprint_is_not_copied_into_the_access_token(self, user):
        _, access = self.logged_in_client()

        payload = AccessToken(access).payload

        assert PASSWORD_FINGERPRINT_CLAIM not in payload
        # และไม่มีค่าที่มาจากแฮชรหัสผ่านหลุดไปในรูปแบบอื่น
        assert user.password not in str(payload)
        assert user.get_session_auth_hash() not in str(payload)
