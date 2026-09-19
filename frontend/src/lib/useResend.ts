import { useCallback, useState } from 'react'

import { ApiError } from './apiError'
import { useCountdown } from './useCountdown'

// backend ให้ขอลิงก์ใหม่ของอีเมลเดียวกันได้ทุก 60 วินาที (หน้าเว็บนับเองไว้ไม่ให้กดแล้วเงียบ)
export const RESEND_COOLDOWN_SECONDS = 60

export type ResendStatus = 'idle' | 'sending' | 'sent' | 'error'

// ตรรกะปุ่ม "ส่งลิงก์อีกครั้ง": กันกดซ้ำระหว่างส่งและระหว่างรอ 60 วินาที แล้วรายงานสถานะให้หน้าจอแสดง
// send = ฟังก์ชันเรียก API (รับอีเมล) — backend ตอบเหมือนกันทุกกรณี จึงบอกได้แค่ว่า "ส่งคำขอแล้ว"
export function useResend(send: (email: string) => Promise<void>) {
  const [status, setStatus] = useState<ResendStatus>('idle')
  // code ของ error ล่าสุด (ใช้แปลข้อความ) เมื่อ status = 'error'
  const [errorCode, setErrorCode] = useState<string | null>(null)
  const [secondsLeft, startCountdown] = useCountdown()

  const trigger = useCallback(
    async (email: string) => {
      if (status === 'sending' || secondsLeft > 0) return
      setStatus('sending')
      setErrorCode(null)
      try {
        await send(email)
        setStatus('sent')
        startCountdown(RESEND_COOLDOWN_SECONDS)
      } catch (error) {
        setErrorCode(error instanceof ApiError ? error.code : 'unknown_error')
        setStatus('error')
      }
    },
    [send, status, secondsLeft, startCountdown],
  )

  return { status, errorCode, secondsLeft, trigger }
}
