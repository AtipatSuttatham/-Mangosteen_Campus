"""Django settings ของโปรเจกต์ LMS

ค่าที่เปลี่ยนตามเครื่อง/สภาพแวดล้อม (secret, DB, host) อ่านจาก environment variable
ดูตัวอย่างค่าที่ต้องตั้งใน `.env.example` ที่ root ของ repo
"""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    # อ่านค่า true/false จาก env (รับ 1/true/yes/on)
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DEBUG = env_bool("DJANGO_DEBUG", False)

# SECRET_KEY: ตอน dev (DEBUG=1) มีค่าสำรองให้ ส่วน production ต้องตั้งเอง ไม่ตั้ง = แอปไม่ยอมเริ่ม
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"
    else:
        raise RuntimeError("ต้องตั้งค่า DJANGO_SECRET_KEY (หรือเปิด DJANGO_DEBUG=1 เฉพาะตอน dev)")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

# แอปที่เปิดใช้งาน: ของ Django เอง + DRF + แอปของโปรเจกต์ (เพิ่มแอปใหม่ต่อท้ายตามฟีเจอร์)
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    # ตารางบันทึก refresh token ที่ถูกเพิกถอนแล้ว (ออกจากระบบ / ถูกหมุนเวียนแทนที่)
    "rest_framework_simplejwt.token_blacklist",
    "common",
    "accounts",
    # ประวัติการกระทำที่เปลี่ยนแปลงข้อมูลสำคัญ (Audit Log)
    "audit",
]

# ใช้โมเดลผู้ใช้ของโปรเจกต์ (accounts.User) แทนของ Django — ต้องตั้งก่อน migrate ครั้งแรก
AUTH_USER_MODEL = "accounts.User"

# middleware ที่ทุก request ผ่านตามลำดับ (session/csrf ยังจำเป็นสำหรับหน้า Django admin)
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ไฟล์ URL หลักของโปรเจกต์
ROOT_URLCONF = "config.urls"

# ระบบ template (ใช้กับหน้า Django admin และอีเมลแบบ template ภายหลัง)
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# จุดเข้าแบบ WSGI สำหรับเซิร์ฟเวอร์ production
WSGI_APPLICATION = "config.wsgi.application"

# ฐานข้อมูล: PostgreSQL (dev รันผ่าน docker-compose.yml ที่ root ของ repo)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "mangosteen"),
        "USER": os.environ.get("POSTGRES_USER", "mangosteen"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# กฎตรวจรหัสผ่านตอนตั้ง/เปลี่ยน — ตรงกับรายการในหน้าตั้งรหัสผ่านของ wireframe
# (ยาวพอ / ไม่ใช่รหัสยอดนิยม / ไม่ใช่ตัวเลขล้วน / ไม่คล้ายข้อมูลผู้ใช้)
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ภาษา/เวลา: ค่าเริ่มต้นเป็นไทย, เก็บเวลาเป็น UTC ใน DB แล้วแปลงเป็น Asia/Bangkok ตอนแสดงผล
LANGUAGE_CODE = "th"
LANGUAGES = [("th", "ไทย"), ("en", "English")]
TIME_ZONE = "Asia/Bangkok"
USE_I18N = True
USE_TZ = True

# อีเมล: ตอน dev พิมพ์ลงคอนโซลแทนการส่งจริง (ตัวที่เขียนเองไม่ crash เมื่อคอนโซลพิมพ์ภาษาไทยไม่ได้)
# ตอนขึ้นเว็บจริงยังไม่ได้เลือก provider — ตั้ง DJANGO_EMAIL_BACKEND และค่า EMAIL_* เองผ่าน environment
# (โค้ดส่งอีเมลใช้ send_mail ของ Django จึงไม่ผูกกับ provider ใด)
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "common.dev_email_backend.ConsoleEmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.environ.get(
    "DJANGO_DEFAULT_FROM_EMAIL", "Mangosteen Campus <noreply@mangosteen.test>"
)

# ที่อยู่ของเว็บ (frontend) ที่ใช้ทำลิงก์ในอีเมล เช่น {FRONTEND_URL}/verify-email?token=...
# ตอน dev ใช้ค่าสำรองได้ ส่วนขึ้นเว็บจริงต้องตั้งเอง — ไม่ตั้ง = แอปไม่ยอมเริ่ม
# (กันส่งลิงก์ localhost ให้ผู้ใช้จริงโดยไม่ตั้งใจ)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "").strip().rstrip("/")
if not FRONTEND_URL:
    if DEBUG:
        FRONTEND_URL = "http://localhost:5180"
    else:
        raise RuntimeError("ต้องตั้งค่า FRONTEND_URL (ที่อยู่เว็บที่ใช้ทำลิงก์ในอีเมล)")

# ที่อยู่ URL ของไฟล์ static (ใช้กับหน้า Django admin)
STATIC_URL = "static/"

# ชนิด primary key เริ่มต้นของทุกตาราง (BigAutoField ตาม docs/database.md)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ไม่ตั้ง CORS: frontend เรียก /api ผ่าน proxy (Vite ตอน dev / hosting ตอน deploy) จึงเป็น origin เดียวกัน
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # ยืนยันตัวตนด้วย access token (JWT) ที่ส่งมาใน header "Authorization: Bearer ..."
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # ปลอดภัยไว้ก่อน: endpoint ต้อง login เสมอ ยกเว้นระบุ AllowAny เป็นรายตัว
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    # ทุก error ของ API มีฟิลด์ "code" ให้ frontend ใช้แปลข้อความเป็นไทย/อังกฤษ
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
}

# JWT: access token อายุสั้น (เก็บในหน่วยความจำของเว็บ) + refresh token อายุ 7 วัน (เก็บใน httpOnly cookie)
# การหมุนเวียน refresh token ทำเองใน accounts/tokens.py (ออก token ใหม่จากข้อมูลผู้ใช้ปัจจุบันทุกครั้ง)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
    # ไม่ให้ simplejwt หมุนเวียนเอง เพราะจะคัดลอก claim เดิม (เช่น role เก่า) ไปทุกครั้ง
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
}
