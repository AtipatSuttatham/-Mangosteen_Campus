import { getAccessToken, refreshSession } from '../auth/session'
import { ApiError } from './apiError'
import { sendRequest, type RequestOptions } from './httpCore'

// เรียก API ที่ต้อง login: แนบ access token ให้เอง
// ถ้า backend ตอบ 401 (token หมดอายุ) จะขอ token ใหม่แล้วลองซ้ำ "ครั้งเดียว" ผู้ใช้ไม่ต้องรู้ตัว
// - ขอ token ใหม่ไม่ได้ (เซสชันหมดจริง): โยน 401 เดิม และ AuthProvider จะพาไปหน้า login
// - ลองซ้ำแล้วยัง 401: โยน error เลย ไม่วนซ้ำ
export async function apiFetch<T>(
  path: string,
  options: Omit<RequestOptions, 'accessToken'> = {},
): Promise<T> {
  try {
    return await sendRequest<T>(path, { ...options, accessToken: getAccessToken() })
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error

    // ถ้าขอ token ใหม่พังเพราะเครือข่าย จะโยน network_error ออกไปตามนั้น (ไม่ถือว่าเซสชันหมด)
    const session = await refreshSession()
    if (!session) throw error
    return sendRequest<T>(path, { ...options, accessToken: session.access })
  }
}
