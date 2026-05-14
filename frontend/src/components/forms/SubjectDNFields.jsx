import Input from '../ui/Input'

export default function SubjectDNFields({ value, onChange }) {
  const update = (field, val) => onChange({ ...value, [field]: val })

  return (
    <div className="space-y-3">
      <Input label="Common Name (CN) *" value={value.CN || ''} onChange={(e) => update('CN', e.target.value)} required placeholder="e.g. example.com" />
      <div className="grid grid-cols-2 gap-3">
        <Input label="Organization (O)" value={value.O || ''} onChange={(e) => update('O', e.target.value)} />
        <Input label="Org Unit (OU)" value={value.OU || ''} onChange={(e) => update('OU', e.target.value)} />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <Input label="Country (C)" value={value.C || ''} onChange={(e) => update('C', e.target.value)} maxLength={2} placeholder="US" />
        <Input label="State (ST)" value={value.ST || ''} onChange={(e) => update('ST', e.target.value)} />
        <Input label="Locality (L)" value={value.L || ''} onChange={(e) => update('L', e.target.value)} />
      </div>
    </div>
  )
}
