import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { submitCSR } from '../../api/certificates'
import { getCAs } from '../../api/cas'
import Select from '../../components/ui/Select'
import Input from '../../components/ui/Input'
import Button from '../../components/ui/Button'

export default function CSRSubmit() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: cas } = useQuery({ queryKey: ['cas-select'], queryFn: () => getCAs(1, 100) })

  const [csrPem, setCsrPem] = useState('')
  const [caId, setCaId] = useState('')
  const [validityDays, setValidityDays] = useState(365)
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: submitCSR,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] })
      navigate(`/certificates/${data.id}`)
    },
    onError: (err) => setError(err.response?.data?.detail || 'Failed to submit CSR'),
  })

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
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Submit CSR</h1>
      <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-surface-3 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">CSR (PEM)</label>
          <textarea
            className="w-full h-40 px-3 py-2 rounded border bg-white dark:bg-surface-4 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-gray-400"
            value={csrPem}
            onChange={(e) => setCsrPem(e.target.value)}
            placeholder="-----BEGIN CERTIFICATE REQUEST-----"
          />
          <input type="file" accept=".pem,.csr,.req" onChange={handleFileUpload} className="mt-2 text-sm text-gray-500" />
        </div>
        <Select label="Issuing CA *" options={caOptions} value={caId} onChange={(e) => setCaId(e.target.value)} required />
        <Input label="Validity (days)" type="number" value={validityDays} onChange={(e) => setValidityDays(e.target.value)} />
        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex gap-3">
          <Button type="submit" disabled={mutation.isPending || !caId || !csrPem}>{mutation.isPending ? 'Submitting...' : 'Submit CSR'}</Button>
          <Button variant="secondary" type="button" onClick={() => navigate('/certificates')}>Cancel</Button>
        </div>
      </form>
    </div>
  )
}
