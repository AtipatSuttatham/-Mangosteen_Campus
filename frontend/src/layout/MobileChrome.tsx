import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router'

import { Icon } from '../components/Icon'
import { LanguageToggle } from '../components/LanguageToggle'
import { LogoMark } from '../components/LogoMark'
import { cx } from '../lib/cx'
import type { User } from '../types/auth'
import { BellButton } from './BellButton'
import { LogoutButton } from './LogoutButton'
import { NavList } from './NavList'
import { NAV_ITEMS, usesDrawer } from './navConfig'
import { Sheet } from './Sheet'
import { UserBadge } from './UserBadge'

// แถบบนของมือถือ (< 1024px): โลโก้ + กระดิ่ง
// - บทบาทที่มีเมนูมาก (ผู้ดูแลระบบ): ปุ่มเมนูซ้ายเปิดลิ้นชักที่มีเมนู/ภาษา/ออกจากระบบ
// - บทบาทอื่น: ปุ่มวงกลมชื่อขวาเปิดแผ่นโปรไฟล์ที่มีภาษา/ออกจากระบบ (เมนูอยู่แถบล่าง)
export function MobileTopBar({ user }: { user: User }) {
  const { t } = useTranslation()
  const [sheetOpen, setSheetOpen] = useState(false)
  const drawer = usesDrawer(user.role)
  const closeSheet = () => setSheetOpen(false)

  return (
    <>
      <header className="flex h-14 shrink-0 items-center justify-between bg-plum-800 px-2 lg:hidden">
        <div className="flex items-center">
          {drawer && (
            <button
              type="button"
              aria-label={t('nav.openMenu')}
              onClick={() => setSheetOpen(true)}
              className="flex size-11 cursor-pointer items-center justify-center text-plum-50 focus-visible:outline-2 focus-visible:outline-sage-400"
            >
              <Icon name="menu" size={24} />
            </button>
          )}
          <div className={cx('flex items-center gap-2.5', !drawer && 'pl-2')}>
            <LogoMark size={22} className="text-sage-400" />
            <span className="font-serif text-[15px] font-semibold text-plum-50">{t('app.name')}</span>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <BellButton tone="onDark" />
          {!drawer && (
            <button
              type="button"
              aria-label={t('nav.profile')}
              onClick={() => setSheetOpen(true)}
              className="mr-1 flex size-[34px] cursor-pointer items-center justify-center rounded-full bg-white/15 font-serif text-sm font-semibold text-plum-50 focus-visible:outline-2 focus-visible:outline-sage-400"
            >
              {Array.from(user.first_name)[0] ?? '?'}
            </button>
          )}
        </div>
      </header>

      {drawer ? (
        <Sheet open={sheetOpen} onClose={closeSheet} label={t('nav.main')} side="left">
          <div className="flex min-h-full flex-col px-4 py-[18px]">
            <div className="mb-5 flex items-center justify-between pl-1.5">
              <div className="flex items-center gap-2.5">
                <LogoMark size={24} className="text-sage-400" />
                <span className="font-serif text-[15px] font-semibold text-plum-50">{t('app.name')}</span>
              </div>
              <button
                type="button"
                aria-label={t('nav.closeMenu')}
                onClick={closeSheet}
                className="flex size-11 cursor-pointer items-center justify-center text-plum-50 focus-visible:outline-2 focus-visible:outline-sage-400"
              >
                <Icon name="close" size={22} />
              </button>
            </div>

            <nav aria-label={t('nav.main')} className="flex-1">
              <NavList role={user.role} size="drawer" onNavigate={closeSheet} />
            </nav>

            <div className="flex flex-col gap-3.5 border-t border-white/15 pt-4">
              <UserBadge user={user} tone="onDark" />
              <LanguageToggle onDark />
              <LogoutButton tone="onDark" />
            </div>
          </div>
        </Sheet>
      ) : (
        <Sheet open={sheetOpen} onClose={closeSheet} label={t('nav.profile')} side="bottom">
          <div className="flex flex-col gap-5 px-5 pt-5 pb-6">
            <div className="flex items-center justify-between">
              <UserBadge user={user} tone="onLight" />
              <button
                type="button"
                aria-label={t('nav.closeMenu')}
                onClick={closeSheet}
                className="flex size-11 cursor-pointer items-center justify-center text-ink-2 focus-visible:outline-2 focus-visible:outline-plum-800"
              >
                <Icon name="close" size={22} />
              </button>
            </div>
            <LanguageToggle />
            <LogoutButton tone="onLight" />
          </div>
        </Sheet>
      )}
    </>
  )
}

// แถบเมนูล่างของมือถือ (< 1024px) สำหรับบทบาทที่มีเมนูไม่เกิน 3 รายการ (ผู้เรียน/ผู้สอน)
export function BottomNav({ user }: { user: User }) {
  const { t } = useTranslation()
  if (usesDrawer(user.role)) return null

  const base = 'flex flex-1 flex-col items-center justify-center gap-[3px] text-xs'

  return (
    <nav
      aria-label={t('nav.main')}
      className="fixed inset-x-0 bottom-0 z-30 flex h-16 bg-plum-800 lg:hidden"
    >
      {NAV_ITEMS[user.role].map((item) =>
        item.to ? (
          <NavLink
            key={item.key}
            to={item.to}
            end
            className={({ isActive }) =>
              cx(base, 'focus-visible:outline-2 focus-visible:outline-sage-400', isActive ? 'font-semibold text-sage-400' : 'font-medium text-plum-300')
            }
          >
            <Icon name={item.icon} size={22} />
            {t(item.labelKey)}
          </NavLink>
        ) : (
          <span
            key={item.key}
            role="link"
            aria-disabled="true"
            title={t('common.comingSoon')}
            className={cx(base, 'cursor-not-allowed font-medium text-plum-300/60')}
          >
            <Icon name={item.icon} size={22} />
            {t(item.labelKey)}
          </span>
        ),
      )}
    </nav>
  )
}
