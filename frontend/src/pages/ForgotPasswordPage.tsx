import { useState, type FormEvent } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { requestPasswordReset } from '../auth/accountApi'
import { AuthLayout } from '../components/AuthLayout'
import { TextField } from '../components/FormFields'
import { ResendBlock } from '../components/ResendBlock'
import { StatusCard } from '../components/StatusCard'
import { ApiError } from '../lib/apiError'

const LINK_CLASS =
  'font-semibold text-plum-800 underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800'

// หน้าลืมรหัสผ่าน ตาม wireframe: กรอกอีเมล → ส่งลิงก์ตั้งรหัสผ่านใหม่ (อายุ 1 ชั่วโมง)
// หลังส่งแสดงข้อความเดิมเสมอ ไม่บอกว่ามีอีเมลนี้ในระบบหรือไม่ (backend ก็ตอบเหมือนกันทุกกรณี)
export default function ForgotPasswordPage() {
  const { t } = useTranslation()

  const [email, setEmail] = useState('')
  const [errorCode, setErrorCode] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  // อีเมลที่ขอลิงก์ไปแล้ว (มีค่า = แสดงหน้า "ตรวจสอบอีเมลของคุณ")
  const [sentTo, setSentTo] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setErrorCode(null)
    const cleanEmail = email.trim()
    try {
      await requestPasswordReset(cleanEmail)
      setSentTo(cleanEmail)
    } catch (error) {
      setErrorCode(error instanceof ApiError ? error.code : 'unknown_error')
      setSubmitting(false)
    }
  }

  const layoutText = { tagline: t('forgot.tagline'), taglineSub: t('forgot.taglineSub') }

  if (sentTo) {
    return (
      <AuthLayout {...layoutText}>
        <StatusCard tone="info" icon="mail" title={t('forgot.sentTitle')}>
          <p className="text-sm leading-[1.7] text-ink-2">
            {/* อีเมลเป็นตัวเข้มเพื่อให้ผู้ใช้ตรวจได้ว่าพิมพ์ถูกไหม */}
            <Trans
              i18nKey="forgot.sentBody"
              values={{ email: sentTo }}
              components={{ email: <span className="font-medium text-ink" /> }}
            />
          </p>
          {/* backend ไม่ส่งลิงก์ตั้งรหัสให้บัญชีที่ยังไม่ยืนยันอีเมล จึงแนะนำไว้ล่วงหน้า (ไม่เปิดเผยสถานะของอีเมลใด) */}
          <p className="text-[13.5px] leading-[1.7] text-ink-2">{t('forgot.sentUnverifiedHint')}</p>

          <ResendBlock email={sentTo} send={requestPasswordReset} i18nPrefix="forgot" />

          <p className="border-t border-line pt-4 text-sm">
            <Link to="/login" className={LINK_CLASS}>
              {t('forgot.backToLogin')}
            </Link>
          </p>
        </StatusCard>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout {...layoutText} title={t('forgot.title')} subtitle={t('forgot.subtitle')}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        {errorCode && (
          <div
            role="alert"
            className="rounded-md border border-error-200 bg-error-50 px-3.5 py-3 text-error-800"
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

        <TextField
          label={t('forgot.email')}
          type="email"
          value={email}
          onChange={setEmail}
          autoComplete="email"
          placeholder={t('forgot.emailPlaceholder')}
          maxLength={254}
        />

        <button
          type="submit"
          disabled={submitting}
          className="h-12 cursor-pointer rounded-md bg-plum-800 text-base font-semibold text-plum-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? t('forgot.submitting') : t('forgot.submit')}
        </button>
      </form>

      <p className="border-t border-line pt-4 text-sm">
        <Link to="/login" className={LINK_CLASS}>
          {t('forgot.backToLogin')}
        </Link>
      </p>
    </AuthLayout>
  )
}
