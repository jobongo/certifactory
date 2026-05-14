export default function Input({ label, error, className = '', ...props }) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {label}
        </label>
      )}
      <input
        className={`w-full px-3 py-2 rounded border transition-colors text-sm
          bg-white dark:bg-surface-4 border-gray-300 dark:border-gray-700
          text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-600
          focus:outline-none focus:ring-1 focus:ring-gray-400 dark:focus:ring-gray-500
          ${error ? 'border-red-500 dark:border-red-500' : ''}`}
        {...props}
      />
      {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
    </div>
  )
}
