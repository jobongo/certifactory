import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createRootCA, createIntermediateCA } from '../../api/cas'
import SubjectDNFields from '../../components/forms/SubjectDNFields'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Button from '../../components/ui/Button'

export default function CACreate() {
  const { id: parentId } = useParams()
  const isIntermediate = !!parentId
  const navigate = useNavigate()
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
      navigate('/cas')
    },
    onError: (err) => setError(err.response?.data?.detail || 'Failed to create CA'),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    mutation.mutate({
      name,
      subject,
      key_algorithm: keyAlgorithm,
      key_size: Number(keySize),
      validity_days: Number(validityDays),
      auto_approve: autoApprove,
    })
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
        {isIntermediate ? 'Create Intermediate CA' : 'Create Root CA'}
      </h1>
      <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-surface-3 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <Input label="CA Name" value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. My Root CA" />
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
        <div className="flex gap-3">
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Creating...' : 'Create CA'}</Button>
          <Button variant="secondary" type="button" onClick={() => navigate('/cas')}>Cancel</Button>
        </div>
      </form>
    </div>
  )
}
