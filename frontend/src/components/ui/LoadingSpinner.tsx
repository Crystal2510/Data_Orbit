import clsx from 'clsx'

interface Props { size?: 'sm' | 'md' | 'lg'; className?: string }

export default function LoadingSpinner({ size = 'md', className }: Props) {
  const s = { sm: 'w-4 h-4 border-2', md: 'w-6 h-6 border-2', lg: 'w-10 h-10 border-[3px]' }[size]
  return (
    <div className={clsx('rounded-full border-slate-700 border-t-indigo-500 animate-spin', s, className)} />
  )
}