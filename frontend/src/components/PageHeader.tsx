interface PageHeaderProps {
  title: string
  subtitle?: string
  className?: string
}

export function PageHeader({ title, subtitle, className = '' }: PageHeaderProps) {
  return (
    <div className={`animate-fade-up ${className}`}>
      <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">{title}</h1>
      {subtitle && (
        <p className="mt-2 text-base sm:text-lg text-secondary-foreground">{subtitle}</p>
      )}
    </div>
  )
}
