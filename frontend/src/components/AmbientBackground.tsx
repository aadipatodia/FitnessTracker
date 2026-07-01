export function AmbientBackground({ scrollY = 0 }: { scrollY?: number }) {
  const parallax1 = scrollY * 0.08
  const parallax2 = scrollY * -0.05
  const parallax3 = scrollY * 0.03

  return (
    <div className="ambient-bg" aria-hidden="true">
      <div
        className="ambient-orb ambient-orb-1"
        style={{ transform: `translateY(${parallax1}px)` }}
      />
      <div
        className="ambient-orb ambient-orb-2"
        style={{ transform: `translateY(${parallax2}px)` }}
      />
      <div
        className="ambient-orb ambient-orb-3"
        style={{ transform: `translateY(${parallax3}px)` }}
      />
    </div>
  )
}
