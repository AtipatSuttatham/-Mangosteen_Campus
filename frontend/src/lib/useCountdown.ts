import { useCallback, useEffect, useState } from 'react'

// ตัวนับถอยหลังเป็นวินาที (ใช้กับปุ่ม "ส่งอีกครั้ง": backend ให้ขอลิงก์ใหม่ได้ทุก 60 วินาที หน้าเว็บนับเองไว้ไม่ให้กดแล้วเงียบ)
// คืน [วินาทีที่เหลือ, ฟังก์ชันเริ่มนับใหม่] — 0 = กดได้แล้ว; backend เป็นตัวบังคับจริง นี่เป็นแค่การช่วยผู้ใช้
export function useCountdown(): [number, (seconds: number) => void] {
  const [remaining, setRemaining] = useState(0)

  useEffect(() => {
    if (remaining <= 0) return
    const timer = window.setTimeout(() => setRemaining((seconds) => seconds - 1), 1000)
    return () => window.clearTimeout(timer)
  }, [remaining])

  const start = useCallback((seconds: number) => setRemaining(seconds), [])
  return [remaining, start]
}
