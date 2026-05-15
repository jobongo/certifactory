import { NavLink } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import {
  DashboardIcon, CertificateAuthorityIcon, CertificateIcon,
  ClockIcon, AuditIcon, UsersIcon,
} from '../../utils/icons'

const navItems = [
  { section: 'Main', items: [
    { to: '/', icon: DashboardIcon, label: 'Dashboard' },
    { to: '/cas', icon: CertificateAuthorityIcon, label: 'Authorities' },
    { to: '/certificates', icon: CertificateIcon, label: 'Certificates' },
    { to: '/pending', icon: ClockIcon, label: 'Pending Requests', roles: ['admin', 'operator'], badge: true },
  ]},
  { section: 'Management', items: [
    { to: '/audit', icon: AuditIcon, label: 'Audit Log', roles: ['admin', 'operator', 'auditor'] },
    { to: '/users', icon: UsersIcon, label: 'Users', roles: ['admin'] },
  ]},
]

export default function Sidebar({ pendingCount = 0, collapsed, onToggle }) {
  const { user } = useAuth()

  return (
    <aside className={`${collapsed ? 'hidden' : 'flex'} md:flex flex-col w-56 bg-white dark:bg-surface-2 border-r border-gray-200 dark:border-gray-800 min-h-0 overflow-y-auto`}>
      {navItems.map((group) => (
        <div key={group.section} className="px-3 py-3">
          <div className="text-[10px] uppercase tracking-wider text-gray-400 dark:text-gray-600 px-3 mb-1">
            {group.section}
          </div>
          {group.items
            .filter((item) => !item.roles || item.roles.includes(user?.role))
            .map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors ${
                    isActive
                      ? 'bg-gray-100 dark:bg-surface-4 text-gray-900 dark:text-gray-100 border-l-2 border-gray-900 dark:border-gray-100 -ml-px'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-surface-3'
                  }`
                }
              >
                <item.icon className="w-4 h-4" />
                <span className="flex-1">{item.label}</span>
                {item.badge && pendingCount > 0 && (
                  <span className="bg-amber-500 text-white text-[10px] px-1.5 py-0.5 rounded-full">
                    {pendingCount}
                  </span>
                )}
              </NavLink>
            ))}
        </div>
      ))}
    </aside>
  )
}
