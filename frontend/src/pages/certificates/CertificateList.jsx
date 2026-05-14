import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getCertificates } from '../../api/certificates'
import { getCAs } from '../../api/cas'
import Table from '../../components/ui/Table'
import Select from '../../components/ui/Select'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import StatusBadge from '../../components/shared/StatusBadge'
import { PlusIcon } from '../../utils/icons'

export default function CertificateList() {
  const navigate = useNavigate()
  const [caId, setCaId] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)

  const params = { page, per_page: 25 }
  if (caId) params.ca_id = caId
  if (status) params.status = status

  const { data: certs, isLoading } = useQuery({ queryKey: ['certificates', params], queryFn: () => getCertificates(params) })
  const { data: cas } = useQuery({ queryKey: ['cas-select'], queryFn: () => getCAs(1, 100) })

  const caOptions = [{ value: '', label: 'All CAs' }, ...(cas?.items?.map((ca) => ({ value: ca.id, label: ca.name })) || [])]
  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'active', label: 'Active' },
    { value: 'pending', label: 'Pending' },
    { value: 'revoked', label: 'Revoked' },
    { value: 'expired', label: 'Expired' },
  ]

  const columns = [
    { key: 'subject_dn', label: 'Subject' },
    { key: 'type', label: 'Type' },
    { key: 'status', label: 'Status', render: (val) => <StatusBadge status={val} /> },
    { key: 'not_after', label: 'Expires', render: (val) => val ? new Date(val).toLocaleDateString() : '—' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Certificates</h1>
        <div className="flex gap-2">
          <Button onClick={() => navigate('/certificates/new')}><PlusIcon className="w-4 h-4" /> New Certificate</Button>
          <Button variant="secondary" onClick={() => navigate('/certificates/csr')}>Submit CSR</Button>
        </div>
      </div>

      <div className="flex gap-3 mb-4">
        <Select options={caOptions} value={caId} onChange={(e) => { setCaId(e.target.value); setPage(1) }} className="w-48" />
        <Select options={statusOptions} value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }} className="w-40" />
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-gray-400">Loading...</div>
      ) : (
        <>
          <Table columns={columns} data={certs?.items || []} onRowClick={(row) => navigate(`/certificates/${row.id}`)} />
          {certs?.total > 25 && (
            <div className="flex gap-2 mt-4 justify-center">
              <Button variant="ghost" size="sm" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button>
              <span className="text-sm text-gray-500 py-1.5">Page {page}</span>
              <Button variant="ghost" size="sm" disabled={certs?.items?.length < 25} onClick={() => setPage(page + 1)}>Next</Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
