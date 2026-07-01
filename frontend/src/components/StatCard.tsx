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
          <p className="text-sm font-semibold uppercase tracking-wide text-accent">{title}</p>
          <p className="mt-2 text-2xl sm:text-3xl font-bold tracking-tight font-display text-foreground">
            {value}
          </p>
          {subtitle && (
            <p className="mt-2 text-base text-secondary-foreground leading-snug">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="flex h-10 w-10 sm:h-11 sm:w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary/30 to-primary/10 text-primary ring-1 ring-primary/30">
            {icon}
          </div>
        )}
      </div>
    </div>
  )
}
