import { useTranslation } from 'react-i18next'

import { useResend } from '../lib/useResend'

type ResendBlockProps = {
  /** อีเมลที่จะส่งลิงก์ใหม่ให้ */
  email: string
  /** ฟังก์ชันเรียก API ขอลิงก์ใหม่ (รับอีเมล) */
  send: (email: string) => Promise<void>
  /** ชุดข้อความ: ใช้คีย์ `${i18nPrefix}.noEmail / resend / resendWait / resent` (เช่น checkInbox, forgot) */
  i18nPrefix: 'checkInbox' | 'forgot'
}

// "ไม่ได้รับอีเมล? ส่งอีกครั้ง" หลังส่งลิงก์ไปที่อีเมลแล้ว: ปุ่มรอ 60 วินาทีระหว่างครั้ง (ตามที่ backend กำหนด)
// แล้วบอกผลด้วยข้อความ (backend ตอบเหมือนกันทุกกรณี จึงบอกได้แค่ว่า "ส่งคำขอแล้ว")
export function ResendBlock({ email, send, i18nPrefix }: ResendBlockProps) {
  const { t } = useTranslation()
  const resend = useResend(send)
  const waiting = resend.secondsLeft > 0

  return (
    <>
      <p className="text-[13.5px] text-ink-2">
        {t(`${i18nPrefix}.noEmail`)}{' '}
        <button
          type="button"
          onClick={() => void resend.trigger(email)}
          disabled={resend.status === 'sending' || waiting}
          className="cursor-pointer font-semibold text-plum-800 underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800 disabled:cursor-not-allowed disabled:text-ink-3 disabled:no-underline"
        >
          {waiting
            ? t(`${i18nPrefix}.resendWait`, { seconds: resend.secondsLeft })
            : t(`${i18nPrefix}.resend`)}
        </button>
      </p>

      {/* ผลการส่ง: role=status ให้โปรแกรมอ่านหน้าจออ่านเมื่อข้อความเปลี่ยน */}
      <div role="status" className="text-[13px] leading-normal text-ok-800">
        {resend.status === 'sent' && t(`${i18nPrefix}.resent`)}
      </div>
      {resend.status === 'error' && (
        <p role="alert" className="text-[13px] leading-normal text-error-800">
          {t(`errors.${resend.errorCode}.title`, { defaultValue: t('errors.unknown_error.title') })}
        </p>
      )}
    </>
  )
}
