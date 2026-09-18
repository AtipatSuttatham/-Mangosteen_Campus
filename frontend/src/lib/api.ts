// ผลตอบกลับของ GET /api/health/
export type HealthResponse = { status: string }

// ตรวจว่า backend ทำงานอยู่ — เรียกผ่าน path /api (Vite proxy ตอน dev / hosting proxy ตอน deploy)
export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/health/')
  if (!response.ok) {
    throw new Error(`ตรวจสถานะ backend ไม่สำเร็จ (HTTP ${response.status})`)
  }
  return (await response.json()) as HealthResponse
}
