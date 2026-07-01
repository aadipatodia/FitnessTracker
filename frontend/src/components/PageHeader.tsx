interface PageHeaderProps {
  title: string
  subtitle?: string
  className?: string
}

export function PageHeader({ title, subtitle, className = '' }: PageHeaderProps) {
  return (
    <div className={`animate-fade-up ${className}`}>
      <h1 className="text-2xl sm:text-3xl font-bold tracking-tight gradient-text-subtle">{title}</h1>
      {subtitle && (
        <p className="mt-1.5 text-sm sm:text-base text-muted-foreground">{subtitle}</p>
      )}
    </div>
  )
}
