import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { submitCSR } from '../../api/certificates'
import { getCAs } from '../../api/cas'
import { getDefaults } from '../../api/settings'
import Modal from '../ui/Modal'
import Select from '../ui/Select'
import Input from '../ui/Input'
import Button from '../ui/Button'

export default function SubmitCSRModal({ isOpen, onClose }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: cas } = useQuery({ queryKey: ['cas-select'], queryFn: () => getCAs(1, 100), enabled: isOpen })
  const { data: defaults } = useQuery({ queryKey: ['settings-defaults'], queryFn: getDefaults })

  const [csrPem, setCsrPem] = useState('')
  const [caId, setCaId] = useState('')
  const [validityDaysInput, setValidityDaysInput] = useState(null)
  const validityDays = validityDaysInput !== null ? validityDaysInput : (defaults?.default_cert_validity_days ?? '')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: submitCSR,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] })
      onClose()
      resetForm()
      navigate(`/certificates/${data.id}`)
    },
    onError: (err) => setError(err.response?.data?.detail || 'Failed to submit CSR'),
  })

  const resetForm = () => { setCsrPem(''); setCaId(''); setValidityDaysInput(null); setError('') }

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => setCsrPem(ev.target.result)
    reader.readAsText(file)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    mutation.mutate({ ca_id: caId, csr_pem: csrPem, type: 'server', validity_days: Number(validityDays) })
  }

  const caOptions = [{ value: '', label: 'Select CA...' }, ...(cas?.items?.map((ca) => ({ value: ca.id, label: ca.name })) || [])]

  return (
    <Modal isOpen={isOpen} onClose={() => { onClose(); resetForm() }} title="Submit CSR" size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">CSR (PEM)</label>
          <textarea
            className="w-full h-40 px-3 py-2 rounded border bg-white dark:bg-surface-4 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-gray-400"
            value={csrPem} onChange={(e) => setCsrPem(e.target.value)} placeholder="-----BEGIN CERTIFICATE REQUEST-----"
          />
          <input type="file" accept=".pem,.csr,.req" onChange={handleFileUpload} className="mt-2 text-sm text-gray-500" />
        </div>
        <Select label="Issuing CA *" options={caOptions} value={caId} onChange={(e) => setCaId(e.target.value)} required />
        <Input label="Validity (days)" type="number" value={validityDays} onChange={(e) => setValidityDaysInput(e.target.value)} />
        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" type="button" onClick={() => { onClose(); resetForm() }}>Cancel</Button>
          <Button type="submit" disabled={mutation.isPending || !caId || !csrPem}>{mutation.isPending ? 'Submitting...' : 'Submit CSR'}</Button>
        </div>
      </form>
    </Modal>
  )
}
