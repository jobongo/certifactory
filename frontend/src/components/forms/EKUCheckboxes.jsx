const EKUS = [
  { key: 'server_auth', label: 'TLS Web Server Auth' },
  { key: 'client_auth', label: 'TLS Web Client Auth' },
  { key: 'code_signing', label: 'Code Signing' },
  { key: 'email_protection', label: 'Email Protection' },
  { key: 'ocsp_signing', label: 'OCSP Signing' },
]

export default function EKUCheckboxes({ value = [], onChange }) {
  const toggle = (key) => {
    if (value.includes(key)) {
      onChange(value.filter((k) => k !== key))
    } else {
      onChange([...value, key])
    }
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Extended Key Usage</label>
      <div className="grid grid-cols-2 gap-2">
        {EKUS.map((eku) => (
          <label key={eku.key} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <input type="checkbox" checked={value.includes(eku.key)} onChange={() => toggle(eku.key)} className="rounded border-gray-300 dark:border-gray-600" />
            {eku.label}
          </label>
        ))}
      </div>
    </div>
  )
}
