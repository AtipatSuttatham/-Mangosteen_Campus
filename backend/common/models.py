"""โมเดล abstract ที่ใช้ร่วมกันทุกแอป (docs/database.md §1)

ตอนนี้มี TimeStampedModel — Auditable / SoftDeleteModel จะเพิ่มพร้อมฟีเจอร์แรกที่ใช้งานจริง
"""

from django.db import models


class TimeStampedModel(models.Model):
    """เพิ่มเวลาสร้าง/แก้ไขล่าสุดให้ทุกตารางที่ inherit (เก็บเป็น UTC แสดงผลเป็น Asia/Bangkok)"""

    # ตั้งอัตโนมัติครั้งเดียวตอนสร้างแถว
    created_at = models.DateTimeField(auto_now_add=True)
    # อัปเดตอัตโนมัติทุกครั้งที่บันทึก
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # abstract = ไม่สร้างตารางของตัวเอง ใช้เป็นแม่แบบให้โมเดลอื่นเท่านั้น
        abstract = True
