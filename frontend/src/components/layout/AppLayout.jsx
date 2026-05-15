import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Navbar from './Navbar'
import Sidebar from './Sidebar'
import { getStats } from '../../api/dashboard'

export default function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const { data: stats } = useQuery({ queryKey: ['dashboard-stats'], queryFn: getStats, refetchInterval: 30000 })

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-surface-1 text-gray-900 dark:text-gray-100">
      <Navbar onMenuToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <div className="flex flex-1 min-h-0">
        <Sidebar pendingCount={stats?.pending_requests || 0} collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
