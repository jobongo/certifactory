import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCertificate, revokeCert, renewCert, downloadCert, approveCert, denyCert } from '../../api/certificates'
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

  const { data: cert, isLoading } = useQuery({ queryKey: ['certificate', id], queryFn: () => getCertificate(id) })

  const revoke = useMutation({
    mutationFn: () => revokeCert(id, revokeReason),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['certificate', id] }); setShowRevoke(false) },
  })

  const renew = useMutation({
    mutationFn: () => renewCert(id),
    onSuccess: (data) => navigate(`/certificates/${data.id}`),
  })

  const approve = useMutation({
    mutationFn: () => approveCert(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['certificate', id] }),
  })

  const deny = useMutation({
    mutationFn: () => denyCert(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['certificate', id] }),
  })

  const handleDownload = async (format) => {
    if (format === 'pkcs12') { setShowPkcs12(true); return }
    const blob = await downloadCert(id, format)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `certificate.${format === 'der' ? 'der' : 'pem'}`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handlePkcs12Download = async () => {
    const blob = await downloadCert(id, 'pkcs12', passphrase)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'certificate.p12'
    a.click()
    URL.revokeObjectURL(url)
    setShowPkcs12(false)
    setPassphrase('')
  }

  if (isLoading) return <div className="text-gray-400 py-8">Loading...</div>
  if (!cert) return <div className="text-gray-400 py-8">Certificate not found</div>

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
            <span className="text-gray-500 dark:text-gray-400 block mb-2">Download</span>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => handleDownload('pem')}><DownloadIcon className="w-4 h-4" /> PEM</Button>
              <Button variant="secondary" size="sm" onClick={() => handleDownload('der')}><DownloadIcon className="w-4 h-4" /> DER</Button>
              <Button variant="secondary" size="sm" onClick={() => handleDownload('pkcs12')}><DownloadIcon className="w-4 h-4" /> PKCS12</Button>
            </div>
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
    </div>
  )
}
