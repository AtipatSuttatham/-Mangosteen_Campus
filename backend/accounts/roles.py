from django.db import models


class Role(models.TextChoices):
    """บทบาทระดับระบบของผู้ใช้ (1 บัญชี = 1 บทบาท)

    สิทธิ์ในแต่ละรายวิชาแยกอิสระจากบทบาทนี้ — ดูจาก CourseTeacher / Enrollment ต่อวิชา
    (เช่น ผู้เรียนเป็นผู้ช่วยสอนในวิชาหนึ่งได้)
    """

    ADMIN = "admin", "ผู้ดูแลระบบ"
    TEACHER = "teacher", "ผู้สอน"
    STUDENT = "student", "ผู้เรียน"
