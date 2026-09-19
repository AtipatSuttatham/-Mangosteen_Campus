import { fireEvent, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { makeUser } from '../test/fetchMock'
import { renderWithAuth } from '../test/renderWithAuth'
import type { Role } from '../types/auth'

// หา <dialog> จากป้ายชื่อ (aria-label) — dialog ที่ปิดอยู่ถูกนับเป็นองค์ประกอบซ่อน
// ชื่อจึงถูกคำนวณเป็นค่าว่าง ค้นด้วย role+name ตรง ๆ ไม่ได้
function getDialog(label: string): HTMLDialogElement {
  const dialog = screen
    .getAllByRole('dialog', { hidden: true })
    .find((element) => element.getAttribute('aria-label') === label)
  if (!dialog) throw new Error(`ไม่พบ dialog ชื่อ ${label}`)
  return dialog as HTMLDialogElement
}

function renderAs(role: Role) {
  const user = makeUser({ role, first_name: 'สมชาย', last_name: 'ใจดี' })
  return renderWithAuth(`/${role}`, { status: 'authenticated', user })
}

// จำนวนเมนูและป้ายของแต่ละบทบาทตาม wireframe
const NAV_LABELS: Record<Role, string[]> = {
  admin: ['แดชบอร์ด', 'จัดการผู้ใช้', 'ภาคเรียน', 'สนับสนุนระบบ', 'สลับมุมมอง', 'Audit Log'],
  teacher: ['แดชบอร์ด', 'รายวิชาของฉัน'],
  student: ['แดชบอร์ด', 'รายวิชาของฉัน', 'ประกาศ'],
}

describe('เปลือกหน้า (แถบเมนู + dashboard)', () => {
  it.each(['admin', 'teacher', 'student'] as const)('เมนูของ %s ตรงตามแบบ', (role) => {
    renderAs(role)

    // แถบเมนูซ้ายเป็น navigation ตัวแรก (จอเล็กมีแถบล่าง/ลิ้นชักซ้ำอีกชุด ซึ่ง CSS ซ่อนตามขนาดจอ)
    const nav = screen.getAllByRole('navigation', { name: 'เมนูหลัก' })[0]
    const labels = within(nav)
      .getAllByRole('link')
      .map((item) => item.textContent)

    expect(labels).toEqual(NAV_LABELS[role])
  })

  it('เมนูแดชบอร์ดเป็นหน้าปัจจุบัน ส่วนเมนูที่ฟีเจอร์ยังไม่มีกดไม่ได้และบอกเหตุผล', () => {
    renderAs('teacher')
    const nav = screen.getAllByRole('navigation', { name: 'เมนูหลัก' })[0]

    expect(within(nav).getByRole('link', { name: 'แดชบอร์ด' })).toHaveAttribute('aria-current', 'page')
    const courses = within(nav).getByRole('link', { name: 'รายวิชาของฉัน' })
    expect(courses).toHaveAttribute('aria-disabled', 'true')
    expect(courses).toHaveAttribute('title', 'ยังไม่เปิดใช้งาน')
  })

  it('ทักทายด้วยชื่อผู้ใช้ และแสดงชื่อเต็มกับบทบาทที่แถบซ้าย', () => {
    renderAs('teacher')

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('สวัสดี, สมชาย')
    const nav = screen.getAllByRole('navigation', { name: 'เมนูหลัก' })[0]
    const sidebar = nav.closest('aside') as HTMLElement
    expect(within(sidebar).getByText('สมชาย ใจดี')).toBeInTheDocument()
    expect(within(sidebar).getByText('ผู้สอน')).toBeInTheDocument()
  })

  it.each([
    ['admin', ['ผู้สอนในระบบ', 'ผู้เรียนในระบบ', 'รายวิชาที่เปิดสอนอยู่', 'กิจกรรมล่าสุด', 'ทางลัด']],
    ['teacher', ['รายวิชาที่กำลังสอน', 'ผู้เรียนทั้งหมด', 'ชิ้นงานรอตรวจ', 'งานที่รอตรวจ', 'รายวิชาของฉัน']],
    [
      'student',
      [
        'รายวิชาที่ลงทะเบียน',
        'งานที่ต้องส่งสัปดาห์นี้',
        'ประกาศที่ยังไม่ได้อ่าน',
        'งานที่ต้องทำเร็วๆ นี้',
        'ประกาศล่าสุด',
      ],
    ],
  ] as const)('dashboard ของ %s มีหัวข้อครบตามแบบ', (role, texts) => {
    renderAs(role)

    for (const text of texts) {
      expect(screen.getAllByText(text).length).toBeGreaterThan(0)
    }
  })

  it('ยังไม่มี API จึงไม่แสดงตัวเลขสมมติ: ตัวเลขสำคัญเป็น "–" และรายการบอกว่ายังไม่มีข้อมูล', () => {
    renderAs('admin')

    const figures = document.querySelector('dl') as HTMLElement
    expect(figures.textContent).not.toMatch(/\d/)
    expect(within(figures).getAllByText('–')).toHaveLength(3)
    expect(screen.getAllByText('ยังไม่มีข้อมูล').length).toBeGreaterThan(0)
  })

  it('ทางลัดของผู้ดูแลระบบครบ 4 รายการ และกดไม่ได้จนกว่าจะมีหน้านั้น', () => {
    renderAs('admin')

    const shortcuts = document.querySelector('#dashboard-secondary')?.parentElement as HTMLElement
    const items = within(shortcuts).getAllByRole('link')

    expect(items.map((item) => item.textContent)).toEqual([
      'จัดการผู้ใช้',
      'สนับสนุนระบบ',
      'สลับมุมมอง',
      'Audit Log',
    ])
    items.forEach((item) => expect(item).toHaveAttribute('aria-disabled', 'true'))
  })

  it('กระดิ่งแจ้งเตือนแสดงแต่กดไม่ได้ (ยังไม่มีระบบแจ้งเตือน)', () => {
    renderAs('student')

    const bells = screen.getAllByRole('button', { name: 'การแจ้งเตือน' })

    expect(bells.length).toBeGreaterThan(0)
    bells.forEach((bell) => expect(bell).toBeDisabled())
  })

  it('กดออกจากระบบที่แถบซ้าย → เรียก logout', () => {
    const { context } = renderAs('teacher')
    const sidebar = screen.getAllByRole('navigation', { name: 'เมนูหลัก' })[0].closest('aside') as HTMLElement

    fireEvent.click(within(sidebar).getByRole('button', { name: 'ออกจากระบบ' }))

    expect(context.logout).toHaveBeenCalledTimes(1)
  })

  it('สลับภาษาที่หัวหน้า dashboard ได้', () => {
    renderAs('student')

    fireEvent.click(screen.getAllByRole('button', { name: 'EN' })[0])

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Hello, สมชาย')
    expect(document.documentElement.lang).toBe('en')
  })
})

describe('มือถือ', () => {
  it('แถบเมนูล่างของผู้เรียน/ผู้สอน มีเมนูครบตามแบบ (ผู้ดูแลระบบไม่มีแถบล่าง)', () => {
    renderAs('student')
    const navs = screen.getAllByRole('navigation', { name: 'เมนูหลัก' })

    // sidebar + แถบล่าง
    expect(navs).toHaveLength(2)
    expect(within(navs[1]).getAllByRole('link').map((i) => i.textContent)).toEqual(NAV_LABELS.student)
  })

  it('ผู้ดูแลระบบ: ปุ่มเมนูเปิดลิ้นชักที่มีเมนู/ภาษา/ออกจากระบบ และปิดได้', () => {
    const { context } = renderAs('admin')
    const drawer = getDialog('เมนูหลัก')
    expect(drawer.open).toBe(false)

    fireEvent.click(screen.getByRole('button', { name: 'เปิดเมนู' }))

    expect(drawer.open).toBe(true)
    const inDrawer = within(drawer)
    expect(inDrawer.getAllByRole('link')).toHaveLength(6)
    expect(inDrawer.getByRole('button', { name: 'EN' })).toBeInTheDocument()
    fireEvent.click(inDrawer.getByRole('button', { name: 'ออกจากระบบ' }))
    expect(context.logout).toHaveBeenCalledTimes(1)

    fireEvent.click(inDrawer.getByRole('button', { name: 'ปิดเมนู' }))
    expect(drawer.open).toBe(false)
  })

  it('ผู้เรียน/ผู้สอน: ปุ่มชื่อวงกลมเปิดแผ่นโปรไฟล์ที่มีภาษา/ออกจากระบบ', () => {
    const { context } = renderAs('teacher')
    const sheet = getDialog('เมนูโปรไฟล์')

    fireEvent.click(screen.getByRole('button', { name: 'เมนูโปรไฟล์' }))

    expect(sheet.open).toBe(true)
    expect(within(sheet).getByText('สมชาย ใจดี')).toBeInTheDocument()
    fireEvent.click(within(sheet).getByRole('button', { name: 'ออกจากระบบ' }))
    expect(context.logout).toHaveBeenCalledTimes(1)
  })

  it('แตะที่ม่านมืด (ตัว dialog เอง) ปิดลิ้นชัก แต่แตะเนื้อหาข้างในไม่ปิด', () => {
    renderAs('admin')
    const drawer = getDialog('เมนูหลัก')
    fireEvent.click(screen.getByRole('button', { name: 'เปิดเมนู' }))

    fireEvent.click(within(drawer).getByText('Mangosteen Campus'))
    expect(drawer.open).toBe(true)

    fireEvent.click(drawer)
    expect(drawer.open).toBe(false)
  })
})
