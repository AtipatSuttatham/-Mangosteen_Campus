import { Fragment } from 'react'
import { useTranslation } from 'react-i18next'

// ภาษาที่ระบบรองรับ (ไทยเป็นค่าเริ่มต้น)
const LANGUAGES = ['th', 'en'] as const

// ปุ่มสลับภาษา TH / EN — ตัวที่เลือกอยู่จะเน้นด้วยตัวหนาและเส้นใต้สีม่วง
export function LanguageToggle() {
  const { t, i18n } = useTranslation()

  return (
    <div role="group" aria-label={t('language.label')} className="flex items-baseline gap-1.5 text-[13px]">
      {LANGUAGES.map((lng, index) => {
        const active = i18n.resolvedLanguage === lng
        return (
          <Fragment key={lng}>
            {/* เครื่องหมายคั่นระหว่างสองภาษา (ตกแต่งอย่างเดียว) */}
            {index > 0 && (
              <span aria-hidden="true" className="text-line">
                /
              </span>
            )}
            <button
              type="button"
              aria-pressed={active}
              onClick={() => void i18n.changeLanguage(lng)}
              className={
                'cursor-pointer border-b-[1.5px] pb-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800 ' +
                (active
                  ? 'border-plum-800 font-bold text-plum-800'
                  : 'border-transparent font-medium text-ink-3')
              }
            >
              {lng.toUpperCase()}
            </button>
          </Fragment>
        )
      })}
    </div>
  )
}
