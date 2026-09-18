"""จุดเข้าแบบ ASGI ของโปรเจกต์ — เซิร์ฟเวอร์ที่รองรับ async (เช่น uvicorn) เรียกตัวแปร `application`"""

import os

from django.core.asgi import get_asgi_application

# ระบุไฟล์ settings ที่ใช้ (ถ้ายังไม่ได้ตั้งไว้ใน environment)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# ตัวแอปที่เซิร์ฟเวอร์ ASGI นำไปรันรับ request
application = get_asgi_application()
