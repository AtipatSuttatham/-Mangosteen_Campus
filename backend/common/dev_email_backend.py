"""ตัวส่งอีเมลสำหรับ dev: พิมพ์อีเมลลงคอนโซลแทนการส่งจริง

ทำไมไม่ใช้ console backend ของ Django ตรง ๆ: คอนโซลบน Windows หลายแบบ (cp1252/cp437) พิมพ์ภาษาไทยไม่ได้
Django จะ error (UnicodeEncodeError) ทำให้ขั้นตอนสมัคร/ลืมรหัสผ่านล้มด้วย ตัวนี้พิมพ์แบบไม่ล้ม
ตัวอักษรที่คอนโซลแสดงไม่ได้จะกลายเป็น "?" แต่ลิงก์ในอีเมลเป็นอังกฤษล้วน จึงอ่านและคัดลอกได้เสมอ
"""

import sys

from django.core.mail.backends.console import EmailBackend


class ConsoleEmailBackend(EmailBackend):
    """พิมพ์ผู้ส่ง/ผู้รับ/หัวข้อ/เนื้อหาของอีเมลลงคอนโซลอย่างปลอดภัย"""

    def write_message(self, message):
        # ประกอบข้อความอ่านง่าย (ไม่พิมพ์ header MIME ดิบที่เข้ารหัสจนอ่านไม่ออก)
        text = "\n".join(
            [
                "-" * 60,
                f"From: {message.from_email}",
                f"To: {', '.join(message.to)}",
                f"Subject: {message.subject}",
                "",
                message.body,
                "-" * 60,
                "",
            ]
        )
        # แปลงเป็นรหัสตัวอักษรของคอนโซลปลายทาง โดยตัวที่พิมพ์ไม่ได้แทนด้วย "?" แทนที่จะ error
        encoding = getattr(self.stream, "encoding", None) or sys.getdefaultencoding()
        self.stream.write(text.encode(encoding, errors="replace").decode(encoding))
