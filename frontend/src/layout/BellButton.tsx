import { useTranslation } from 'react-i18next'

import { Icon } from '../components/Icon'
import { cx } from '../lib/cx'

type BellButtonProps = {
  /** onDark = ไอคอนอ่อนบนแถบม่วงมือถือ, onLight = ปุ่มวงกลมขอบบางบนพื้นหน้า (จอกว้าง) */
  tone: 'onDark' | 'onLight'
}

// ปุ่มกระดิ่งแจ้งเตือน — ตอนนี้ยังไม่มีระบบแจ้งเตือน จึงแสดงตามแบบแต่กดไม่ได้ และไม่มีจุดบอกจำนวน
export function BellButton({ tone }: BellButtonProps) {
  const { t } = useTranslation()

  return (
    <button
      type="button"
      disabled
      aria-label={t('nav.notifications')}
      title={t('common.comingSoon')}
      className={cx(
        'flex shrink-0 cursor-not-allowed items-center justify-center rounded-full opacity-70',
        tone === 'onDark'
          ? 'size-11 text-plum-50'
          : 'size-10 border border-line bg-white text-plum-800',
      )}
    >
      <Icon name="bell" size={tone === 'onDark' ? 22 : 19} />
    </button>
  )
}
