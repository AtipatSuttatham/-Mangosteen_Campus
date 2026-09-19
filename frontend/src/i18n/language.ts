// ภาษาที่ระบบรองรับ (ไทยเป็นค่าเริ่มต้น)
export const SUPPORTED_LANGUAGES = ['th', 'en'] as const
export type Language = (typeof SUPPORTED_LANGUAGES)[number]
export const DEFAULT_LANGUAGE: Language = 'th'

// คีย์ที่ใช้เก็บภาษาที่ผู้ใช้เลือกไว้ในเบราว์เซอร์ (เป็นค่าตั้งค่าหน้าจอ ไม่ใช่ข้อมูลลับ)
const STORAGE_KEY = 'mangosteen.language'

function isLanguage(value: unknown): value is Language {
  return SUPPORTED_LANGUAGES.some((language) => language === value)
}

// อ่านภาษาที่เคยเลือกไว้ — คืน null ถ้าไม่เคยเลือก ค่าเสียหาย หรือเบราว์เซอร์ไม่ให้ใช้ที่เก็บข้อมูล (เช่น โหมดส่วนตัว)
export function readStoredLanguage(): Language | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return isLanguage(value) ? value : null
  } catch {
    return null
  }
}

// จำภาษาที่เลือก (บันทึกไม่ได้ก็ไม่เป็นไร แค่ครั้งหน้าจะกลับเป็นค่าเริ่มต้น)
export function storeLanguage(language: string): void {
  if (!isLanguage(language)) return
  try {
    localStorage.setItem(STORAGE_KEY, language)
  } catch {
    // ที่เก็บข้อมูลใช้ไม่ได้ — ข้ามไป
  }
}

// ภาษาตอนเปิดเว็บ: ที่เคยเลือกไว้ ถ้าไม่มีใช้ไทย
export function getInitialLanguage(): Language {
  return readStoredLanguage() ?? DEFAULT_LANGUAGE
}
