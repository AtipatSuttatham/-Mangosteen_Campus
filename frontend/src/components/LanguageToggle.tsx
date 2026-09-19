import { Fragment } from 'react'
import { useTranslation } from 'react-i18next'

import { SUPPORTED_LANGUAGES } from '../i18n/language'

type LanguageToggleProps = {
  /** ใช้สีอ่อนเมื่ออยู่บนพื้นม่วงในจอเล็ก (ต่ำกว่า lg) และกลับเป็นสีปกติบนจอกว้าง — ใช้กับหน้า login */
  lightBelowLg?: boolean
  /** ใช้สีอ่อนเสมอ (วางบนพื้นม่วง เช่น ลิ้นชักเมนูมือถือ) */
  onDark?: boolean
}

// ปุ่มสลับภาษา TH / EN — ตัวที่เลือกอยู่จะเน้นด้วยตัวหนาและเส้นใต้
export function LanguageToggle({ lightBelowLg = false, onDark = false }: LanguageToggleProps) {
  const { t, i18n } = useTranslation()

  let activeTone = 'border-plum-800 text-plum-800'
  let inactiveTone = 'text-ink-3'
  let dividerTone = 'text-line'
  if (onDark) {
    activeTone = 'border-sage-400 text-plum-50'
    inactiveTone = 'text-plum-300'
    dividerTone = 'text-plum-300'
  } else if (lightBelowLg) {
    activeTone = 'border-sage-400 text-plum-50 lg:border-plum-800 lg:text-plum-800'
    inactiveTone = 'text-plum-300 lg:text-ink-3'
    dividerTone = 'text-plum-300 lg:text-line'
  }

  return (
    <div role="group" aria-label={t('language.label')} className="flex items-baseline gap-1.5 text-[13px]">
      {SUPPORTED_LANGUAGES.map((lng, index) => {
        const active = i18n.resolvedLanguage === lng
        return (
          <Fragment key={lng}>
            {/* เครื่องหมายคั่นระหว่างสองภาษา (ตกแต่งอย่างเดียว) */}
            {index > 0 && (
              <span aria-hidden="true" className={dividerTone}>
                /
              </span>
            )}
            <button
              type="button"
              aria-pressed={active}
              onClick={() => void i18n.changeLanguage(lng)}
              className={
                'cursor-pointer border-b-[1.5px] pb-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-plum-800 ' +
                (active ? `${activeTone} font-bold` : `border-transparent font-medium ${inactiveTone}`)
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
