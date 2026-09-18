"""จุดเข้าแบบ WSGI ของโปรเจกต์ — เซิร์ฟเวอร์ production (เช่น gunicorn) เรียกตัวแปร `application`"""

import os

from django.core.wsgi import get_wsgi_application

# ระบุไฟล์ settings ที่ใช้ (ถ้ายังไม่ได้ตั้งไว้ใน environment)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# ตัวแอปที่เซิร์ฟเวอร์ WSGI นำไปรันรับ request
application = get_wsgi_application()
