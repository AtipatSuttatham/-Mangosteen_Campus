import { vi } from 'vitest'

import type { ApiError } from '../lib/apiError'
import type { User } from '../types/auth'

// คำขอที่ถูกจำลองรับไว้ (ให้ test ตรวจว่าเรียกอะไร ส่ง header อะไร)
export type MockCall = {
  url: string
  method: string
  headers: Headers
  body: unknown
  credentials: RequestCredentials | undefined
}

export type MockHandler = (call: MockCall) => Response | Promise<Response>

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

// response ที่ backend ตอบเมื่อ error (รูปแบบเดียวกับ backend จริง: { code, detail })
export function errorResponse(status: number, code: string): Response {
  return jsonResponse({ code, detail: code }, status)
}

// ผู้ใช้ตัวอย่างสำหรับ test (ระบุเฉพาะส่วนที่ต่าง)
export function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    email: 'teacher@example.com',
    student_or_staff_id: 'T0042',
    role: 'teacher',
    first_name: 'สมชาย',
    last_name: 'ใจดี',
    first_name_en: '',
    last_name_en: '',
    is_email_verified: true,
    avatar_url: '',
    ...overrides,
  }
}

// จำลอง fetch ทั้งระบบ: handlers ใช้คีย์รูปแบบ "METHOD /path" เช่น "POST /api/auth/login/"
// เรียกเส้นทางที่ไม่ได้จำลองไว้จะได้ 404 พร้อม code = unmocked_route (ให้เห็นชัดใน test)
export function mockFetch(handlers: Record<string, MockHandler>) {
  const calls: MockCall[] = []

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString()
    const method = (init?.method ?? 'GET').toUpperCase()
    const call: MockCall = {
      url,
      method,
      headers: new Headers(init?.headers),
      body: typeof init?.body === 'string' ? JSON.parse(init.body) : undefined,
      credentials: init?.credentials,
    }
    calls.push(call)

    const handler = handlers[`${method} ${url}`]
    return handler ? handler(call) : errorResponse(404, 'unmocked_route')
  })

  vi.stubGlobal('fetch', fetchMock)

  return {
    calls,
    // จำนวนครั้งที่เรียกเส้นทางนั้น เช่น countOf('POST /api/auth/refresh/')
    countOf: (key: string) => calls.filter((c) => `${c.method} ${c.url}` === key).length,
  }
}

// รอผลของ promise ที่คาดว่าจะล้มเหลว แล้วคืน error (ชนิด ApiError เพื่อให้อ่าน code/status ได้โดยไม่ต้อง cast)
export async function rejection(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise
  } catch (error) {
    return error as ApiError
  }
  throw new Error('คาดว่าจะเกิด error แต่คำขอสำเร็จ')
}

// ตัวหน่วงให้ test ควบคุมจังหวะที่คำขอตอบกลับได้ (ใช้ทดสอบคำขอที่ชนกัน)
export function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((r) => {
    resolve = r
  })
  return { promise, resolve }
}
