import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import { DEFAULT_LANGUAGE, getInitialLanguage, storeLanguage } from './language'
import en from './locales/en.json'
import th from './locales/th.json'

const initialLanguage = getInitialLanguage()

// ตั้งค่าระบบหลายภาษา: ใช้ภาษาที่ผู้ใช้เคยเลือกไว้ ถ้าไม่มีใช้ไทย
// ข้อความทุกตัวในแอปต้องมาจาก translation key ในไฟล์ locales
void i18n.use(initReactI18next).init({
  resources: {
    th: { translation: th },
    en: { translation: en },
  },
  lng: initialLanguage,
  fallbackLng: DEFAULT_LANGUAGE,
  // React escape ข้อความให้อยู่แล้ว ไม่ต้อง escape ซ้ำ
  interpolation: { escapeValue: false },
})

// ให้ attribute lang ของ <html> ตรงกับภาษาที่แสดงอยู่ (screen reader และการตัดคำภาษาไทยใช้ค่านี้)
document.documentElement.lang = initialLanguage

// เมื่อผู้ใช้สลับภาษา: อัปเดต lang ของหน้า และจำไว้สำหรับครั้งหน้า
i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng
  storeLanguage(lng)
})

export default i18n
