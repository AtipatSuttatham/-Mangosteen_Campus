import { useTranslation } from 'react-i18next'

import { cx } from '../lib/cx'
import type { User } from '../types/auth'

type UserBadgeProps = {
  user: User
  /** onDark = วางบนพื้นม่วง (sidebar/ลิ้นชัก), onLight = วางบนพื้นสว่าง (ลิ้นชักโปรไฟล์) */
  tone: 'onDark' | 'onLight'
}

// วงกลมตัวอักษรแรกของชื่อ + ชื่อเต็ม + บทบาท
export function UserBadge({ user, tone }: UserBadgeProps) {
  const { t } = useTranslation()
  const dark = tone === 'onDark'

  return (
    <div className="flex items-center gap-2.5">
      <div
        aria-hidden="true"
        className={cx(
          'flex size-9 shrink-0 items-center justify-center rounded-full font-serif text-sm font-semibold',
          dark ? 'bg-white/12 text-plum-50' : 'bg-plum-800/10 text-plum-800',
        )}
      >
        {Array.from(user.first_name)[0] ?? '?'}
      </div>
      <div className="min-w-0">
        <div className={cx('truncate text-[13px] font-semibold', dark ? 'text-plum-50' : 'text-ink')}>
          {user.first_name} {user.last_name}
        </div>
        <div className={cx('text-xs', dark ? 'text-plum-300' : 'text-ink-2')}>{t(`roles.${user.role}`)}</div>
      </div>
    </div>
  )
}
