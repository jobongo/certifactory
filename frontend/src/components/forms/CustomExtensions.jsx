import Input from '../ui/Input'
import Button from '../ui/Button'
import { PlusIcon, XIcon } from '../../utils/icons'

export default function CustomExtensions({ value = [], onChange }) {
  const add = () => onChange([...value, { oid: '', critical: false, value: '' }])
  const remove = (i) => onChange(value.filter((_, idx) => idx !== i))
  const update = (i, field, val) => {
    const next = [...value]
    next[i] = { ...next[i], [field]: val }
    onChange(next)
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Custom Extensions</label>
      {value.map((ext, i) => (
        <div key={i} className="flex gap-2 items-start">
          <Input value={ext.oid} onChange={(e) => update(i, 'oid', e.target.value)} placeholder="OID (e.g. 1.2.3.4)" className="w-40" />
          <label className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400 pt-2">
            <input type="checkbox" checked={ext.critical} onChange={(e) => update(i, 'critical', e.target.checked)} />
            Critical
          </label>
          <Input value={ext.value} onChange={(e) => update(i, 'value', e.target.value)} placeholder="Value" className="flex-1" />
          <button onClick={() => remove(i)} className="p-2 text-gray-400 hover:text-red-500 mt-0.5">
            <XIcon className="w-4 h-4" />
          </button>
        </div>
      ))}
      <Button variant="ghost" size="sm" onClick={add} type="button">
        <PlusIcon className="w-4 h-4" /> Add Extension
      </Button>
    </div>
  )
}
