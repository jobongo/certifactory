import Select from '../ui/Select'
import Input from '../ui/Input'
import Button from '../ui/Button'
import { PlusIcon, XIcon } from '../../utils/icons'

const sanTypes = [
  { value: 'DNS', label: 'DNS' },
  { value: 'IP', label: 'IP' },
  { value: 'Email', label: 'Email' },
  { value: 'URI', label: 'URI' },
]

export default function SANFields({ value = [], onChange }) {
  const add = () => onChange([...value, { type: 'DNS', value: '' }])
  const remove = (i) => onChange(value.filter((_, idx) => idx !== i))
  const update = (i, field, val) => {
    const next = [...value]
    next[i] = { ...next[i], [field]: val }
    onChange(next)
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        Subject Alternative Names
      </label>
      {value.map((san, i) => (
        <div key={i} className="flex gap-2 items-start">
          <Select options={sanTypes} value={san.type} onChange={(e) => update(i, 'type', e.target.value)} className="w-28" />
          <Input value={san.value} onChange={(e) => update(i, 'value', e.target.value)} placeholder="e.g. example.com" className="flex-1" />
          <button onClick={() => remove(i)} className="p-2 text-gray-400 hover:text-red-500 mt-0.5">
            <XIcon className="w-4 h-4" />
          </button>
        </div>
      ))}
      <Button variant="ghost" size="sm" onClick={add} type="button">
        <PlusIcon className="w-4 h-4" /> Add SAN
      </Button>
    </div>
  )
}
