import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAuditLogs, exportAuditLogs } from '../api/audit'
import Table from '../components/ui/Table'
import Select from '../components/ui/Select'
import Button from '../components/ui/Button'
import { DownloadIcon } from '../utils/icons'

const actionOptions = [
  { value: '', label: 'All Actions' },
  { value: 'created_ca', label: 'Created CA' },
  { value: 'issued_cert', label: 'Issued Cert' },
  { value: 'revoked_cert', label: 'Revoked Cert' },
  { value: 'approved_request', label: 'Approved Request' },
  { value: 'denied_request', label: 'Denied Request' },
  { value: 'login', label: 'Login' },
  { value: 'generated_crl', label: 'Generated CRL' },
]

export default function AuditLog() {
  const [action, setAction] = useState('')
  const [page, setPage] = useState(1)

  const params = { page, per_page: 25 }
  if (action) params.action = action

  const { data, isLoading } = useQuery({ queryKey: ['audit', params], queryFn: () => getAuditLogs(params) })

  const handleExport = async () => {
    const blob = await exportAuditLogs(action ? { action } : {})
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'audit_logs.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const columns = [
    { key: 'created_at', label: 'Timestamp', render: (val) => new Date(val).toLocaleString() },
    { key: 'action', label: 'Action', render: (val) => val.replace(/_/g, ' ') },
    { key: 'resource_type', label: 'Resource Type' },
    { key: 'resource_id', label: 'Resource ID', render: (val) => val?.slice(0, 8) + '...' },
    { key: 'ip_address', label: 'IP' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Audit Log</h1>
        <Button variant="secondary" onClick={handleExport}><DownloadIcon className="w-4 h-4" /> Export CSV</Button>
      </div>
      <div className="flex gap-3 mb-4">
        <Select options={actionOptions} value={action} onChange={(e) => { setAction(e.target.value); setPage(1) }} className="w-48" />
      </div>
      {isLoading ? <div className="text-center py-8 text-gray-400">Loading...</div> : (
        <>
          <Table columns={columns} data={data?.items || []} />
          {data?.total > 25 && (
            <div className="flex gap-2 mt-4 justify-center">
              <Button variant="ghost" size="sm" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button>
              <span className="text-sm text-gray-500 py-1.5">Page {page}</span>
              <Button variant="ghost" size="sm" disabled={data?.items?.length < 25} onClick={() => setPage(page + 1)}>Next</Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
