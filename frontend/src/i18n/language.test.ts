import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getInitialLanguage, readStoredLanguage, storeLanguage } from './language'

// เริ่มทุกข้อจากที่เก็บข้อมูลว่าง (ตัวตั้งค่ากลางของ test สลับภาษาเป็นไทยก่อนทุกข้อ ซึ่งทำให้ระบบจำ "th" ไว้แล้ว)
beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  localStorage.clear()
})

describe('ภาษาที่จำไว้', () => {
  it('ไม่เคยเลือก → ใช้ไทย', () => {
    expect(readStoredLanguage()).toBeNull()
    expect(getInitialLanguage()).toBe('th')
  })

  it('เลือกอังกฤษแล้ว → ครั้งหน้าเปิดเป็นอังกฤษ', () => {
    storeLanguage('en')

    expect(getInitialLanguage()).toBe('en')
  })

  it('ค่าที่เก็บไว้เสียหายหรือไม่รู้จัก → ใช้ไทย (ไม่เชื่อค่าจากที่เก็บข้อมูลโดยไม่ตรวจ)', () => {
    localStorage.setItem('mangosteen.language', '<script>')

    expect(readStoredLanguage()).toBeNull()
    expect(getInitialLanguage()).toBe('th')
  })

  it('ไม่บันทึกภาษาที่ระบบไม่รองรับ', () => {
    storeLanguage('fr')

    expect(readStoredLanguage()).toBeNull()
  })

  it('เบราว์เซอร์ไม่ให้ใช้ที่เก็บข้อมูล (เช่นโหมดส่วนตัว) → ไม่ error และใช้ไทย', () => {
    const blocked = () => {
      throw new DOMException('blocked', 'SecurityError')
    }
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(blocked)
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(blocked)

    expect(() => storeLanguage('en')).not.toThrow()
    expect(getInitialLanguage()).toBe('th')

    vi.restoreAllMocks()
  })
})
