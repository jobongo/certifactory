import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSettings, updateSettings } from '../api/settings'
import Card, { CardHeader, CardBody } from '../components/ui/Card'
import Button from '../components/ui/Button'

const categoryLabels = {
  security: 'Security',
  certificates: 'Certificates',
  maintenance: 'Maintenance',
}

const categoryDescriptions = {
  security: 'Session management, authentication, and password policies',
  certificates: 'Default values for certificate and CA creation',
  maintenance: 'Background job schedules and data retention',
}

function SettingField({ settingKey, definition, value, onChange }) {
  if (definition.type === 'bool') {
    return (
      <div className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{definition.label}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{definition.description}</div>
        </div>
        <button
          type="button"
          onClick={() => onChange(settingKey, !value)}
          className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${
            value ? 'bg-gray-800 dark:bg-gray-200' : 'bg-gray-300 dark:bg-gray-700'
          }`}
        >
          <span
            className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white dark:bg-gray-900 shadow transform transition-transform duration-200 ${
              value ? 'translate-x-5' : 'translate-x-0'
            }`}
          />
        </button>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <div className="flex-1 mr-4">
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{definition.label}</div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          {definition.description}
          {definition.min != null && definition.max != null && (
            <span className="ml-1">({definition.min}–{definition.max})</span>
          )}
        </div>
      </div>
      <input
        type="number"
        min={definition.min}
        max={definition.max}
        value={value}
        onChange={(e) => onChange(settingKey, parseInt(e.target.value) || 0)}
        className="w-24 px-3 py-1.5 rounded border text-sm text-right
          bg-white dark:bg-surface-4 border-gray-300 dark:border-gray-700
          text-gray-900 dark:text-gray-100
          focus:outline-none focus:ring-1 focus:ring-gray-400 dark:focus:ring-gray-500"
      />
    </div>
  )
}

export default function Settings() {
  const queryClient = useQueryClient()
  const [localValues, setLocalValues] = useState(null)
  const [hasChanges, setHasChanges] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [saveSuccess, setSaveSuccess] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
  })

  useEffect(() => {
    if (data && !localValues) {
      setLocalValues({ ...data.values })
    }
  }, [data])

  const saveMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: (result) => {
      queryClient.setQueryData(['settings'], (old) => ({ ...old, values: result.values }))
      queryClient.invalidateQueries({ queryKey: ['settings-defaults'] })
      setLocalValues({ ...result.values })
      setHasChanges(false)
      setSaveError('')
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    },
    onError: (err) => {
      setSaveError(err.response?.data?.detail || 'Failed to save settings')
    },
  })

  if (isLoading) return null

  const values = localValues || data?.values || {}
  const definitions = data?.definitions || {}

  const handleChange = (key, value) => {
    const updated = { ...values, [key]: value }
    setLocalValues(updated)
    setHasChanges(true)
    setSaveError('')
    setSaveSuccess(false)
  }

  const handleSave = () => {
    const changed = {}
    for (const key of Object.keys(values)) {
      if (values[key] !== data.values[key]) {
        changed[key] = values[key]
      }
    }
    if (Object.keys(changed).length > 0) {
      saveMutation.mutate(changed)
    }
  }

  const handleReset = () => {
    setLocalValues({ ...data.values })
    setHasChanges(false)
    setSaveError('')
    setSaveSuccess(false)
  }

  const categories = {}
  for (const [key, defn] of Object.entries(definitions)) {
    const cat = defn.category
    if (!categories[cat]) categories[cat] = []
    categories[cat].push({ key, ...defn })
  }

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Settings</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Global system configuration</p>
        </div>
        <div className="flex items-center gap-2">
          {saveSuccess && (
            <span className="text-sm text-green-600 dark:text-green-400">Saved</span>
          )}
          {saveError && (
            <span className="text-sm text-red-500">{saveError}</span>
          )}
          {hasChanges && (
            <>
              <Button variant="secondary" size="sm" onClick={handleReset}>
                Discard
              </Button>
              <Button size="sm" onClick={handleSave} disabled={saveMutation.isPending}>
                {saveMutation.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="space-y-6">
        {Object.entries(categoryLabels).map(([cat, label]) => {
          const items = categories[cat]
          if (!items) return null
          return (
            <Card key={cat}>
              <CardHeader>
                <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{label}</h2>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{categoryDescriptions[cat]}</p>
              </CardHeader>
              <CardBody>
                {items.map((item) => (
                  <SettingField
                    key={item.key}
                    settingKey={item.key}
                    definition={item}
                    value={values[item.key]}
                    onChange={handleChange}
                  />
                ))}
              </CardBody>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
