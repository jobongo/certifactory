import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { importCertificate } from '../../api/import'
import { getCAs } from '../../api/cas'
import Modal from '../ui/Modal'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Button from '../ui/Button'

const formatOptions = [
  { value: 'pem', label: 'PEM / DER' },
  { value: 'pkcs12', label: 'PKCS12 / PFX' },
]

export default function ImportCertModal({ isOpen, onClose }) {
  const queryClient = useQueryClient()
  const { data: cas } = useQuery({ queryKey: ['cas-select'], queryFn: () => getCAs(1, 100), enabled: isOpen })

  const [format, setFormat] = useState('pem')
  const [certFile, setCertFile] = useState(null)
  const [keyFile, setKeyFile] = useState(null)
  const [pkcs12File, setPkcs12File] = useState(null)
  const [passphrase, setPassphrase] = useState('')
  const [caId, setCaId] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: importCertificate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] })
      onClose()
      resetForm()
    },
    onError: (err) => setError(err.response?.data?.detail || 'Import failed'),
  })

  const resetForm = () => {
    setFormat('pem')
    setCertFile(null)
    setKeyFile(null)
    setPkcs12File(null)
    setPassphrase('')
    setCaId('')
    setError('')
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    const formData = new FormData()
    if (format === 'pkcs12') {
      if (pkcs12File) formData.append('pkcs12_file', pkcs12File)
      if (passphrase) formData.append('passphrase', passphrase)
    } else {
      if (certFile) formData.append('cert_file', certFile)
      if (keyFile) formData.append('key_file', keyFile)
    }
    if (caId) formData.append('ca_id', caId)
    mutation.mutate(formData)
  }

  const caOptions = [{ value: '', label: 'Auto-detect (or select)' }, ...(cas?.items?.map((ca) => ({ value: ca.id, label: ca.name })) || [])]

  return (
    <Modal isOpen={isOpen} onClose={() => { onClose(); resetForm() }} title="Import Certificate" size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Select label="Format" options={formatOptions} value={format} onChange={(e) => setFormat(e.target.value)} />

        {format === 'pem' ? (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Certificate File *</label>
              <input type="file" accept=".pem,.crt,.cer,.der" onChange={(e) => setCertFile(e.target.files?.[0])} className="text-sm text-gray-500 dark:text-gray-400" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Private Key File (optional)</label>
              <input type="file" accept=".pem,.key,.der" onChange={(e) => setKeyFile(e.target.files?.[0])} className="text-sm text-gray-500 dark:text-gray-400" />
            </div>
          </>
        ) : (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">PKCS12 / PFX File *</label>
              <input type="file" accept=".p12,.pfx" onChange={(e) => setPkcs12File(e.target.files?.[0])} className="text-sm text-gray-500 dark:text-gray-400" />
            </div>
            <Input label="Passphrase" type="password" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} />
          </>
        )}

        <Select label="Issuing CA" options={caOptions} value={caId} onChange={(e) => setCaId(e.target.value)} />
        <p className="text-xs text-gray-500 dark:text-gray-400">Leave as auto-detect to match by issuer field. Select manually if auto-detect fails.</p>

        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" type="button" onClick={() => { onClose(); resetForm() }}>Cancel</Button>
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Importing...' : 'Import Certificate'}</Button>
        </div>
      </form>
    </Modal>
  )
}
