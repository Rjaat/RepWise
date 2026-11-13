import type { ReactNode } from 'react'
import { classNames } from './classNames'

export interface AppShellNavigationItem {
  href: string
  label: string
  isCurrent?: boolean
}
export interface AppShellProps {
  children: ReactNode
  navigation: AppShellNavigationItem[]
  wordmark?: string
}

function NavigationLink({
  item,
  mobile = false,
}: {
  item: AppShellNavigationItem
  mobile?: boolean
}) {
  const base = mobile ? 'rw-bottom-nav__link' : 'rw-nav-link'
  return (
    <a
      aria-current={item.isCurrent ? 'page' : undefined}
      className={classNames(base, item.isCurrent && `${base}--current`)}
      href={item.href}
    >
      {item.label}
    </a>
  )
}

export function AppShell({
  children,
  navigation,
  wordmark = 'RepWise',
}: AppShellProps) {
  return (
    <div className="rw-app-shell">
      <a className="rw-skip-link" href="#main-content">
        Skip to main content
      </a>
      <aside aria-label="Primary" className="rw-sidebar">
        <a aria-label="RepWise home" className="rw-wordmark" href="/">
          {wordmark}
        </a>
        <nav aria-label="Primary navigation">
          <ul className="rw-nav-list">
            {navigation.map((item) => (
              <li key={item.href}>
                <NavigationLink item={item} />
              </li>
            ))}
          </ul>
        </nav>
      </aside>
      <main className="rw-main" id="main-content" tabIndex={-1}>
        {children}
      </main>
      <nav aria-label="Mobile primary navigation" className="rw-bottom-nav">
        {navigation.slice(0, 4).map((item) => (
          <NavigationLink item={item} key={item.href} mobile />
        ))}
      </nav>
    </div>
  )
}
