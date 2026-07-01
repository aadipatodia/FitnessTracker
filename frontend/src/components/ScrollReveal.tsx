import { cn } from '@/lib/utils'
import { useInView } from '@/hooks/useInView'
import { CSSProperties, ReactNode } from 'react'

export type ScrollRevealAnimation =
  | 'fade-up'
  | 'fade-down'
  | 'fade-in'
  | 'slide-left'
  | 'slide-right'
  | 'scale'
  | 'blur-up'

interface ScrollRevealProps {
  children: ReactNode
  className?: string
  animation?: ScrollRevealAnimation
  delay?: number
  duration?: number
  once?: boolean
  threshold?: number
  rootMargin?: string
  style?: CSSProperties
}

export function ScrollReveal({
  children,
  className,
  animation = 'fade-up',
  delay = 0,
  duration = 700,
  once = true,
  threshold,
  rootMargin,
  style,
}: ScrollRevealProps) {
  const { ref, inView } = useInView<HTMLDivElement>({ once, threshold, rootMargin })

  return (
    <div
      ref={ref}
      className={cn(
        'scroll-reveal',
        `scroll-reveal-${animation}`,
        inView && 'scroll-reveal-visible',
        className,
      )}
      style={{
        ...style,
        '--reveal-delay': `${delay}ms`,
        '--reveal-duration': `${duration}ms`,
      } as CSSProperties}
    >
      {children}
    </div>
  )
}

/** Stagger delay in ms for list items */
export function revealDelay(index: number, step = 90): number {
  return index * step
}
