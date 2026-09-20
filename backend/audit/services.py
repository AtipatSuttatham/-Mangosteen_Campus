"""เขียน Audit Log — ฟังก์ชันเดียวที่ระบบใช้เพิ่มแถวลงตาราง AuditLog (docs/database.md §10)

ทุกฟังก์ชันไม่รู้จัก HTTP เกินกว่าที่ request_context อ่านจาก request — view/service เรียกใช้ได้เลย
"""

import datetime
from collections.abc import Iterable, Mapping
from typing import Any

from django.contrib.contenttypes.models import ContentType

from .models import AuditAction, AuditLog

# ความยาวสูงสุดของข้อความที่เก็บ (ตรงกับความยาวคอลัมน์ / กัน user-agent และ path ยาวผิดปกติทำแถวบวม)
MAX_REPR_LENGTH = 255
MAX_USER_AGENT_LENGTH = 200
MAX_PATH_LENGTH = 200


def log_action(
    *,
    actor,
    action: str,
    target=None,
    changes: dict | None = None,
    context: dict | None = None,
    impersonated_by=None,
) -> AuditLog:
    """บันทึกการกระทำ 1 รายการ แล้วคืนแถว AuditLog ที่สร้าง

    - actor: ผู้กระทำ (None = ระบบทำเอง)
    - target: วัตถุที่ถูกกระทำ (instance ของโมเดลใดก็ได้ที่บันทึกลงฐานข้อมูลแล้ว) หรือ None ถ้าไม่มีวัตถุ
      เช่น เข้าสู่ระบบ — ถ้าเป็นการลบ ให้เรียกก่อนสั่งลบ เพราะหลังลบ Django จะล้าง pk ของ instance
    - changes: ใช้ field_changes สร้าง — ห้ามใส่รหัสผ่านหรือโทเคน
    - context: ใช้ request_context สร้าง

    เขียนใน "ธุรกรรมเดียวกับผู้เรียก" (ไม่เปิดธุรกรรมแยก): ถ้าการกระทำนั้นย้อนกลับ log ก็ย้อนกลับด้วย
    จะไม่มี log ของสิ่งที่ไม่เคยเกิด และถ้าเขียน log ไม่ได้ ตัวการกระทำก็ล้มด้วย (Audit Log ตกหล่นเงียบ ๆ อันตรายกว่า)
    """
    # ตรวจก่อนถึงฐานข้อมูล: พิมพ์ชื่อ action ผิดต้องรู้ทันที ไม่ใช่รอให้ constraint ปฏิเสธ
    if action not in AuditAction.values:
        raise ValueError(f"action ไม่ถูกต้อง: {action!r}")

    content_type = None
    object_id = None
    object_repr = ""
    if target is not None:
        if target.pk is None:
            raise ValueError("target ต้องบันทึกลงฐานข้อมูลแล้ว (ไม่มี pk) — ถ้าจะบันทึกการลบ ให้เรียกก่อนสั่งลบ")
        content_type = ContentType.objects.get_for_model(target)
        object_id = str(target.pk)
        object_repr = str(target)[:MAX_REPR_LENGTH]

    return AuditLog.objects.create(
        actor=actor,
        impersonated_by=impersonated_by,
        action=action,
        content_type=content_type,
        object_id=object_id,
        object_repr=object_repr,
        changes=changes,
        context=context,
    )


def _json_safe(value: Any) -> Any:
    """แปลงค่าให้เก็บเป็น JSON ได้: ชนิดพื้นฐานคงเดิม, วันที่เป็น ISO, อย่างอื่นเป็นข้อความ"""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, datetime.date):  # datetime.datetime เป็นลูกของ date จึงครอบคลุมทั้งคู่
        return value.isoformat()
    return str(value)


def field_changes(
    before: Mapping[str, Any], after: Mapping[str, Any], fields: Iterable[str]
) -> dict:
    """เทียบค่าเดิม/ค่าใหม่เฉพาะ "ฟิลด์ที่ระบุ" แล้วคืน {"ฟิลด์": [เดิม, ใหม่]} เฉพาะที่เปลี่ยน

    ระบุฟิลด์เป็น whitelist ทุกครั้ง จึงไม่มีทางที่รหัสผ่านหรือโทเคนจะหลุดเข้า log
    (ฟิลด์ที่ไม่ได้ระบุไม่ถูกเทียบและไม่ถูกเก็บ แม้จะอยู่ใน before/after)
    ระบุฟิลด์ที่ไม่มีใน before หรือ after จะโยน KeyError — พิมพ์ชื่อผิดแล้วตกหล่นเงียบ ๆ ไม่ได้
    """
    changes = {}
    for name in fields:
        old, new = before[name], after[name]
        if old != new:
            changes[name] = [_json_safe(old), _json_safe(new)]
    return changes


def request_context(request) -> dict:
    """ที่มาของคำขอสำหรับเก็บใน AuditLog.context: IP, user-agent, path

    - IP มาจาก REMOTE_ADDR เท่านั้น ไม่เชื่อ X-Forwarded-For เพราะผู้ส่งปลอมค่าได้เอง — เมื่ออยู่หลัง proxy
      ค่านี้จะเป็น IP ของ proxy จนกว่าจะตั้งค่า proxy ที่เชื่อถือได้ (ดู docs/pre-deploy-checklist.md)
    - path ไม่รวม query string เพราะ query อาจมีโทเคนในลิงก์ (เช่น ?token=...)
    รับได้ทั้ง HttpRequest ของ Django และ Request ของ DRF
    """
    return {
        "ip": request.META.get("REMOTE_ADDR"),
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:MAX_USER_AGENT_LENGTH],
        "path": request.path[:MAX_PATH_LENGTH],
    }
