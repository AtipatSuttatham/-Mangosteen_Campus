import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './locales/en.json'
import th from './locales/th.json'

// ตั้งค่าระบบหลายภาษา: ค่าเริ่มต้นเป็นไทย ข้อความทุกตัวในแอปต้องมาจาก translation key ในไฟล์ locales
void i18n.use(initReactI18next).init({
  resources: {
    th: { translation: th },
    en: { translation: en },
  },
  lng: 'th',
  fallbackLng: 'th',
  // React escape ข้อความให้อยู่แล้ว ไม่ต้อง escape ซ้ำ
  interpolation: { escapeValue: false },
})

// ให้ attribute lang ของ <html> ตรงกับภาษาที่เลือก (screen reader และการตัดคำภาษาไทยใช้ค่านี้)
i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng
})

export default i18n
