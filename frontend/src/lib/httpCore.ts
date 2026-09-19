import { ApiError } from './apiError'

export type RequestOptions = {
  method?: string
  /** เนื้อหาคำขอ (จะส่งเป็น JSON) */
  body?: unknown
  headers?: Record<string, string>
  /** access token ที่จะแนบเป็น Authorization: Bearer */
  accessToken?: string | null
  signal?: AbortSignal
}

// ยิงคำขอไป backend หนึ่งครั้ง (ไม่มีการขอ token ใหม่/ลองซ้ำ — ชั้นนั้นอยู่ที่ apiClient.ts)
// สำเร็จ: คืนเนื้อหา JSON (หรือ undefined ถ้า 204) | ไม่สำเร็จ: โยน ApiError
export async function sendRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (options.body !== undefined) headers.set('Content-Type', 'application/json')
  if (options.accessToken) headers.set('Authorization', `Bearer ${options.accessToken}`)

  let response: Response
  try {
    response = await fetch(path, {
      method: options.method ?? 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      // ส่ง cookie (refresh token) ไปกับคำขอที่เป็น origin เดียวกันเท่านั้น
      credentials: 'same-origin',
      signal: options.signal,
    })
  } catch (cause) {
    // ผู้เรียกสั่งยกเลิกเอง ไม่ใช่ปัญหาเครือข่าย — ส่งต่อตามเดิม
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new ApiError(0, 'network_error', undefined, undefined, { cause })
  }

  if (!response.ok) throw await ApiError.fromResponse(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
