import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getCAs, getCATree } from '../../api/cas'
import Button from '../../components/ui/Button'
import Table from '../../components/ui/Table'
import StatusBadge from '../../components/shared/StatusBadge'
import { PlusIcon, TableIcon, TreeIcon, ChevronRightIcon, ChevronDownIcon } from '../../utils/icons'

function TreeNode({ node, level = 0 }) {
  const [expanded, setExpanded] = useState(true)
  const navigate = useNavigate()
  const hasChildren = node.children?.length > 0

  return (
    <div>
      <div
        className="flex items-center gap-2 py-2 px-3 hover:bg-gray-50 dark:hover:bg-surface-4 cursor-pointer rounded text-sm"
        style={{ paddingLeft: `${level * 24 + 12}px` }}
      >
        {hasChildren ? (
          <button onClick={() => setExpanded(!expanded)} className="text-gray-400">
            {expanded ? <ChevronDownIcon className="w-3 h-3" /> : <ChevronRightIcon className="w-3 h-3" />}
          </button>
        ) : <span className="w-3" />}
        <span className="flex-1 text-gray-900 dark:text-gray-100" onClick={() => navigate(`/cas/${node.id}`)}>
          {node.name}
        </span>
        <StatusBadge status={node.status} />
      </div>
      {expanded && hasChildren && node.children.map((child) => (
        <TreeNode key={child.id} node={child} level={level + 1} />
      ))}
    </div>
  )
}

export default function CAList() {
  const [view, setView] = useState('table')
  const navigate = useNavigate()
  const { data: cas, isLoading } = useQuery({ queryKey: ['cas'], queryFn: () => getCAs(1, 100) })
  const { data: tree } = useQuery({ queryKey: ['cas-tree'], queryFn: getCATree, enabled: view === 'tree' })

  const columns = [
    { key: 'name', label: 'Name' },
    { key: 'type', label: 'Type' },
    { key: 'status', label: 'Status', render: (val) => <StatusBadge status={val} /> },
    { key: 'subject_dn', label: 'Subject DN' },
    { key: 'not_after', label: 'Expires', render: (val) => new Date(val).toLocaleDateString() },
    { key: 'auto_approve', label: 'Auto-Approve', render: (val) => val ? 'Yes' : 'No' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Certificate Authorities</h1>
        <div className="flex items-center gap-2">
          <div className="flex border border-gray-200 dark:border-gray-700 rounded">
            <button onClick={() => setView('table')} className={`p-2 ${view === 'table' ? 'bg-gray-100 dark:bg-surface-4' : ''}`}>
              <TableIcon className="w-4 h-4 text-gray-500" />
            </button>
            <button onClick={() => setView('tree')} className={`p-2 ${view === 'tree' ? 'bg-gray-100 dark:bg-surface-4' : ''}`}>
              <TreeIcon className="w-4 h-4 text-gray-500" />
            </button>
          </div>
          <Button onClick={() => navigate('/cas/new')}><PlusIcon className="w-4 h-4" /> Create Root CA</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-gray-400">Loading...</div>
      ) : view === 'table' ? (
        <Table columns={columns} data={cas?.items || []} onRowClick={(row) => navigate(`/cas/${row.id}`)} />
      ) : (
        <div className="bg-white dark:bg-surface-3 rounded-lg border border-gray-200 dark:border-gray-800 py-2">
          {tree?.map((node) => <TreeNode key={node.id} node={node} />)}
          {tree?.length === 0 && <div className="text-center py-8 text-gray-400">No CAs created yet</div>}
        </div>
      )}
    </div>
  )
}
