import datetime
import json
from decimal import Decimal

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from accounts.models import User
from accounts.roles import Role
from audit.models import AuditAction, AuditLog
from audit.services import (
    MAX_PATH_LENGTH,
    MAX_REPR_LENGTH,
    MAX_USER_AGENT_LENGTH,
    field_changes,
    log_action,
    request_context,
)

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres)
pytestmark = pytest.mark.django_db


def make_user(email="admin@example.com", **extra):
    return User.objects.create_user(
        email=email, password="Str0ng-pass-123", first_name="สมชาย", last_name="ใจดี", **extra
    )


class TestLogAction:
    def test_records_every_field(self):
        admin = make_user("admin@example.com", role=Role.ADMIN)
        target = make_user("new@example.com")

        log = log_action(
            actor=admin,
            action=AuditAction.CREATE,
            target=target,
            changes={"role": [None, "student"]},
            context={"ip": "10.0.0.5", "path": "/api/admin/users/"},
        )

        log.refresh_from_db()
        assert log.actor == admin
        assert log.impersonated_by is None
        assert log.action == "create"
        assert log.content_type == ContentType.objects.get_for_model(User)
        assert log.object_id == str(target.pk)
        assert log.object_repr == "new@example.com"
        assert log.changes == {"role": [None, "student"]}
        assert log.context == {"ip": "10.0.0.5", "path": "/api/admin/users/"}
        assert log.created_at is not None

    def test_target_is_optional(self):
        # เข้าสู่ระบบ/ออกจากระบบไม่มีวัตถุที่ถูกกระทำ
        user = make_user()

        log = log_action(actor=user, action=AuditAction.LOGIN)

        assert log.content_type is None
        assert log.object_id is None
        assert log.object_repr == ""

    def test_actor_may_be_the_system(self):
        target = make_user()

        log = log_action(actor=None, action=AuditAction.UPDATE, target=target)

        assert log.actor is None

    def test_records_impersonator(self):
        real_admin = make_user("real@example.com", role=Role.ADMIN)
        target = make_user("target@example.com")

        log = log_action(
            actor=target, impersonated_by=real_admin, action=AuditAction.UPDATE, target=target
        )

        assert log.actor == target
        assert log.impersonated_by == real_admin

    def test_unknown_action_is_rejected_before_writing(self):
        with pytest.raises(ValueError):
            log_action(actor=None, action="hack")

        assert AuditLog.objects.count() == 0

    def test_unsaved_target_is_rejected(self):
        # ไม่มี pk = ไม่รู้ว่าชี้ไปแถวไหน (กรณีลบ ต้องเรียกก่อนสั่งลบ)
        unsaved = User(email="ghost@example.com")

        with pytest.raises(ValueError):
            log_action(actor=None, action=AuditAction.DELETE, target=unsaved)

        assert AuditLog.objects.count() == 0

    def test_long_object_repr_is_truncated(self, monkeypatch):
        target = make_user()
        # ให้ข้อความแทนผู้ใช้ยาวเกินคอลัมน์ (255) ชั่วคราวเฉพาะ test นี้
        monkeypatch.setattr(User, "__str__", lambda self: "ก" * 400)

        log = log_action(actor=None, action=AuditAction.UPDATE, target=target)

        assert len(log.object_repr) == MAX_REPR_LENGTH

    def test_log_rolls_back_with_the_action(self):
        # เขียนในธุรกรรมเดียวกับผู้เรียก: การกระทำล้ม log ต้องไม่เหลือ (ไม่มี log ของสิ่งที่ไม่เคยเกิด)
        target = make_user()

        with pytest.raises(RuntimeError), transaction.atomic():
            log_action(actor=None, action=AuditAction.UPDATE, target=target)
            raise RuntimeError("การกระทำล้มเหลวหลังบันทึก log")

        assert AuditLog.objects.count() == 0


class TestFieldChanges:
    def test_returns_only_changed_fields(self):
        before = {"role": "student", "first_name": "สมชาย", "is_active": True}
        after = {"role": "teacher", "first_name": "สมชาย", "is_active": True}

        assert field_changes(before, after, ["role", "first_name", "is_active"]) == {
            "role": ["student", "teacher"]
        }

    def test_nothing_changed_gives_empty_dict(self):
        state = {"role": "student"}

        assert field_changes(state, dict(state), ["role"]) == {}

    def test_fields_outside_the_whitelist_never_appear(self):
        # รหัสผ่านเปลี่ยนจริงใน before/after แต่ไม่ได้อยู่ใน whitelist จึงต้องไม่หลุดเข้า log
        before = {"role": "student", "password": "pbkdf2$old-hash"}
        after = {"role": "teacher", "password": "pbkdf2$new-hash"}

        changes = field_changes(before, after, ["role"])

        assert "password" not in changes
        assert "hash" not in json.dumps(changes)

    def test_field_missing_from_data_raises(self):
        # พิมพ์ชื่อฟิลด์ผิดแล้วตกหล่นเงียบ ๆ ไม่ได้ — Audit Log ที่ขาดโดยไม่รู้ตัวอันตรายกว่าล้มดัง ๆ
        with pytest.raises(KeyError):
            field_changes({"role": "student"}, {"role": "teacher"}, ["rol"])

    def test_values_are_json_safe(self):
        before = {
            "role": Role.STUDENT,
            "joined": datetime.datetime(2026, 9, 1, 8, 30, tzinfo=datetime.UTC),
            "birthday": datetime.date(2000, 1, 2),
            "score": Decimal("7.50"),
        }
        after = {
            "role": Role.TEACHER,
            "joined": datetime.datetime(2026, 9, 2, 9, 0, tzinfo=datetime.UTC),
            "birthday": datetime.date(2000, 1, 3),
            "score": Decimal("8.25"),
        }

        changes = field_changes(before, after, ["role", "joined", "birthday", "score"])

        assert changes == {
            "role": ["student", "teacher"],
            "joined": ["2026-09-01T08:30:00+00:00", "2026-09-02T09:00:00+00:00"],
            "birthday": ["2000-01-02", "2000-01-03"],
            "score": ["7.50", "8.25"],
        }
        # เก็บลง JSONField ได้จริง
        json.dumps(changes)


class TestRequestContext:
    factory = APIRequestFactory()

    def test_reads_ip_user_agent_and_path(self):
        request = self.factory.get(
            "/api/admin/users/", REMOTE_ADDR="10.0.0.5", HTTP_USER_AGENT="Mozilla/5.0 Test"
        )

        assert request_context(request) == {
            "ip": "10.0.0.5",
            "user_agent": "Mozilla/5.0 Test",
            "path": "/api/admin/users/",
        }

    def test_ignores_forwarded_for_header(self):
        # X-Forwarded-For ผู้ส่งปลอมได้เอง — ต้องใช้ REMOTE_ADDR
        request = self.factory.get(
            "/", REMOTE_ADDR="10.0.0.5", HTTP_X_FORWARDED_FOR="6.6.6.6, 7.7.7.7"
        )

        assert request_context(request)["ip"] == "10.0.0.5"

    def test_path_excludes_query_string(self):
        # query อาจมีโทเคนในลิงก์ (?token=...) ห้ามเก็บลง log
        request = self.factory.get("/reset-password?token=SECRET-TOKEN-VALUE")

        context = request_context(request)

        assert context["path"] == "/reset-password"
        assert "SECRET-TOKEN-VALUE" not in json.dumps(context)

    def test_long_user_agent_and_path_are_truncated(self):
        request = self.factory.get("/" + "a" * 500, HTTP_USER_AGENT="U" * 900)

        context = request_context(request)

        assert len(context["user_agent"]) == MAX_USER_AGENT_LENGTH
        assert len(context["path"]) == MAX_PATH_LENGTH

    def test_missing_user_agent_is_empty_string(self):
        request = self.factory.get("/")

        assert request_context(request)["user_agent"] == ""

    def test_accepts_drf_request(self):
        request = Request(self.factory.get("/api/x/", REMOTE_ADDR="10.0.0.9"))

        assert request_context(request)["ip"] == "10.0.0.9"
