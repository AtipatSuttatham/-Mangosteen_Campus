import re

import pytest
from django.core import mail

from accounts.emails import (
    send_account_invite_email,
    send_password_reset_email,
    send_verification_email,
)
from accounts.models import User

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres); pytest-django ใช้กล่องอีเมลจำลอง (mail.outbox) ให้เอง
pytestmark = pytest.mark.django_db

TOKEN = "abc-DEF_123"


@pytest.fixture(autouse=True)
def frontend_url(settings):
    """ทุก test ใช้ที่อยู่เว็บสมมติเดียวกัน (ไม่ขึ้นกับค่าในเครื่องที่รัน)"""
    settings.FRONTEND_URL = "https://campus.example.ac.th"


@pytest.fixture
def user():
    return User.objects.create_user(
        email="student@example.com", password="Str0ng-pass-123", first_name="มานี", last_name="ใจดี"
    )


class TestVerificationEmail:
    def test_goes_to_the_user_with_a_working_link(self, user):
        send_verification_email(user, TOKEN)

        message = mail.outbox[0]
        assert message.to == ["student@example.com"]
        assert "https://campus.example.ac.th/verify-email?token=abc-DEF_123" in message.body

    def test_contains_both_thai_and_english_and_the_lifetime(self, user):
        send_verification_email(user, TOKEN)

        message = mail.outbox[0]
        assert "สวัสดี มานี" in message.body
        assert "Hello มานี" in message.body
        assert "24 ชั่วโมง" in message.body
        assert "24 hours" in message.body
        assert "Verify your email" in message.subject
        assert "ยืนยันอีเมล" in message.subject


class TestAccountInviteEmail:
    def test_goes_to_the_user_with_a_link_to_the_set_password_page(self, user):
        send_account_invite_email(user, TOKEN)

        message = mail.outbox[0]
        assert message.to == ["student@example.com"]
        assert "https://campus.example.ac.th/reset-password?token=abc-DEF_123" in message.body

    def test_says_seven_days_in_both_languages(self, user):
        send_account_invite_email(user, TOKEN)

        body = mail.outbox[0].body
        assert "หมดอายุใน 7 วัน" in body
        assert "expires in 7 days" in body
        # ต้องไม่ขึ้นเป็นชั่วโมง (7 วัน = 168 ชั่วโมง อ่านยาก)
        assert "168" not in body

    def test_is_addressed_to_the_person_and_says_an_admin_created_the_account(self, user):
        send_account_invite_email(user, TOKEN)

        message = mail.outbox[0]
        assert "สวัสดี มานี" in message.body
        assert "Hello มานี" in message.body
        assert "ผู้ดูแลระบบสร้างบัญชี" in message.body
        assert "An administrator has created" in message.body
        assert "ตั้งรหัสผ่านเพื่อเริ่มใช้งาน" in message.subject
        assert "Your account is ready" in message.subject

    def test_existing_emails_still_say_hours(self, user):
        # เพิ่ม days เข้าเทมเพลตแล้ว อีเมลเดิม (ชั่วโมง) ต้องไม่เปลี่ยน
        send_verification_email(user, TOKEN)
        send_password_reset_email(user, TOKEN)

        assert "24 ชั่วโมง" in mail.outbox[0].body
        assert "1 ชั่วโมง" in mail.outbox[1].body


class TestPasswordResetEmail:
    def test_goes_to_the_user_with_a_working_link(self, user):
        send_password_reset_email(user, TOKEN)

        message = mail.outbox[0]
        assert message.to == ["student@example.com"]
        assert "https://campus.example.ac.th/reset-password?token=abc-DEF_123" in message.body

    def test_says_one_hour_in_both_languages(self, user):
        send_password_reset_email(user, TOKEN)

        message = mail.outbox[0]
        assert "1 ชั่วโมง" in message.body
        # ภาษาอังกฤษต้องเป็นเอกพจน์ "1 hour" ไม่ใช่ "1 hours"
        assert "1 hour." in message.body
        assert "1 hours" not in message.body


def test_link_is_built_from_frontend_url_in_settings(user, settings):
    # ลิงก์ = FRONTEND_URL + path + โทเคน (การตัด / ท้ายของ FRONTEND_URL ทำใน settings.py ตอนอ่านค่า)
    settings.FRONTEND_URL = "http://localhost:5180"

    send_verification_email(user, TOKEN)

    link = re.search(r"http\S+", mail.outbox[0].body).group()
    assert link == "http://localhost:5180/verify-email?token=abc-DEF_123"


def test_names_with_special_characters_are_not_html_escaped(user):
    # อีเมลเป็นข้อความล้วน — ชื่อที่มี & หรือ < ต้องแสดงตามจริง ไม่กลายเป็น &amp; / &lt;
    user.first_name = "Tom & <Jerry>"
    user.save()

    send_verification_email(user, TOKEN)

    body = mail.outbox[0].body
    assert "Tom & <Jerry>" in body
    assert "&amp;" not in body
    assert "&lt;" not in body
