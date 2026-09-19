import { useState, type FormEvent } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { registerAccount, resendVerification } from '../auth/accountApi'
import { AuthLayout } from '../components/AuthLayout'
import { PasswordField, TextField } from '../components/FormFields'
import { StatusCard } from '../components/StatusCard'
import { ApiError, type FieldErrors } from '../lib/apiError'
import { fieldErrorNode } from '../lib/fieldErrors'
import { useResend } from '../lib/useResend'

// ปุ่มลิงก์แบบตัวอักษรม่วง (ใช้ทั้งลิงก์ไปหน้าอื่นและปุ่มที่หน้าตาเป็นลิงก์)
const LINK_CLASS =
  'font-semibold text-plum-800 underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800'

// หน้าสมัครสมาชิกด้วยอีเมล ตาม wireframe: ได้บัญชีผู้เรียนที่ต้องยืนยันอีเมลก่อนเข้าใช้งาน
export default function RegisterPage() {
  const { t } = useTranslation()

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  // รหัสกฎที่ไม่ผ่านของแต่ละช่อง (จาก backend หรือที่ตรวจเองในหน้านี้) เก็บเป็นรหัสไว้แปลตามภาษาปัจจุบัน
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  // error ที่ไม่ผูกกับช่องใด (เช่นเครือข่ายล่ม)
  const [errorCode, setErrorCode] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  // อีเมลที่สมัครสำเร็จ (มีค่า = แสดงหน้า "ตรวจสอบอีเมลของคุณ")
  const [sentTo, setSentTo] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorCode(null)

    // ช่อง "ยืนยันรหัสผ่าน" ตรวจที่หน้าเว็บ (ไม่ส่งไป backend)
    if (password !== confirmPassword) {
      setFieldErrors({ confirm_password: ['mismatch'] })
      return
    }

    setSubmitting(true)
    setFieldErrors({})
    const cleanEmail = email.trim()
    try {
      await registerAccount({
        email: cleanEmail,
        password,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
      })
      // ไม่เก็บรหัสผ่านค้างในหน่วยความจำของหน้าต่อไป
      setPassword('')
      setConfirmPassword('')
      setSentTo(cleanEmail)
    } catch (error) {
      if (error instanceof ApiError && error.code === 'email_taken') {
        setFieldErrors({ email: ['email_taken'] })
      } else if (error instanceof ApiError && error.code === 'validation_error' && error.errorCodes) {
        setFieldErrors(error.errorCodes)
      } else {
        setErrorCode(error instanceof ApiError ? error.code : 'unknown_error')
      }
      setSubmitting(false)
    }
  }

  const layoutText = { tagline: t('register.tagline'), taglineSub: t('register.taglineSub') }

  if (sentTo) {
    return (
      <AuthLayout {...layoutText}>
        <CheckInbox email={sentTo} />
      </AuthLayout>
    )
  }

  return (
    <AuthLayout {...layoutText} title={t('register.title')} subtitle={t('register.subtitle')}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-[18px]">
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

        <div className="grid grid-cols-2 gap-3.5">
          <TextField
            label={t('register.firstName')}
            value={firstName}
            onChange={setFirstName}
            autoComplete="given-name"
            maxLength={150}
            error={fieldErrorNode(t, fieldErrors.first_name)}
          />
          <TextField
            label={t('register.lastName')}
            value={lastName}
            onChange={setLastName}
            autoComplete="family-name"
            maxLength={150}
            error={fieldErrorNode(t, fieldErrors.last_name)}
          />
        </div>

        <TextField
          label={t('register.email')}
          type="email"
          value={email}
          onChange={setEmail}
          autoComplete="email"
          placeholder={t('register.emailPlaceholder')}
          maxLength={254}
          error={
            fieldErrors.email?.includes('email_taken') ? (
              // อีเมลนี้มีบัญชีแล้ว: บอกทางไปต่อ (เข้าสู่ระบบ)
              <>
                {t('fieldErrors.email_taken')}{' '}
                <Link to="/login" className={LINK_CLASS}>
                  {t('register.login')}
                </Link>
              </>
            ) : (
              fieldErrorNode(t, fieldErrors.email)
            )
          }
        />

        <PasswordField
          label={t('register.password')}
          value={password}
          onChange={setPassword}
          autoComplete="new-password"
          maxLength={1024}
          hint={t('register.passwordHint')}
          error={fieldErrorNode(t, fieldErrors.password)}
        />

        <PasswordField
          label={t('register.confirmPassword')}
          value={confirmPassword}
          onChange={setConfirmPassword}
          autoComplete="new-password"
          maxLength={1024}
          error={fieldErrorNode(t, fieldErrors.confirm_password)}
        />

        <button
          type="submit"
          disabled={submitting}
          className="mt-1 h-12 cursor-pointer rounded-md bg-plum-800 text-base font-semibold text-plum-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? t('register.submitting') : t('register.submit')}
        </button>
      </form>

      <p className="border-t border-line pt-4 text-sm text-ink-2">
        {t('register.haveAccount')}{' '}
        <Link to="/login" className={LINK_CLASS}>
          {t('register.login')}
        </Link>
      </p>
    </AuthLayout>
  )
}

// หน้า "ตรวจสอบอีเมลของคุณ" หลังสมัครสำเร็จ พร้อมปุ่มส่งลิงก์ยืนยันอีกครั้ง (รอ 60 วินาทีระหว่างครั้งตามที่ backend กำหนด)
function CheckInbox({ email }: { email: string }) {
  const { t } = useTranslation()
  const resend = useResend(resendVerification)

  return (
    <StatusCard tone="info" icon="mail" title={t('checkInbox.title')}>
      <p className="text-sm leading-[1.7] text-ink-2">
        {/* อีเมลเป็นตัวเข้มเพื่อให้ผู้ใช้เห็นชัดว่าส่งไปที่ไหน (ตรวจว่าพิมพ์ถูกไหม) */}
        <Trans
          i18nKey="checkInbox.body"
          values={{ email }}
          components={{ email: <span className="font-medium text-ink" /> }}
        />
      </p>

      <p className="text-[13.5px] text-ink-2">
        {t('checkInbox.noEmail')}{' '}
        <button
          type="button"
          onClick={() => void resend.trigger(email)}
          disabled={resend.status === 'sending' || resend.secondsLeft > 0}
          className={`cursor-pointer ${LINK_CLASS} disabled:cursor-not-allowed disabled:text-ink-3 disabled:no-underline`}
        >
          {resend.secondsLeft > 0
            ? t('checkInbox.resendWait', { seconds: resend.secondsLeft })
            : t('checkInbox.resend')}
        </button>
      </p>

      {/* ผลการส่ง: role=status ให้โปรแกรมอ่านหน้าจออ่านเมื่อข้อความเปลี่ยน */}
      <div role="status" className="text-[13px] leading-normal text-ok-800">
        {resend.status === 'sent' && t('checkInbox.resent')}
      </div>
      {resend.status === 'error' && (
        <p role="alert" className="text-[13px] leading-normal text-error-800">
          {t(`errors.${resend.errorCode}.title`, { defaultValue: t('errors.unknown_error.title') })}
        </p>
      )}
    </StatusCard>
  )
}
