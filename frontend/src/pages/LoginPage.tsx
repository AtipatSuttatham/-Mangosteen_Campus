import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { useAuth } from '../auth/useAuth'
import { LanguageToggle } from '../components/LanguageToggle'
import { LogoMark } from '../components/LogoMark'
import { ApiError } from '../lib/apiError'

// หน้าเข้าสู่ระบบ (แบบเรียบ — ตรรกะครบแล้ว หน้าตาตาม wireframe จะทำในก้อนถัดไป)
export default function LoginPage() {
  const { t } = useTranslation()
  const { login } = useAuth()

  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  // code ของ error ล่าสุด (ใช้แปลข้อความ) และสถานะกำลังส่งข้อมูล
  const [errorCode, setErrorCode] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setErrorCode(null)
    try {
      // สำเร็จ: สถานะล็อกอินเปลี่ยน แล้ว PublicOnly จะพาไปหน้าที่ตั้งใจไว้เอง
      await login(identifier, password)
    } catch (error) {
      setErrorCode(error instanceof ApiError ? error.code : 'unknown_error')
      setSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-screen flex-col">
      <header className="flex justify-end p-6">
        <LanguageToggle />
      </header>

      <section className="m-auto flex w-full max-w-sm flex-col gap-6 px-6 pb-24">
        <div className="flex flex-col items-start gap-3">
          <LogoMark size={40} className="text-plum-800" />
          <h1 className="font-serif text-3xl leading-snug font-semibold">{t('login.title')}</h1>
          <p className="text-sm text-ink-2">{t('login.subtitle')}</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {errorCode && (
            <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900">
              {t(`errors.${errorCode}`, { defaultValue: t('errors.unknown_error') })}
            </p>
          )}

          <label className="flex flex-col gap-1.5 text-sm font-medium">
            {t('login.identifier')}
            <input
              name="identifier"
              type="text"
              autoComplete="username"
              required
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              placeholder={t('login.identifierPlaceholder')}
              className="h-11 rounded-md border border-line bg-white px-3 text-base"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-sm font-medium">
            {t('login.password')}
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t('login.passwordPlaceholder')}
              className="h-11 rounded-md border border-line bg-white px-3 text-base"
            />
          </label>

          <button
            type="submit"
            disabled={submitting}
            className="h-11 cursor-pointer rounded-md bg-plum-800 font-semibold text-plum-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? t('login.submitting') : t('login.submit')}
          </button>
        </form>
      </section>
    </main>
  )
}
