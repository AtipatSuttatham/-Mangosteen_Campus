import { useTranslation } from 'react-i18next'

import { PASSWORD_RULES } from '../lib/passwordRules'
import { Icon } from './Icon'

type PasswordRulesProps = {
  password: string
  /** ผู้ใช้กดส่งแล้วหรือยัง — ข้อที่ยังไม่ผ่านจึงเปลี่ยนจากสีเทา (ยังพิมพ์อยู่) เป็นสีแดง */
  attempted: boolean
  /** รหัสกฎที่ backend ปฏิเสธล่าสุด (ถ้ามี) */
  serverCodes: string[]
}

// รายการเงื่อนไขของรหัสผ่านที่ติ๊กสดตอนพิมพ์ ตาม wireframe: ผ่าน = วงกลมเขียวมีเครื่องหมายถูก, ยังไม่ผ่าน = วงกลมเทา,
// ไม่ผ่านหลังกดส่ง/ถูก backend ปฏิเสธ = วงกลมแดง — สถานะบอกด้วยข้อความสำหรับโปรแกรมอ่านหน้าจอด้วย ไม่ใช้สีอย่างเดียว
// กฎที่ต้องใช้ข้อมูลฝั่ง backend (รหัสคนใช้กัน / คล้ายชื่อหรืออีเมล) ไม่อยู่ในรายการนี้ — แสดงเป็นข้อความใต้ช่องเมื่อถูกปฏิเสธ
export function PasswordRules({ password, attempted, serverCodes }: PasswordRulesProps) {
  const { t } = useTranslation()

  return (
    <ul aria-label={t('reset.rulesLabel')} className="flex flex-col gap-2.5 border-y border-line py-3.5">
      {PASSWORD_RULES.map((rule) => {
        // backend ปฏิเสธข้อนี้ = ไม่ผ่านแน่ แม้หน้าเว็บนับว่าผ่าน (กันหน้าเว็บโชว์ติ๊กเขียวหลอก ๆ)
        const rejectedByServer = serverCodes.includes(rule.backendCode)
        const met = rule.met(password)
        const passed = met && !rejectedByServer
        // แดงเมื่อ backend ปฏิเสธ หรือกดส่งแล้วแต่ยังไม่ผ่าน; ระหว่างพิมพ์ที่ยังไม่ผ่านเป็นสีเทา
        const bad = rejectedByServer || (!met && attempted)

        return (
          <li
            key={rule.labelKey}
            className={`flex items-center gap-2.5 text-[13.5px] ${
              passed ? 'text-ink' : bad ? 'text-error-800' : 'text-ink-3'
            }`}
          >
            <span
              aria-hidden="true"
              className={`flex size-[18px] shrink-0 items-center justify-center rounded-full border ${
                passed
                  ? 'border-ok-800 text-ok-800'
                  : bad
                    ? 'border-error-800 text-error-800'
                    : 'border-ink-3 text-transparent'
              }`}
            >
              <Icon name={bad ? 'close' : 'check'} size={11} />
            </span>
            <span>{t(rule.labelKey)}</span>
            {/* สถานะเป็นข้อความสำหรับโปรแกรมอ่านหน้าจอ (ผู้ใช้ทั่วไปเห็นจากวงกลม) */}
            <span className="sr-only">{passed ? t('reset.rulePassed') : t('reset.ruleFailed')}</span>
          </li>
        )
      })}
    </ul>
  )
}
