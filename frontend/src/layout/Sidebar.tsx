import { useTranslation } from 'react-i18next'

import { LogoMark } from '../components/LogoMark'
import type { User } from '../types/auth'
import { LogoutButton } from './LogoutButton'
import { NavList } from './NavList'
import { UserBadge } from './UserBadge'

// แถบเมนูซ้ายของจอกว้าง (>= 1024px) — พื้นม่วง กว้าง 264px ติดขอบจอไม่เลื่อนตามเนื้อหา
export function Sidebar({ user }: { user: User }) {
  const { t } = useTranslation()

  return (
    <aside className="sticky top-0 hidden h-screen w-[264px] shrink-0 flex-col bg-plum-800 px-[22px] py-7 lg:flex">
      <div className="mb-9 flex items-center gap-[11px] px-0.5">
        <LogoMark size={26} className="text-sage-400" />
        <span className="font-serif text-base font-semibold text-plum-50">{t('app.name')}</span>
      </div>

      <nav aria-label={t('nav.main')} className="flex-1">
        <NavList role={user.role} />
      </nav>

      <div className="flex flex-col gap-3 border-t border-white/15 pt-[18px]">
        <UserBadge user={user} tone="onDark" />
        <LogoutButton tone="onDark" />
      </div>
    </aside>
  )
}
