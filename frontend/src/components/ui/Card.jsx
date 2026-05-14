export default function Card({ children, className = '', onClick }) {
  return (
    <div
      className={`bg-white dark:bg-surface-4 rounded-lg border border-gray-200 dark:border-gray-800 ${onClick ? 'cursor-pointer hover:border-gray-300 dark:hover:border-gray-700' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className = '' }) {
  return <div className={`px-4 py-3 border-b border-gray-200 dark:border-gray-800 ${className}`}>{children}</div>
}

export function CardBody({ children, className = '' }) {
  return <div className={`px-4 py-4 ${className}`}>{children}</div>
}
