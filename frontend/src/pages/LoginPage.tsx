import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate } from 'react-router'

import { resendVerification } from '../auth/accountApi'
import { useAuth } from '../auth/useAuth'
import { AuthLayout } from '../components/AuthLayout'
import { PasswordField, TextField } from '../components/FormFields'
import { ApiError } from '../lib/apiError'
import { useResend } from '../lib/useResend'

// ข้อความที่หน้าอื่นฝากมาแสดงบนหน้า login (ผ่าน state ของการเปลี่ยนหน้า)
type LoginNotice = { notice?: 'passwordReset' } | null

// หน้าเข้าสู่ระบบ ตาม wireframe (โครงหน้าอยู่ที่ AuthLayout)
export default function LoginPage() {
  const { t } = useTranslation()
  const { login } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  // ตั้งรหัสผ่านใหม่สำเร็จแล้วถูกพามาที่นี่: จำไว้เป็นค่าของหน้านี้ แล้วล้างออกจาก state ของเบราว์เซอร์
  // (กดรีเฟรชแล้วข้อความหายไป ไม่ค้างตลอดไป)
  const [passwordResetDone] = useState(() => (location.state as LoginNotice)?.notice === 'passwordReset')
  useEffect(() => {
    if (passwordResetDone) navigate(location.pathname, { replace: true, state: null })
    // ทำครั้งเดียวตอนเปิดหน้า
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  // code ของ error ล่าสุด (ใช้แปลข้อความ) และสถานะกำลังส่งข้อมูล
  const [errorCode, setErrorCode] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const resend = useResend(resendVerification)

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
  // ส่งลิงก์ยืนยันใหม่ได้เฉพาะเมื่อกรอกเป็นอีเมล (มี @) — รหัสนักศึกษา/พนักงานไม่มีทางรู้อีเมล
  const canResend = isWarning && identifier.includes('@')
  const resendWaiting = resend.secondsLeft > 0

  return (
    <AuthLayout title={t('login.title')} subtitle={t('login.subtitle')}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        {passwordResetDone && (
          <div
            role="status"
            className="rounded-md border border-ok-200 bg-ok-50 px-3.5 py-3 text-sm font-medium text-ok-800"
          >
            {t('login.passwordResetDone')}
          </div>
        )}

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

            {canResend && (
              <div className="mt-2.5">
                <button
                  type="button"
                  onClick={() => void resend.trigger(identifier.trim())}
                  disabled={resend.status === 'sending' || resendWaiting}
                  className="cursor-pointer text-[13px] font-semibold underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-warn-800 disabled:cursor-not-allowed disabled:no-underline disabled:opacity-70"
                >
                  {resendWaiting
                    ? t('login.resendWait', { seconds: resend.secondsLeft })
                    : t('login.resendVerification')}
                </button>
                <div role="status" className="mt-1 text-[13px]">
                  {resend.status === 'sent' && t('login.verificationSent')}
                </div>
                {resend.status === 'error' && (
                  <p className="mt-1 text-[13px]">
                    {t(`errors.${resend.errorCode}.title`, {
                      defaultValue: t('errors.unknown_error.title'),
                    })}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        <TextField
          label={t('login.identifier')}
          value={identifier}
          onChange={setIdentifier}
          autoComplete="username"
          placeholder={t('login.identifierPlaceholder')}
        />

        <PasswordField
          label={t('login.password')}
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
          placeholder={t('login.passwordPlaceholder')}
          // ลืมรหัสผ่าน: อยู่ใต้ช่องรหัสผ่านตามที่ผู้ใช้กำหนด
          footer={
            <Link
              to="/forgot-password"
              className="self-start text-[13px] font-medium text-plum-800 underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800"
            >
              {t('login.forgot')}
            </Link>
          }
        />

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
        <Link
          to="/register"
          className="font-semibold text-plum-800 underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800"
        >
          {t('login.register')}
        </Link>
      </p>
    </AuthLayout>
  )
}
