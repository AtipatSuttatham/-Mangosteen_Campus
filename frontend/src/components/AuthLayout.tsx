import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { LanguageToggle } from './LanguageToggle'
import { CalyxOutline, LogoMark } from './LogoMark'

type AuthLayoutProps = {
  /** ข้อความใหญ่บนแผงม่วง (จอกว้างเท่านั้น) — ไม่ใส่ = ข้อความประจำระบบ */
  tagline?: string
  /** ข้อความรองใต้ข้อความใหญ่บนแผงม่วง */
  taglineSub?: string
  /** หัวข้อ (h1) ของฟอร์ม — ไม่ใส่ = เนื้อหาเริ่มใต้แถบม่วงเลย ใช้กับหน้าสถานะที่หัวข้ออยู่ในการ์ดเอง */
  title?: string
  /** คำอธิบายใต้หัวข้อ */
  subtitle?: string
  children: ReactNode
}

// โครงหน้าของหน้าที่ยังไม่ล็อกอินทั้งหมด (login / สมัคร / ยืนยันอีเมล / ลืมรหัสผ่าน / ตั้งรหัสผ่านใหม่) ตาม wireframe:
// จอกว้าง (>= 1024px) แผงม่วงซ้าย + เนื้อหาขวา, จอเล็ก แถบม่วงด้านบน + เนื้อหาด้านล่าง
export function AuthLayout({ tagline, taglineSub, title, subtitle, children }: AuthLayoutProps) {
  const { t } = useTranslation()

  return (
    <main className="relative flex min-h-screen flex-col lg:flex-row">
      {/* ปุ่มสลับภาษาตัวเดียว: บนจอเล็กอยู่บนแถบม่วง (สีอ่อน) บนจอกว้างอยู่มุมขวาบนของเนื้อหา */}
      <div className="absolute top-6 right-6 z-20 lg:top-9 lg:right-14">
        <LanguageToggle lightBelowLg />
      </div>

      {/* แผงแบรนด์: จอเล็กเป็นแถบสูง 236px, จอกว้างเป็นแผงซ้ายกว้าง 520px */}
      <aside className="relative h-[236px] shrink-0 overflow-hidden bg-plum-800 px-6 pt-6 lg:h-auto lg:w-[520px] lg:px-11 lg:py-9">
        <CalyxOutline className="absolute -right-[130px] -bottom-[150px] size-[360px] text-sage-400 opacity-55 lg:-right-[250px] lg:-bottom-[260px] lg:size-[760px]" />

        <div className="relative flex items-center gap-3">
          <LogoMark size={26} className="text-sage-400" />
          <span className="font-serif text-base font-semibold text-plum-50">{t('app.name')}</span>
        </div>

        {/* ข้อความแนะนำ: แสดงเฉพาะจอกว้าง */}
        <div className="relative mt-[170px] hidden max-w-[360px] lg:block">
          <p className="font-serif text-[34px] leading-[1.45] font-semibold text-plum-50">
            {tagline ?? t('app.tagline')}
          </p>
          <p className="mt-4 text-[15px] leading-[1.75] text-plum-300">
            {taglineSub ?? t('login.taglineSub')}
          </p>
        </div>
      </aside>

      <section className="relative z-10 flex flex-1 flex-col px-6 pb-10 lg:px-14 lg:py-9">
        {/* ไม่มีหัวข้อ (หน้าสถานะ) = เนื้อหาเริ่มใต้แถบม่วงโดยเว้นระยะบนจอเล็ก */}
        <div
          className={`mx-auto flex w-full max-w-[400px] flex-col gap-5 lg:my-auto ${title ? '' : 'mt-8 lg:mt-0'}`}
        >
          {/* หัวข้อ: จอเล็กดึงขึ้นไปวางบนแถบม่วง (ตัวอักษรสีอ่อน) จอกว้างอยู่ในคอลัมน์ฟอร์มตามปกติ */}
          {title && (
            <header className="-mt-20 mb-6 lg:mt-0 lg:mb-0">
              <h1 className="font-serif text-[30px] leading-[1.4] font-semibold text-plum-50 lg:text-[32px] lg:text-ink">
                {title}
              </h1>
              {subtitle && (
                <p className="text-sm leading-relaxed text-plum-300 lg:mt-1 lg:text-ink-2">{subtitle}</p>
              )}
            </header>
          )}

          {children}
        </div>
      </section>
    </main>
  )
}
