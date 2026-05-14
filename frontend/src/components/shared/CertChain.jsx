import { ChevronRightIcon } from '../../utils/icons'

export default function CertChain({ chain }) {
  if (!chain || chain.length === 0) return null

  return (
    <div className="flex items-center gap-1 text-sm">
      {chain.map((item, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <ChevronRightIcon className="w-3 h-3 text-gray-400" />}
          <span className={i === chain.length - 1 ? 'font-medium text-gray-900 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400'}>
            {item}
          </span>
        </span>
      ))}
    </div>
  )
}
