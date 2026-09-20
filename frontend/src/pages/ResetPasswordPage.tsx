import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router'

import { checkResetToken, resetPassword } from '../auth/accountApi'
import { clearSession } from '../auth/session'
import { AuthLayout } from '../components/AuthLayout'
import { PasswordField } from '../components/FormFields'
import { PasswordRules } from '../components/PasswordRules'
import { StatusCard } from '../components/StatusCard'
import { ApiError } from '../lib/apiError'
import { fieldErrorNode } from '../lib/fieldErrors'
import { meetsPasswordRules, PASSWORD_RULES } from '../lib/passwordRules'

const PRIMARY_BUTTON_CLASS =
  'h-12 cursor-pointer rounded-md bg-plum-800 px-6 text-base font-semibold text-plum-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800 disabled:cursor-not-allowed disabled:opacity-60'

// รหัสกฎที่รายการติ๊กแสดงอยู่แล้ว — ที่เหลือ (รหัสคนใช้กัน / คล้ายชื่อหรืออีเมล) แสดงเป็นข้อความใต้ช่อง
const CHECKLIST_CODES: string[] = PASSWORD_RULES.map((rule) => rule.backendCode)

// ผลการตรวจลิงก์: กำลังตรวจ / ใช้ได้ (พร้อมอีเมลของบัญชี) / ใช้ไม่ได้ / ติดต่อระบบไม่ได้ (ลองใหม่ได้)
type Phase = { kind: 'checking' } | { kind: 'form'; email: string } | { kind: 'invalid' } | { kind: 'network' }

// หน้าที่เปิดจากลิงก์ในอีเมลลืมรหัสผ่าน (/reset-password?token=...) — ใช้ตั้งรหัสแรกของบัญชีที่ Admin สร้างให้ได้ด้วย
export default function ResetPasswordPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const token = params.get('token')

  const [phase, setPhase] = useState<Phase>({ kind: 'checking' })
  // กันตรวจลิงก์ซ้ำตอน dev ที่ React รัน effect สองรอบ (เหมือนหน้ายืนยันอีเมล)
  const started = useRef(false)

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  // กดส่งแล้วหรือยัง (ข้อที่ยังไม่ผ่านจะกลายเป็นสีแดง) และรหัสกฎที่ backend ปฏิเสธล่าสุด
  const [attempted, setAttempted] = useState(false)
  const [serverCodes, setServerCodes] = useState<string[]>([])
  const [mismatch, setMismatch] = useState(false)
  const [errorCode, setErrorCode] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function check() {
    setPhase({ kind: 'checking' })
    if (!token) {
      setPhase({ kind: 'invalid' })
      return
    }
    try {
      setPhase({ kind: 'form', email: await checkResetToken(token) })
    } catch (error) {
      const linkIsBad =
        error instanceof ApiError && (error.code === 'token_invalid' || error.code === 'token_expired')
      setPhase(linkIsBad ? { kind: 'invalid' } : { kind: 'network' })
    }
  }

  useEffect(() => {
    if (started.current) return
    started.current = true
    void check()
    // check ผูกกับ token ของ URL ที่เปิดหน้ามา (หน้านี้ไม่รองรับเปลี่ยน token ระหว่างเปิดอยู่)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAttempted(true)
    setErrorCode(null)
    setServerCodes([])
    setMismatch(false)

    if (password !== confirmPassword) {
      setMismatch(true)
      return
    }
    // ยังไม่ผ่านกฎที่ตรวจได้ในหน้าเว็บ: ไม่ต้องส่งไปให้ backend ปฏิเสธ (รายการกฎเป็นสีแดงบอกอยู่แล้ว)
    if (!meetsPasswordRules(password) || !token) return

    setSubmitting(true)
    try {
      await resetPassword(token, password)
      // เซสชันเดิมของบัญชีนี้ตายแล้วที่ backend — ล้างสถานะล็อกอินในหน้าเว็บด้วย ไม่งั้นคนที่ล็อกอินค้างอยู่
      // จะถูกหน้า login เด้งกลับ dashboard ทั้งที่ใช้งานต่อไม่ได้
      clearSession()
      navigate('/login', { replace: true, state: { notice: 'passwordReset' } })
    } catch (error) {
      if (error instanceof ApiError && (error.code === 'token_invalid' || error.code === 'token_expired')) {
        // ลิงก์ถูกใช้/แทนที่/หมดอายุระหว่างที่กรอก
        setPhase({ kind: 'invalid' })
      } else if (error instanceof ApiError && error.code === 'validation_error' && error.errorCodes) {
        setServerCodes(error.errorCodes.password ?? [])
      } else {
        setErrorCode(error instanceof ApiError ? error.code : 'unknown_error')
      }
      setSubmitting(false)
    }
  }

  const layoutText = { tagline: t('reset.tagline'), taglineSub: t('reset.taglineSub') }

  if (phase.kind === 'checking') {
    return (
      <AuthLayout {...layoutText}>
        <p role="status" className="text-ink-2">
          {t('reset.checking')}
        </p>
      </AuthLayout>
    )
  }

  if (phase.kind === 'network') {
    return (
      <AuthLayout {...layoutText}>
        <StatusCard tone="warn" icon="clock" title={t('errors.network_error.title')}>
          <p className="text-sm leading-[1.7] text-ink-2">{t('errors.network_error.description')}</p>
          <button type="button" onClick={() => void check()} className={`${PRIMARY_BUTTON_CLASS} mt-2`}>
            {t('reset.retry')}
          </button>
        </StatusCard>
      </AuthLayout>
    )
  }

  if (phase.kind === 'invalid') {
    return (
      <AuthLayout {...layoutText}>
        <StatusCard tone="warn" icon="clock" title={t('reset.invalidTitle')}>
          <p className="text-sm leading-[1.7] text-ink-2">{t('reset.invalidBody')}</p>
          <Link
            to="/forgot-password"
            className="mt-2 flex h-12 items-center justify-center rounded-md border border-plum-800 text-base font-semibold text-plum-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800"
          >
            {t('reset.requestNew')}
          </Link>
        </StatusCard>
      </AuthLayout>
    )
  }

  // ข้อความใต้ช่องรหัสผ่านสำหรับกฎที่ไม่อยู่ในรายการติ๊ก (รหัสคนใช้กัน / คล้ายชื่อหรืออีเมล)
  const extraCodes = serverCodes.filter((code) => !CHECKLIST_CODES.includes(code))

  return (
    <AuthLayout
      {...layoutText}
      title={t('reset.title')}
      subtitle={t('reset.subtitle', { email: phase.email })}
    >
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

        <PasswordField
          label={t('reset.newPassword')}
          value={password}
          onChange={(value) => {
            setPassword(value)
            // แก้รหัสแล้ว ผลปฏิเสธเก่าไม่เกี่ยวแล้ว
            setServerCodes([])
          }}
          autoComplete="new-password"
          maxLength={1024}
          error={fieldErrorNode(t, extraCodes)}
        />

        <PasswordField
          label={t('reset.confirmPassword')}
          value={confirmPassword}
          onChange={setConfirmPassword}
          autoComplete="new-password"
          maxLength={1024}
          error={fieldErrorNode(t, mismatch ? ['mismatch'] : undefined)}
        />

        <PasswordRules password={password} attempted={attempted} serverCodes={serverCodes} />

        <button type="submit" disabled={submitting} className={`${PRIMARY_BUTTON_CLASS} w-full`}>
          {submitting ? t('reset.submitting') : t('reset.submit')}
        </button>
      </form>
    </AuthLayout>
  )
}
