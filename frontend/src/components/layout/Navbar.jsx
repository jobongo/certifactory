import { useAuth } from '../../hooks/useAuth'
import { useTheme } from '../../hooks/useTheme'
import { useNavigate } from 'react-router-dom'
import Dropdown, { DropdownItem } from '../ui/Dropdown'
import { SunIcon, MoonIcon, BellIcon, MenuIcon, ChevronDownIcon } from '../../utils/icons'

export default function Navbar({ onMenuToggle }) {
  const { user, logout } = useAuth()
  const { isDark, toggle } = useTheme()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="h-14 flex items-center justify-between px-4 bg-white dark:bg-surface-2 border-b border-gray-200 dark:border-gray-800">
      <div className="flex items-center gap-3">
        <button onClick={onMenuToggle} className="md:hidden text-gray-500 dark:text-gray-400">
          <MenuIcon />
        </button>
        <span className="text-base font-semibold text-gray-900 dark:text-gray-100 tracking-tight">
          PKI Manager
        </span>
      </div>

      <div className="flex items-center gap-3">
        <button onClick={toggle} className="p-2 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-surface-4">
          {isDark ? <SunIcon className="w-4 h-4" /> : <MoonIcon className="w-4 h-4" />}
        </button>

        <button className="p-2 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-surface-4">
          <BellIcon className="w-4 h-4" />
        </button>

        <Dropdown
          trigger={
            <button className="flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-surface-4">
              <div className="w-7 h-7 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs font-medium text-gray-600 dark:text-gray-300">
                {user?.username?.slice(0, 2).toUpperCase()}
              </div>
              <div className="hidden sm:block text-left">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{user?.username}</div>
                <div className="text-[10px] text-gray-500 dark:text-gray-500">{user?.role}</div>
              </div>
              <ChevronDownIcon className="w-3 h-3 text-gray-400" />
            </button>
          }
        >
          <DropdownItem onClick={handleLogout}>Logout</DropdownItem>
        </Dropdown>
      </div>
    </header>
  )
}
