import io

from django.core.mail import EmailMessage

from common.dev_email_backend import ConsoleEmailBackend


class LimitedStream(io.TextIOWrapper):
    """จำลองคอนโซลที่พิมพ์ภาษาไทยไม่ได้ (เหมือน cp1252 บน Windows)"""

    def __init__(self):
        super().__init__(io.BytesIO(), encoding="cp1252", write_through=True)

    def written(self) -> str:
        return self.buffer.getvalue().decode("cp1252")


def make_message():
    return EmailMessage(
        subject="ยืนยันอีเมล / Verify",
        body="สวัสดี\nhttp://localhost:5180/verify-email?token=abc-DEF_123\nHello",
        from_email="Mangosteen Campus <noreply@mangosteen.test>",
        to=["student@example.com"],
    )


def test_does_not_crash_when_the_console_cannot_print_thai():
    stream = LimitedStream()

    sent = ConsoleEmailBackend(stream=stream).send_messages([make_message()])

    assert sent == 1
    output = stream.written()
    # ลิงก์ (อังกฤษล้วน) ต้องอ่านออกครบ แม้ภาษาไทยถูกแทนด้วย ?
    assert "http://localhost:5180/verify-email?token=abc-DEF_123" in output
    assert "To: student@example.com" in output
    assert "Subject: ?" in output


def test_prints_thai_normally_when_the_console_supports_it():
    stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", write_through=True)

    ConsoleEmailBackend(stream=stream).send_messages([make_message()])

    assert "สวัสดี" in stream.buffer.getvalue().decode("utf-8")
