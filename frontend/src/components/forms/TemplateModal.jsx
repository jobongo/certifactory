import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createTemplate, updateTemplate } from '../../api/templates'
import Modal from '../ui/Modal'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Button from '../ui/Button'
import KeyUsageCheckboxes from './KeyUsageCheckboxes'
import EKUCheckboxes from './EKUCheckboxes'

export default function TemplateModal({ isOpen, onClose, caId, template }) {
  const queryClient = useQueryClient()
  const isEdit = !!template

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [certType, setCertType] = useState('server')
  const [keyAlgorithm, setKeyAlgorithm] = useState('RSA')
  const [keySize, setKeySize] = useState(2048)
  const [validityDays, setValidityDays] = useState(365)
  const [keyUsage, setKeyUsage] = useState([])
  const [eku, setEku] = useState([])
  const [org, setOrg] = useState('')
  const [ou, setOu] = useState('')
  const [country, setCountry] = useState('')
  const [state, setState] = useState('')
  const [locality, setLocality] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (template) {
      setName(template.name)
      setDescription(template.description || '')
      setCertType(template.type)
      setKeyAlgorithm(template.key_algorithm)
      setKeySize(template.key_size)
      setValidityDays(template.validity_days)
      setKeyUsage(template.key_usage || [])
      setEku(template.extended_key_usage || [])
      const sd = template.subject_defaults || {}
      setOrg(sd.O || ''); setOu(sd.OU || ''); setCountry(sd.C || '')
      setState(sd.ST || ''); setLocality(sd.L || '')
    } else {
      setName(''); setDescription(''); setCertType('server'); setKeyAlgorithm('RSA')
      setKeySize(2048); setValidityDays(365); setKeyUsage([]); setEku([])
      setOrg(''); setOu(''); setCountry(''); setState(''); setLocality('')
    }
    setError('')
  }, [template, isOpen])

  const mutation = useMutation({
    mutationFn: (data) => isEdit
      ? updateTemplate(caId, template.id, data)
      : createTemplate(caId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates', caId] })
      onClose()
    },
    onError: (err) => setError(err.response?.data?.detail || 'Failed to save template'),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    const subjectDefaults = {}
    if (org) subjectDefaults.O = org
    if (ou) subjectDefaults.OU = ou
    if (country) subjectDefaults.C = country
    if (state) subjectDefaults.ST = state
    if (locality) subjectDefaults.L = locality
    mutation.mutate({
      name, description: description || null, type: certType,
      key_algorithm: keyAlgorithm, key_size: Number(keySize),
      validity_days: Number(validityDays),
      key_usage: keyUsage.length ? keyUsage : null,
      extended_key_usage: eku.length ? eku : null,
      subject_defaults: Object.keys(subjectDefaults).length ? subjectDefaults : null,
    })
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={isEdit ? 'Edit Template' : 'Create Template'} size="lg">
      <form onSubmit={handleSubmit} className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
        <Input label="Template Name *" value={name} onChange={(e) => setName(e.target.value)} required />
        <Input label="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
        <div className="grid grid-cols-2 gap-4">
          <Select label="Type" options={[
            { value: 'server', label: 'Server' },
            { value: 'client', label: 'Client' },
            { value: 'custom', label: 'Custom' },
          ]} value={certType} onChange={(e) => setCertType(e.target.value)} />
          <Select label="Key Algorithm" options={[
            { value: 'RSA', label: 'RSA' },
            { value: 'EC', label: 'EC' },
          ]} value={keyAlgorithm} onChange={(e) => setKeyAlgorithm(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Input label="Key Size" type="number" value={keySize} onChange={(e) => setKeySize(e.target.value)} />
          <Input label="Validity (days)" type="number" value={validityDays} onChange={(e) => setValidityDays(e.target.value)} />
        </div>
        <div className="border-t border-gray-200 dark:border-gray-800 pt-4">
          <div className="text-xs uppercase tracking-wider text-gray-400 dark:text-gray-600 mb-3">Subject Defaults</div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Organization (O)" value={org} onChange={(e) => setOrg(e.target.value)} />
            <Input label="Org Unit (OU)" value={ou} onChange={(e) => setOu(e.target.value)} />
          </div>
          <div className="grid grid-cols-3 gap-3 mt-3">
            <Input label="Country (C)" value={country} onChange={(e) => setCountry(e.target.value)} maxLength={2} placeholder="US" />
            <Input label="State (ST)" value={state} onChange={(e) => setState(e.target.value)} />
            <Input label="Locality (L)" value={locality} onChange={(e) => setLocality(e.target.value)} />
          </div>
        </div>
        <KeyUsageCheckboxes value={keyUsage} onChange={setKeyUsage} />
        <EKUCheckboxes value={eku} onChange={setEku} />
        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" type="button" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={mutation.isPending || !name}>
            {mutation.isPending ? 'Saving...' : isEdit ? 'Update' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
