from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

from common.models import TimeStampedModel

from .managers import UserManager
from .roles import Role
from .validators import validate_staff_id


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """บัญชีผู้ใช้ทุกคน (ผู้ดูแลระบบ / ผู้สอน / ผู้เรียน) ตาม docs/database.md §3

    เข้าสู่ระบบได้ 2 ทาง: อีเมล หรือรหัสนักศึกษา/พนักงาน (ช่องเดียว แยกด้วยอักขระ @)
    """

    # อีเมล: เก็บเป็นตัวพิมพ์เล็กเสมอ จึงห้ามซ้ำแบบไม่สนตัวพิมพ์ (แปลงใน normalize_fields)
    email = models.EmailField("อีเมล", unique=True)
    # รหัสนักศึกษา/พนักงาน: ว่างได้ (NULL) เช่นผู้เรียนที่สมัครเอง; แยกตัวพิมพ์เล็ก/ใหญ่; ห้ามมี @
    student_or_staff_id = models.CharField(
        "รหัสนักศึกษา/พนักงาน",
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        validators=[validate_staff_id],
    )
    # บทบาทระดับระบบ (สิทธิ์รายวิชาดูจากตารางอื่น — ดู roles.py)
    role = models.CharField("บทบาท", max_length=10, choices=Role.choices, default=Role.STUDENT)

    first_name = models.CharField("ชื่อ", max_length=150)
    last_name = models.CharField("นามสกุล", max_length=150)
    # ชื่อภาษาอังกฤษของบุคคล (ไม่บังคับ) ใช้ในเอกสาร/รายชื่อทางการ
    first_name_en = models.CharField("ชื่อ (อังกฤษ)", max_length=150, blank=True)
    last_name_en = models.CharField("นามสกุล (อังกฤษ)", max_length=150, blank=True)

    # ยืนยันอีเมลแล้วหรือยัง — บัญชีสมัครเองต้องเป็น True ก่อนเข้าใช้งาน
    is_email_verified = models.BooleanField("ยืนยันอีเมลแล้ว", default=False)
    # Admin ปิดบัญชีได้ด้วยการตั้งเป็น False (ผู้ใช้ที่มีประวัติเรียน/สอนไม่ลบจริง)
    is_active = models.BooleanField("เปิดใช้งาน", default=True)
    # สิทธิ์เข้าหน้า Django admin เท่านั้น (คนละเรื่องกับ role); is_superuser มาจาก PermissionsMixin
    is_staff = models.BooleanField("เข้า Django admin ได้", default=False)

    avatar_url = models.URLField("รูปโปรไฟล์", max_length=500, blank=True)
    # ใครสร้างบัญชีนี้ (ว่าง = สมัครเอง)
    created_by = models.ForeignKey(
        "self",
        verbose_name="สร้างโดย",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_users",
    )
    date_joined = models.DateTimeField("วันที่เริ่มใช้งาน", default=timezone.now)

    objects = UserManager()

    # ใช้อีเมลเป็นตัวระบุตัวตนของ Django (createsuperuser, หน้า admin login)
    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    # ช่องที่ createsuperuser ต้องถามเพิ่มนอกจากอีเมลและรหัสผ่าน
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "ผู้ใช้"
        verbose_name_plural = "ผู้ใช้"
        # กฎเดียวกับ normalize_fields แต่บังคับที่ระดับฐานข้อมูลเป็นตาข่ายกันพลาด
        # (กันข้อมูลที่เขียนเลี่ยง save() เช่น bulk_create หรือ SQL ตรง ๆ)
        constraints = [
            models.CheckConstraint(
                condition=Q(email=Lower("email")),
                name="accounts_user_email_lowercase",
            ),
            models.CheckConstraint(
                condition=Q(student_or_staff_id__isnull=True)
                | (~Q(student_or_staff_id="") & ~Q(student_or_staff_id__contains="@")),
                name="accounts_user_staff_id_valid",
            ),
            models.CheckConstraint(
                condition=Q(role__in=Role.values),
                name="accounts_user_role_valid",
            ),
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        """ชื่อเต็มสำหรับแสดงผล (ชื่อ + นามสกุล ตามที่ผู้ใช้กรอก)"""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    def normalize_fields(self):
        """แปลงข้อมูลให้เป็นรูปแบบเดียวกันก่อนบันทึก

        - อีเมล: ตัดช่องว่างหัวท้าย + ตัวพิมพ์เล็กทั้งหมด
        - รหัสนักศึกษา/พนักงาน: ตัดช่องว่างหัวท้าย (แยกตัวพิมพ์เล็ก/ใหญ่ ไม่แปลง) ถ้าว่างให้เป็น NULL
        """
        if self.email:
            self.email = self.email.strip().lower()
        if self.student_or_staff_id is not None:
            # สตริงว่างต้องเก็บเป็น NULL ไม่เช่นนั้นผู้ใช้ 2 คนที่ไม่มีรหัสจะชน unique กัน
            self.student_or_staff_id = self.student_or_staff_id.strip() or None

    def clean(self):
        super().clean()
        # ให้ฟอร์ม (เช่นหน้า Django admin) ตรวจ unique กับค่าที่ normalize แล้ว
        self.normalize_fields()

    def save(self, *args, **kwargs):
        # ทุกทางที่บันทึกผ่าน ORM ได้ข้อมูลรูปแบบเดียวกันเสมอ
        self.normalize_fields()
        super().save(*args, **kwargs)
