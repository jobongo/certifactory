import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createRootCA, createIntermediateCA } from '../../api/cas'
import Modal from '../ui/Modal'
import SubjectDNFields from './SubjectDNFields'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Button from '../ui/Button'

export default function CreateCAModal({ isOpen, onClose, parentId = null }) {
  const isIntermediate = !!parentId
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [subject, setSubject] = useState({ CN: '' })
  const [keyAlgorithm, setKeyAlgorithm] = useState('RSA')
  const [keySize, setKeySize] = useState(2048)
  const [validityDays, setValidityDays] = useState(3650)
  const [autoApprove, setAutoApprove] = useState(false)
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: (data) => isIntermediate ? createIntermediateCA(parentId, data) : createRootCA(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cas'] })
      queryClient.invalidateQueries({ queryKey: ['cas-tree'] })
      onClose()
      resetForm()
    },
    onError: (err) => setError(err.response?.data?.detail || 'Failed to create CA'),
  })

  const resetForm = () => {
    setName(''); setSubject({ CN: '' }); setKeyAlgorithm('RSA'); setKeySize(2048)
    setValidityDays(3650); setAutoApprove(false); setError('')
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    mutation.mutate({
      name, subject, key_algorithm: keyAlgorithm,
      key_size: Number(keySize), validity_days: Number(validityDays), auto_approve: autoApprove,
    })
  }

  return (
    <Modal isOpen={isOpen} onClose={() => { onClose(); resetForm() }} title={isIntermediate ? 'Create Intermediate CA' : 'Create Root CA'} size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input label="CA Name *" value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. My Root CA" />
        <SubjectDNFields value={subject} onChange={setSubject} />
        <div className="grid grid-cols-2 gap-4">
          <Select label="Key Algorithm" options={[{ value: 'RSA', label: 'RSA' }, { value: 'EC', label: 'EC' }]} value={keyAlgorithm} onChange={(e) => setKeyAlgorithm(e.target.value)} />
          <Select label="Key Size" options={
            keyAlgorithm === 'RSA'
              ? [{ value: '2048', label: '2048' }, { value: '4096', label: '4096' }]
              : [{ value: '256', label: 'P-256' }, { value: '384', label: 'P-384' }]
          } value={String(keySize)} onChange={(e) => setKeySize(e.target.value)} />
        </div>
        <Input label="Validity (days)" type="number" value={validityDays} onChange={(e) => setValidityDays(e.target.value)} />
        <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
          <input type="checkbox" checked={autoApprove} onChange={(e) => setAutoApprove(e.target.checked)} />
          Auto-approve certificate requests
        </label>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" type="button" onClick={() => { onClose(); resetForm() }}>Cancel</Button>
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Creating...' : 'Create CA'}</Button>
        </div>
      </form>
    </Modal>
  )
}
