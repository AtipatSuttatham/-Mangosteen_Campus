import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { useAuth } from '../auth/useAuth'
import { LanguageToggle } from '../components/LanguageToggle'
import { CalyxOutline, LogoMark } from '../components/LogoMark'
import { ApiError } from '../lib/apiError'

// ลักษณะร่วมของช่องกรอกข้อมูล (สูง 48px ตัวอักษรอย่างน้อย 16px กันเบราว์เซอร์มือถือซูมเองตอนแตะช่อง)
const FIELD_CLASS =
  'h-12 w-full rounded-md border border-field bg-white px-3.5 text-base text-ink placeholder:text-ink-3 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-plum-800'

// ปุ่มที่หน้าปลายทางยังไม่มี (ลืมรหัสผ่าน / สมัครสมาชิก): แสดงตามตำแหน่งในแบบแต่กดไม่ได้ จะเปิดในก้อนบัญชีและอีเมล
function ComingSoonLink({ label, className = '' }: { label: string; className?: string }) {
  const { t } = useTranslation()
  return (
    <button
      type="button"
      disabled
      title={t('common.comingSoon')}
      className={`cursor-not-allowed text-ink-3 ${className}`}
    >
      {label}
    </button>
  )
}

// หน้าเข้าสู่ระบบ ตาม wireframe: จอกว้าง (>= 1024px) แผงม่วงซ้าย + ฟอร์มขวา, จอเล็ก แถบม่วงด้านบน + ฟอร์มด้านล่าง
export default function LoginPage() {
  const { t } = useTranslation()
  const { login } = useAuth()

  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
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

  // ยังไม่ยืนยันอีเมลใช้กล่องเหลือง (เป็นคำเตือน) error อื่นใช้กล่องแดง
  const isWarning = errorCode === 'email_not_verified'

  return (
    <main className="relative flex min-h-screen flex-col lg:flex-row">
      {/* ปุ่มสลับภาษาตัวเดียว: บนจอเล็กอยู่บนแถบม่วง (สีอ่อน) บนจอกว้างอยู่มุมขวาบนของฟอร์ม */}
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
          <p className="font-serif text-[34px] leading-[1.45] font-semibold text-plum-50">{t('app.tagline')}</p>
          <p className="mt-4 text-[15px] leading-[1.75] text-plum-300">{t('login.taglineSub')}</p>
        </div>
      </aside>

      <section className="relative z-10 flex flex-1 flex-col px-6 pb-10 lg:px-14 lg:py-9">
        <div className="mx-auto flex w-full max-w-[400px] flex-col gap-5 lg:my-auto">
          {/* หัวข้อ: จอเล็กดึงขึ้นไปวางบนแถบม่วง (ตัวอักษรสีอ่อน) จอกว้างอยู่ในคอลัมน์ฟอร์มตามปกติ */}
          <header className="-mt-20 mb-6 lg:mt-0 lg:mb-0">
            <h1 className="font-serif text-[30px] leading-[1.4] font-semibold text-plum-50 lg:text-[32px] lg:text-ink">
              {t('login.title')}
            </h1>
            <p className="text-sm leading-relaxed text-plum-300 lg:mt-1 lg:text-ink-2">{t('login.subtitle')}</p>
          </header>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            {errorCode && (
              <div
                role="alert"
                className={
                  isWarning
                    ? 'rounded-md border border-warn-200 bg-warn-50 px-3.5 py-3 text-warn-800'
                    : 'rounded-md border border-error-200 bg-error-50 px-3.5 py-3 text-error-800'
                }
              >
                <p className="text-sm font-semibold">
                  {t(`errors.${errorCode}.title`, { defaultValue: t('errors.unknown_error.title') })}
                </p>
                <p className="mt-0.5 text-[13px] leading-normal">
                  {t(`errors.${errorCode}.description`, {
                    defaultValue: t('errors.unknown_error.description'),
                  })}
                </p>
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label htmlFor="login-identifier" className="text-[13.5px] font-medium">
                {t('login.identifier')}
              </label>
              <input
                id="login-identifier"
                name="identifier"
                type="text"
                autoComplete="username"
                required
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
                placeholder={t('login.identifierPlaceholder')}
                className={FIELD_CLASS}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="login-password" className="text-[13.5px] font-medium">
                {t('login.password')}
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder={t('login.passwordPlaceholder')}
                  className={`${FIELD_CLASS} pr-[72px]`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((shown) => !shown)}
                  aria-pressed={showPassword}
                  aria-label={showPassword ? t('login.hidePasswordLabel') : t('login.showPasswordLabel')}
                  className="absolute top-1.5 right-1.5 h-9 cursor-pointer rounded px-3 text-[13px] font-semibold text-plum-800 focus-visible:outline-2 focus-visible:outline-plum-800"
                >
                  {showPassword ? t('login.hidePassword') : t('login.showPassword')}
                </button>
              </div>
              {/* ลืมรหัสผ่าน: อยู่ใต้ช่องรหัสผ่านตามที่ผู้ใช้กำหนด */}
              <ComingSoonLink label={t('login.forgot')} className="self-start text-[13px] font-medium" />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="h-12 cursor-pointer rounded-md bg-plum-800 text-base font-semibold text-plum-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? t('login.submitting') : t('login.submit')}
            </button>
          </form>

          <p className="border-t border-line pt-[18px] text-sm text-ink-2">
            {t('login.noAccount')}{' '}
            <ComingSoonLink label={t('login.register')} className="font-semibold" />
          </p>
        </div>
      </section>
    </main>
  )
}
