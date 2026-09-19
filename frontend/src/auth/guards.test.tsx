import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { makeUser } from '../test/fetchMock'
import { renderWithAuth } from '../test/renderWithAuth'

const loggedOut = { status: 'unauthenticated' as const, user: null }
const teacher = { status: 'authenticated' as const, user: makeUser({ role: 'teacher' }) }
const admin = { status: 'authenticated' as const, user: makeUser({ role: 'admin' }) }

describe('ตัวกันหน้า', () => {
  it('ระหว่างกู้เซสชัน (loading) แสดงข้อความกำลังโหลด ยังไม่เด้งไปไหน', () => {
    const { router } = renderWithAuth('/teacher', { status: 'loading', user: null })

    expect(screen.getByRole('status')).toHaveTextContent('กำลังโหลด')
    expect(router.state.location.pathname).toBe('/teacher')
  })

  it('ยังไม่ล็อกอินแล้วเข้าหน้าที่ต้องล็อกอิน → ไปหน้า login', () => {
    const { router } = renderWithAuth('/teacher', loggedOut)

    expect(router.state.location.pathname).toBe('/login')
    expect(screen.getByRole('heading', { name: 'เข้าสู่ระบบ' })).toBeInTheDocument()
  })

  it('จำหน้าที่ตั้งใจจะเข้าไว้ เพื่อพากลับหลังล็อกอิน', () => {
    const { router } = renderWithAuth('/teacher?tab=1', loggedOut)

    expect(router.state.location.state).toMatchObject({
      from: { pathname: '/teacher', search: '?tab=1' },
    })
  })

  it('ผิดบทบาท → พาไปหน้าแรกของบทบาทตัวเอง (เห็น dashboard ของผู้สอน)', () => {
    const { router } = renderWithAuth('/admin', teacher)

    expect(router.state.location.pathname).toBe('/teacher')
    expect(screen.getByText('ชิ้นงานรอตรวจ')).toBeInTheDocument()
    expect(screen.queryByText('ผู้สอนในระบบ')).not.toBeInTheDocument()
  })

  it('บทบาทตรงกับหน้า → เข้าได้ (เห็น dashboard ของผู้ดูแลระบบ)', () => {
    const { router } = renderWithAuth('/admin', admin)

    expect(router.state.location.pathname).toBe('/admin')
    expect(screen.getByText('ผู้สอนในระบบ')).toBeInTheDocument()
  })

  it('ล็อกอินแล้วเข้าหน้า login → พาไปหน้าแรกของบทบาท', () => {
    const { router } = renderWithAuth('/login', teacher)

    expect(router.state.location.pathname).toBe('/teacher')
  })

  it('เข้า "/" → พาไปหน้าแรกของบทบาท', () => {
    const { router } = renderWithAuth('/', admin)

    expect(router.state.location.pathname).toBe('/admin')
  })

  it('เส้นทางที่ไม่มีอยู่ → กลับหน้าแรก และถ้ายังไม่ล็อกอินก็ต่อไปหน้า login', () => {
    const { router } = renderWithAuth('/nope/nothing', loggedOut)

    expect(router.state.location.pathname).toBe('/login')
  })

  it('ยังไม่ล็อกอินเข้าหน้า login ได้ตามปกติ', () => {
    const { router } = renderWithAuth('/login', loggedOut)

    expect(router.state.location.pathname).toBe('/login')
  })
})
