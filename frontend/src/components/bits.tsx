/* Shared furniture for the v3 light system (docs/12-DESIGN-LIGHT.md).
   Colour NEVER carries meaning alone: every lane badge ships an icon AND
   the word. Confidence is a ring — never a printed number.
   The v2 dossier chrome (sheet marks, stamps, letter-spaced uppercase)
   is deleted; SheetMark survives only as a no-op so nothing breaks. */

import { useEffect, useRef, useState } from 'react'

import type { Lane } from '../api/types'

/* ---------------------------------------------------------- icons */

const svg = (size: number) => ({
  width: size,
  height: size,
  viewBox: '0 0 16 16',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
  focusable: 'false' as const,
})

export function LaneIcon({ lane, size = 14 }: { lane: Lane; size?: number }) {
  const common = svg(size)
  switch (lane) {
    case 'answered':
      return (
        <svg {...common}>
          <path d="M2.6 8.6 L6.3 12.2 L13.4 4.2" />
        </svg>
      )
    case 'asked_back':
      return (
        <svg {...common}>
          <path d="M5.1 5.5a3 3 0 1 1 3.5 3.4v1.4" />
          <path d="M8.6 13.2v.1" />
        </svg>
      )
    case 'held':
      return (
        <svg {...common}>
          <path d="M5.8 3.4v9.2" />
          <path d="M10.2 3.4v9.2" />
        </svg>
      )
    case 'referred':
      return (
        <svg {...common}>
          <path d="M8 3.2 L14 13.4 H2 Z" />
          <path d="M8 6.8v3" />
          <path d="M8 11.6v.1" />
        </svg>
      )
  }
}

/* ------------------------------------------- the four bucket icons (/maya)
   lucide geometry, 24-box, 2px round strokes. One icon per bucket so the
   pastel tint never carries the meaning on its own. */

const lucide = (size: number) => ({
  width: size,
  height: size,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
  focusable: 'false' as const,
})

/* pencil — it wrote her reply */
export function PencilIcon({ size = 22 }: { size?: number }) {
  return (
    <svg {...lucide(size)}>
      <path d="M21.17 6.81a1 1 0 0 0-3.99-3.99L3.84 16.17a2 2 0 0 0-.5.83l-1.32 4.35a.5.5 0 0 0 .62.63l4.36-1.33a2 2 0 0 0 .83-.5z" />
      <path d="m15 5 4 4" />
    </svg>
  )
}

/* speech bubble — it asked them a question */
export function MessageIcon({ size = 22 }: { size?: number }) {
  return (
    <svg {...lucide(size)}>
      <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
    </svg>
  )
}

/* pause — it wasn't sure, so it saved them for her */
export function PauseIcon({ size = 22 }: { size?: number }) {
  return (
    <svg {...lucide(size)}>
      <rect x="14" y="4" width="4" height="16" rx="1" />
      <rect x="6" y="4" width="4" height="16" rx="1" />
    </svg>
  )
}

/* shield — it refused, and said who to ask instead */
export function ShieldIcon({ size = 22 }: { size?: number }) {
  return (
    <svg {...lucide(size)}>
      <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
    </svg>
  )
}

/* play / stop — the voice note player. Filled, not stroked, so the
   control still reads as a button at 14px across a room. */
export function PlayIcon({ size = 16 }: { size?: number }) {
  return (
    <svg {...svg(size)} fill="currentColor" stroke="none">
      <path d="M5.4 3.3a.7.7 0 0 1 1.06-.6l6.1 4.7a.7.7 0 0 1 0 1.2l-6.1 4.7a.7.7 0 0 1-1.06-.6z" />
    </svg>
  )
}

export function StopIcon({ size = 16 }: { size?: number }) {
  return (
    <svg {...svg(size)} fill="currentColor" stroke="none">
      <rect x="4.2" y="4.2" width="7.6" height="7.6" rx="1.6" />
    </svg>
  )
}

/* a microphone — marks a message that was spoken, not typed */
export function MicIcon({ size = 14 }: { size?: number }) {
  return (
    <svg {...svg(size)} strokeWidth={1.6}>
      <rect x="6" y="1.6" width="4" height="8" rx="2" />
      <path d="M3.4 7.2a4.6 4.6 0 0 0 9.2 0" />
      <path d="M8 11.8v2.6" />
    </svg>
  )
}

/* a small waveform — marks a message that arrived as audio */
export function WaveIcon({ size = 16 }: { size?: number }) {
  return (
    <svg {...svg(size)} strokeWidth={1.7}>
      <path d="M2.4 6.6v2.8" />
      <path d="M5.4 4.4v7.2" />
      <path d="M8 2.6v10.8" />
      <path d="M10.6 5.2v5.6" />
      <path d="M13.6 6.9v2.2" />
    </svg>
  )
}

export function DraftIcon({ size = 16 }: { size?: number }) {
  return (
    <svg {...svg(size)}>
      <path d="M11.4 2.7 13.3 4.6 5.4 12.5 2.8 13.2 3.5 10.6 Z" />
      <path d="M2.5 14.6h11" />
    </svg>
  )
}

export function CheckIcon({ size = 16 }: { size?: number }) {
  return (
    <svg {...svg(size)} strokeWidth={2.4}>
      <path d="M2.8 8.5 L6.2 11.9 L13.2 4.4" />
    </svg>
  )
}

export function ArrowIcon({ size = 14 }: { size?: number }) {
  return (
    <svg {...svg(size)}>
      <path d="M3 8h10" />
      <path d="M9 4.2 12.8 8 9 11.8" />
    </svg>
  )
}

export function MinusIcon({ size = 16 }: { size?: number }) {
  return (
    <svg {...svg(size)} strokeWidth={2.4}>
      <path d="M3.4 8h9.2" />
    </svg>
  )
}

/* ---------------------------------------------------------- lanes */

/* Plain English. No jargon on screen, anywhere — no lanes, no triage,
   no gates, no judgments. */
export const LANE_WORD: Record<Lane, string> = {
  answered: 'it wrote her reply',
  asked_back: 'it asked them a question',
  held: 'it wasn’t sure, so it saved them for her',
  referred: 'it refused, and said who to ask instead',
}

export const LANE_MEANING: Record<Lane, string> = {
  answered: 'written the way she would say it',
  asked_back: 'one question back, so the answer fits them',
  held: 'not sure enough to answer for her',
  referred: 'not hers to answer — it says who to ask',
}

/* wash + ink + icon + word. Never colour alone. */
const LANE_BADGE: Record<Lane, string> = {
  answered: 'badge-ok',
  asked_back: 'badge-info',
  held: 'badge-warn',
  referred: 'badge-danger',
}

export function LaneBadge({ lane, size = 13 }: { lane: Lane; size?: number }) {
  return (
    <span className={`badge ${LANE_BADGE[lane]}`}>
      <LaneIcon lane={lane} size={size} />
      <span>{LANE_WORD[lane]}</span>
    </span>
  )
}

/* ---------------------------------------------------------- confidence */

/* Ring fill + thickness. No digits, ever. The accessible name is a word
   band, not a score. */
export function ConfidenceRing({ value, size = 28 }: { value: number; size?: number }) {
  const v = Math.max(0, Math.min(1, value))
  const stroke = 3
  const r = size / 2 - stroke / 2 - 1
  const c = 2 * Math.PI * r
  const band = v >= 0.8 ? 'high' : v >= 0.55 ? 'medium' : 'low'
  return (
    <span className={`conf conf-${band}`} title={`confidence: ${band}`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--hairline-soft)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth={stroke}
          strokeDasharray={`${c * v} ${c}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <span className="sr-only">confidence {band}</span>
    </span>
  )
}

/* ---------------------------------------------------------- footnotes */

export function EvidenceRef({ code }: { code: string }) {
  return <span className="ref">{code}</span>
}

export function Rule() {
  return <hr className="hairline" />
}

/* Deleted by the v3 light system (docs/12-DESIGN-LIGHT.md §4).
   Kept as a no-op so older call sites keep compiling. */
export function SheetMark(_props: { n: string; of?: number }) {
  return null
}

/* ---------------------------------------------------------- motion */

export function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

/* Counts 0 -> target once, then stops. Never loops. Reduced motion lands
   on the final value immediately. */
export function useCountUp(target: number, duration = 1400, run = true) {
  const [value, setValue] = useState(run ? 0 : target)
  const done = useRef(false)

  useEffect(() => {
    if (!run || done.current) return
    if (prefersReducedMotion()) {
      setValue(target)
      done.current = true
      return
    }
    let raf = 0
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      setValue(target * eased)
      if (t < 1) {
        raf = requestAnimationFrame(tick)
      } else {
        done.current = true
      }
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration, run])

  return value
}
