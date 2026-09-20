from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """แบ่งหน้าแบบเลขหน้า ใช้ร่วมกันทุกรายการของระบบ (20 รายการต่อหน้า)

    ผู้เรียกกำหนดขนาดหน้าเองไม่ได้ (ไม่รับ page_size ใน URL) จึงไม่มีใครขอครั้งละหลายแสนแถวได้
    เลขหน้าที่ไม่ถูกต้องหรือเกินหน้าสุดท้าย → 404 (มาตรฐานของ DRF) หน้าเว็บกลับไปหน้า 1 เมื่อเปลี่ยนตัวกรอง

    คำตอบ: count (จำนวนทั้งหมด), page, page_size, total_pages, next, previous, results
    """

    page_size = 20
    # ไม่ตั้งชื่อพารามิเตอร์ขนาดหน้า = ผู้เรียกปรับขนาดไม่ได้
    page_size_query_param = None

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.page.paginator.per_page,
                "total_pages": self.page.paginator.num_pages,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
