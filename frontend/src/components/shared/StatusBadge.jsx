import Badge from '../ui/Badge'

const statusMap = {
  active: { variant: 'success', label: 'Active' },
  disabled: { variant: 'default', label: 'Disabled' },
  expired: { variant: 'danger', label: 'Expired' },
  revoked: { variant: 'danger', label: 'Revoked' },
  pending: { variant: 'warning', label: 'Pending' },
  denied: { variant: 'danger', label: 'Denied' },
}

export default function StatusBadge({ status }) {
  const config = statusMap[status] || { variant: 'default', label: status }
  return <Badge variant={config.variant}>{config.label}</Badge>
}
