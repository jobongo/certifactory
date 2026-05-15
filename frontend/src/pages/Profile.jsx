import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../hooks/useTheme'
import { changePassword } from '../api/auth'
import { getTokens, createToken, revokeToken } from '../api/tokens'
import Card, { CardBody } from '../components/ui/Card'
import Input from '../components/ui/Input'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import { SunIcon, MoonIcon, PlusIcon } from '../utils/icons'

export default function Profile() {
  const { user } = useAuth()
  const { isDark, toggle } = useTheme()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')

  const queryClient = useQueryClient()
  const { data: tokens } = useQuery({ queryKey: ['tokens'], queryFn: getTokens })
  const [showCreateToken, setShowCreateToken] = useState(false)
  const [tokenName, setTokenName] = useState('')
  const [newToken, setNewToken] = useState('')

  const createTokenMutation = useMutation({
    mutationFn: createToken,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tokens'] })
      setNewToken(data.token)
      setShowCreateToken(false)
      setTokenName('')
    },
  })

  const revokeTokenMutation = useMutation({
    mutationFn: revokeToken,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tokens'] }),
  })

  const passwordMutation = useMutation({
    mutationFn: () => changePassword(currentPassword, newPassword),
    onSuccess: () => {
      setPasswordSuccess('Password changed successfully')
      setPasswordError('')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    },
    onError: (err) => {
      setPasswordError(err.response?.data?.detail || 'Failed to change password')
      setPasswordSuccess('')
    },
  })

  const handlePasswordSubmit = (e) => {
    e.preventDefault()
    setPasswordError('')
    setPasswordSuccess('')
    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match')
      return
    }
    if (newPassword.length < 4) {
      setPasswordError('Password must be at least 4 characters')
      return
    }
    passwordMutation.mutate()
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Profile</h1>

      <div className="space-y-6">
        {/* Account Info */}
        <Card>
          <CardBody>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Account Information</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500 dark:text-gray-400">Username</span>
                <div className="mt-1 text-gray-900 dark:text-gray-100 font-medium">{user?.username}</div>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">Email</span>
                <div className="mt-1 text-gray-900 dark:text-gray-100">{user?.email}</div>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">Role</span>
                <div className="mt-1 text-gray-900 dark:text-gray-100 capitalize">{user?.role}</div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Appearance */}
        <Card>
          <CardBody>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Appearance</h2>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-900 dark:text-gray-100">Theme</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Choose between light and dark mode</div>
              </div>
              <button
                onClick={toggle}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-surface-4 transition-colors"
              >
                {isDark ? <MoonIcon className="w-4 h-4 text-gray-400" /> : <SunIcon className="w-4 h-4 text-gray-500" />}
                <span className="text-sm text-gray-700 dark:text-gray-300">{isDark ? 'Dark' : 'Light'}</span>
              </button>
            </div>
          </CardBody>
        </Card>

        {/* Change Password */}
        <Card>
          <CardBody>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Change Password</h2>
            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              <Input
                label="Current Password"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
              />
              <Input
                label="New Password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
              <Input
                label="Confirm New Password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
              {passwordError && <p className="text-sm text-red-500">{passwordError}</p>}
              {passwordSuccess && <p className="text-sm text-emerald-500">{passwordSuccess}</p>}
              <Button type="submit" disabled={passwordMutation.isPending}>
                {passwordMutation.isPending ? 'Changing...' : 'Change Password'}
              </Button>
            </form>
          </CardBody>
        </Card>

        {/* API Tokens */}
        <Card>
          <CardBody>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">API Tokens</h2>
              <Button size="sm" onClick={() => setShowCreateToken(true)}>
                <PlusIcon className="w-4 h-4" /> Create Token
              </Button>
            </div>

            {newToken && (
              <div className="mb-4 p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                <p className="text-sm font-medium text-emerald-800 dark:text-emerald-300 mb-1">Token created — copy it now, it won't be shown again</p>
                <code className="block text-xs font-mono bg-white dark:bg-surface-4 p-2 rounded border border-gray-200 dark:border-gray-700 break-all select-all text-gray-900 dark:text-gray-100">
                  {newToken}
                </code>
              </div>
            )}

            {tokens?.items?.length === 0 && !newToken && (
              <p className="text-sm text-gray-400">No API tokens created yet</p>
            )}

            {tokens?.items?.length > 0 && (
              <div className="space-y-2">
                {tokens.items.map((t) => (
                  <div key={t.id} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800 last:border-0">
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{t.name}</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        <code>{t.token_prefix}...</code>
                        {' · '}Created {new Date(t.created_at).toLocaleDateString()}
                        {t.last_used_at && <>{' · '}Last used {new Date(t.last_used_at).toLocaleDateString()}</>}
                      </div>
                    </div>
                    {t.is_active ? (
                      <Button variant="ghost" size="sm" onClick={() => { if (confirm('Revoke this token?')) revokeTokenMutation.mutate(t.id) }}>
                        Revoke
                      </Button>
                    ) : (
                      <span className="text-xs text-red-500">Revoked</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>

        <Modal isOpen={showCreateToken} onClose={() => setShowCreateToken(false)} title="Create API Token">
          <form onSubmit={(e) => { e.preventDefault(); createTokenMutation.mutate(tokenName) }} className="space-y-4">
            <Input label="Token Name" value={tokenName} onChange={(e) => setTokenName(e.target.value)} required placeholder="e.g. CI Pipeline" />
            <p className="text-xs text-gray-500 dark:text-gray-400">The token will have the same permissions as your account ({user?.role}).</p>
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" type="button" onClick={() => setShowCreateToken(false)}>Cancel</Button>
              <Button type="submit" disabled={createTokenMutation.isPending}>Create</Button>
            </div>
          </form>
        </Modal>
      </div>
    </div>
  )
}
