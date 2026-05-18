import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCA, getCAChain, disableCA, enableCA, updateCA, deleteCA } from '../../api/cas'
import { getCertificates } from '../../api/certificates'
import Tabs from '../../components/ui/Tabs'
import Table from '../../components/ui/Table'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import StatusBadge from '../../components/shared/StatusBadge'
import CertChain from '../../components/shared/CertChain'
import CreateCAModal from '../../components/forms/CreateCAModal'
import { useAuth } from '../../hooks/useAuth'
import { DownloadIcon } from '../../utils/icons'

export default function CADetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showIntermediate, setShowIntermediate] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [showForceDelete, setShowForceDelete] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [forceDeleteMessage, setForceDeleteMessage] = useState('')

  const { data: ca, isLoading } = useQuery({ queryKey: ['ca', id], queryFn: () => getCA(id) })
  const { data: chain } = useQuery({ queryKey: ['ca-chain', id], queryFn: () => getCAChain(id) })
  const { data: certs } = useQuery({ queryKey: ['ca-certs', id], queryFn: () => getCertificates({ ca_id: id }) })

  const toggleStatus = useMutation({
    mutationFn: () => ca?.status === 'active' ? disableCA(id) : enableCA(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ca', id] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (force) => deleteCA(id, force),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cas'] })
      navigate('/cas')
    },
    onError: (err) => {
      const detail = err.response?.data?.detail || 'Failed to delete CA'
      if (detail.includes('force=true')) {
        setShowDelete(false)
        setForceDeleteMessage(detail)
        setShowForceDelete(true)
      } else {
        setDeleteError(detail)
      }
    },
  })

  if (!ca) return <div className="text-gray-400 py-8">{isLoading ? '' : 'CA not found'}</div>

  const certColumns = [
    { key: 'subject_dn', label: 'Subject' },
    { key: 'type', label: 'Type' },
    { key: 'status', label: 'Status', render: (val) => <StatusBadge status={val} /> },
    { key: 'not_after', label: 'Expires', render: (val) => val ? new Date(val).toLocaleDateString() : '—' },
  ]

  const tabs = [
    {
      key: 'overview', label: 'Overview',
      content: (
        <div className="space-y-4 text-sm">
          <CertChain chain={chain?.chain?.map((_, i) => i === 0 ? ca.subject_dn : `Parent ${i}`).reverse()} />
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div><span className="text-gray-500 dark:text-gray-400">Subject DN:</span> <span className="text-gray-900 dark:text-gray-100 ml-2">{ca.subject_dn}</span></div>
            <div><span className="text-gray-500 dark:text-gray-400">Serial:</span> <span className="text-gray-900 dark:text-gray-100 ml-2">{ca.serial_number}</span></div>
            <div><span className="text-gray-500 dark:text-gray-400">Valid From:</span> <span className="ml-2">{new Date(ca.not_before).toLocaleDateString()}</span></div>
            <div><span className="text-gray-500 dark:text-gray-400">Valid Until:</span> <span className="ml-2">{new Date(ca.not_after).toLocaleDateString()}</span></div>
            <div><span className="text-gray-500 dark:text-gray-400">Algorithm:</span> <span className="ml-2">{ca.key_algorithm} {ca.key_size}</span></div>
            <div><span className="text-gray-500 dark:text-gray-400">Type:</span> <span className="ml-2">{ca.type}</span></div>
          </div>
          <div className="border-t border-gray-200 dark:border-gray-800 pt-4 mt-4">
            <span className="text-gray-500 dark:text-gray-400 block mb-2">Download</span>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => {
                const blob = new Blob([ca.certificate_pem], { type: 'application/x-pem-file' })
                const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `${ca.name}.pem`; a.click(); URL.revokeObjectURL(a.href)
              }}><DownloadIcon className="w-4 h-4" /> Certificate PEM</Button>
              <Button variant="secondary" size="sm" onClick={() => {
                const chainPem = chain?.chain?.join('\n') || ca.certificate_pem
                const blob = new Blob([chainPem], { type: 'application/x-pem-file' })
                const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `${ca.name}-chain.pem`; a.click(); URL.revokeObjectURL(a.href)
              }}><DownloadIcon className="w-4 h-4" /> Full Chain</Button>
            </div>
          </div>
        </div>
      ),
    },
    {
      key: 'certificates', label: 'Certificates',
      content: <Table columns={certColumns} data={certs?.items || []} onRowClick={(row) => navigate(`/certificates/${row.id}`)} />,
    },
    {
      key: 'settings', label: 'Settings',
      content: (
        <div className="space-y-3 text-sm">
          <div><span className="text-gray-500 dark:text-gray-400">Auto-Approve:</span> <span className="ml-2">{ca.auto_approve ? 'Yes' : 'No'}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">OCSP Signing:</span> <span className="ml-2">{ca.ocsp_signing_mode}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">CRL Interval:</span> <span className="ml-2">{ca.crl_regen_interval_hours}h</span></div>
        </div>
      ),
    },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{ca.name}</h1>
          <div className="flex items-center gap-2 mt-1"><StatusBadge status={ca.status} /></div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowIntermediate(true)}>Create Intermediate</Button>
          {user?.role === 'admin' && (
            <>
              <Button variant={ca.status === 'active' ? 'danger' : 'primary'} onClick={() => toggleStatus.mutate()}>
                {ca.status === 'active' ? 'Disable' : 'Enable'}
              </Button>
              <Button variant="danger" onClick={() => setShowDelete(true)}>
                Delete
              </Button>
            </>
          )}
        </div>
      </div>
      {deleteError && <p className="text-sm text-red-500 mb-4">{deleteError}</p>}
      <div className="bg-white dark:bg-surface-3 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <Tabs tabs={tabs} />
      </div>
      <CreateCAModal isOpen={showIntermediate} onClose={() => setShowIntermediate(false)} parentId={id} />

      <Modal isOpen={showDelete} onClose={() => setShowDelete(false)} title="Delete CA">
        <div className="space-y-4">
          <p className="text-sm text-gray-700 dark:text-gray-300">
            Are you sure you want to delete <strong>{ca.name}</strong>? This cannot be undone.
          </p>
          {deleteError && <p className="text-sm text-red-500">{deleteError}</p>}
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => { setShowDelete(false); setDeleteError('') }}>Cancel</Button>
            <Button variant="danger" onClick={() => deleteMutation.mutate(false)} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={showForceDelete} onClose={() => setShowForceDelete(false)} title="Force Delete CA">
        <div className="space-y-4">
          <p className="text-sm text-gray-700 dark:text-gray-300">{forceDeleteMessage}</p>
          <p className="text-sm text-red-500 font-medium">This will revoke all certificates and remove all child CAs. This cannot be undone.</p>
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setShowForceDelete(false)}>Cancel</Button>
            <Button variant="danger" onClick={() => { setShowForceDelete(false); deleteMutation.mutate(true) }} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending ? 'Deleting...' : 'Force Delete'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
