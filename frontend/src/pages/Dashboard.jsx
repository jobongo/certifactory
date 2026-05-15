import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getStats, getExpiring } from '../api/dashboard'
import { getAuditLogs } from '../api/audit'
import Card, { CardBody } from '../components/ui/Card'
import StatusBadge from '../components/shared/StatusBadge'

function StatCard({ label, value, color, to }) {
  const navigate = useNavigate()
  return (
    <Card onClick={() => to && navigate(to)} className="p-4">
      <div className={`text-2xl font-bold ${color || 'text-gray-900 dark:text-gray-100'}`}>{value}</div>
      <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">{label}</div>
    </Card>
  )
}

export default function Dashboard() {
  const { data: stats } = useQuery({ queryKey: ['dashboard-stats'], queryFn: getStats })
  const { data: expiring } = useQuery({ queryKey: ['dashboard-expiring'], queryFn: () => getExpiring() })
  const { data: activity } = useQuery({ queryKey: ['dashboard-activity'], queryFn: () => getAuditLogs({ per_page: 5 }) })

  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-1">Dashboard</h1>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">Overview of your PKI infrastructure</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Active CAs" value={stats?.active_cas ?? '—'} to="/cas" />
        <StatCard label="Active Certs" value={stats?.active_certs ?? '—'} color="text-emerald-500" to="/certificates" />
        <StatCard label="Pending Requests" value={stats?.pending_requests ?? '—'} color="text-amber-500" to="/pending" />
        <StatCard label="Expiring Soon" value={stats?.expiring_soon ?? '—'} color="text-red-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardBody>
            <h2 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">Expiring Certificates</h2>
            {expiring?.items?.length === 0 && <p className="text-sm text-gray-400">None expiring soon</p>}
            <div className="space-y-2">
              {expiring?.items?.slice(0, 5).map((cert) => {
                const days = Math.ceil((new Date(cert.not_after) - new Date()) / 86400000)
                return (
                  <div key={cert.id} className="flex justify-between text-sm">
                    <span className="text-gray-700 dark:text-gray-300">{cert.subject_dn}</span>
                    <span className={days <= 7 ? 'text-red-500' : 'text-amber-500'}>{days}d</span>
                  </div>
                )
              })}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <h2 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">Recent Activity</h2>
            {activity?.items?.length === 0 && <p className="text-sm text-gray-400">No recent activity</p>}
            <div className="space-y-2">
              {activity?.items?.map((log) => (
                <div key={log.id} className="text-sm text-gray-600 dark:text-gray-400">
                  <span className="text-gray-900 dark:text-gray-200">{log.username || log.user_id?.slice(0, 8)}</span>
                  {' '}{log.action.replace(/_/g, ' ')} — {new Date(log.created_at).toLocaleString()}
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
