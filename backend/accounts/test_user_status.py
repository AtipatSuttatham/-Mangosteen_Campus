from itertools import product

import pytest

from .models import User
from .user_status import UserStatus, has_no_password, status_filter, status_of

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres)
pytestmark = pytest.mark.django_db

# รหัสผ่านตัวอย่าง: แฮชจริงหน้าตาทั่วไป / ยังไม่มีรหัส (ขึ้นต้น "!") / กรณีขอบ: สตริงว่าง และ "!" เดี่ยว ๆ
HASHED = "pbkdf2_sha256$1$salt$hash"
UNUSABLE = "!aBcDeF1234567890"


def unsaved(password=HASHED, is_active=True, is_email_verified=True):
    return User(
        email="x@example.com",
        password=password,
        is_active=is_active,
        is_email_verified=is_email_verified,
    )


class TestStatusOf:
    def test_active(self):
        assert status_of(unsaved()) == UserStatus.ACTIVE

    def test_pending_password_when_no_password_yet(self):
        assert status_of(unsaved(password=UNUSABLE)) == UserStatus.PENDING_PASSWORD

    def test_pending_verification_when_email_not_verified(self):
        assert status_of(unsaved(is_email_verified=False)) == UserStatus.PENDING_VERIFICATION

    def test_disabled(self):
        assert status_of(unsaved(is_active=False)) == UserStatus.DISABLED

    def test_disabled_wins_over_everything(self):
        user = unsaved(password=UNUSABLE, is_active=False, is_email_verified=False)

        assert status_of(user) == UserStatus.DISABLED

    def test_no_password_wins_over_unverified_email(self):
        user = unsaved(password=UNUSABLE, is_email_verified=False)

        assert status_of(user) == UserStatus.PENDING_PASSWORD

    def test_real_unusable_password_from_django_counts_as_no_password(self):
        # บัญชีที่ Admin สร้างให้ใช้ create_user(password=None) จึงต้องถูกมองว่ายังไม่มีรหัส
        user = User.objects.create_user(email="new@example.com", password=None)

        assert has_no_password(user.password)
        assert status_of(user) == UserStatus.PENDING_PASSWORD


class TestFilterMatchesStatusOf:
    """กฎแสดงผล (status_of) กับกฎกรอง (status_filter) ต้องให้ผลเดียวกันทุกชุดเงื่อนไข"""

    @pytest.fixture
    def users(self):
        created = []
        # ครบทุกชุด: บัญชีเปิด/ปิด × มี/ไม่มีรหัสผ่าน × ยืนยัน/ไม่ยืนยันอีเมล = 8 ชุด
        # และกรณีขอบของรหัสผ่านอีก 2 ชุด (สตริงว่าง = มีรหัส, "!" เดี่ยว ๆ = ไม่มีรหัส)
        combos = list(product([True, False], [HASHED, UNUSABLE], [True, False]))
        combos += [(True, "", True), (True, "!", True)]
        for index, (is_active, password, verified) in enumerate(combos):
            created.append(
                User.objects.create(
                    email=f"user{index}@example.com",
                    password=password,
                    first_name="ทดสอบ",
                    last_name="ระบบ",
                    is_active=is_active,
                    is_email_verified=verified,
                )
            )
        return created

    @pytest.mark.parametrize("status", UserStatus.values)
    def test_filter_returns_exactly_the_users_with_that_status(self, users, status):
        expected = {user.pk for user in users if status_of(user) == status}

        actual = set(User.objects.filter(status_filter(status)).values_list("pk", flat=True))

        assert actual == expected

    def test_every_status_is_reachable(self, users):
        # กันกรณี test ข้างบนผ่านเพราะทุกสถานะว่างเปล่าเหมือนกัน
        assert {status_of(user) for user in users} == set(UserStatus.values)

    def test_each_user_is_in_exactly_one_status(self, users):
        for user in users:
            matching = [
                status
                for status in UserStatus.values
                if User.objects.filter(pk=user.pk).filter(status_filter(status)).exists()
            ]

            assert matching == [status_of(user)]

    def test_unknown_status_is_rejected(self):
        with pytest.raises(ValueError):
            status_filter("hack")
