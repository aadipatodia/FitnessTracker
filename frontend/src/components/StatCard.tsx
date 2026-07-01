import { cn } from '@/lib/utils'

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: React.ReactNode
  trend?: 'up' | 'down' | 'neutral'
  className?: string
}

export function StatCard({ title, value, subtitle, icon, className }: StatCardProps) {
  return (
    <div className={cn('luxury-card rounded-xl p-4 sm:p-5 h-full', className)}>
      <div className="relative flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[11px] sm:text-xs uppercase tracking-wider text-muted-foreground">{title}</p>
          <p className="mt-1.5 text-xl sm:text-2xl font-bold tracking-tight font-display gradient-text-subtle">
            {value}
          </p>
          {subtitle && (
            <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="flex h-9 w-9 sm:h-10 sm:w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 text-primary ring-1 ring-primary/20">
            {icon}
          </div>
        )}
      </div>
    </div>
  )
}
