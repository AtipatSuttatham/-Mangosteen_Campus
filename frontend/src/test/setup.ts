// ตัวช่วยตรวจ DOM ใน test เช่น toBeInTheDocument
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

import { setAccessToken } from '../auth/session'
import i18n from '../i18n'

// ทุก test เริ่มที่ภาษาไทยเสมอ (ค่าเริ่มต้นของระบบ)
beforeEach(async () => {
  await i18n.changeLanguage('th')
})

afterEach(() => {
  // ล้าง component ที่ render ไว้เพื่อไม่ให้ปนกัน
  cleanup()
  // เลิกจำลอง fetch และล้าง access token ที่ค้างในหน่วยความจำ
  vi.unstubAllGlobals()
  setAccessToken(null)
  // ล้างภาษาที่จำไว้ ไม่ให้ค้างข้าม test
  localStorage.clear()
})
