#!/usr/bin/env python
"""ตัวสั่งงาน Django (runserver, migrate, createsuperuser ฯลฯ)"""

import os
import sys


def main():
    """เรียกคำสั่งจัดการของ Django ตามอาร์กิวเมนต์ที่ส่งมา"""
    # ระบุไฟล์ settings ที่ใช้ (ถ้ายังไม่ได้ตั้งไว้ใน environment)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # ยังไม่ได้ติดตั้ง Django หรือไม่ได้อยู่ใน virtual environment ของ uv
        raise ImportError(
            "ไม่พบ Django — ติดตั้งด้วย `uv sync` แล้วรันผ่าน `uv run python manage.py ...`"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
