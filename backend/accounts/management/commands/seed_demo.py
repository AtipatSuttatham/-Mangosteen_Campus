import os

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from accounts.roles import Role

# บัญชีทดสอบ 1 บัญชีต่อบทบาท — อีเมลใช้โดเมน .test (โดเมนสงวน ไม่มีอีเมลจริงถูกส่งออกไปข้างนอก)
# ล็อกอินได้ทั้งด้วยรหัส (student_or_staff_id) หรืออีเมล
DEMO_ACCOUNTS = [
    {
        "role": Role.ADMIN,
        "student_or_staff_id": "ADM001",
        "email": "admin.demo@mangosteen.test",
        "first_name": "แอดมิน",
        "last_name": "ทดสอบ",
    },
    {
        "role": Role.TEACHER,
        "student_or_staff_id": "TCH001",
        "email": "teacher.demo@mangosteen.test",
        "first_name": "สมศรี",
        "last_name": "ผู้สอน",
    },
    {
        "role": Role.STUDENT,
        "student_or_staff_id": "6501001",
        "email": "student.demo@mangosteen.test",
        "first_name": "มานี",
        "last_name": "ผู้เรียน",
    },
]

# ชื่อตัวแปร environment ที่เก็บรหัสผ่านของบัญชีทดสอบ (ตั้งใน .env ที่ไม่เข้า git)
PASSWORD_ENV_NAME = "DEMO_PASSWORD"


class Command(BaseCommand):
    # ข้อความที่พิมพ์ออกหน้าจอเป็นอังกฤษล้วน (ASCII) เพราะคอนโซล Windows หลายแบบ
    # (cp1252/cp437) พิมพ์ภาษาไทยไม่ได้และจะ error ทั้งคำสั่ง — คอมเมนต์ในโค้ดยังเป็นภาษาไทยตามปกติ
    help = (
        "Create/reset the 3 demo accounts (dev only). Password is read from DEMO_PASSWORD in .env"
    )

    def handle(self, *args, **options):
        # รั้วกัน: ห้ามรันบนเว็บจริง เพราะจะเกิดบัญชี admin ที่ใครก็รู้รหัสได้ (docs/pre-deploy-checklist.md ข้อ 4)
        if not settings.DEBUG:
            raise CommandError("seed_demo only runs in dev mode (DJANGO_DEBUG=1)")

        # ไม่มีรหัสให้ = หยุด ไม่สุ่มหรือใช้ค่าเริ่มต้นให้ (repo เป็น public จึงห้ามมีรหัสตายตัวในโค้ด)
        password = os.environ.get(PASSWORD_ENV_NAME, "")
        if not password:
            raise CommandError(
                f"{PASSWORD_ENV_NAME} is not set - add {PASSWORD_ENV_NAME}=<your password> to .env "
                "and run again with --env-file ../.env"
            )

        # กันตั้งรหัสอ่อนเกินไป ด้วยตัวตรวจเดียวกับที่ตั้งไว้ใน AUTH_PASSWORD_VALIDATORS
        try:
            validate_password(password)
        except ValidationError as error:
            raise CommandError(
                f"{PASSWORD_ENV_NAME} is not acceptable: {' '.join(error.messages)}"
            ) from error

        # ทำทั้งหมดในธุรกรรมเดียว — ถ้าบัญชีไหนพลาดจะไม่เหลือบัญชีที่สร้างค้างครึ่งทาง
        with transaction.atomic():
            for account in DEMO_ACCOUNTS:
                created = self._upsert(account, password)
                status = "created" if created else "updated"
                self.stdout.write(
                    f"{status}: {account['role']:<8} "
                    f"{account['student_or_staff_id']} / {account['email']}"
                )

        self.stdout.write(
            self.style.SUCCESS("Done - log in with the ID or email above and the DEMO_PASSWORD")
        )

    def _upsert(self, account: dict, password: str) -> bool:
        """สร้างบัญชี ถ้ามีอีเมลนี้อยู่แล้วให้แก้ข้อมูลและรหัสผ่านให้ตรง (คืน True เมื่อสร้างใหม่)"""
        # รหัสนี้ต้องไม่ถูกบัญชีอื่น (คนละอีเมล) ถือไว้ — ไม่แตะบัญชีของคนอื่นเงียบ ๆ
        holder = User.objects.filter(student_or_staff_id=account["student_or_staff_id"]).first()
        if holder is not None and holder.email != account["email"]:
            raise CommandError(
                f"ID {account['student_or_staff_id']} belongs to another account ({holder.email}) "
                "- nothing was changed"
            )

        user = User.objects.filter(email=account["email"]).first()
        created = user is None
        if created:
            user = User(email=account["email"])

        user.role = account["role"]
        user.student_or_staff_id = account["student_or_staff_id"]
        user.first_name = account["first_name"]
        user.last_name = account["last_name"]
        # บัญชีที่ Admin/ระบบสร้างให้ ถือว่าเจ้าของยืนยันอีเมลแล้ว (ตามที่ตัดสินใจไว้)
        user.is_email_verified = True
        user.is_active = True
        user.set_password(password)
        user.save()
        return created
