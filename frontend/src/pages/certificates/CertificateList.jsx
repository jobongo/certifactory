import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getCertificates } from '../../api/certificates'
import { getCAs } from '../../api/cas'
import Table from '../../components/ui/Table'
import Select from '../../components/ui/Select'
import Button from '../../components/ui/Button'
import StatusBadge from '../../components/shared/StatusBadge'
import ImportCertModal from '../../components/forms/ImportCertModal'
import CreateCertModal from '../../components/forms/CreateCertModal'
import SubmitCSRModal from '../../components/forms/SubmitCSRModal'
import { PlusIcon, UploadIcon, SearchIcon } from '../../utils/icons'

function parseSubjectDN(dn) {
  const parts = {}
  if (!dn) return parts
  for (const segment of dn.split(',')) {
    const idx = segment.indexOf('=')
    if (idx === -1) continue
    const key = segment.substring(0, idx).trim()
    const val = segment.substring(idx + 1).trim()
    parts[key] = val
  }
  return parts
}

function OrgCell({ parsed }) {
  const fields = [
    parsed.O, parsed.OU, parsed.C, parsed.ST, parsed.L,
  ].filter(Boolean)
  if (!fields.length) return <span className="text-gray-400 dark:text-gray-600">—</span>
  return (
    <span className="text-xs text-gray-500 dark:text-gray-400 truncate block max-w-[200px]" title={fields.join(', ')}>
      {fields.join(', ')}
    </span>
  )
}

function SANCell({ san }) {
  if (!san?.length) return <span className="text-gray-400 dark:text-gray-600">—</span>
  const text = san.map((s) => s.value).join(', ')
  return (
    <span className="text-xs text-gray-700 dark:text-gray-300 truncate block max-w-[200px]" title={text}>
      {text}
    </span>
  )
}

export default function CertificateList() {
  const navigate = useNavigate()
  const [caId, setCaId] = useState('')
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState('desc')
  const [page, setPage] = useState(1)
  const [showImport, setShowImport] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [showCSR, setShowCSR] = useState(false)

  const params = { page, per_page: 25, sort_by: sortBy, sort_order: sortOrder }
  if (caId) params.ca_id = caId
  if (status) params.status = status
  if (search) params.search = search

  const { data: certs, isLoading } = useQuery({ queryKey: ['certificates', params], queryFn: () => getCertificates(params), placeholderData: (prev) => prev })
  const { data: cas } = useQuery({ queryKey: ['cas-select'], queryFn: () => getCAs(1, 100) })

  const caOptions = [{ value: '', label: 'All CAs' }, ...(cas?.items?.map((ca) => ({ value: ca.id, label: ca.name })) || [])]
  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'active', label: 'Active' },
    { value: 'pending', label: 'Pending' },
    { value: 'revoked', label: 'Revoked' },
    { value: 'expired', label: 'Expired' },
  ]

  const handleSort = (key) => {
    if (sortBy === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(key)
      setSortOrder('asc')
    }
    setPage(1)
  }

  const handleSearch = (e) => {
    e.preventDefault()
    setSearch(searchInput)
    setPage(1)
  }

  const columns = [
    {
      key: 'subject_dn', label: 'Common Name', sortable: true,
      render: (_, row) => {
        const parsed = parseSubjectDN(row.subject_dn)
        const cn = parsed.CN || row.subject_dn
        return <span className="font-medium text-gray-900 dark:text-gray-100 truncate block max-w-[200px]" title={cn}>{cn}</span>
      },
    },
    {
      key: 'org', label: 'Organization',
      render: (_, row) => <OrgCell parsed={parseSubjectDN(row.subject_dn)} />,
    },
    {
      key: 'san', label: 'SAN',
      render: (_, row) => <SANCell san={row.san} />,
    },
    { key: 'type', label: 'Type', sortable: true },
    { key: 'status', label: 'Status', sortable: true, render: (val) => <StatusBadge status={val} /> },
    {
      key: 'not_after', label: 'Expires', sortable: true,
      render: (val) => val ? new Date(val).toLocaleDateString() : '—',
    },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Certificates</h1>
        <div className="flex gap-2">
          <Button onClick={() => setShowCreate(true)}><PlusIcon className="w-4 h-4" /> New Certificate</Button>
          <Button variant="secondary" onClick={() => setShowCSR(true)}>Submit CSR</Button>
          <Button variant="secondary" onClick={() => setShowImport(true)}><UploadIcon className="w-4 h-4" /> Import</Button>
        </div>
      </div>

      <div className="flex gap-3 mb-4">
        <form onSubmit={handleSearch} className="relative flex-1 max-w-sm">
          <SearchIcon className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by subject..."
            className="w-full pl-9 pr-3 py-2 rounded border text-sm bg-white dark:bg-surface-4 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-gray-400 dark:focus:ring-gray-500"
            onBlur={() => { if (searchInput !== search) { setSearch(searchInput); setPage(1) } }}
          />
          {search && (
            <button type="button" onClick={() => { setSearchInput(''); setSearch(''); setPage(1) }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xs">
              ✕
            </button>
          )}
        </form>
        <Select options={caOptions} value={caId} onChange={(e) => { setCaId(e.target.value); setPage(1) }} className="w-48" />
        <Select options={statusOptions} value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }} className="w-40" />
      </div>

      <Table columns={columns} data={certs?.items || []} onRowClick={(row) => navigate(`/certificates/${row.id}`)} hideEmpty={isLoading} sortBy={sortBy} sortOrder={sortOrder} onSort={handleSort} />
      {certs?.total > 25 && (
        <div className="flex gap-2 mt-4 justify-center">
          <Button variant="ghost" size="sm" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button>
          <span className="text-sm text-gray-500 py-1.5">Page {page} of {Math.ceil(certs.total / 25)}</span>
          <Button variant="ghost" size="sm" disabled={certs?.items?.length < 25} onClick={() => setPage(page + 1)}>Next</Button>
        </div>
      )}

      <ImportCertModal isOpen={showImport} onClose={() => setShowImport(false)} />
      <CreateCertModal isOpen={showCreate} onClose={() => setShowCreate(false)} />
      <SubmitCSRModal isOpen={showCSR} onClose={() => setShowCSR(false)} />
    </div>
  )
}
