import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCertificate, revokeCert, renewCert, downloadCert, approveCert, denyCert, deleteCert } from '../../api/certificates'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import StatusBadge from '../../components/shared/StatusBadge'
import { useAuth } from '../../hooks/useAuth'
import { DownloadIcon } from '../../utils/icons'

export default function CertificateDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showRevoke, setShowRevoke] = useState(false)
  const [revokeReason, setRevokeReason] = useState('unspecified')
  const [showPkcs12, setShowPkcs12] = useState(false)
  const [passphrase, setPassphrase] = useState('')
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [showPem, setShowPem] = useState(false)
  const [pemView, setPemView] = useState('cert')
  const [copied, setCopied] = useState(false)

  const { data: cert, isLoading } = useQuery({ queryKey: ['certificate', id], queryFn: () => getCertificate(id) })

  const revoke = useMutation({
    mutationFn: () => revokeCert(id, revokeReason),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['certificate', id] }); queryClient.invalidateQueries({ queryKey: ['certificates'] }); setShowRevoke(false) },
  })

  const renew = useMutation({
    mutationFn: () => renewCert(id),
    onSuccess: (data) => navigate(`/certificates/${data.id}`),
  })

  const approve = useMutation({
    mutationFn: () => approveCert(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['certificate', id] }); queryClient.invalidateQueries({ queryKey: ['certificates'] }) },
  })

  const deny = useMutation({
    mutationFn: () => denyCert(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['certificate', id] }); queryClient.invalidateQueries({ queryKey: ['certificates'] }) },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteCert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] })
      navigate('/certificates')
    },
    onError: (err) => setDeleteError(err.response?.data?.detail || 'Failed to delete certificate'),
  })

  const getCN = () => {
    const match = cert?.subject_dn?.match(/CN=([^,]+)/)
    return match ? match[1].replace(/[^a-zA-Z0-9._-]/g, '_') : 'certificate'
  }

  const handleDownload = async (format) => {
    if (format === 'pkcs12') { setShowPkcs12(true); return }
    const cn = getCN()
    const blob = await downloadCert(id, format)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${cn}.${format === 'der' ? 'der' : 'pem'}`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleKeyDownload = async () => {
    const cn = getCN()
    const blob = await downloadCert(id, 'pem', null, true)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${cn}.key`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handlePkcs12Download = async () => {
    const cn = getCN()
    const blob = await downloadCert(id, 'pkcs12', passphrase)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${cn}.p12`
    a.click()
    URL.revokeObjectURL(url)
    setShowPkcs12(false)
    setPassphrase('')
  }

  if (!cert) return <div className="text-gray-400 py-8">{isLoading ? '' : 'Certificate not found'}</div>

  const isAdmin = user?.role === 'admin' || user?.role === 'operator'
  const revokeReasons = [
    { value: 'unspecified', label: 'Unspecified' }, { value: 'key_compromise', label: 'Key Compromise' },
    { value: 'ca_compromise', label: 'CA Compromise' }, { value: 'superseded', label: 'Superseded' },
    { value: 'cessation_of_operation', label: 'Cessation of Operation' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{cert.subject_dn}</h1>
          <div className="flex items-center gap-2 mt-1"><StatusBadge status={cert.status} /></div>
        </div>
        <div className="flex gap-2">
          {cert.status === 'active' && isAdmin && (
            <>
              <Button variant="secondary" onClick={() => renew.mutate()}>Renew</Button>
              <Button variant="danger" onClick={() => setShowRevoke(true)}>Revoke</Button>
            </>
          )}
          {cert.status === 'pending' && isAdmin && (
            <>
              <Button onClick={() => approve.mutate()}>Approve</Button>
              <Button variant="danger" onClick={() => deny.mutate()}>Deny</Button>
            </>
          )}
          {['revoked', 'expired', 'denied'].includes(cert.status) && isAdmin && (
            <Button variant="danger" onClick={() => setShowDeleteModal(true)}>Delete</Button>
          )}
        </div>
      </div>

      <div className="bg-white dark:bg-surface-3 rounded-lg border border-gray-200 dark:border-gray-800 p-6 space-y-4 text-sm">
        <div className="grid grid-cols-2 gap-4">
          <div><span className="text-gray-500 dark:text-gray-400">Subject DN:</span><span className="ml-2 text-gray-900 dark:text-gray-100">{cert.subject_dn}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">Serial:</span><span className="ml-2">{cert.serial_number}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">Type:</span><span className="ml-2">{cert.type}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">Algorithm:</span><span className="ml-2">{cert.key_algorithm} {cert.key_size}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">Valid From:</span><span className="ml-2">{cert.not_before ? new Date(cert.not_before).toLocaleDateString() : '—'}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">Valid Until:</span><span className="ml-2">{cert.not_after ? new Date(cert.not_after).toLocaleDateString() : '—'}</span></div>
        </div>

        {cert.san?.length > 0 && (
          <div>
            <span className="text-gray-500 dark:text-gray-400">SANs:</span>
            <div className="mt-1 flex flex-wrap gap-1">
              {cert.san.map((s, i) => (
                <span key={i} className="px-2 py-0.5 bg-gray-100 dark:bg-surface-4 rounded text-xs">{s.type}: {s.value}</span>
              ))}
            </div>
          </div>
        )}

        {cert.certificate_pem && (
          <div className="border-t border-gray-200 dark:border-gray-800 pt-4">
            <span className="text-gray-500 dark:text-gray-400 block mb-2">Download Certificate</span>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => handleDownload('pem')}><DownloadIcon className="w-4 h-4" /> PEM</Button>
              <Button variant="secondary" size="sm" onClick={() => handleDownload('der')}><DownloadIcon className="w-4 h-4" /> DER</Button>
              <Button variant="secondary" size="sm" onClick={() => handleDownload('pkcs12')}><DownloadIcon className="w-4 h-4" /> PKCS12</Button>
              <Button variant="secondary" size="sm" onClick={() => { setShowPem(true); setPemView('cert'); setCopied(false) }}>View PEM</Button>
            </div>
            {cert.has_private_key && (
              <div className="mt-3">
                <span className="text-gray-500 dark:text-gray-400 block mb-2">Download Private Key</span>
                <Button variant="secondary" size="sm" onClick={handleKeyDownload}><DownloadIcon className="w-4 h-4" /> Private Key (PEM)</Button>
              </div>
            )}
          </div>
        )}
      </div>

      <Modal isOpen={showRevoke} onClose={() => setShowRevoke(false)} title="Revoke Certificate">
        <div className="space-y-4">
          <Select label="Revocation Reason" options={revokeReasons} value={revokeReason} onChange={(e) => setRevokeReason(e.target.value)} />
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setShowRevoke(false)}>Cancel</Button>
            <Button variant="danger" onClick={() => revoke.mutate()}>Revoke</Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={showPkcs12} onClose={() => setShowPkcs12(false)} title="PKCS12 Passphrase">
        <div className="space-y-4">
          <Input label="Passphrase" type="password" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} />
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setShowPkcs12(false)}>Cancel</Button>
            <Button onClick={handlePkcs12Download}>Download</Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={showDeleteModal} onClose={() => { setShowDeleteModal(false); setDeleteError('') }} title="Delete Certificate">
        <div className="space-y-4">
          <p className="text-sm text-gray-700 dark:text-gray-300">
            Are you sure you want to delete this certificate? This cannot be undone.
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 font-mono break-all">{cert.subject_dn}</p>
          {deleteError && <p className="text-sm text-red-500">{deleteError}</p>}
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => { setShowDeleteModal(false); setDeleteError('') }}>Cancel</Button>
            <Button variant="danger" onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={showPem} onClose={() => setShowPem(false)} title="Certificate PEM" size="lg">
        <div className="space-y-3">
          {cert?.csr_pem && (
            <div className="flex gap-1 text-sm">
              <button type="button" onClick={() => { setPemView('cert'); setCopied(false) }}
                className={`px-3 py-1 rounded ${pemView === 'cert' ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
                Certificate
              </button>
              <button type="button" onClick={() => { setPemView('csr'); setCopied(false) }}
                className={`px-3 py-1 rounded ${pemView === 'csr' ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
                CSR
              </button>
            </div>
          )}
          <pre className="text-xs bg-gray-50 dark:bg-surface-4 border border-gray-200 dark:border-gray-800 rounded p-3 overflow-x-auto max-h-[50vh] overflow-y-auto select-all whitespace-pre-wrap break-all font-mono">
            {pemView === 'csr' ? cert?.csr_pem : cert?.certificate_pem}
          </pre>
          <div className="flex justify-end">
            <Button variant="secondary" size="sm" onClick={() => {
              const text = pemView === 'csr' ? cert?.csr_pem : cert?.certificate_pem
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
