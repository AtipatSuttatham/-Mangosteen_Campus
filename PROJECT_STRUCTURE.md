# โครงสร้างโปรเจกต์

> ต้องอัปเดตไฟล์นี้ทุกครั้งที่เพิ่ม/ย้าย/ลบไฟล์หรือโฟลเดอร์สำคัญ (ดู `CLAUDE.md`)
> ไม่ลิสต์ของที่ generate เอง (`.venv/`, `node_modules/`, `__pycache__/`)

```
Mangosteen_Campus/
├── CLAUDE.md               กติกาโปรเจกต์ + tech stack + สิทธิ์ตาม role (อ่านก่อนเริ่มงานทุกครั้ง)
├── PROJECT_STRUCTURE.md    ไฟล์นี้ — แผนที่โครงสร้างไฟล์/โฟลเดอร์
├── .gitattributes          บังคับ line ending เป็น LF ทั้ง repo และระบุไฟล์ไบนารี
├── .gitignore              ไฟล์ที่ห้ามเข้า git (.env, .venv, node_modules ฯลฯ)
├── .env.example            ตัวอย่างค่า environment (คัดลอกเป็น .env ที่ root แล้วแก้ค่า)
├── docker-compose.yml      รัน PostgreSQL ตอน dev (เฉพาะ DB — backend/frontend รันตรงบนเครื่อง)
│
├── docs/                   เอกสารออกแบบ
│   ├── database.md           สเปกฐานข้อมูลเต็ม (field / constraint / ความสัมพันธ์) v1.3 freeze
│   ├── database-guide.md     ใครเขียน/ใครอ่านแต่ละตาราง, state machine, workflow ครบวงจร
│   ├── database-erd.md       ERD แบบ Mermaid แยกตามโดเมน
│   ├── database-fields.md    สรุป field ทุกตารางแบบ quick reference
│   └── design.md             แนวทางดีไซน์ UI (สี ฟอนต์ โครงหน้า) + สถานะ wireframe
│
└── backend/                Django 5.2 + DRF (จัดการแพ็กเกจด้วย uv)
    ├── pyproject.toml        dependency + ตั้งค่า pytest / ruff
    ├── uv.lock               ล็อกเวอร์ชัน dependency (commit เสมอ)
    ├── manage.py             ตัวสั่งงาน Django (runserver, migrate ฯลฯ)
    ├── config/               ตัวโปรเจกต์ Django
    │   ├── settings.py         ตั้งค่าทั้งหมด (อ่านจาก env: DB, secret, host; เขตเวลา Asia/Bangkok)
    │   ├── urls.py             URL หลัก — API ทั้งหมดอยู่ใต้ /api/
    │   ├── wsgi.py             จุดเข้าแบบ WSGI (ใช้ตอน deploy)
    │   └── asgi.py             จุดเข้าแบบ ASGI
    └── common/               แอปกลางที่ใช้ร่วมกัน
        ├── models.py           (ว่าง) จะเป็นที่อยู่ของ abstract model: TimeStampedModel / Auditable / SoftDeleteModel
        ├── views.py            health check (`GET /api/health/`)
        └── test_health.py      test ของ health check
```

## ที่ยังไม่มี (จะเพิ่มตามลำดับ)
- `frontend/` — React + Vite + TypeScript + Tailwind v4
- `.github/workflows/` — CI (backend: pytest + ruff / frontend: tsc + eslint + vitest)
- แอป backend อื่นตาม `docs/database.md` §2 (accounts, academics, ฯลฯ) — เพิ่มพร้อมฟีเจอร์ที่ใช้
