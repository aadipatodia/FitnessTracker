import { useEffect, useState } from 'react'

export function ScrollProgress() {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const main = document.querySelector('main')
    if (!main) return

    const onScroll = () => {
      const max = main.scrollHeight - main.clientHeight
      setProgress(max > 0 ? (main.scrollTop / max) * 100 : 0)
    }

    onScroll()
    main.addEventListener('scroll', onScroll, { passive: true })
    return () => main.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div
      className="pointer-events-none fixed top-0 left-0 right-0 z-[60] h-[2px] lg:left-64"
      aria-hidden="true"
    >
      <div
        className="h-full origin-left bg-gradient-to-r from-primary/60 via-primary to-accent transition-[width] duration-150 ease-out"
        style={{
          width: `${progress}%`,
          boxShadow: progress > 0 ? '0 0 12px rgba(201, 169, 98, 0.5)' : undefined,
        }}
      />
    </div>
  )
}
