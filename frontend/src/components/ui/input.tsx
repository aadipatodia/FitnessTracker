import { cn } from '@/lib/utils'
import { InputHTMLAttributes, forwardRef } from 'react'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        'flex h-10 w-full rounded-xl border border-input bg-muted/50 px-3 py-2 text-base text-foreground placeholder:text-secondary-foreground/60 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/30 focus:bg-muted/80 disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      ref={ref}
      {...props}
    />
  )
)
Input.displayName = 'Input'

export const Label = forwardRef<HTMLLabelElement, React.LabelHTMLAttributes<HTMLLabelElement>>(
  ({ className, ...props }, ref) => (
    <label
      ref={ref}
      className={cn('text-sm font-medium text-foreground/90 tracking-wide', className)}
      {...props}
    />
  )
)
Label.displayName = 'Label'

export const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      className={cn(
        'flex min-h-[80px] w-full rounded-xl border border-input bg-muted/50 px-3 py-2 text-base text-foreground placeholder:text-secondary-foreground/60 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/30 focus:bg-muted/80 disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      ref={ref}
      {...props}
    />
  )
)
Textarea.displayName = 'Textarea'

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => (
    <select
      className={cn(
        'flex h-10 w-full rounded-xl border border-input bg-muted/50 px-3 py-2 text-base text-foreground transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/30',
        className
      )}
      ref={ref}
      {...props}
    />
  )
)
Select.displayName = 'Select'
