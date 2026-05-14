const KEY_USAGES = [
  { key: 'digital_signature', label: 'Digital Signature' },
  { key: 'key_encipherment', label: 'Key Encipherment' },
  { key: 'data_encipherment', label: 'Data Encipherment' },
  { key: 'key_agreement', label: 'Key Agreement' },
  { key: 'key_cert_sign', label: 'Certificate Sign' },
  { key: 'crl_sign', label: 'CRL Sign' },
  { key: 'content_commitment', label: 'Content Commitment' },
]

export default function KeyUsageCheckboxes({ value = [], onChange }) {
  const toggle = (key) => {
    if (value.includes(key)) {
      onChange(value.filter((k) => k !== key))
    } else {
      onChange([...value, key])
    }
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Key Usage</label>
      <div className="grid grid-cols-2 gap-2">
        {KEY_USAGES.map((ku) => (
          <label key={ku.key} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <input type="checkbox" checked={value.includes(ku.key)} onChange={() => toggle(ku.key)} className="rounded border-gray-300 dark:border-gray-600" />
            {ku.label}
          </label>
        ))}
      </div>
    </div>
  )
}
