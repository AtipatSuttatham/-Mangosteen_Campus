from datetime import timedelta

import pytest
from django.contrib.auth.hashers import make_password
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import User
from .roles import Role
from .tokens import issue_refresh_token

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres)
pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"
# แฮชรหัสผ่านคำนวณครั้งเดียว ใช้ใส่ผู้ใช้จำนวนมาก (แฮชใหม่ให้ทุกคนช้าเกินไป)
USABLE_HASH = make_password(PASSWORD)
# รหัสผ่านของบัญชีที่ Admin สร้างให้แต่เจ้าของยังไม่ตั้งรหัส (ขึ้นต้นด้วย "!")
NO_PASSWORD = "!not-set-yet"

LIST_URL = reverse("admin-user-list")

ROW_FIELDS = {
    "id",
    "email",
    "student_or_staff_id",
    "role",
    "first_name",
    "last_name",
    "first_name_en",
    "last_name_en",
    "status",
    "is_active",
    "is_email_verified",
    "last_login",
    "date_joined",
}
DETAIL_FIELDS = ROW_FIELDS | {"updated_at", "created_by"}


def detail_url(user):
    return reverse("admin-user-detail", args=[user.pk])


def bearer(user):
    return f"Bearer {issue_refresh_token(user).access_token}"


def make_user(email, role=Role.STUDENT, **extra):
    """สร้างผู้ใช้ 1 คน (ไม่แฮชรหัสผ่านใหม่) ค่าเริ่มต้น = ผู้เรียนที่ใช้งานอยู่ ยืนยันอีเมลแล้ว"""
    fields = {
        "password": USABLE_HASH,
        "first_name": "สมชาย",
        "last_name": "ใจดี",
        "is_email_verified": True,
    }
    fields.update(extra)
    return User.objects.create(email=email, role=role, **fields)


def bulk_students(count, **extra):
    """สร้างผู้เรียนจำนวนมากในครั้งเดียว"""
    return User.objects.bulk_create(
        [
            User(
                email=f"student{index:03d}@example.com",
                password=USABLE_HASH,
                first_name="นักเรียน",
                last_name=f"หมายเลข{index}",
                is_email_verified=True,
                role=Role.STUDENT,
                **extra,
            )
            for index in range(count)
        ]
    )


def emails(response):
    return [row["email"] for row in response.data["results"]]


@pytest.fixture
def admin():
    return make_user("admin@example.com", role=Role.ADMIN, first_name="อภิชาติ", last_name="วงศ์สกุล")


@pytest.fixture
def api(admin):
    """client ที่ล็อกอินเป็น Admin"""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=bearer(admin))
    return client


class TestPermissions:
    def test_anonymous_gets_401(self):
        client = APIClient()
        user = make_user("someone@example.com")

        assert client.get(LIST_URL).status_code == 401
        assert client.get(detail_url(user)).status_code == 401

    @pytest.mark.parametrize("role", [Role.TEACHER, Role.STUDENT])
    def test_other_roles_get_403(self, role):
        user = make_user(f"{role}@example.com", role=role)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=bearer(user))

        list_response = client.get(LIST_URL)
        detail_response = client.get(detail_url(user))

        assert list_response.status_code == 403
        assert list_response.data["code"] == "permission_denied"
        assert detail_response.status_code == 403

    def test_non_admin_is_denied_before_filters_are_checked(self):
        # สิทธิ์ตรวจก่อนพารามิเตอร์: คนที่ไม่ใช่ Admin ไม่ได้ข้อความ error ของตัวกรอง (ไม่รั่วโครงสร้าง API)
        student = make_user("student@example.com")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=bearer(student))

        response = client.get(LIST_URL, {"role": "hack"})

        assert response.status_code == 403

    def test_demoted_admin_with_old_token_is_denied(self, admin):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=bearer(admin))
        User.objects.filter(pk=admin.pk).update(role=Role.TEACHER)

        assert client.get(LIST_URL).status_code == 403

    def test_responses_are_never_cacheable(self, api):
        user = make_user("someone@example.com")

        assert api.get(LIST_URL)["Cache-Control"] == "no-store"
        assert api.get(detail_url(user))["Cache-Control"] == "no-store"
        # คำตอบที่เป็น error ก็ห้าม cache
        assert APIClient().get(LIST_URL)["Cache-Control"] == "no-store"
        assert api.get(reverse("admin-user-detail", args=[999999]))["Cache-Control"] == "no-store"


class TestListResponse:
    def test_shape_of_the_response_and_rows(self, api, admin):
        response = api.get(LIST_URL)

        assert response.status_code == 200
        assert set(response.data) == {
            "count",
            "page",
            "page_size",
            "total_pages",
            "next",
            "previous",
            "role_counts",
            "results",
        }
        assert set(response.data["results"][0]) == ROW_FIELDS
        assert response.data["results"][0]["email"] == admin.email

    def test_no_password_or_hash_is_ever_returned(self, api):
        make_user("pending@example.com", password=NO_PASSWORD)

        body = api.get(LIST_URL).content.decode().lower()

        # ตรวจ "ชื่อฟิลด์" password (ค่าสถานะ pending_password มีคำนี้อยู่ด้วยโดยชอบ)
        assert '"password"' not in body
        assert "pbkdf2" not in body
        assert USABLE_HASH.lower() not in body
        assert NO_PASSWORD not in body

    def test_times_are_in_bangkok_time(self, api, admin):
        response = api.get(LIST_URL)

        assert response.data["results"][0]["date_joined"].endswith("+07:00")

    def test_status_is_reported_per_user(self, api):
        make_user("pending@example.com", password=NO_PASSWORD)
        make_user("unverified@example.com", is_email_verified=False)
        make_user("disabled@example.com", is_active=False)

        rows = {row["email"]: row["status"] for row in api.get(LIST_URL).data["results"]}

        assert rows == {
            "admin@example.com": "active",
            "pending@example.com": "pending_password",
            "unverified@example.com": "pending_verification",
            "disabled@example.com": "disabled",
        }


class TestPagination:
    def test_pages_of_twenty(self, api):
        bulk_students(44)  # รวม Admin ที่สร้างไว้ = 45

        first = api.get(LIST_URL)
        second = api.get(LIST_URL, {"page": 2})
        third = api.get(LIST_URL, {"page": 3})

        assert [len(r.data["results"]) for r in (first, second, third)] == [20, 20, 5]
        assert first.data["count"] == 45
        assert first.data["total_pages"] == 3
        assert first.data["page_size"] == 20
        assert third.data["next"] is None

    def test_page_after_the_last_is_404(self, api):
        bulk_students(44)

        response = api.get(LIST_URL, {"page": 4})

        assert response.status_code == 404
        assert response.data["code"] == "not_found"

    def test_absurd_page_numbers_are_404_not_500(self, api):
        assert api.get(LIST_URL, {"page": "9" * 40}).status_code == 404
        assert api.get(LIST_URL, {"page": "abc"}).status_code == 404
        assert api.get(LIST_URL, {"page": -1}).status_code == 404

    def test_no_user_is_duplicated_or_lost_across_pages_when_times_are_equal(self, api, admin):
        # ผู้ใช้ทั้งหมดมี date_joined เท่ากัน: ลำดับต้องคงที่ด้วย id ไม่เช่นนั้นแบ่งหน้าแล้วคนซ้ำ/ตกหล่น
        same_time = timezone.now()
        User.objects.filter(pk=admin.pk).update(date_joined=same_time)
        bulk_students(44, date_joined=same_time)

        seen = []
        for page in (1, 2, 3):
            seen += emails(api.get(LIST_URL, {"page": page}))

        assert len(seen) == 45
        assert len(set(seen)) == 45

    def test_client_cannot_choose_page_size(self, api):
        bulk_students(44)

        response = api.get(LIST_URL, {"page_size": 100})

        assert len(response.data["results"]) == 20


class TestOrdering:
    def test_newest_account_first(self, api):
        now = timezone.now()
        make_user("oldest@example.com", date_joined=now - timedelta(days=30))
        make_user("newer@example.com", date_joined=now - timedelta(days=2))
        make_user("middle@example.com", date_joined=now - timedelta(days=10))

        # admin สร้างเมื่อครู่นี้จึงใหม่สุด
        assert emails(api.get(LIST_URL)) == [
            "admin@example.com",
            "newer@example.com",
            "middle@example.com",
            "oldest@example.com",
        ]

    def test_equal_times_are_ordered_by_id_newest_first(self, api, admin):
        same_time = timezone.now()
        User.objects.filter(pk=admin.pk).update(date_joined=same_time)
        first = make_user("first@example.com", date_joined=same_time)
        second = make_user("second@example.com", date_joined=same_time)

        result = emails(api.get(LIST_URL))

        assert result == [second.email, first.email, admin.email]


class TestFilters:
    @pytest.fixture
    def people(self, admin):
        return {
            "teacher": make_user("teacher@example.com", role=Role.TEACHER),
            "pending": make_user("pending@example.com", password=NO_PASSWORD),
            "unverified": make_user("unverified@example.com", is_email_verified=False),
            "disabled": make_user("disabled@example.com", is_active=False),
        }

    def test_filter_by_role(self, api, people):
        assert emails(api.get(LIST_URL, {"role": "teacher"})) == ["teacher@example.com"]
        assert emails(api.get(LIST_URL, {"role": "admin"})) == ["admin@example.com"]
        assert len(emails(api.get(LIST_URL, {"role": "student"}))) == 3

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            ("active", {"admin@example.com", "teacher@example.com"}),
            ("pending_password", {"pending@example.com"}),
            ("pending_verification", {"unverified@example.com"}),
            ("disabled", {"disabled@example.com"}),
        ],
    )
    def test_filter_by_each_status(self, api, people, status, expected):
        response = api.get(LIST_URL, {"status": status})

        assert set(emails(response)) == expected

    def test_role_and_status_combine(self, api, people):
        response = api.get(LIST_URL, {"role": "student", "status": "disabled"})

        assert emails(response) == ["disabled@example.com"]

    def test_blank_filters_mean_no_filter(self, api, people):
        response = api.get(LIST_URL, {"role": "", "status": "", "search": ""})

        assert response.data["count"] == 5

    @pytest.mark.parametrize("params", [{"role": "hack"}, {"status": "hack"}, {"role": "Admin"}])
    def test_unknown_values_are_rejected_with_error_codes(self, api, params):
        response = api.get(LIST_URL, params)

        assert response.status_code == 400
        assert response.data["code"] == "validation_error"
        field = next(iter(params))
        assert response.data["error_codes"][field] == ["invalid_choice"]


class TestSearch:
    @pytest.fixture
    def people(self, admin):
        return {
            "natthaphon": make_user(
                "natthaphon.m@example.ac.th",
                role=Role.TEACHER,
                first_name="ณัฐพล",
                last_name="เมืองแก้ว",
                first_name_en="Natthaphon",
                last_name_en="Muangkaew",
                student_or_staff_id="T0042",
            ),
            "manee": make_user(
                "manee.j@example.com",
                first_name="มานี",
                last_name="ใจตรง",
                student_or_staff_id="650612001",
            ),
            "chaiwat": make_user(
                "chaiwat.t@example.com",
                first_name="ชัยวัฒน์",
                last_name="ทองดี",
                student_or_staff_id="650612044",
            ),
            # ชื่อต้นเหมือนคนแรก นามสกุลเหมือนคนที่สอง — ใช้ทดสอบว่า "ทุกคำ" ต้องเจอในคนเดียวกัน
            "mixed": make_user("mixed@example.com", first_name="ณัฐพล", last_name="ใจตรง"),
        }

    def search(self, api, text, **extra):
        return set(emails(api.get(LIST_URL, {"search": text, **extra})))

    def test_by_first_name_and_last_name(self, api, people):
        assert self.search(api, "มานี") == {"manee.j@example.com"}
        assert self.search(api, "ทองดี") == {"chaiwat.t@example.com"}

    def test_full_name_with_space_needs_every_word(self, api, people):
        assert self.search(api, "ณัฐพล เมือง") == {"natthaphon.m@example.ac.th"}

    def test_every_word_must_match_the_same_person(self, api, people):
        # "ณัฐพล" มี 2 คน "ใจตรง" มี 2 คน แต่ทั้งสองคำพร้อมกันมีแค่ 1 คน (ไม่ใช่ OR)
        assert self.search(api, "ณัฐพล ใจตรง") == {"mixed@example.com"}

    def test_words_may_match_different_fields(self, api, people):
        assert self.search(api, "ชัยวัฒน์ 650612044") == {"chaiwat.t@example.com"}

    def test_email_part_ignores_case(self, api, people):
        assert self.search(api, "CHAIWAT.T") == {"chaiwat.t@example.com"}

    def test_id_part_matches_anywhere(self, api, people):
        assert self.search(api, "6506120") == {"manee.j@example.com", "chaiwat.t@example.com"}

    def test_english_name_ignores_case(self, api, people):
        assert self.search(api, "muangkaew") == {"natthaphon.m@example.ac.th"}

    def test_surrounding_and_repeated_spaces_are_ignored(self, api, people):
        assert self.search(api, "   ชัยวัฒน์    ") == {"chaiwat.t@example.com"}

    def test_blank_search_means_no_search(self, api, people):
        assert len(self.search(api, "    ")) == 5  # ผู้ใช้ 4 คนในชุดนี้ + Admin

    def test_only_first_five_words_are_used(self, api, people):
        # คำที่ 6 ไม่มีในใครเลย แต่ถูกตัดทิ้ง จึงยังเจอคนแรก (ถ้าไม่ตัด ผลต้องว่างเปล่า)
        text = "ณัฐพล เมืองแก้ว natthaphon T0042 muangkaew ไม่มีคำนี้แน่นอน"

        assert self.search(api, text) == {"natthaphon.m@example.ac.th"}

    def test_too_long_search_is_rejected(self, api):
        response = api.get(LIST_URL, {"search": "ก" * 101})

        assert response.status_code == 400
        assert response.data["error_codes"]["search"] == ["max_length"]

    def test_no_match_gives_empty_page_with_zero_counts(self, api, people):
        response = api.get(LIST_URL, {"search": "ไม่มีใครชื่อนี้"})

        assert response.status_code == 200
        assert response.data["count"] == 0
        assert response.data["results"] == []
        assert response.data["role_counts"] == {"all": 0, "admin": 0, "teacher": 0, "student": 0}

    def test_percent_and_underscore_are_plain_characters(self, api, people):
        # ถ้าไม่ escape: "_" ตรงกับทุกอักขระ และ "%" ตรงกับทุกอย่าง จะได้ผู้ใช้ทุกคน
        make_user("under_score@example.com")

        assert self.search(api, "_") == {"under_score@example.com"}
        assert self.search(api, "%") == set()

    @pytest.mark.parametrize(
        "text", ["'; DROP TABLE accounts_user; --", "' OR '1'='1", '"><script>']
    )
    def test_hostile_text_is_harmless(self, api, people, text):
        response = api.get(LIST_URL, {"search": text})

        assert response.status_code == 200
        assert response.data["count"] == 0
        assert User.objects.count() == 5

    def test_search_combines_with_filters(self, api, people):
        assert self.search(api, "ณัฐพล", role="teacher") == {"natthaphon.m@example.ac.th"}
        assert self.search(api, "ณัฐพล", status="pending_password") == set()


class TestRoleCounts:
    @pytest.fixture
    def people(self, admin):
        make_user("teacher1@example.com", role=Role.TEACHER)
        make_user("teacher2@example.com", role=Role.TEACHER, password=NO_PASSWORD)
        make_user("student1@example.com")
        make_user("student2@example.com")
        make_user("student3@example.com", password=NO_PASSWORD)

    def counts(self, api, **params):
        return api.get(LIST_URL, params).data["role_counts"]

    def test_counts_every_role(self, api, people):
        assert self.counts(api) == {"all": 6, "admin": 1, "teacher": 2, "student": 3}

    def test_role_filter_does_not_change_the_counts(self, api, people):
        # ถ้าแท็บที่เลือกทำให้แท็บอื่นเป็นศูนย์ ผู้ใช้จะสลับแท็บไม่ได้
        response = api.get(LIST_URL, {"role": "teacher"})

        assert response.data["role_counts"] == {"all": 6, "admin": 1, "teacher": 2, "student": 3}
        assert response.data["count"] == 2

    def test_status_filter_changes_the_counts(self, api, people):
        assert self.counts(api, status="pending_password") == {
            "all": 2,
            "admin": 0,
            "teacher": 1,
            "student": 1,
        }

    def test_search_changes_the_counts(self, api, people):
        assert self.counts(api, search="student") == {
            "all": 3,
            "admin": 0,
            "teacher": 0,
            "student": 3,
        }

    def test_all_equals_count_when_role_is_not_filtered(self, api, people):
        response = api.get(LIST_URL, {"status": "active"})

        assert response.data["role_counts"]["all"] == response.data["count"]

    def test_zero_roles_are_still_present(self, api, admin):
        assert self.counts(api) == {"all": 1, "admin": 1, "teacher": 0, "student": 0}


class TestQueryCount:
    def test_number_of_queries_does_not_grow_with_the_number_of_users(
        self, api, django_assert_max_num_queries
    ):
        bulk_students(30)

        # ผู้ใช้ที่ยืนยันตัวตน + นับทั้งหมด + ดึงหน้า + นับตามบทบาท ไม่มีคิวรีเพิ่มต่อแถว (N+1)
        with django_assert_max_num_queries(6):
            response = api.get(LIST_URL)

        assert len(response.data["results"]) == 20


class TestDetail:
    def test_fields_and_creator(self, api, admin):
        user = make_user("created@example.com", created_by=admin)

        response = api.get(detail_url(user))

        assert response.status_code == 200
        assert set(response.data) == DETAIL_FIELDS
        assert response.data["email"] == "created@example.com"
        assert response.data["created_by"] == {"id": admin.pk, "full_name": "อภิชาติ วงศ์สกุล"}
        assert response.data["updated_at"] is not None

    def test_self_registered_user_has_no_creator(self, api):
        user = make_user("self@example.com", is_email_verified=False)

        response = api.get(detail_url(user))

        assert response.data["created_by"] is None
        assert response.data["status"] == "pending_verification"

    def test_disabled_user_can_still_be_viewed(self, api):
        user = make_user("off@example.com", is_active=False)

        response = api.get(detail_url(user))

        assert response.status_code == 200
        assert response.data["status"] == "disabled"

    def test_no_password_or_hash_is_ever_returned(self, api):
        user = make_user("pending@example.com", password=NO_PASSWORD)

        body = api.get(detail_url(user)).content.decode().lower()

        assert '"password"' not in body
        assert "pbkdf2" not in body
        assert NO_PASSWORD not in body

    def test_unknown_id_is_404(self, api):
        response = api.get(reverse("admin-user-detail", args=[999999]))

        assert response.status_code == 404
        assert response.data["code"] == "not_found"

    def test_non_numeric_id_is_404(self, api):
        assert api.get("/api/admin/users/abc/").status_code == 404

    def test_number_of_queries_is_small(self, api, admin, django_assert_max_num_queries):
        user = make_user("created@example.com", created_by=admin)

        # ผู้ใช้ที่ยืนยันตัวตน + ผู้ใช้ที่ดูพร้อมผู้สร้าง (select_related ในคิวรีเดียว) = 2 คิวรีพอดี
        with django_assert_max_num_queries(2):
            api.get(detail_url(user))
