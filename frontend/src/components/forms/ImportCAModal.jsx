import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { importCA } from '../../api/import'
import Modal from '../ui/Modal'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Button from '../ui/Button'

const formatOptions = [
  { value: 'pem', label: 'PEM / DER' },
  { value: 'pkcs12', label: 'PKCS12 / PFX' },
]

export default function ImportCAModal({ isOpen, onClose }) {
  const queryClient = useQueryClient()
  const [format, setFormat] = useState('pem')
  const [name, setName] = useState('')
  const [certFile, setCertFile] = useState(null)
  const [keyFile, setKeyFile] = useState(null)
  const [pkcs12File, setPkcs12File] = useState(null)
  const [passphrase, setPassphrase] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: importCA,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cas'] })
      queryClient.invalidateQueries({ queryKey: ['cas-tree'] })
      onClose()
      resetForm()
    },
    onError: (err) => setError(err.response?.data?.detail || 'Import failed'),
  })

  const resetForm = () => {
    setFormat('pem')
    setName('')
    setCertFile(null)
    setKeyFile(null)
    setPkcs12File(null)
    setPassphrase('')
    setError('')
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    const formData = new FormData()
    formData.append('name', name)
    if (format === 'pkcs12') {
      if (pkcs12File) formData.append('pkcs12_file', pkcs12File)
      if (passphrase) formData.append('passphrase', passphrase)
    } else {
      if (certFile) formData.append('cert_file', certFile)
      if (keyFile) formData.append('key_file', keyFile)
    }
    mutation.mutate(formData)
  }

  return (
    <Modal isOpen={isOpen} onClose={() => { onClose(); resetForm() }} title="Import CA" size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input label="CA Name *" value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. Imported Root CA" />
        <Select label="Format" options={formatOptions} value={format} onChange={(e) => setFormat(e.target.value)} />

        {format === 'pem' ? (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Certificate File *</label>
              <input type="file" accept=".pem,.crt,.cer,.der" onChange={(e) => setCertFile(e.target.files?.[0])} className="text-sm text-gray-500 dark:text-gray-400" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Private Key File *</label>
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

        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" type="button" onClick={() => { onClose(); resetForm() }}>Cancel</Button>
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Importing...' : 'Import CA'}</Button>
        </div>
      </form>
    </Modal>
  )
}
