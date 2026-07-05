import { useEffect, useRef, useState } from 'react'

interface UseInViewOptions {
  threshold?: number
  rootMargin?: string
  once?: boolean
  root?: Element | null
}

export function useInView<T extends Element = HTMLDivElement>(
  options: UseInViewOptions = {},
) {
  const { threshold = 0.08, rootMargin = '0px 0px 0px 0px', once = true, root = null } = options
  const ref = useRef<T>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const scrollRoot = root ?? document.querySelector('main')

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true)
          if (once) observer.unobserve(el)
        } else if (!once) {
          setInView(false)
        }
      },
      { threshold, rootMargin, root: scrollRoot ?? undefined },
    )

    observer.observe(el)
    return () => observer.disconnect()
  }, [threshold, rootMargin, once, root])

  return { ref, inView }
}
