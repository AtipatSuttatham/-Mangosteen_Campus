# โครงสร้างโปรเจกต์

> ต้องอัปเดตไฟล์นี้ทุกครั้งที่เพิ่ม/ย้าย/ลบไฟล์หรือโฟลเดอร์สำคัญ (ดู `CLAUDE.md`)
> ไม่ลิสต์ของที่ generate เอง (`.venv/`, `node_modules/`, `dist/`, `__pycache__/`)

```
Mangosteen_Campus/
├── CLAUDE.md               กติกาโปรเจกต์ + tech stack + สิทธิ์ตาม role (อ่านก่อนเริ่มงานทุกครั้ง)
├── README.md               วิธีรันในเครื่อง (dev) + คำสั่งตรวจโค้ดก่อน push
├── PROJECT_STRUCTURE.md    ไฟล์นี้ — แผนที่โครงสร้างไฟล์/โฟลเดอร์
├── .gitattributes          บังคับ line ending เป็น LF ทั้ง repo และระบุไฟล์ไบนารี
├── .gitignore              ไฟล์ที่ห้ามเข้า git (.env, .venv, node_modules ฯลฯ)
├── .env.example            ตัวอย่างค่า environment (คัดลอกเป็น .env ที่ root แล้วแก้ค่า)
├── docker-compose.yml      รัน PostgreSQL ตอน dev (เฉพาะ DB — backend/frontend รันตรงบนเครื่อง)
│
├── .github/
│   └── workflows/
│       └── ci.yml            CI (GitHub Actions): backend = ruff + pytest / frontend = tsc + eslint + vitest
│
├── docs/                   เอกสารออกแบบ
│   ├── database.md           สเปกฐานข้อมูลเต็ม (field / constraint / ความสัมพันธ์) v1.3 freeze
│   ├── database-guide.md     ใครเขียน/ใครอ่านแต่ละตาราง, state machine, workflow ครบวงจร
│   ├── database-erd.md       ERD แบบ Mermaid แยกตามโดเมน
│   ├── database-fields.md    สรุป field ทุกตารางแบบ quick reference
│   └── design.md             แนวทางดีไซน์ UI (สี ฟอนต์ โครงหน้า) + สถานะ wireframe
│
├── backend/                Django 5.2 + DRF (จัดการแพ็กเกจด้วย uv)
│   ├── pyproject.toml        dependency + ตั้งค่า pytest / ruff
│   ├── uv.lock               ล็อกเวอร์ชัน dependency (commit เสมอ)
│   ├── manage.py             ตัวสั่งงาน Django (runserver, migrate ฯลฯ)
│   ├── config/               ตัวโปรเจกต์ Django
│   │   ├── settings.py         ตั้งค่าทั้งหมด (อ่านจาก env: DB, secret, host; เขตเวลา Asia/Bangkok)
│   │   ├── urls.py             URL หลัก — API ทั้งหมดอยู่ใต้ /api/
│   │   ├── wsgi.py             จุดเข้าแบบ WSGI (ใช้ตอน deploy)
│   │   └── asgi.py             จุดเข้าแบบ ASGI
│   ├── common/               แอปกลางที่ใช้ร่วมกัน
│   │   ├── models.py           abstract model กลาง: TimeStampedModel (Auditable / SoftDeleteModel จะเพิ่มภายหลัง)
│   │   ├── views.py            health check (`GET /api/health/`)
│   │   └── test_health.py      test ของ health check
│   └── accounts/             บัญชีผู้ใช้ (ต่อไปคือล็อกอิน/สมัคร/ยืนยันอีเมล)
│       ├── models.py           User แบบกำหนดเอง (อีเมลเป็นตัวล็อกอิน + รหัสนักศึกษา/พนักงาน + role) พร้อม constraint
│       ├── roles.py            บทบาทระดับระบบ: admin / teacher / student
│       ├── validators.py       ตรวจรหัสนักศึกษา/พนักงาน (ห้ามมี @)
│       ├── managers.py         create_user / create_superuser
│       ├── forms.py            ฟอร์มสร้าง/แก้ผู้ใช้ในหน้า Django admin
│       ├── admin.py            หน้าจัดการผู้ใช้ใน Django admin (ใช้ชั่วคราวก่อนมีหน้าจัดการจริง)
│       ├── migrations/         migration ของแอปนี้ (0001 = ตารางผู้ใช้ ซึ่งเป็น migration แรกของโปรเจกต์)
│       ├── test_models.py      test กฎของ User (normalize อีเมล/รหัส, unique, constraint ของฐานข้อมูล)
│       └── test_admin.py       test หน้า admin และคำสั่ง createsuperuser
│
└── frontend/               React 19 + Vite + TypeScript + Tailwind v4 (จัดการแพ็กเกจด้วย pnpm)
    ├── package.json          dependency + สคริปต์ (dev / build / typecheck / lint / test)
    ├── pnpm-lock.yaml        ล็อกเวอร์ชัน dependency (commit เสมอ)
    ├── index.html            หน้า HTML ตั้งต้นของ SPA (lang=th)
    ├── vite.config.ts        ตั้งค่า Vite: Tailwind, proxy /api → Django, ตั้งค่า vitest
    ├── eslint.config.js      กฎ ESLint (TypeScript + React hooks)
    ├── tsconfig*.json        ตั้งค่า TypeScript (app = โค้ดแอป, node = ไฟล์ config)
    ├── public/
    │   └── favicon.svg       ไอคอนแท็บเบราว์เซอร์ (ตราดอก 6 กลีบ)
    └── src/
        ├── main.tsx          จุดเริ่มแอป: โหลดฟอนต์/สไตล์/i18n แล้ว render ภายใต้ QueryClientProvider
        ├── App.tsx           หน้าเริ่มต้นชั่วคราว (จะถูกแทนด้วยหน้า login/dashboard)
        ├── App.test.tsx      test ของ App (ภาษา ไทย/อังกฤษ + สถานะเชื่อมต่อ backend)
        ├── index.css         Tailwind + โทเคนสี/ฟอนต์ของแบรนด์ (@theme)
        ├── components/       component ที่ใช้ซ้ำ: LogoMark (ตราดอก), LanguageToggle (สลับ TH/EN)
        ├── i18n/             ระบบหลายภาษา: index.ts (ตั้งค่า, ค่าเริ่มต้น = ไทย) + locales/th.json, en.json
        ├── lib/api.ts        ฟังก์ชันเรียก backend (ตอนนี้มีแค่ health check)
        └── test/setup.ts     ตั้งค่าที่รันก่อนทุก test
```

## ที่ยังไม่มี (จะเพิ่มตามลำดับ)
- แอป backend อื่นตาม `docs/database.md` §2 (academics, enrollment ฯลฯ) — เพิ่มพร้อมฟีเจอร์ที่ใช้
- หน้าจอจริงตาม wireframe (login, dashboard ฯลฯ) และ React Router
