import { describe, expect, it, vi } from 'vitest'

import { errorResponse, jsonResponse, mockFetch, rejection } from '../test/fetchMock'
import { ApiError } from './apiError'
import { sendRequest } from './httpCore'

// จำลองว่า fetch ล้มเหลวด้วย error ที่กำหนด (เช่น ต่อเครือข่ายไม่ได้)
function stubFetchRejecting(error: unknown) {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error))
}

describe('sendRequest', () => {
  it('คืนเนื้อหา JSON และส่ง cookie เฉพาะ origin เดียวกัน', async () => {
    const mock = mockFetch({ 'GET /api/thing/': () => jsonResponse({ ok: true }) })

    const result = await sendRequest<{ ok: boolean }>('/api/thing/')

    expect(result).toEqual({ ok: true })
    expect(mock.calls[0].headers.get('Accept')).toBe('application/json')
    expect(mock.calls[0].credentials).toBe('same-origin')
  })

  it('ส่ง body เป็น JSON พร้อม Content-Type และแนบ Bearer token', async () => {
    const mock = mockFetch({ 'POST /api/thing/': () => jsonResponse({}) })

    await sendRequest('/api/thing/', { method: 'POST', body: { a: 1 }, accessToken: 'abc' })

    const call = mock.calls[0]
    expect(call.body).toEqual({ a: 1 })
    expect(call.headers.get('Content-Type')).toBe('application/json')
    expect(call.headers.get('Authorization')).toBe('Bearer abc')
  })

  it('ไม่ใส่ Authorization ถ้าไม่มี token', async () => {
    const mock = mockFetch({ 'GET /api/thing/': () => jsonResponse({}) })

    await sendRequest('/api/thing/')

    expect(mock.calls[0].headers.has('Authorization')).toBe(false)
  })

  it('คืน undefined เมื่อ backend ตอบ 204', async () => {
    mockFetch({ 'POST /api/thing/': () => new Response(null, { status: 204 }) })

    await expect(sendRequest('/api/thing/', { method: 'POST' })).resolves.toBeUndefined()
  })

  it('โยน ApiError พร้อม code และ status จาก backend', async () => {
    mockFetch({ 'POST /api/thing/': () => errorResponse(401, 'invalid_credentials') })

    const error = await rejection(sendRequest('/api/thing/', { method: 'POST' }))

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(401)
    expect(error.code).toBe('invalid_credentials')
  })

  it('อ่านข้อผิดพลาดรายฟิลด์ของ validation_error', async () => {
    mockFetch({
      'POST /api/thing/': () =>
        jsonResponse({ code: 'validation_error', errors: { identifier: ['ต้องกรอก'] } }, 400),
    })

    const error = await rejection(sendRequest('/api/thing/', { method: 'POST' }))

    expect(error.code).toBe('validation_error')
    expect(error.errors).toEqual({ identifier: ['ต้องกรอก'] })
  })

  it('เนื้อหา error ที่ไม่ใช่ JSON ได้ code = unknown_error', async () => {
    mockFetch({
      'GET /api/thing/': () => new Response('<html>Bad gateway</html>', { status: 502 }),
    })

    const error = await rejection(sendRequest('/api/thing/'))

    expect(error.status).toBe(502)
    expect(error.code).toBe('unknown_error')
  })

  it('ติดต่อเซิร์ฟเวอร์ไม่ได้ → ApiError status 0 code = network_error', async () => {
    stubFetchRejecting(new TypeError('Failed to fetch'))

    const error = await rejection(sendRequest('/api/thing/'))

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(0)
    expect(error.code).toBe('network_error')
  })

  it('การยกเลิกคำขอโดยผู้เรียก (AbortError) ไม่ถูกแปลงเป็น network_error', async () => {
    stubFetchRejecting(new DOMException('aborted', 'AbortError'))

    const error = await rejection(sendRequest('/api/thing/'))

    expect(error).not.toBeInstanceOf(ApiError)
    expect(error.name).toBe('AbortError')
  })
})
