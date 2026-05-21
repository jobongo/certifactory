import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCA, getCAChain, disableCA, enableCA, updateCA, deleteCA } from '../../api/cas'
import { getCertificates } from '../../api/certificates'
import { generateCRL, downloadCRL, getCRLInfo } from '../../api/crl'
import { getTemplates, deleteTemplate } from '../../api/templates'
import Tabs from '../../components/ui/Tabs'
import Table from '../../components/ui/Table'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import StatusBadge from '../../components/shared/StatusBadge'
import CertChain from '../../components/shared/CertChain'
import CreateCAModal from '../../components/forms/CreateCAModal'
import TemplateModal from '../../components/forms/TemplateModal'
import { useAuth } from '../../hooks/useAuth'
import { DownloadIcon, PlusIcon, XIcon } from '../../utils/icons'

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
  const [showTemplateModal, setShowTemplateModal] = useState(false)
  const [editTemplate, setEditTemplate] = useState(null)
  const [showPem, setShowPem] = useState(false)
  const [pemView, setPemView] = useState('cert')
  const [copied, setCopied] = useState(false)

  const { data: ca, isLoading } = useQuery({ queryKey: ['ca', id], queryFn: () => getCA(id) })
  const { data: chain } = useQuery({ queryKey: ['ca-chain', id], queryFn: () => getCAChain(id) })
  const { data: certs } = useQuery({ queryKey: ['ca-certs', id], queryFn: () => getCertificates({ ca_id: id }) })
  const { data: crlInfo } = useQuery({ queryKey: ['crl-info', id], queryFn: () => getCRLInfo(id) })
  const { data: templates } = useQuery({ queryKey: ['templates', id], queryFn: () => getTemplates(id) })

  const deleteTemplateMutation = useMutation({
    mutationFn: (templateId) => deleteTemplate(id, templateId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['templates', id] }),
  })

  const toggleStatus = useMutation({
    mutationFn: () => ca?.status === 'active' ? disableCA(id) : enableCA(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ca', id] }),
  })

  const crlGenerateMutation = useMutation({
    mutationFn: () => generateCRL(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['crl-info', id] }),
  })

  const handleCRLDownload = async () => {
    const blob = await downloadCRL(id)
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${ca?.name || 'crl'}.crl`
    a.click()
    URL.revokeObjectURL(a.href)
  }

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
                const blob = new Blob([ca.certificate_pem], { type: 'application/x-x509-ca-cert' })
                const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `${ca.name}.crt`; a.click(); URL.revokeObjectURL(a.href)
              }}><DownloadIcon className="w-4 h-4" /> Certificate</Button>
              <Button variant="secondary" size="sm" onClick={() => {
                const chainPem = chain?.chain?.join('\n') || ca.certificate_pem
                const blob = new Blob([chainPem], { type: 'application/x-x509-ca-cert' })
                const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `${ca.name}-chain.crt`; a.click(); URL.revokeObjectURL(a.href)
              }}><DownloadIcon className="w-4 h-4" /> Full Chain</Button>
              <Button variant="secondary" size="sm" onClick={() => { setShowPem(true); setPemView('cert'); setCopied(false) }}>View PEM</Button>
              <Button variant="secondary" size="sm" onClick={handleCRLDownload}>
                <DownloadIcon className="w-4 h-4" /> CRL
              </Button>
              <Button variant="secondary" size="sm" onClick={() => crlGenerateMutation.mutate()} disabled={crlGenerateMutation.isPending}>
                {crlGenerateMutation.isPending ? 'Generating...' : crlGenerateMutation.isSuccess ? 'CRL Regenerated' : 'Regenerate CRL'}
              </Button>
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
          {crlInfo && (
            <div className="border-t border-gray-200 dark:border-gray-800 pt-3 mt-3 space-y-2">
              <div className="text-xs uppercase tracking-wider text-gray-400 dark:text-gray-600 mb-2">CRL Status</div>
              <div><span className="text-gray-500 dark:text-gray-400">CRL Number:</span> <span className="ml-2">{crlInfo.crl_number}</span></div>
              <div><span className="text-gray-500 dark:text-gray-400">Last Generated:</span> <span className="ml-2">{new Date(crlInfo.this_update).toLocaleString()}</span></div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">Next Update:</span>
                <span className={`ml-2 ${new Date(crlInfo.next_update) < new Date() ? 'text-red-500' : ''}`}>
                  {new Date(crlInfo.next_update).toLocaleString()}
                </span>
              </div>
            </div>
          )}
          {!crlInfo && (
            <div className="border-t border-gray-200 dark:border-gray-800 pt-3 mt-3">
              <span className="text-gray-400 dark:text-gray-600 text-xs">No CRL generated yet</span>
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'templates', label: 'Templates',
      content: (
        <div className="space-y-3">
          {user?.role === 'admin' && (
            <div className="flex justify-end">
              <Button size="sm" onClick={() => { setEditTemplate(null); setShowTemplateModal(true) }}>
                <PlusIcon className="w-4 h-4" /> New Template
              </Button>
            </div>
          )}
          {templates?.length === 0 && (
            <p className="text-sm text-gray-400 dark:text-gray-600 py-4 text-center">No templates defined for this CA</p>
          )}
          {templates?.map((t) => (
            <div key={t.id} className="flex items-start justify-between p-3 rounded border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-surface-4">
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{t.name}</div>
                {t.description && <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{t.description}</div>}
                <div className="flex gap-3 mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                  <span>{t.type}</span>
                  <span>{t.key_algorithm} {t.key_size}</span>
                  <span>{t.validity_days}d</span>
                  {t.key_usage?.length > 0 && <span>KU: {t.key_usage.length}</span>}
                  {t.extended_key_usage?.length > 0 && <span>EKU: {t.extended_key_usage.length}</span>}
                </div>
              </div>
              {user?.role === 'admin' && (
                <div className="flex gap-1 ml-2 shrink-0">
                  <Button variant="ghost" size="sm" onClick={() => { setEditTemplate(t); setShowTemplateModal(true) }}>Edit</Button>
                  <Button variant="ghost" size="sm" onClick={() => deleteTemplateMutation.mutate(t.id)}>
                    <XIcon className="w-3 h-3" />
                  </Button>
                </div>
              )}
            </div>
          ))}
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
      <TemplateModal isOpen={showTemplateModal} onClose={() => { setShowTemplateModal(false); setEditTemplate(null) }} caId={id} template={editTemplate} />

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

      <Modal isOpen={showPem} onClose={() => setShowPem(false)} title="Certificate PEM" size="lg">
        <div className="space-y-3">
          {chain?.chain?.length > 1 && (
            <div className="flex gap-1 text-sm">
              <button type="button" onClick={() => { setPemView('cert'); setCopied(false) }}
                className={`px-3 py-1 rounded ${pemView === 'cert' ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
                Certificate
              </button>
              <button type="button" onClick={() => { setPemView('chain'); setCopied(false) }}
                className={`px-3 py-1 rounded ${pemView === 'chain' ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
                Full Chain
              </button>
            </div>
          )}
          <pre className="text-xs bg-gray-50 dark:bg-surface-4 border border-gray-200 dark:border-gray-800 rounded p-3 overflow-x-auto max-h-[50vh] overflow-y-auto select-all whitespace-pre-wrap break-all font-mono">
            {pemView === 'chain' ? (chain?.chain?.join('\n') || ca?.certificate_pem) : ca?.certificate_pem}
          </pre>
          <div className="flex justify-end">
            <Button variant="secondary" size="sm" onClick={() => {
              const text = pemView === 'chain' ? (chain?.chain?.join('\n') || ca?.certificate_pem) : ca?.certificate_pem
              navigator.clipboard.writeText(text)
              setCopied(true)
              setTimeout(() => setCopied(false), 2000)
            }}>
              {copied ? 'Copied!' : 'Copy to Clipboard'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
