import { useId, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

// ลักษณะร่วมของช่องกรอกข้อมูล (สูง 48px ตัวอักษรอย่างน้อย 16px กันเบราว์เซอร์มือถือซูมเองตอนแตะช่อง)
export const FIELD_CLASS =
  'h-12 w-full rounded-md border border-field bg-white px-3.5 text-base text-ink placeholder:text-ink-3 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-plum-800 aria-[invalid=true]:border-error-800'

type FieldShellProps = {
  id: string
  label: string
  /** คำอธิบายใต้ช่อง (เช่น เงื่อนไขของรหัสผ่าน) */
  hint?: string
  /** ข้อความผิดพลาดใต้ช่อง — มี = ช่องถูกทำเครื่องหมายว่าไม่ถูกต้อง */
  error?: ReactNode
  children: ReactNode
}

// ป้ายชื่อ + ช่อง + คำอธิบาย + ข้อความผิดพลาด (ผูกกับช่องด้วย aria-describedby ให้โปรแกรมอ่านหน้าจออ่านให้)
function FieldShell({ id, label, hint, error, children }: FieldShellProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[13.5px] font-medium">
        {label}
      </label>
      {children}
      {hint && (
        <p id={`${id}-hint`} className="text-[12.5px] leading-normal text-ink-3">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-[13px] leading-normal text-error-800">
          {error}
        </p>
      )}
    </div>
  )
}

// รวม id ของคำอธิบาย/ข้อผิดพลาดที่มีอยู่จริง ไว้ใส่ aria-describedby
function describedBy(id: string, hint?: string, error?: ReactNode): string | undefined {
  const ids = [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(Boolean)
  return ids.length > 0 ? ids.join(' ') : undefined
}

type InputProps = {
  label: string
  value: string
  onChange: (value: string) => void
  autoComplete?: string
  placeholder?: string
  required?: boolean
  maxLength?: number
  hint?: string
  error?: ReactNode
  /** id ของช่อง (ไม่ใส่ = สร้างให้เอง) */
  id?: string
  /** ข้อความเพิ่มเติมใต้ช่อง เช่น ลิงก์ "ลืมรหัสผ่าน" */
  footer?: ReactNode
}

type TextFieldProps = InputProps & { type?: 'text' | 'email' }

// ช่องข้อความทั่วไป (ชื่อ, อีเมล ฯลฯ)
export function TextField({
  label,
  value,
  onChange,
  type = 'text',
  autoComplete,
  placeholder,
  required = true,
  maxLength,
  hint,
  error,
  id,
  footer,
}: TextFieldProps) {
  const autoId = useId()
  const fieldId = id ?? autoId

  return (
    <FieldShell id={fieldId} label={label} hint={hint} error={error}>
      <input
        id={fieldId}
        type={type}
        autoComplete={autoComplete}
        required={required}
        maxLength={maxLength}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(fieldId, hint, error)}
        className={FIELD_CLASS}
      />
      {footer}
    </FieldShell>
  )
}

// ช่องรหัสผ่านพร้อมปุ่ม แสดง/ซ่อน (ปุ่มบอกสถานะให้โปรแกรมอ่านหน้าจอด้วย aria-pressed)
export function PasswordField({
  label,
  value,
  onChange,
  autoComplete,
  placeholder,
  required = true,
  maxLength,
  hint,
  error,
  id,
  footer,
}: InputProps) {
  const { t } = useTranslation()
  const autoId = useId()
  const fieldId = id ?? autoId
  const [shown, setShown] = useState(false)

  return (
    <FieldShell id={fieldId} label={label} hint={hint} error={error}>
      <div className="relative">
        <input
          id={fieldId}
          type={shown ? 'text' : 'password'}
          autoComplete={autoComplete}
          required={required}
          maxLength={maxLength}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(fieldId, hint, error)}
          className={`${FIELD_CLASS} pr-[72px]`}
        />
        <button
          type="button"
          onClick={() => setShown((current) => !current)}
          aria-pressed={shown}
          aria-label={shown ? t('form.hidePasswordLabel') : t('form.showPasswordLabel')}
          className="absolute top-1.5 right-1.5 h-9 cursor-pointer rounded px-3 text-[13px] font-semibold text-plum-800 focus-visible:outline-2 focus-visible:outline-plum-800"
        >
          {shown ? t('form.hidePassword') : t('form.showPassword')}
        </button>
      </div>
      {footer}
    </FieldShell>
  )
}
