// รูปแบบ error ที่ backend ส่งกลับ (สัญญาที่ docs/api-auth.md)
type ErrorBody = { code?: unknown; detail?: unknown; errors?: unknown }

// ข้อผิดพลาดรายฟิลด์ เช่น { identifier: ["..."] } (มาพร้อม code = validation_error)
export type FieldErrors = Record<string, string[]>

function isFieldErrors(value: unknown): value is FieldErrors {
  return (
    typeof value === 'object' &&
    value !== null &&
    Object.values(value).every(
      (messages) => Array.isArray(messages) && messages.every((m) => typeof m === 'string'),
    )
  )
}

// error จากการเรียก API — ใช้ `code` เป็นกุญแจแปลข้อความ (ไม่แสดง message จาก backend ตรง ๆ)
export class ApiError extends Error {
  /** สถานะ HTTP (0 = ติดต่อเซิร์ฟเวอร์ไม่ได้) */
  status: number
  /** รหัส error เช่น invalid_credentials, network_error, unknown_error */
  code: string
  /** ข้อผิดพลาดรายฟิลด์ (เฉพาะ validation_error) */
  errors?: FieldErrors

  constructor(
    status: number,
    code: string,
    message?: string,
    errors?: FieldErrors,
    options?: ErrorOptions,
  ) {
    super(message ?? code, options)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.errors = errors
  }

  // สร้างจาก response ที่ไม่สำเร็จ (อ่านเนื้อหา JSON ถ้ามี ถ้าไม่ใช่ JSON ให้ code = unknown_error)
  static async fromResponse(response: Response): Promise<ApiError> {
    let body: ErrorBody = {}
    try {
      body = (await response.json()) as ErrorBody
    } catch {
      // เนื้อหาไม่ใช่ JSON (เช่น หน้า error ของ proxy) — ใช้ค่าเริ่มต้นด้านล่าง
    }
    const code = typeof body.code === 'string' ? body.code : 'unknown_error'
    const detail = typeof body.detail === 'string' ? body.detail : undefined
    const errors = isFieldErrors(body.errors) ? body.errors : undefined
    return new ApiError(response.status, code, detail, errors)
  }
}
