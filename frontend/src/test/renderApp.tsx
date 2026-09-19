import { render } from '@testing-library/react'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

import { AuthProvider } from '../auth/AuthProvider'
import { appRoutes } from '../router'

// render แอปจริง (AuthProvider + เส้นทางทั้งหมด) เริ่มที่ path ที่กำหนด
// คืน router เพื่อให้ test ตรวจ path ปัจจุบันได้ (router.state.location.pathname)
export function renderApp(path = '/') {
  const router = createMemoryRouter(appRoutes, { initialEntries: [path] })
  render(
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>,
  )
  return router
}
