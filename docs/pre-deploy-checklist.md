# เช็กลิสต์ก่อนขึ้นเว็บจริง (deploy)

> รวบรวมสิ่งที่ "ตั้งใจเลื่อนไว้" ระหว่างพัฒนา เพื่อไม่ให้ลืมก่อนเปิดให้คนจริงใช้ — เพิ่มข้อได้เรื่อย ๆ
> ผลตรวจล่าสุดของ `manage.py check --deploy` (ตั้ง DEBUG=0): มี 5 คำเตือน ซึ่งปิดได้ด้วยข้อ 2

## ความปลอดภัย (ต้องทำก่อนเปิดใช้งาน)
1. **จำกัดจำนวนครั้งที่ล็อกอินผิด** (ต่อรหัส/อีเมล และต่อ IP) — ตอนนี้ไม่มี; รวมถึง endpoint กรอกรหัสเข้าเรียนเมื่อทำ
2. **ตั้งค่า Django สำหรับ production** (ตอนนี้ `settings.py` ยังไม่มีค่าเหล่านี้):
   - `DJANGO_DEBUG=0` และ `DJANGO_SECRET_KEY` เป็นค่าสุ่มยาวอย่างน้อย 50 ตัวอักษร (ตั้งใน environment ของ hosting ไม่ใส่ใน git)
   - `DJANGO_ALLOWED_HOSTS` เป็นโดเมนจริง
   - `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True` (ใช้กับหน้า Django admin)
   - `SECURE_SSL_REDIRECT=True` (หรือให้ proxy/hosting บังคับ https) และ `SECURE_PROXY_SSL_HEADER` ถ้าอยู่หลัง proxy
   - `SECURE_HSTS_SECONDS` (เริ่มด้วยค่าน้อย แล้วค่อยเพิ่ม)
   - `CSRF_TRUSTED_ORIGINS` เป็นโดเมนจริง
   - รัน `uv run python manage.py check --deploy` ให้ไม่เหลือคำเตือน
3. **cookie ของ refresh token:** ตั้ง Secure อัตโนมัติเมื่อ `DEBUG=0` — ตรวจว่า hosting ที่เลือกส่งต่อ `Set-Cookie` และ path `/api/auth/` ผ่าน proxy ได้ และเว็บกับ API เป็น same-site (`docs/api-auth.md`)
4. **ไม่มีบัญชีทดสอบ:** ไม่รัน `seed_demo` บนเว็บจริง (คำสั่งมีรั้วกันให้ทำงานเฉพาะ DEBUG=1 และต้องมี `DEMO_PASSWORD` — ไม่ตั้งค่านี้บนเว็บจริง) และสร้างผู้ดูแลระบบจริงด้วย `createsuperuser`
5. **repo เป็น public:** ตรวจอีกครั้งว่าไม่มีความลับในประวัติ git และไม่มี `.env` ที่ถูก commit (ตอนนี้ตรวจแล้วไม่มี)

## ข้อมูลและงานเบื้องหลัง
6. **ลบ token ที่หมดอายุ** เป็นระยะ ด้วยคำสั่ง `flushexpiredtokens` ของ simplejwt
7. **ตัวตั้งเวลาสำหรับส่งควิซอัตโนมัติ** (คำสั่ง management รันทุกนาที) — เป็นเงื่อนไขในการเลือก hosting (ต้องรองรับ cron หรือรันตลอด)
8. **สำรองข้อมูลฐานข้อมูลอัตโนมัติ** และใช้ผู้ใช้ฐานข้อมูลที่ไม่ใช่ superuser
9. **อีเมลจริง:** ตอนนี้ใช้ console backend (ลิงก์แสดงใน terminal) — ต้องเลือก provider ก่อนให้ผู้ใช้จริงสมัคร/ตั้งรหัสผ่าน (ยังไม่ได้เลือก)
10. **Audit Log** ของการล็อกอิน/ออกจากระบบ (รอทำระบบ Audit)
11. **เก็บความลับเป็น environment variable เสมอ** เช่น รหัสฐานข้อมูล, Cloudinary (เมื่อถึงเวลา)
