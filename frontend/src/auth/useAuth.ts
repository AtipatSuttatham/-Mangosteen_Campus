import { useContext } from 'react'

import { AuthContext, type AuthContextValue } from './authContext'

// ใช้อ่านสถานะล็อกอินและสั่ง login / logout จาก component ใดก็ได้ที่อยู่ใต้ AuthProvider
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth ต้องใช้ภายใต้ AuthProvider')
  return context
}
