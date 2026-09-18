"""Django settings ของโปรเจกต์ LMS

ค่าที่เปลี่ยนตามเครื่อง/สภาพแวดล้อม (secret, DB, host) อ่านจาก environment variable
ดูตัวอย่างค่าที่ต้องตั้งใน `.env.example` ที่ root ของ repo
"""

import os
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

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "common",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ไม่ตั้ง CORS: frontend เรียก /api ผ่าน proxy (Vite ตอน dev / hosting ตอน deploy) จึงเป็น origin เดียวกัน
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # ก้อนถัดไป (ระบบ login) จะเพิ่ม JWT ที่นี่ — ตอนนี้ยังไม่มีวิธียืนยันตัวตน
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    # ปลอดภัยไว้ก่อน: endpoint ต้อง login เสมอ ยกเว้นระบุ AllowAny เป็นรายตัว
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
