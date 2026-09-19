import { useTranslation } from 'react-i18next'

import { useAuth } from '../auth/useAuth'
import { Icon } from '../components/Icon'
import { cx } from '../lib/cx'

type LogoutButtonProps = {
  /** onDark = ข้อความอ่อนบนพื้นม่วง, onLight = ปุ่มมีขอบบนพื้นสว่าง */
  tone: 'onDark' | 'onLight'
}

// ปุ่มออกจากระบบ (ล้างสถานะในหน้าเว็บเสมอ แม้ backend ตอบไม่สำเร็จ)
export function LogoutButton({ tone }: LogoutButtonProps) {
  const { t } = useTranslation()
  const { logout } = useAuth()

  return (
    <button
      type="button"
      onClick={() => void logout()}
      className={cx(
        'flex cursor-pointer items-center gap-2 text-[13px] font-medium focus-visible:outline-2 focus-visible:outline-offset-2',
        tone === 'onDark'
          ? 'text-plum-300 focus-visible:outline-sage-400'
          : 'h-11 justify-center rounded-md border border-plum-800 px-4 font-semibold text-plum-800 focus-visible:outline-plum-800',
      )}
    >
      <Icon name="logout" size={15} />
      {t('nav.logout')}
    </button>
  )
}
