import { useTranslation } from 'react-i18next'

// ข้อความเต็มหน้าจอสั้น ๆ เช่น "กำลังโหลด" (ใช้ระหว่างกู้เซสชันตอนเปิดเว็บ)
export function PageMessage({ messageKey }: { messageKey: string }) {
  const { t } = useTranslation()

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <p role="status" className="text-ink-2">
        {t(messageKey)}
      </p>
    </main>
  )
}
