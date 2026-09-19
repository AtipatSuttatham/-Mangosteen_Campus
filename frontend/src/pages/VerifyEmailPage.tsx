import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router'

import { resendVerification, verifyEmail } from '../auth/accountApi'
import { AuthLayout } from '../components/AuthLayout'
import { TextField } from '../components/FormFields'
import { StatusCard } from '../components/StatusCard'
import { ApiError } from '../lib/apiError'
import { useResend } from '../lib/useResend'

const LINK_CLASS =
  'font-semibold text-plum-800 underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800'

const PRIMARY_BUTTON_CLASS =
  'h-12 cursor-pointer rounded-md bg-plum-800 px-6 text-base font-semibold text-plum-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800 disabled:cursor-not-allowed disabled:opacity-60'

// ผลของการยืนยัน: กำลังยืนยัน / สำเร็จ / ลิงก์ใช้ไม่ได้ (ไม่มี/ใช้แล้ว/หมดอายุ) / เครือข่ายล่ม (ลองใหม่ได้)
type Phase = 'loading' | 'verified' | 'invalid' | 'network'

// หน้าที่เปิดจากลิงก์ในอีเมลยืนยัน (/verify-email?token=...) — เรียก API ยืนยันให้เองทันที
export default function VerifyEmailPage() {
  const { t } = useTranslation()
  const [params] = useSearchParams()
  const token = params.get('token')

  const [phase, setPhase] = useState<Phase>('loading')
  // กันเรียกยืนยันซ้ำ: ตอน dev React รัน effect สองรอบ ถ้าไม่กัน คำขอที่สองจะได้ "ลิงก์ถูกใช้แล้ว"
  // ทั้งที่ครั้งแรกสำเร็จ (โทเคนใช้ได้ครั้งเดียว) จึงจำไว้ว่าเรียกไปแล้ว และไม่ใช้ตัวยกเลิกผลลัพธ์แบบ cleanup
  const started = useRef(false)

  async function run() {
    setPhase('loading')
    if (!token) {
      setPhase('invalid')
      return
    }
    try {
      await verifyEmail(token)
      setPhase('verified')
    } catch (error) {
      // ลิงก์ใช้ไม่ได้ (ไม่มี/ใช้แล้ว/หมดอายุ/ผิดจุดประสงค์) → ให้ขอลิงก์ใหม่; อย่างอื่น (เครือข่ายล่ม ฯลฯ) → ลองอีกครั้งได้
      const linkIsBad =
        error instanceof ApiError && (error.code === 'token_invalid' || error.code === 'token_expired')
      setPhase(linkIsBad ? 'invalid' : 'network')
    }
  }

  useEffect(() => {
    if (started.current) return
    started.current = true
    void run()
    // run ผูกกับ token ของ URL ที่เปิดหน้ามา (หน้านี้ไม่รองรับเปลี่ยน token ระหว่างเปิดอยู่)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (phase === 'loading') {
    return (
      <AuthLayout>
        <p role="status" className="text-ink-2">
          {t('verifyEmail.loading')}
        </p>
      </AuthLayout>
    )
  }

  if (phase === 'verified') {
    return (
      <AuthLayout>
        <StatusCard tone="success" icon="check" title={t('verifyEmail.successTitle')}>
          <p className="text-sm leading-[1.7] text-ink-2">{t('verifyEmail.successBody')}</p>
          <Link to="/login" className={`${PRIMARY_BUTTON_CLASS} mt-2 flex items-center justify-center`}>
            {t('verifyEmail.login')}
          </Link>
        </StatusCard>
      </AuthLayout>
    )
  }

  if (phase === 'network') {
    return (
      <AuthLayout>
        <StatusCard tone="warn" icon="clock" title={t('errors.network_error.title')}>
          <p className="text-sm leading-[1.7] text-ink-2">{t('errors.network_error.description')}</p>
          <button type="button" onClick={() => void run()} className={`${PRIMARY_BUTTON_CLASS} mt-2`}>
            {t('verifyEmail.retry')}
          </button>
        </StatusCard>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      <InvalidLink />
    </AuthLayout>
  )
}

// ลิงก์ใช้ไม่ได้แล้ว: ระบบไม่รู้ว่าเป็นของใคร (โทเคนหมดอายุ/ไม่มี) จึงให้กรอกอีเมลเพื่อขอลิงก์ใหม่
function InvalidLink() {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const resend = useResend(resendVerification)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void resend.trigger(email.trim())
  }

  const waiting = resend.secondsLeft > 0

  return (
    <StatusCard tone="warn" icon="clock" title={t('verifyEmail.invalidTitle')}>
      <p className="text-sm leading-[1.7] text-ink-2">{t('verifyEmail.invalidBody')}</p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
        <TextField
          label={t('verifyEmail.email')}
          type="email"
          value={email}
          onChange={setEmail}
          autoComplete="email"
          placeholder={t('verifyEmail.emailPlaceholder')}
          maxLength={254}
        />
        <button
          type="submit"
          disabled={resend.status === 'sending' || waiting}
          className="h-12 cursor-pointer rounded-md border border-plum-800 text-base font-semibold text-plum-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {resend.status === 'sending'
            ? t('verifyEmail.sending')
            : waiting
              ? t('verifyEmail.sendWait', { seconds: resend.secondsLeft })
              : t('verifyEmail.send')}
        </button>
      </form>

      <div role="status" className="text-[13px] leading-normal text-ok-800">
        {resend.status === 'sent' && t('verifyEmail.sent')}
      </div>
      {resend.status === 'error' && (
        <p role="alert" className="text-[13px] leading-normal text-error-800">
          {t(`errors.${resend.errorCode}.title`, { defaultValue: t('errors.unknown_error.title') })}
        </p>
      )}

      <p className="border-t border-line pt-4 text-sm text-ink-2">
        {t('verifyEmail.alreadyVerified')}{' '}
        <Link to="/login" className={LINK_CLASS}>
          {t('verifyEmail.login')}
        </Link>
      </p>
    </StatusCard>
  )
}
