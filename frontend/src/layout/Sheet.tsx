import { useEffect, useRef, type ReactNode } from 'react'

import { cx } from '../lib/cx'

type SheetProps = {
  open: boolean
  onClose: () => void
  /** ชื่อของลิ้นชักสำหรับโปรแกรมอ่านหน้าจอ */
  label: string
  /** left = ลิ้นชักเมนูด้านซ้าย (พื้นม่วง), bottom = แผ่นด้านล่าง (พื้นสว่าง) */
  side: 'left' | 'bottom'
  children: ReactNode
}

// ลิ้นชัก/แผ่นเลื่อนขึ้นบนมือถือ — ใช้ <dialog> มาตรฐานของเบราว์เซอร์
// ได้การดักโฟกัสในลิ้นชัก ปุ่ม Esc ปิด และม่านมืดด้านหลังมาให้โดยไม่ต้องเขียนเอง
export function Sheet({ open, onClose, label, side, children }: SheetProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  // ให้สถานะ open ของ React กับสถานะจริงของ <dialog> ตรงกัน
  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      aria-label={label}
      // ปิดด้วย Esc หรือปิดผ่านโค้ด → แจ้งให้ผู้ใช้ component ตั้ง open เป็น false
      onClose={onClose}
      // แตะที่ม่านมืด (ตัว <dialog> เอง ไม่ใช่เนื้อหาข้างใน) → ปิด
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
      className={cx(
        'fixed m-0 max-h-none p-0 backdrop:bg-ink/55',
        side === 'left'
          ? 'inset-y-0 left-0 h-dvh w-[300px] max-w-[85vw] overflow-y-auto bg-plum-800 text-plum-50'
          : 'inset-x-0 top-auto bottom-0 w-full max-w-none rounded-t-2xl bg-paper text-ink',
      )}
    >
      {children}
    </dialog>
  )
}
