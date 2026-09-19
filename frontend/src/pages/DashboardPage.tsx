import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { useAuth } from '../auth/useAuth'
import { Icon } from '../components/Icon'
import { LanguageToggle } from '../components/LanguageToggle'
import { cx } from '../lib/cx'
import { BellButton } from '../layout/BellButton'
import { NAV_ITEMS } from '../layout/navConfig'
import { ADMIN_SHORTCUT_KEYS, DASHBOARD } from './dashboardConfig'

// หน้า dashboard ของทั้ง 3 บทบาท (โครงเดียวกัน หัวข้อต่างกันตามบทบาท — ดู dashboardConfig.ts)
// ตอนนี้ยังไม่มี API ของรายวิชา/ผู้ใช้/งาน จึงแสดง "–" แทนตัวเลข และ "ยังไม่มีข้อมูล" ในรายการ (ไม่ใส่ตัวเลขสมมติ)
export default function DashboardPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  // อยู่ใต้ RequireAuth เสมอจึงมีผู้ใช้ — เช็กไว้เพื่อให้ชนิดข้อมูลถูกต้อง
  if (!user) return null

  const config = DASHBOARD[user.role]
  const shortcuts = NAV_ITEMS.admin.filter((item) => ADMIN_SHORTCUT_KEYS.includes(item.key))

  return (
    <>
      {/* หัวหน้า: คำทักทาย + (จอกว้าง) กระดิ่งและปุ่มสลับภาษา — บนมือถือสองอย่างนี้อยู่ที่แถบบน/ลิ้นชักแล้ว */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-serif text-[28px] leading-snug font-semibold">
            {t('dashboard.greeting', { name: user.first_name })}
          </h1>
          <p className="mt-0.5 text-sm text-ink-2">{t(config.subtitleKey)}</p>
        </div>
        <div className="hidden items-center gap-[18px] lg:flex">
          <BellButton tone="onLight" />
          <LanguageToggle />
        </div>
      </div>

      {/* ตัวเลขสำคัญ 3 ตัว คั่นด้วยเส้นตั้ง (โครงสร้าง dt/dd เพื่อให้ผู้ใช้โปรแกรมอ่านหน้าจอได้ยินป้ายก่อนค่า) */}
      <dl className="mt-6 flex items-stretch">
        {config.figures.map((figure, index) => (
          <div
            key={figure.labelKey}
            className={cx(
              'flex min-w-0 flex-1 flex-col-reverse justify-end lg:flex-none',
              index > 0 && 'ml-4 border-l border-line pl-4 lg:ml-10 lg:pl-10',
            )}
          >
            <dt className="mt-[7px] text-[13px] leading-snug text-ink-2">{t(figure.labelKey)}</dt>
            <dd
              className={cx(
                'font-serif text-4xl leading-none font-semibold lg:text-[38px]',
                figure.highlight ? 'text-plum-800' : 'text-ink',
              )}
            >
              <span aria-hidden="true">–</span>
              <span className="sr-only">{t('dashboard.noData')}</span>
            </dd>
          </div>
        ))}
      </dl>

      <div className="mt-6 border-b border-line" />

      <div className="mt-2 flex flex-col gap-2 lg:flex-row lg:gap-12">
        <section aria-labelledby="dashboard-primary" className="pt-6 lg:flex-[1.6]">
          <h2 id="dashboard-primary" className="mb-3.5 font-serif text-[17px] font-semibold">
            {t(config.primaryTitleKey)}
          </h2>
          <p className="border-y border-line py-6 text-sm text-ink-2">{t('dashboard.empty')}</p>
        </section>

        <section aria-labelledby="dashboard-secondary" className="pt-6 lg:flex-1 lg:pl-1">
          <h2 id="dashboard-secondary" className="mb-3.5 font-serif text-[17px] font-semibold">
            {t(config.secondary.titleKey)}
          </h2>

          {config.secondary.kind === 'shortcuts' ? (
            <ul className="border-b border-line">
              {shortcuts.map((item) => (
                <li key={item.key} className="border-t border-line">
                  {item.to ? (
                    <Link to={item.to} className="flex items-center gap-3 py-3 text-sm font-medium">
                      <Icon name={item.icon} size={17} className="text-plum-800" />
                      {t(item.labelKey)}
                    </Link>
                  ) : (
                    // ฟีเจอร์ยังไม่เปิดใช้งาน: แสดงตามแบบแต่กดไม่ได้
                    <span
                      role="link"
                      aria-disabled="true"
                      title={t('common.comingSoon')}
                      className="flex cursor-not-allowed items-center gap-3 py-3 text-sm font-medium text-ink-3"
                    >
                      <Icon name={item.icon} size={17} className="text-plum-800/50" />
                      {t(item.labelKey)}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="border-y border-line py-6 text-sm text-ink-2">{t('dashboard.empty')}</p>
          )}
        </section>
      </div>
    </>
  )
}
