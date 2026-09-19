import logging
import re
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from accounts import registration
from accounts.email_tokens import (
    RESET_PASSWORD_LIFETIME,
    VERIFY_EMAIL_LIFETIME,
    issue_token,
)
from accounts.models import EmailVerificationToken, TokenPurpose, User
from accounts.roles import Role

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres); pytest-django ใช้กล่องอีเมลจำลอง (mail.outbox) ให้เอง
pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/auth/register/"
VERIFY_URL = "/api/auth/verify-email/"
RESEND_URL = "/api/auth/resend-verification/"
LOGIN_URL = "/api/auth/login/"

PASSWORD = "Str0ng-pass-123"
OTHER_PASSWORD = "Another-Str0ng-456"


@pytest.fixture
def client():
    return APIClient()


def payload(**overrides):
    """ข้อมูลสมัครที่ถูกต้อง (ระบุเฉพาะส่วนที่ต่างในแต่ละ test)"""
    data = {
        "email": "manee@example.com",
        "password": PASSWORD,
        "first_name": "มานี",
        "last_name": "ใจดี",
    }
    data.update(overrides)
    return data


def register(client, **overrides):
    return client.post(REGISTER_URL, payload(**overrides), format="json")


def token_in(message) -> str:
    """ดึงโทเคนจากลิงก์ในอีเมล (เหมือนที่หน้าเว็บอ่านจาก URL)"""
    return re.search(r"token=([\w-]+)", message.body).group(1)


def age_tokens(seconds=61):
    """ทำให้โทเคนทุกใบดูเก่าลง เพื่อข้ามกฎรอ 60 วินาที โดยไม่ต้องรอจริง"""
    EmailVerificationToken.objects.update(created_at=timezone.now() - timedelta(seconds=seconds))


def login(client, identifier="manee@example.com", password=PASSWORD):
    return client.post(LOGIN_URL, {"identifier": identifier, "password": password}, format="json")


class TestRegister:
    def test_creates_an_unverified_student_and_sends_the_verification_link(self, client):
        response = register(client)

        assert response.status_code == 202
        user = User.objects.get(email="manee@example.com")
        assert user.role == Role.STUDENT
        assert user.is_email_verified is False
        assert user.is_active
        assert user.student_or_staff_id is None
        assert user.created_by is None
        assert (user.first_name, user.last_name) == ("มานี", "ใจดี")
        assert user.check_password(PASSWORD)
        # ส่งอีเมลยืนยัน 1 ฉบับถึงเจ้าของอีเมล และลิงก์ใช้ยืนยันได้จริง
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["manee@example.com"]
        assert (
            client.post(VERIFY_URL, {"token": token_in(mail.outbox[0])}, format="json").status_code
            == 200
        )

    def test_response_leaks_neither_token_nor_password(self, client):
        response = register(client)

        assert response.json() == {}
        assert PASSWORD not in response.content.decode()
        assert token_in(mail.outbox[0]) not in response.content.decode()

    def test_ignores_role_and_privilege_fields_sent_by_the_client(self, client):
        # กัน mass assignment: สมัครเองแล้วส่ง role=admin ต้องไม่ได้สิทธิ์เพิ่ม
        register(
            client,
            role="admin",
            is_staff=True,
            is_superuser=True,
            is_email_verified=True,
            is_active=True,
            student_or_staff_id="HACK001",
            created_by=1,
        )

        user = User.objects.get()
        assert user.role == Role.STUDENT
        assert not user.is_staff
        assert not user.is_superuser
        assert user.is_email_verified is False
        assert user.student_or_staff_id is None
        assert user.created_by is None

    def test_email_is_stored_lowercase_and_trimmed(self, client):
        register(client, email="  Manee@Example.COM ")

        assert User.objects.get().email == "manee@example.com"

    def test_names_are_trimmed(self, client):
        register(client, first_name="  มานี ", last_name=" ใจดี  ")

        user = User.objects.get()
        assert (user.first_name, user.last_name) == ("มานี", "ใจดี")

    @pytest.mark.parametrize(
        "overrides",
        [
            {"email": ""},
            {"email": "not-an-email"},
            {"email": "a" * 250 + "@example.com"},
            {"first_name": ""},
            {"first_name": "   "},
            {"first_name": "ก" * 151},
            {"last_name": ""},
            {"last_name": "ข" * 151},
            {"password": ""},
            {"password": "x" * 1025},
        ],
    )
    def test_rejects_invalid_fields_without_creating_anything(self, client, overrides):
        response = register(client, **overrides)

        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"
        assert User.objects.count() == 0
        assert mail.outbox == []

    @pytest.mark.parametrize("missing", ["email", "password", "first_name", "last_name"])
    def test_rejects_missing_fields(self, client, missing):
        data = payload()
        del data[missing]

        response = client.post(REGISTER_URL, data, format="json")

        assert response.status_code == 400
        assert missing in response.json()["errors"]
        assert User.objects.count() == 0

    @pytest.mark.parametrize(
        ("password", "expected_code"),
        [
            ("Ab1!", "password_too_short"),
            ("password1234", "password_too_common"),
            ("83920175", "password_entirely_numeric"),
            # เกือบเหมือนอีเมลของผู้สมัครเอง (ตัวตรวจต้องเห็นข้อมูลที่กรอกมา ไม่งั้นข้อนี้จะผ่านเข้ามาได้)
            ("manee.jaidee@example.cm", "password_too_similar"),
        ],
    )
    def test_weak_passwords_are_rejected_with_a_code_per_rule(
        self, client, password, expected_code
    ):
        response = register(client, email="manee.jaidee@example.com", password=password)

        assert response.status_code == 400
        body = response.json()
        assert body["code"] == "validation_error"
        assert expected_code in body["error_codes"]["password"]
        assert User.objects.count() == 0

    def test_password_and_other_field_errors_come_in_the_same_response(self, client):
        response = register(client, password="12345678", first_name="")

        errors = response.json()["errors"]
        assert "password" in errors
        assert "first_name" in errors

    def test_password_with_spaces_is_kept_exactly(self, client):
        register(client, password="  spaced Str0ng pass  ")

        assert User.objects.get().check_password("  spaced Str0ng pass  ")

    def test_registration_does_not_log_the_user_in(self, client):
        response = register(client)

        assert "refresh_token" not in response.cookies
        assert "access" not in response.json()


class TestRegisterExistingEmail:
    def test_verified_account_gets_email_taken_and_is_left_untouched(self, client):
        User.objects.create_user(
            email="manee@example.com",
            password=OTHER_PASSWORD,
            first_name="ตัวจริง",
            last_name="เดิม",
            is_email_verified=True,
        )

        response = register(client)

        assert response.status_code == 409
        assert response.json()["code"] == "email_taken"
        user = User.objects.get()
        assert user.check_password(OTHER_PASSWORD)
        assert user.first_name == "ตัวจริง"
        assert mail.outbox == []

    def test_admin_created_teacher_cannot_be_taken_over_by_registering(self, client):
        teacher = User.objects.create_user(
            email="manee@example.com",
            password=None,
            role=Role.TEACHER,
            student_or_staff_id="T0042",
            first_name="อาจารย์",
            last_name="ผู้สอน",
            is_email_verified=True,
        )

        response = register(client)

        assert response.status_code == 409
        teacher.refresh_from_db()
        assert teacher.role == Role.TEACHER
        assert not teacher.has_usable_password()

    def test_disabled_account_gets_email_taken(self, client):
        User.objects.create_user(
            email="manee@example.com",
            password=OTHER_PASSWORD,
            first_name="ถูก",
            last_name="ปิด",
            is_active=False,
        )

        response = register(client)

        assert response.status_code == 409
        assert User.objects.get().check_password(OTHER_PASSWORD)
        assert mail.outbox == []

    def test_email_case_does_not_bypass_the_check(self, client):
        User.objects.create_user(
            email="manee@example.com",
            password=OTHER_PASSWORD,
            first_name="ก",
            last_name="ข",
            is_email_verified=True,
        )

        response = register(client, email="MANEE@Example.com")

        assert response.status_code == 409


class TestRegisterAgainWhilePending:
    def test_overwrites_password_and_names_and_sends_a_fresh_link(self, client):
        register(client, first_name="เก่า", last_name="เก่า", password=PASSWORD)
        old_token = token_in(mail.outbox[0])
        age_tokens()

        response = register(client, first_name="ใหม่", last_name="ล่าสุด", password=OTHER_PASSWORD)

        assert response.status_code == 202
        user = User.objects.get()
        assert user.check_password(OTHER_PASSWORD)
        assert not user.check_password(PASSWORD)
        assert (user.first_name, user.last_name) == ("ใหม่", "ล่าสุด")
        assert len(mail.outbox) == 2
        # ลิงก์ฉบับแรกใช้ไม่ได้แล้ว ต้องใช้ฉบับใหม่
        assert (
            client.post(VERIFY_URL, {"token": old_token}, format="json").json()["code"]
            == "token_invalid"
        )
        assert (
            client.post(VERIFY_URL, {"token": token_in(mail.outbox[1])}, format="json").status_code
            == 200
        )

    def test_within_60_seconds_updates_the_data_but_sends_no_second_email(self, client):
        register(client, password=PASSWORD)

        register(client, password=OTHER_PASSWORD)

        assert len(mail.outbox) == 1
        assert User.objects.get().check_password(OTHER_PASSWORD)

    def test_pre_registering_someone_elses_email_gives_the_attacker_nothing(self, client):
        # คนร้ายสมัครด้วยอีเมลของเหยื่อ + รหัสของตัวเอง ก่อนเจ้าของอีเมลจะสมัคร
        register(client, password="Attacker-Pass-777")
        age_tokens()
        # เจ้าของอีเมลสมัครจริงทับ แล้วกดลิงก์ที่ได้
        register(client, password=OTHER_PASSWORD)
        client.post(VERIFY_URL, {"token": token_in(mail.outbox[-1])}, format="json")

        # รหัสของคนร้ายใช้เข้าไม่ได้ ส่วนเจ้าของเข้าได้
        assert login(client, password="Attacker-Pass-777").status_code == 401
        assert login(client, password=OTHER_PASSWORD).status_code == 200

    def test_a_simultaneous_registration_falls_back_to_overwriting(self, client, monkeypatch):
        # จำลองว่าอีกคำขอสร้างบัญชีตัดหน้าไปหลังเราค้นหาแล้วไม่พบ (ชน unique ตอนสร้าง)
        User.objects.create_user(
            email="manee@example.com", password=PASSWORD, first_name="ก", last_name="ข"
        )
        real_lock = registration._lock_user
        calls = []

        def lookup_misses_first_time(email):
            calls.append(email)
            return None if len(calls) == 1 else real_lock(email)

        monkeypatch.setattr(registration, "_lock_user", lookup_misses_first_time)

        response = register(client, password=OTHER_PASSWORD, first_name="ล่าสุด")

        assert response.status_code == 202
        user = User.objects.get()
        assert user.check_password(OTHER_PASSWORD)
        assert user.first_name == "ล่าสุด"


class TestRegisterThenLogin:
    def test_cannot_log_in_until_verified_then_can(self, client):
        register(client)

        blocked = login(client)
        assert blocked.status_code == 403
        assert blocked.json()["code"] == "email_not_verified"

        client.post(VERIFY_URL, {"token": token_in(mail.outbox[0])}, format="json")

        allowed = login(client)
        assert allowed.status_code == 200
        assert allowed.json()["user"]["role"] == "student"


class TestEmailFailure:
    def test_still_accepts_the_registration_when_sending_fails_and_logs_it(
        self, client, monkeypatch, caplog
    ):
        def broken(user, raw_token):
            raise RuntimeError("smtp down")

        monkeypatch.setattr(registration, "send_verification_email", broken)

        with caplog.at_level(logging.ERROR, logger="accounts.registration"):
            response = register(client)

        assert response.status_code == 202
        assert User.objects.filter(email="manee@example.com").exists()
        assert "ส่งอีเมลยืนยันไม่สำเร็จ" in caplog.text


class TestVerifyEmail:
    @pytest.fixture
    def pending(self, client):
        register(client)
        return User.objects.get(), token_in(mail.outbox[0])

    def test_valid_token_verifies_the_account(self, client, pending):
        user, token = pending

        response = client.post(VERIFY_URL, {"token": token}, format="json")

        assert response.status_code == 200
        assert response.json() == {"email_verified": True}
        user.refresh_from_db()
        assert user.is_email_verified is True

    def test_token_works_only_once(self, client, pending):
        _, token = pending
        client.post(VERIFY_URL, {"token": token}, format="json")

        again = client.post(VERIFY_URL, {"token": token}, format="json")

        assert again.status_code == 400
        assert again.json()["code"] == "token_invalid"

    def test_expired_token_is_reported_as_expired_and_does_not_verify(self, client, pending):
        user, token = pending
        EmailVerificationToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

        response = client.post(VERIFY_URL, {"token": token}, format="json")

        assert response.status_code == 400
        assert response.json()["code"] == "token_expired"
        user.refresh_from_db()
        assert user.is_email_verified is False

    @pytest.mark.parametrize("bad", ["garbage", "x" * 256, "abc' OR '1'='1"])
    def test_garbage_tokens_are_invalid(self, client, pending, bad):
        response = client.post(VERIFY_URL, {"token": bad}, format="json")

        assert response.status_code == 400
        assert response.json()["code"] == "token_invalid"

    @pytest.mark.parametrize("body", [{}, {"token": ""}, {"token": "   "}, {"token": "x" * 257}])
    def test_missing_or_oversized_token_is_a_validation_error(self, client, body):
        response = client.post(VERIFY_URL, body, format="json")

        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"

    def test_a_password_reset_link_cannot_verify_an_email(self, client, pending):
        user, _ = pending
        reset_token = issue_token(user, TokenPurpose.RESET_PASSWORD, RESET_PASSWORD_LIFETIME)

        response = client.post(VERIFY_URL, {"token": reset_token}, format="json")

        assert response.json()["code"] == "token_invalid"
        user.refresh_from_db()
        assert user.is_email_verified is False

    def test_disabled_account_cannot_verify_and_the_token_is_not_consumed(self, client, pending):
        user, token = pending
        user.is_active = False
        user.save()

        response = client.post(VERIFY_URL, {"token": token}, format="json")

        assert response.json()["code"] == "token_invalid"
        user.refresh_from_db()
        assert user.is_email_verified is False
        # ธุรกรรมย้อนกลับ: โทเคนยังไม่ถูกใช้ (ถ้า Admin เปิดบัญชีกลับ ลิงก์เดิมยังใช้ได้ถ้ายังไม่หมดอายุ)
        assert EmailVerificationToken.objects.get().used_at is None

    def test_get_does_not_verify(self, client, pending):
        # ลิงก์ถูกโปรแกรมสแกนอีเมลเปิดล่วงหน้าด้วย GET ได้ — ต้องไม่ทำให้ยืนยันหรือใช้โทเคนไป
        user, token = pending

        response = client.get(f"{VERIFY_URL}?token={token}")

        assert response.status_code == 405
        user.refresh_from_db()
        assert user.is_email_verified is False
        assert EmailVerificationToken.objects.get().used_at is None

    def test_verifying_needs_no_login(self, client, pending):
        _, token = pending

        # ไม่ส่ง Authorization และแนบ token เสียมา ก็ยังต้องผ่าน (ไม่ตรวจ token เดิม)
        client.credentials(HTTP_AUTHORIZATION="Bearer this.is.not.valid")
        response = client.post(VERIFY_URL, {"token": token}, format="json")

        assert response.status_code == 200


class TestResendVerification:
    @pytest.fixture
    def pending(self, client):
        register(client)
        age_tokens()
        mail.outbox.clear()
        return User.objects.get()

    def resend(self, client, email="manee@example.com"):
        return client.post(RESEND_URL, {"email": email}, format="json")

    def test_sends_a_new_link_and_cancels_the_old_one(self, client):
        register(client)
        old_token = token_in(mail.outbox[0])
        age_tokens()

        response = self.resend(client)

        assert response.status_code == 202
        assert len(mail.outbox) == 2
        new_token = token_in(mail.outbox[1])
        assert new_token != old_token
        assert (
            client.post(VERIFY_URL, {"token": old_token}, format="json").json()["code"]
            == "token_invalid"
        )
        assert client.post(VERIFY_URL, {"token": new_token}, format="json").status_code == 200

    def test_email_case_and_spaces_do_not_matter(self, client, pending):
        self.resend(client, email="  MANEE@Example.com ")

        assert len(mail.outbox) == 1

    def test_within_60_seconds_sends_nothing_but_still_answers_the_same(self, client):
        register(client)
        mail.outbox.clear()

        response = self.resend(client)

        assert response.status_code == 202
        assert mail.outbox == []

    def test_answers_identically_whether_or_not_the_email_can_receive_a_link(self, client, pending):
        User.objects.create_user(
            email="verified@example.com",
            password=PASSWORD,
            first_name="ก",
            last_name="ข",
            is_email_verified=True,
        )
        User.objects.create_user(
            email="disabled@example.com",
            password=PASSWORD,
            first_name="ค",
            last_name="ง",
            is_active=False,
        )

        answers = [
            self.resend(client, email="manee@example.com"),  # ส่งได้จริง
            self.resend(client, email="nobody@example.com"),  # ไม่มีในระบบ
            self.resend(client, email="verified@example.com"),  # ยืนยันแล้ว
            self.resend(client, email="disabled@example.com"),  # ถูกปิด
        ]

        assert {(r.status_code, r.content) for r in answers} == {(202, b"{}")}
        # ส่งจริงแค่ฉบับเดียว ให้บัญชีที่สมัครค้างอยู่
        assert [m.to for m in mail.outbox] == [["manee@example.com"]]

    def test_invalid_email_format_is_a_validation_error(self, client):
        response = self.resend(client, email="not-an-email")

        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"

    def test_missing_email_is_a_validation_error(self, client):
        response = client.post(RESEND_URL, {}, format="json")

        assert response.status_code == 400

    def test_does_not_touch_the_account_or_leak_the_token(self, client, pending):
        response = self.resend(client)

        pending.refresh_from_db()
        assert pending.check_password(PASSWORD)
        assert token_in(mail.outbox[0]) not in response.content.decode()

    def test_the_verification_link_lasts_24_hours(self, client):
        register(client)

        stored = EmailVerificationToken.objects.get()
        assert stored.purpose == TokenPurpose.VERIFY_EMAIL
        assert abs((stored.expires_at - stored.created_at) - VERIFY_EMAIL_LIFETIME) < timedelta(
            seconds=5
        )
