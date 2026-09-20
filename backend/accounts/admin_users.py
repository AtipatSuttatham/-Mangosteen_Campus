"""ค้นหา/กรอง/เรียงรายชื่อผู้ใช้สำหรับหน้าจัดการผู้ใช้ของ Admin (ก้อน d2)

ทุกฟังก์ชันไม่รู้จัก HTTP — view เรียกใช้ แล้วแปลงผลเป็นคำตอบของ API
สัญญากับหน้าเว็บอยู่ที่ docs/api-admin-users.md
"""

from django.db.models import Count, Q, QuerySet

from .models import User
from .roles import Role
from .user_status import status_filter

# ข้อความค้นหายาวสุดกี่ตัวอักษร (ตรวจที่ serializer) และใช้กี่คำแรก
# ผู้ใช้ค้นชื่อ/รหัส/อีเมลไม่เกินไม่กี่คำ ตัดส่วนเกินทิ้งกันคำขอที่สร้างเงื่อนไขหนักโดยไม่จำเป็น
MAX_SEARCH_LENGTH = 100
MAX_SEARCH_TERMS = 5

# ฟิลด์ที่ค้นหาได้ (ชื่อไทย/อังกฤษ อีเมล รหัสนักศึกษา/พนักงาน)
SEARCH_FIELDS = (
    "first_name",
    "last_name",
    "first_name_en",
    "last_name_en",
    "email",
    "student_or_staff_id",
)


def search_terms(text: str) -> list[str]:
    """แยกข้อความค้นหาเป็นคำ (ตัดด้วยช่องว่าง) ใช้ไม่เกิน MAX_SEARCH_TERMS คำแรก"""
    return text.split()[:MAX_SEARCH_TERMS]


def filtered_users(*, status: str | None = None, search: str = "") -> QuerySet[User]:
    """ผู้ใช้ที่ผ่านตัวกรองสถานะและคำค้น (ยังไม่กรองบทบาท) — ใช้ทั้งรายการและตัวเลขบนแท็บบทบาท

    คำค้น: "ทุกคำ" ต้องเจอในฟิลด์ใดฟิลด์หนึ่งของ SEARCH_FIELDS ("ณัฐพล เมือง" เจอคนเดียวที่มีทั้งสองคำ)
    เจอบางส่วนของคำได้ ไม่สนตัวพิมพ์เล็ก/ใหญ่ และเครื่องหมาย % กับ _ ที่พิมพ์มาถือเป็นตัวอักษรธรรมดา
    (Django escape ให้ตอนใช้ icontains)
    """
    queryset = User.objects.all()
    if status:
        queryset = queryset.filter(status_filter(status))
    for term in search_terms(search):
        any_field = Q()
        for field in SEARCH_FIELDS:
            any_field |= Q(**{f"{field}__icontains": term})
        # filter ต่อกันทีละคำ = AND ระหว่างคำ, OR ระหว่างฟิลด์
        queryset = queryset.filter(any_field)
    return queryset


def list_users(
    *, role: str | None = None, status: str | None = None, search: str = ""
) -> QuerySet[User]:
    """รายชื่อผู้ใช้ตามตัวกรอง เรียงบัญชีที่สร้างล่าสุดก่อน

    เรียงด้วย id ต่อท้ายเสมอ: ถ้าเวลาสร้างเท่ากัน (เช่นนำเข้าพร้อมกัน) ลำดับต้องคงที่
    ไม่เช่นนั้นแบ่งหน้าแล้วคนซ้ำหรือตกหล่นระหว่างหน้า
    """
    queryset = filtered_users(status=status, search=search)
    if role:
        queryset = queryset.filter(role=role)
    return queryset.order_by("-date_joined", "-id")


def role_counts(*, status: str | None = None, search: str = "") -> dict[str, int]:
    """จำนวนผู้ใช้ต่อบทบาทสำหรับแท็บบนหน้ารายชื่อ: {"all", "admin", "teacher", "student"}

    นับตามคำค้นและตัวกรองสถานะ แต่ "ไม่นับตามตัวกรองบทบาท" (ไม่งั้นแท็บอื่นเป็นศูนย์หมด)
    ใช้คิวรีเดียว และบทบาทที่ไม่มีผู้ใช้ตอบ 0 ไม่ตัดคีย์ทิ้ง
    """
    rows = filtered_users(status=status, search=search).order_by().values("role")
    counts = {role: 0 for role in Role.values}
    for row in rows.annotate(total=Count("id")):
        counts[row["role"]] = row["total"]
    return {"all": sum(counts.values()), **counts}
