import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../hooks/useTheme'
import { changePassword } from '../api/auth'
import Card, { CardBody } from '../components/ui/Card'
import Input from '../components/ui/Input'
import Button from '../components/ui/Button'
import { SunIcon, MoonIcon } from '../utils/icons'

export default function Profile() {
  const { user } = useAuth()
  const { isDark, toggle } = useTheme()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')

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
      </div>
    </div>
  )
}
