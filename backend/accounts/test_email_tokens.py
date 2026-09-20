from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.email_tokens import (
    INVITE_LIFETIME,
    RESEND_COOLDOWN,
    RESET_PASSWORD_LIFETIME,
    VERIFY_EMAIL_LIFETIME,
    cancel_unused_tokens,
    consume_token,
    hash_token,
    issue_token,
    seconds_until_resend,
)
from accounts.exceptions import TokenExpired, TokenInvalid
from accounts.models import EmailVerificationToken, TokenPurpose, User

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres)
pytestmark = pytest.mark.django_db

VERIFY = TokenPurpose.VERIFY_EMAIL
RESET = TokenPurpose.RESET_PASSWORD


@pytest.fixture
def user():
    return User.objects.create_user(
        email="student@example.com", password="Str0ng-pass-123", first_name="มานี", last_name="ใจดี"
    )


class TestInviteLifetime:
    def test_invite_link_lives_seven_days(self):
        assert INVITE_LIFETIME == timedelta(days=7)

    def test_invite_uses_the_reset_password_purpose_with_a_longer_expiry(self, user):
        # ลิงก์ตั้งรหัสแรกที่ Admin ส่งใช้จุดประสงค์เดียวกับ "ลืมรหัสผ่าน" (ต่างกันที่อายุเท่านั้น)
        before = timezone.now()
        raw = issue_token(user, RESET, INVITE_LIFETIME)

        stored = EmailVerificationToken.objects.get()
        assert stored.purpose == RESET
        assert stored.expires_at >= before + timedelta(days=7)
        assert consume_token(raw, RESET) == user


class TestCancelUnusedTokens:
    def test_cancels_every_unused_link_of_every_purpose(self, user):
        verify = issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)
        reset = issue_token(user, RESET, RESET_PASSWORD_LIFETIME)

        cancel_unused_tokens(user)

        with pytest.raises(TokenInvalid):
            consume_token(verify, VERIFY)
        with pytest.raises(TokenInvalid):
            consume_token(reset, RESET)

    def test_does_not_touch_other_users(self, user):
        other = User.objects.create_user(
            email="other@example.com", password="Str0ng-pass-123", first_name="ก", last_name="ข"
        )
        others_token = issue_token(other, RESET, RESET_PASSWORD_LIFETIME)

        cancel_unused_tokens(user)

        assert consume_token(others_token, RESET) == other

    def test_keeps_the_original_used_time_of_already_used_links(self, user):
        raw = issue_token(user, RESET, RESET_PASSWORD_LIFETIME)
        consume_token(raw, RESET)
        used_at = EmailVerificationToken.objects.get().used_at

        cancel_unused_tokens(user)

        assert EmailVerificationToken.objects.get().used_at == used_at

    def test_cancelling_does_not_reset_the_resend_cooldown(self, user):
        # เวลาออกโทเคน (created_at) ไม่เปลี่ยน กฎรอ 60 วินาทีจึงยังนับจากลิงก์ล่าสุดตามเดิม
        issue_token(user, RESET, RESET_PASSWORD_LIFETIME)
        before = seconds_until_resend(user, RESET)

        cancel_unused_tokens(user)

        assert 0 < seconds_until_resend(user, RESET) <= before


class TestIssue:
    def test_database_keeps_only_the_hash_never_the_real_token(self, user):
        raw = issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)

        stored = EmailVerificationToken.objects.get()
        assert stored.token_hash == hash_token(raw)
        assert stored.token_hash != raw
        assert len(stored.token_hash) == 64
        # ไม่มีคอลัมน์ไหนในตารางเก็บตัวโทเคนจริง
        for value in (stored.token_hash, stored.purpose):
            assert raw not in str(value)

    def test_tokens_are_random_and_long_enough(self, user):
        first = issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)
        second = issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)

        assert first != second
        # 32 ไบต์ → base64 ประมาณ 43 ตัวอักษร (256 บิต)
        assert len(first) >= 43

    def test_expiry_follows_the_lifetime_given(self, user):
        before = timezone.now()
        issue_token(user, RESET, RESET_PASSWORD_LIFETIME)

        stored = EmailVerificationToken.objects.get()
        assert before + RESET_PASSWORD_LIFETIME <= stored.expires_at
        assert stored.expires_at <= timezone.now() + RESET_PASSWORD_LIFETIME
        assert stored.used_at is None

    def test_issuing_again_cancels_the_old_unused_link(self, user):
        old = issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)
        new = issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)

        with pytest.raises(TokenInvalid):
            consume_token(old, VERIFY)
        assert consume_token(new, VERIFY) == user

    def test_issuing_does_not_cancel_links_of_other_purposes_or_users(self, user):
        other = User.objects.create_user(
            email="other@example.com", password="Str0ng-pass-123", first_name="อื่น", last_name="คน"
        )
        reset_token = issue_token(user, RESET, RESET_PASSWORD_LIFETIME)
        others_token = issue_token(other, VERIFY, VERIFY_EMAIL_LIFETIME)

        issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)

        assert consume_token(reset_token, RESET) == user
        assert consume_token(others_token, VERIFY) == other


class TestConsume:
    def test_valid_token_returns_its_owner_and_marks_used(self, user):
        raw = issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)

        assert consume_token(raw, VERIFY) == user
        assert EmailVerificationToken.objects.get().used_at is not None

    def test_token_works_only_once(self, user):
        raw = issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)
        consume_token(raw, VERIFY)

        with pytest.raises(TokenInvalid):
            consume_token(raw, VERIFY)

    def test_expired_token_is_rejected_as_expired_and_not_marked_used(self, user):
        raw = issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)
        EmailVerificationToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

        with pytest.raises(TokenExpired):
            consume_token(raw, VERIFY)
        assert EmailVerificationToken.objects.get().used_at is None

    def test_token_of_one_purpose_cannot_be_used_for_another(self, user):
        # เอาลิงก์ยืนยันอีเมลไปตั้งรหัสผ่านไม่ได้ (และกลับกัน)
        verify_token = issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)

        with pytest.raises(TokenInvalid):
            consume_token(verify_token, RESET)
        # การลองผิดจุดประสงค์ไม่ทำให้โทเคนถูกใช้ไป
        assert consume_token(verify_token, VERIFY) == user

    @pytest.mark.parametrize("bad", ["", "not-a-real-token", "x" * 500, " ", "abc' OR '1'='1"])
    def test_garbage_tokens_are_invalid(self, bad, user):
        issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)

        with pytest.raises(TokenInvalid):
            consume_token(bad, VERIFY)

    def test_the_stored_hash_is_not_accepted_as_a_token(self, user):
        # คนที่เห็นฐานข้อมูล (เห็นแฮช) เอาแฮชมาเป็นโทเคนไม่ได้
        issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)
        stored_hash = EmailVerificationToken.objects.get().token_hash

        with pytest.raises(TokenInvalid):
            consume_token(stored_hash, VERIFY)


class TestResendCooldown:
    def test_no_wait_when_nothing_was_issued_yet(self, user):
        assert seconds_until_resend(user, VERIFY) == 0

    def test_must_wait_right_after_issuing(self, user):
        issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)

        wait = seconds_until_resend(user, VERIFY)

        assert 0 < wait <= RESEND_COOLDOWN.total_seconds()

    def test_no_wait_after_the_cooldown_passed(self, user):
        issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)
        EmailVerificationToken.objects.update(
            created_at=timezone.now() - RESEND_COOLDOWN - timedelta(seconds=1)
        )

        assert seconds_until_resend(user, VERIFY) == 0

    def test_cooldown_is_separate_per_purpose_and_per_user(self, user):
        other = User.objects.create_user(
            email="other@example.com", password="Str0ng-pass-123", first_name="อื่น", last_name="คน"
        )
        issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)

        assert seconds_until_resend(user, RESET) == 0
        assert seconds_until_resend(other, VERIFY) == 0

    def test_cooldown_still_applies_after_the_link_was_used(self, user):
        # ใช้ลิงก์ไปแล้วก็ยังนับ 60 วินาทีจากตอนออก กันสแปมด้วยการสลับใช้/ขอใหม่
        raw = issue_token(user, RESET, RESET_PASSWORD_LIFETIME)
        consume_token(raw, RESET)

        assert seconds_until_resend(user, RESET) > 0
