import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router'

import { Icon } from '../components/Icon'
import { cx } from '../lib/cx'
import type { Role } from '../types/auth'
import { NAV_ITEMS } from './navConfig'

type NavListProps = {
  role: Role
  /** sidebar = แถบซ้ายบนจอกว้าง, drawer = ลิ้นชักบนมือถือ (ตัวใหญ่กว่า กดง่ายกว่า) */
  size?: 'sidebar' | 'drawer'
  /** เรียกเมื่อกดเมนูที่ใช้งานได้ (เช่น ปิดลิ้นชัก) */
  onNavigate?: () => void
}

// รายการเมนูบนพื้นม่วง: เมนูที่เปิดใช้แล้วเป็นลิงก์ (ตัวที่เลือกอยู่มีแถบเขียวด้านซ้าย)
// เมนูที่ฟีเจอร์ยังไม่มีแสดงจางและกดไม่ได้ เพื่อไม่ให้กดแล้วหลงทาง
export function NavList({ role, size = 'sidebar', onNavigate }: NavListProps) {
  const { t } = useTranslation()

  const base = cx(
    'flex items-center gap-3 border-l-[3px] px-3.5',
    size === 'drawer' ? 'h-12 text-[15px]' : 'h-10 text-sm',
  )

  return (
    <ul className="flex flex-col gap-0.5">
      {NAV_ITEMS[role].map((item) => (
        <li key={item.key}>
          {item.to ? (
            <NavLink
              to={item.to}
              end
              onClick={onNavigate}
              className={({ isActive }) =>
                cx(
                  base,
                  'focus-visible:outline-2 focus-visible:outline-sage-400',
                  isActive
                    ? 'border-sage-400 font-semibold text-plum-50'
                    : 'border-transparent font-medium text-plum-300',
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon name={item.icon} className={isActive ? 'text-sage-400' : undefined} />
                  {t(item.labelKey)}
                </>
              )}
            </NavLink>
          ) : (
            <span
              role="link"
              aria-disabled="true"
              title={t('common.comingSoon')}
              className={cx(base, 'cursor-not-allowed border-transparent font-medium text-plum-300/60')}
            >
              <Icon name={item.icon} />
              {t(item.labelKey)}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}
