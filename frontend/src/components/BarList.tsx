export interface Bar {
  label: string
  value: number
  /** Nome de uma cor do tema (ex.: "critical"), usado como classe CSS. */
  tone?: string
}

/** Barras horizontais proporcionais ao maior valor. CSS puro, sem biblioteca de gráficos. */
export function BarList({ bars }: { bars: Bar[] }) {
  const max = Math.max(1, ...bars.map((bar) => bar.value))
  return (
    <ul className="bars">
      {bars.map((bar) => (
        <li key={bar.label}>
          <span className="bars__label">{bar.label}</span>
          <span className="bars__track">
            <span
              className={`bars__fill bars__fill--${bar.tone ?? 'neutral'}`}
              style={{ width: `${(bar.value / max) * 100}%` }}
            />
          </span>
          <span className="bars__value">{bar.value}</span>
        </li>
      ))}
    </ul>
  )
}
