import { render } from '@testing-library/react'
import { vi } from 'vitest'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

import { AuthContext, type AuthContextValue } from '../auth/authContext'
import { appRoutes } from '../router'

// render เส้นทางจริงด้วยสถานะล็อกอินที่กำหนดเอง (ไม่ต้องยิง API)
// คืน router (ตรวจ path ปัจจุบัน) และ context (ตรวจว่ามีการเรียก login/logout)
export function renderWithAuth(path: string, value: Partial<AuthContextValue>) {
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
  return { router, context }
}
