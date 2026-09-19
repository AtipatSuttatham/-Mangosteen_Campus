// ตัวช่วยตรวจ DOM ใน test เช่น toBeInTheDocument
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

import { setAccessToken } from '../auth/session'
import i18n from '../i18n'

// jsdom ยังไม่มี <dialog>.showModal()/close() (ลิ้นชักเมนูมือถือใช้ <dialog>) — จำลองแบบง่ายให้ test ทำงานได้
// (ของจริงในเบราว์เซอร์จัดการโฟกัส/Esc/ม่านมืดเอง ส่วนนี้จำลองเฉพาะการเปิด-ปิดและเหตุการณ์ close)
if (typeof HTMLDialogElement !== 'undefined' && !HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute('open', '')
  }
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    if (!this.hasAttribute('open')) return
    this.removeAttribute('open')
    this.dispatchEvent(new Event('close'))
  }
}

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
