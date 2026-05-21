export default function Table({ columns, data, onRowClick, hideEmpty = false, sortBy, sortOrder, onSort }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-800">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400 ${col.sortable && onSort ? 'cursor-pointer select-none hover:text-gray-700 dark:hover:text-gray-300' : ''}`}
                onClick={() => col.sortable && onSort?.(col.key)}
              >
                <span className="inline-flex items-center gap-1">
                  {col.label}
                  {col.sortable && sortBy === col.key && (
                    <span className="text-xs">{sortOrder === 'asc' ? '▲' : '▼'}</span>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={row.id || i}
              className={`border-b border-gray-100 dark:border-gray-800/50 ${onRowClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-surface-4' : ''}`}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map((col) => (
                <td key={col.key} className={`px-4 py-3 text-gray-700 dark:text-gray-300 whitespace-nowrap ${col.className || ''}`}>
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length === 0 && !hideEmpty && (
        <div className="text-center py-8 text-gray-400 dark:text-gray-600">No data</div>
      )}
    </div>
  )
}
