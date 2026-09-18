import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { LanguageToggle } from './components/LanguageToggle'
import { LogoMark } from './components/LogoMark'
import { fetchHealth } from './lib/api'

// หน้าเริ่มต้นชั่วคราว: ใช้ยืนยันว่า Tailwind, i18n และการเรียก backend ผ่าน /api ทำงานครบ
// (หน้า login และ dashboard จริงจะมาแทนที่ในก้อนถัดไป)
export default function App() {
  const { t } = useTranslation()

  // เรียก /api/health/ ดูว่า backend ตอบกลับได้ไหม (ไม่ลองซ้ำเพื่อให้เห็นผลทันที)
  const health = useQuery({ queryKey: ['health'], queryFn: fetchHealth, retry: false })

  // เลือกข้อความสถานะตามผลการเรียก
  let statusKey = 'status.ok'
  if (health.isPending) statusKey = 'status.checking'
  else if (health.isError) statusKey = 'status.error'

  return (
    <main className="flex min-h-screen flex-col">
      <header className="flex justify-end p-6">
        <LanguageToggle />
      </header>

      <section className="m-auto flex max-w-md flex-col items-start gap-4 px-6 pb-24">
        <LogoMark size={44} className="text-plum-800" />
        <h1 className="font-serif text-4xl leading-snug font-semibold">{t('app.name')}</h1>
        <p className="leading-relaxed text-ink-2">{t('app.tagline')}</p>
        <p role="status" className="w-full border-t border-line pt-4 text-sm text-ink-3">
          {t(statusKey)}
        </p>
      </section>
    </main>
  )
}
