import { useTranslation } from 'react-i18next'

import { useAuth } from '../auth/useAuth'
import { LanguageToggle } from '../components/LanguageToggle'
import { LogoMark } from '../components/LogoMark'

// หน้าแรกชั่วคราวของแต่ละบทบาท (แสดงชื่อ + บทบาท + ปุ่มออกจากระบบ)
// dashboard จริงตาม wireframe จะมาแทนที่ในก้อนถัดไป
export default function RoleHomePage() {
  const { t } = useTranslation()
  const { user, logout } = useAuth()

  // อยู่ใต้ RequireAuth เสมอจึงมีผู้ใช้ — เช็กไว้เพื่อให้ชนิดข้อมูลถูกต้อง
  if (!user) return null

  return (
    <main className="flex min-h-screen flex-col">
      <header className="flex justify-end p-6">
        <LanguageToggle />
      </header>

      <section className="m-auto flex max-w-md flex-col items-start gap-4 px-6 pb-24">
        <LogoMark size={44} className="text-plum-800" />
        <h1 className="font-serif text-3xl leading-snug font-semibold">
          {t('home.greeting', { name: user.first_name })}
        </h1>
        <p className="font-medium text-plum-800">{t(`roles.${user.role}`)}</p>
        <p className="text-sm text-ink-2">{t('home.placeholder')}</p>
        <button
          type="button"
          onClick={() => void logout()}
          className="h-10 cursor-pointer rounded-md border border-plum-800 px-4 font-semibold text-plum-800"
        >
          {t('nav.logout')}
        </button>
      </section>
    </main>
  )
}
