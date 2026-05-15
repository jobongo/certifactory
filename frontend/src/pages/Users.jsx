import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getUsers, createUser, updateUser, deleteUser, resetUserPassword } from '../api/users'
import Table from '../components/ui/Table'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import Badge from '../components/ui/Badge'
import { PlusIcon } from '../utils/icons'

export default function Users() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['users'], queryFn: () => getUsers(1, 100) })
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'requester' })
  const [error, setError] = useState('')
  const [showResetPassword, setShowResetPassword] = useState(false)
  const [resetUserId, setResetUserId] = useState(null)
  const [resetPassword, setResetPassword] = useState('')
  const [resetError, setResetError] = useState('')

  const create = useMutation({
    mutationFn: createUser,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['users'] }); setShowCreate(false); setForm({ username: '', email: '', password: '', role: 'requester' }) },
    onError: (err) => setError(err.response?.data?.detail || 'Failed'),
  })

  const roleChange = useMutation({
    mutationFn: ({ id, role }) => updateUser(id, { role }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  })

  const deactivate = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  })

  const resetPw = useMutation({
    mutationFn: () => resetUserPassword(resetUserId, resetPassword),
    onSuccess: () => { setShowResetPassword(false); setResetPassword(''); setResetError('') },
    onError: (err) => setResetError(err.response?.data?.detail || 'Failed to reset password'),
  })

  const roleOptions = [
    { value: 'admin', label: 'Admin' }, { value: 'operator', label: 'Operator' },
    { value: 'requester', label: 'Requester' }, { value: 'auditor', label: 'Auditor' },
  ]

  const columns = [
    { key: 'username', label: 'Username' },
    { key: 'email', label: 'Email' },
    {
      key: 'role', label: 'Role',
      render: (val, row) => (
        <select value={val} onChange={(e) => roleChange.mutate({ id: row.id, role: e.target.value })}
          className="bg-transparent border border-gray-200 dark:border-gray-700 rounded px-2 py-1 text-sm">
          {roleOptions.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
      ),
    },
    { key: 'is_active', label: 'Status', render: (val) => <Badge variant={val ? 'success' : 'danger'}>{val ? 'Active' : 'Inactive'}</Badge> },
    {
      key: 'id', label: '',
      render: (_, row) => (
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" onClick={() => { setResetUserId(row.id); setShowResetPassword(true) }}>
            Reset Password
          </Button>
          {row.is_active && (
            <Button variant="ghost" size="sm" onClick={() => { if (confirm('Deactivate this user?')) deactivate.mutate(row.id) }}>
              Deactivate
            </Button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Users</h1>
        <Button onClick={() => setShowCreate(true)}><PlusIcon className="w-4 h-4" /> Create User</Button>
      </div>
      <Table columns={columns} data={data?.items || []} hideEmpty={isLoading} />
      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create User">
        <form onSubmit={(e) => { e.preventDefault(); setError(''); create.mutate(form) }} className="space-y-4">
          <Input label="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
          <Input label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          <Input label="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          <Select label="Role" options={roleOptions} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
          {error && <p className="text-sm text-red-500">{error}</p>}
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" type="button" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button type="submit" disabled={create.isPending}>Create</Button>
          </div>
        </form>
      </Modal>
      <Modal isOpen={showResetPassword} onClose={() => { setShowResetPassword(false); setResetPassword(''); setResetError('') }} title="Reset User Password">
        <form onSubmit={(e) => { e.preventDefault(); resetPw.mutate() }} className="space-y-4">
          <Input label="New Password" type="password" value={resetPassword} onChange={(e) => setResetPassword(e.target.value)} required />
          {resetError && <p className="text-sm text-red-500">{resetError}</p>}
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" type="button" onClick={() => { setShowResetPassword(false); setResetPassword('') }}>Cancel</Button>
            <Button type="submit" disabled={resetPw.isPending}>{resetPw.isPending ? 'Resetting...' : 'Reset Password'}</Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
