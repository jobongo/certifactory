import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCertificates, approveCert, denyCert } from '../api/certificates'
import Card, { CardBody } from '../components/ui/Card'
import Button from '../components/ui/Button'

export default function PendingRequests() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['pending'], queryFn: () => getCertificates({ status: 'pending', per_page: 100 }) })

  const approve = useMutation({
    mutationFn: approveCert,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['pending'] }); queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] }) },
  })

  const deny = useMutation({
    mutationFn: denyCert,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['pending'] }); queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] }) },
  })

  if (isLoading) return <div className="text-gray-400 py-8">Loading...</div>

  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Pending Requests</h1>
      {data?.items?.length === 0 && <p className="text-gray-400">No pending requests</p>}
      <div className="space-y-4">
        {data?.items?.map((cert) => (
          <Card key={cert.id}>
            <CardBody>
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-medium text-gray-900 dark:text-gray-100">{cert.subject_dn}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">Type: {cert.type} · Requested: {new Date(cert.created_at).toLocaleDateString()}</div>
                  {cert.san?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {cert.san.map((s, i) => (
                        <span key={i} className="px-2 py-0.5 bg-gray-100 dark:bg-surface-3 rounded text-xs text-gray-600 dark:text-gray-400">{s.type}: {s.value}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => approve.mutate(cert.id)}>Approve</Button>
                  <Button size="sm" variant="danger" onClick={() => deny.mutate(cert.id)}>Deny</Button>
                </div>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>
    </div>
  )
}
