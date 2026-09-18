// ตัวช่วยตรวจ DOM ใน test เช่น toBeInTheDocument
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// ล้าง component ที่ render ไว้หลังจบแต่ละ test เพื่อไม่ให้ปนกัน
afterEach(() => {
  cleanup()
})
