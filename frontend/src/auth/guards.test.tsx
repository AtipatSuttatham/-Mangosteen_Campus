import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

import { appRoutes } from '../router'
import { makeUser } from '../test/fetchMock'
import { AuthContext, type AuthContextValue } from './authContext'

// render เส้นทางจริงด้วยสถานะล็อกอินที่กำหนดเอง (ไม่ต้องยิง API)
function renderWithAuth(path: string, value: Partial<AuthContextValue>) {
  const context: AuthContextValue = {
    status: 'authenticated',
    user: null,
    login: vi.fn(),
    logout: vi.fn(),
    ...value,
  }
  const router = createMemoryRouter(appRoutes, { initialEntries: [path] })
  render(
    <AuthContext.Provider value={context}>
      <RouterProvider router={router} />
    </AuthContext.Provider>,
  )
  return router
}

const loggedOut = { status: 'unauthenticated' as const, user: null }
const teacher = { status: 'authenticated' as const, user: makeUser({ role: 'teacher' }) }
const admin = { status: 'authenticated' as const, user: makeUser({ role: 'admin' }) }

describe('ตัวกันหน้า', () => {
  it('ระหว่างกู้เซสชัน (loading) แสดงข้อความกำลังโหลด ยังไม่เด้งไปไหน', () => {
    const router = renderWithAuth('/teacher', { status: 'loading', user: null })

    expect(screen.getByRole('status')).toHaveTextContent('กำลังโหลด')
    expect(router.state.location.pathname).toBe('/teacher')
  })

  it('ยังไม่ล็อกอินแล้วเข้าหน้าที่ต้องล็อกอิน → ไปหน้า login', () => {
    const router = renderWithAuth('/teacher', loggedOut)

    expect(router.state.location.pathname).toBe('/login')
    expect(screen.getByRole('heading', { name: 'เข้าสู่ระบบ' })).toBeInTheDocument()
  })

  it('จำหน้าที่ตั้งใจจะเข้าไว้ เพื่อพากลับหลังล็อกอิน', () => {
    const router = renderWithAuth('/teacher?tab=1', loggedOut)

    expect(router.state.location.state).toMatchObject({
      from: { pathname: '/teacher', search: '?tab=1' },
    })
  })

  it('ผิดบทบาท → พาไปหน้าแรกของบทบาทตัวเอง', () => {
    const router = renderWithAuth('/admin', teacher)

    expect(router.state.location.pathname).toBe('/teacher')
    expect(screen.getByText('ผู้สอน')).toBeInTheDocument()
  })

  it('บทบาทตรงกับหน้า → เข้าได้', () => {
    const router = renderWithAuth('/admin', admin)

    expect(router.state.location.pathname).toBe('/admin')
    expect(screen.getByText('ผู้ดูแลระบบ')).toBeInTheDocument()
  })

  it('ล็อกอินแล้วเข้าหน้า login → พาไปหน้าแรกของบทบาท', () => {
    const router = renderWithAuth('/login', teacher)

    expect(router.state.location.pathname).toBe('/teacher')
  })

  it('เข้า "/" → พาไปหน้าแรกของบทบาท', () => {
    const router = renderWithAuth('/', admin)

    expect(router.state.location.pathname).toBe('/admin')
  })

  it('เส้นทางที่ไม่มีอยู่ → กลับหน้าแรก และถ้ายังไม่ล็อกอินก็ต่อไปหน้า login', () => {
    const router = renderWithAuth('/nope/nothing', loggedOut)

    expect(router.state.location.pathname).toBe('/login')
  })

  it('ยังไม่ล็อกอินเข้าหน้า login ได้ตามปกติ', () => {
    const router = renderWithAuth('/login', loggedOut)

    expect(router.state.location.pathname).toBe('/login')
  })
})
