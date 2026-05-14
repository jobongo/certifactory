import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createCertificate } from '../../api/certificates'
import { getCAs } from '../../api/cas'
import SubjectDNFields from '../../components/forms/SubjectDNFields'
import SANFields from '../../components/forms/SANFields'
import KeyUsageCheckboxes from '../../components/forms/KeyUsageCheckboxes'
import EKUCheckboxes from '../../components/forms/EKUCheckboxes'
import CustomExtensions from '../../components/forms/CustomExtensions'
import Select from '../../components/ui/Select'
import Input from '../../components/ui/Input'
import Button from '../../components/ui/Button'

export default function CertificateCreate() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: cas } = useQuery({ queryKey: ['cas-select'], queryFn: () => getCAs(1, 100) })

  const [caId, setCaId] = useState('')
  const [subject, setSubject] = useState({ CN: '' })
  const [sans, setSans] = useState([{ type: 'DNS', value: '' }])
  const [certType, setCertType] = useState('server')
  const [keyAlgorithm, setKeyAlgorithm] = useState('RSA')
  const [keySize, setKeySize] = useState(2048)
  const [validityDays, setValidityDays] = useState(365)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [keyUsage, setKeyUsage] = useState([])
  const [eku, setEku] = useState([])
  const [customExts, setCustomExts] = useState([])
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: createCertificate,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] })
      navigate(`/certificates/${data.id}`)
    },
    onError: (err) => setError(err.response?.data?.detail || 'Failed to create certificate'),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    const data = {
      ca_id: caId,
      subject,
      san: sans.filter((s) => s.value),
      type: certType,
      key_algorithm: keyAlgorithm,
      key_size: Number(keySize),
      validity_days: Number(validityDays),
    }
    if (showAdvanced) {
      if (keyUsage.length) data.key_usage = keyUsage
      if (eku.length) data.extended_key_usage = eku
      if (customExts.length) data.custom_extensions = customExts.filter((e) => e.oid)
    }
    mutation.mutate(data)
  }

  const caOptions = [{ value: '', label: 'Select CA...' }, ...(cas?.items?.map((ca) => ({ value: ca.id, label: ca.name })) || [])]

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Create Certificate</h1>
      <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-surface-3 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <Select label="Issuing CA *" options={caOptions} value={caId} onChange={(e) => setCaId(e.target.value)} required />
        <SubjectDNFields value={subject} onChange={setSubject} />
        <SANFields value={sans} onChange={setSans} />
        <div className="grid grid-cols-3 gap-4">
          <Select label="Type" options={[{ value: 'server', label: 'Server' }, { value: 'client', label: 'Client' }, { value: 'custom', label: 'Custom' }]} value={certType} onChange={(e) => setCertType(e.target.value)} />
          <Select label="Key Algorithm" options={[{ value: 'RSA', label: 'RSA' }, { value: 'EC', label: 'EC' }]} value={keyAlgorithm} onChange={(e) => setKeyAlgorithm(e.target.value)} />
          <Input label="Validity (days)" type="number" value={validityDays} onChange={(e) => setValidityDays(e.target.value)} />
        </div>

        <button type="button" onClick={() => setShowAdvanced(!showAdvanced)} className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
          {showAdvanced ? '▾ Hide Advanced' : '▸ Show Advanced'}
        </button>

        {showAdvanced && (
          <div className="space-y-4 border-t border-gray-200 dark:border-gray-800 pt-4">
            <KeyUsageCheckboxes value={keyUsage} onChange={setKeyUsage} />
            <EKUCheckboxes value={eku} onChange={setEku} />
            <CustomExtensions value={customExts} onChange={setCustomExts} />
          </div>
        )}

        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex gap-3">
          <Button type="submit" disabled={mutation.isPending || !caId}>{mutation.isPending ? 'Creating...' : 'Create Certificate'}</Button>
          <Button variant="secondary" type="button" onClick={() => navigate('/certificates')}>Cancel</Button>
        </div>
      </form>
    </div>
  )
}
