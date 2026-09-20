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
│   ├── database.md           สเปกฐานข้อมูลเต็ม (field / constraint / ความสัมพันธ์) v1.4 freeze
│   ├── database-guide.md     ใครเขียน/ใครอ่านแต่ละตาราง, state machine, workflow ครบวงจร
│   ├── database-erd.md       ERD แบบ Mermaid แยกตามโดเมน
│   ├── database-fields.md    สรุป field ทุกตารางแบบ quick reference
│   ├── api-auth.md           สัญญา API ล็อกอิน (endpoint, cookie, รูปแบบ error) สำหรับฝั่งเว็บ
│   ├── pre-deploy-checklist.md  เช็กลิสต์สิ่งที่ต้องทำก่อนขึ้นเว็บจริง (ความปลอดภัย, งานเบื้องหลัง, อีเมล)
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
│   │   ├── test_health.py      test ของ health check
│   │   ├── exceptions.py       ตัวจัดการ error ของ API ทั้งระบบ — ทุก error มี `code` ให้ frontend ใช้แปลภาษา
│   │   ├── test_exceptions.py  test ของตัวจัดการ error
│   │   ├── dev_email_backend.py  ตัวส่งอีเมลตอน dev: พิมพ์ลงคอนโซลโดยไม่ crash เมื่อคอนโซล Windows พิมพ์ภาษาไทยไม่ได้
│   │   └── test_dev_email_backend.py  test ของตัวส่งอีเมลตอน dev
│   └── accounts/             บัญชีผู้ใช้ (ต่อไปคือล็อกอิน/สมัคร/ยืนยันอีเมล)
│       ├── models.py           User แบบกำหนดเอง (อีเมลเป็นตัวล็อกอิน + รหัสนักศึกษา/พนักงาน + role) และ EmailVerificationToken
│       ├── roles.py            บทบาทระดับระบบ: admin / teacher / student
│       ├── validators.py       ตรวจรหัสนักศึกษา/พนักงาน (ห้ามมี @)
│       ├── managers.py         create_user / create_superuser
│       ├── forms.py            ฟอร์มสร้าง/แก้ผู้ใช้ในหน้า Django admin
│       ├── admin.py            หน้าจัดการผู้ใช้ใน Django admin (ใช้ชั่วคราวก่อนมีหน้าจัดการจริง)
│       ├── services.py         หาผู้ใช้จากช่อง login ช่องเดียว (@ = อีเมล) และตรวจรหัสผ่าน
│       ├── tokens.py           ออก/ตรวจ refresh token (ใส่ role + ผูกกับรหัสผ่านปัจจุบัน) และตั้ง/ลบ cookie
│       ├── email_tokens.py     ออก/ใช้โทเคนครั้งเดียวในลิงก์อีเมล (เก็บเฉพาะแฮช), กฎขอลิงก์ใหม่ทุก 60 วินาที
│       ├── emails.py           ส่งอีเมลลิงก์ยืนยันอีเมล / ตั้งรหัสผ่านใหม่ (ไทย+อังกฤษในฉบับเดียว)
│       ├── registration.py     ตรรกะสมัครเองด้วยอีเมล / ยืนยันอีเมล / ขอลิงก์ยืนยันใหม่
│       ├── password_reset.py   ตรรกะลืมรหัสผ่าน: ขอลิงก์ / ตรวจลิงก์ / ตั้งรหัสใหม่ (เซสชันเดิมใช้ไม่ได้)
│       ├── password_rules.py   ตรวจกฎรหัสผ่านพร้อมรหัส code รายกฎ (ใช้ร่วมตอนสมัครและตั้งรหัสใหม่)
│       ├── templates/accounts/email/  ข้อความอีเมล: verify_email.txt, reset_password.txt
│       ├── serializers.py      รูปแบบข้อมูลเข้า-ออกของ login และข้อมูลผู้ใช้
│       ├── exceptions.py       error ของระบบล็อกอิน (แต่ละตัวมี `code`)
│       ├── views.py            endpoint: login / refresh / logout / me / register / verify-email / resend-verification / forgot-password / reset-password (+ check)
│       ├── urls.py             เส้นทางใต้ /api/auth/
│       ├── management/commands/
│       │   └── seed_demo.py    คำสั่งสร้าง/รีเซ็ตบัญชีทดสอบ 3 บทบาท (เฉพาะ DEBUG=1, รหัสผ่านจาก DEMO_PASSWORD ใน .env)
│       ├── migrations/         migration ของแอปนี้ (0001 = ตารางผู้ใช้, 0002 = ตารางโทเคนในลิงก์อีเมล)
│       ├── test_models.py      test กฎของ User (normalize อีเมล/รหัส, unique, constraint ของฐานข้อมูล)
│       ├── test_admin.py       test หน้า admin และคำสั่ง createsuperuser
│       ├── test_auth_api.py    test API ล็อกอินทั้งชุด (ปกติ + กรณีโจมตี)
│       ├── test_seed_demo.py   test คำสั่ง seed_demo (รั้วกัน DEBUG, รหัสผ่าน, รันซ้ำ, ล็อกอินได้จริง)
│       ├── test_email_tokens.py  test โทเคนในลิงก์อีเมล (ครั้งเดียว, หมดอายุ, ผิดจุดประสงค์, กฎ 60 วินาที)
│       ├── test_emails.py      test อีเมลยืนยัน/ตั้งรหัสผ่าน (ลิงก์ถูก, ครบสองภาษา)
│       ├── test_registration_api.py  test API สมัคร/ยืนยันอีเมล/ส่งลิงก์ใหม่ (ปกติ + กรณีโจมตี เช่น สมัครทับ, ยกระดับสิทธิ์)
│       └── test_password_reset_api.py  test API ลืมรหัสผ่าน/ตั้งรหัสใหม่ และเซสชันเก่าตายเมื่อรหัสเปลี่ยน
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
        ├── main.tsx          จุดเริ่มแอป: โหลดฟอนต์/สไตล์/i18n แล้ว render ภายใต้ QueryClientProvider > AuthProvider > Router
        ├── router.tsx        เส้นทางทั้งหมด: /login /register /forgot-password (เฉพาะคนที่ยังไม่ล็อกอิน), /verify-email /reset-password (เปิดจากลิงก์ในอีเมล ไม่มีตัวกัน),
        │                     / (ไปหน้าแรกตามบทบาท), /admin /teacher /student (จำกัดตามบทบาท, อยู่ใต้เปลือกหน้า AppShell)
        ├── index.css         Tailwind + โทเคนสี/ฟอนต์ของแบรนด์ (@theme)
        ├── pages/            หน้าจอ
        │   ├── LoginPage.tsx      หน้า login ตาม wireframe (มีปุ่มส่งลิงก์ยืนยันอีกครั้งเมื่อบัญชียังไม่ยืนยันอีเมล)
        │   ├── RegisterPage.tsx   หน้าสมัครสมาชิกด้วยอีเมล + หน้า "ตรวจสอบอีเมลของคุณ" หลังสมัคร (ส่งลิงก์อีกครั้งได้ทุก 60 วินาที)
        │   ├── VerifyEmailPage.tsx  หน้าที่เปิดจากลิงก์ยืนยันอีเมล: ยืนยันให้เองครั้งเดียว / ลิงก์ใช้ไม่ได้ → กรอกอีเมลขอลิงก์ใหม่
        │   ├── ForgotPasswordPage.tsx  หน้าลืมรหัสผ่าน: กรอกอีเมล → ข้อความเดิมเสมอ ไม่บอกว่ามีบัญชีหรือไม่ (ส่งอีกครั้งได้ทุก 60 วินาที)
        │   ├── ResetPasswordPage.tsx  หน้าที่เปิดจากลิงก์ตั้งรหัสผ่าน: ตรวจลิงก์ → ฟอร์มรหัสใหม่ + รายการกฎ → ไปหน้า login (เซสชันเดิมใช้ไม่ได้)
        │   ├── DashboardPage.tsx  dashboard ของทั้ง 3 บทบาท (โครงเปล่า: ตัวเลขเป็น "–" จนกว่าจะมี API)
        │   └── dashboardConfig.ts หัวข้อ/ตัวเลขสำคัญ/ช่องข้อมูลของ dashboard แต่ละบทบาท
        ├── layout/           เปลือกหน้าหลังล็อกอิน: AppShell (รวมทุกส่วน), Sidebar (จอกว้าง), MobileChrome (แถบบน + แถบล่างของมือถือ),
        │                     NavList + navConfig (เมนูตามบทบาท; เมนูที่ยังไม่มีหน้ากดไม่ได้), Sheet (ลิ้นชัก/แผ่นล่างด้วย <dialog>),
        │                     UserBadge, LogoutButton, BellButton (กระดิ่ง ยังกดไม่ได้)
        ├── components/       component ที่ใช้ซ้ำ: LogoMark (ตราดอก), Icon (ไอคอน), LanguageToggle (สลับ TH/EN), PageMessage (ข้อความเต็มหน้า เช่น กำลังโหลด),
        │                     AuthLayout (โครงหน้าของหน้าที่ยังไม่ล็อกอินทั้งหมด: แผงม่วง + เนื้อหา),
        │                     FormFields (ช่องข้อความ / ช่องรหัสผ่านแสดง-ซ่อน พร้อมข้อความผิดพลาดที่ผูก aria), StatusCard (วงกลมไอคอน + หัวข้อ ของหน้าสถานะ),
        │                     ResendBlock ("ไม่ได้รับอีเมล? ส่งอีกครั้ง" พร้อมนับถอยหลัง), PasswordRules (รายการกฎรหัสผ่านที่ติ๊กสดตอนพิมพ์)
        ├── i18n/             ระบบหลายภาษา: index.ts (ตั้งค่า) + language.ts (จำภาษาที่ผู้ใช้เลือกไว้ในเบราว์เซอร์, ค่าเริ่มต้น = ไทย) + locales/th.json, en.json
        ├── lib/              ชั้นเรียก API + ตัวช่วยเล็ก ๆ
        │   ├── cx.ts           รวมชื่อ class เข้าด้วยกัน
        │   ├── apiError.ts     ApiError: error จาก backend ที่มี `code` (และ errorCodes รายฟิลด์) ไว้แปลข้อความ
        │   ├── fieldErrors.tsx แปลรหัสกฎที่ไม่ผ่านของช่อง (เช่น password_too_short) เป็นข้อความใต้ช่อง
        │   ├── passwordRules.ts กฎรหัสผ่านที่ตรวจในหน้าเว็บได้ (ยาว ≥ 8 ตัวอักษร / ไม่เป็นตัวเลขล้วน) นับตัวอักษรแบบเดียวกับ backend
        │   ├── useCountdown.ts / useResend.ts  ตัวนับถอยหลัง 60 วินาทีและตรรกะปุ่ม "ส่งลิงก์อีกครั้ง"
        │   ├── httpCore.ts     ยิงคำขอ 1 ครั้ง (แนบ token, แปลง error) ไม่มีการลองซ้ำ
        │   └── apiClient.ts    เรียก API ที่ต้อง login: 401 → ขอ token ใหม่แล้วลองซ้ำครั้งเดียว
        ├── auth/             ระบบล็อกอินฝั่งเว็บ
        │   ├── session.ts      เก็บ access token ในหน่วยความจำ, login/logout/refresh (ขอทีละคำขอ), สัญญาณเมื่อเซสชันเปลี่ยน
        │   ├── accountApi.ts   เรียก API สมัคร / ยืนยันอีเมล / ส่งลิงก์ใหม่ / ลืมรหัสผ่าน / ตั้งรหัสใหม่ (ไม่ต้องล็อกอิน)
        │   ├── AuthProvider.tsx  เก็บสถานะล็อกอินของทั้งแอป (loading / authenticated / unauthenticated) และกู้เซสชันตอนเปิดเว็บ
        │   ├── authContext.ts  ตัว context + ชนิดข้อมูล    useAuth.ts  hook อ่านสถานะ/สั่ง login-logout
        │   ├── guards.tsx      ตัวกันหน้า: RequireAuth, RequireRole, PublicOnly, RedirectToHome
        │   └── roles.ts        หน้าแรก (path) ของแต่ละบทบาท
        ├── types/auth.ts     ชนิดข้อมูล User / Role / Session ตรงกับ backend
        └── test/             ตัวช่วยสำหรับ test: setup.ts (ตั้งค่าก่อนทุก test), fetchMock.ts (จำลอง backend), renderApp.tsx (render แอปจริงด้วย router), renderWithAuth.tsx (render เส้นทางจริงด้วยสถานะล็อกอินที่กำหนดเอง)
                              (ไฟล์ *.test.ts(x) อยู่ข้างไฟล์ที่ทดสอบ)
```

## ที่ยังไม่มี (จะเพิ่มตามลำดับ)
- แอป backend อื่นตาม `docs/database.md` §2 (academics, enrollment ฯลฯ) — เพิ่มพร้อมฟีเจอร์ที่ใช้
- หน้าจอจริงตาม wireframe (login และ dashboard แบบเต็ม ฯลฯ) — ตอนนี้ login เป็นแบบเรียบ และหน้าแรกของแต่ละบทบาทเป็นหน้าชั่วคราว
