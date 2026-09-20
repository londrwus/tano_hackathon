/* /ask — the public link. One big calm question, generous pastel chips,
   one button.

   Skin is MULTI-SELECT: you can pick dry AND redness, and both are sent.
   That is the measured bug fix, not a nicety — the old screen threw away
   everything after the first one.

   Plain English only. Nothing on this screen says what it is doing
   underneath. */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { postAsk } from '../api/client'
import { CheckIcon } from '../components/bits'
import { setPageMeta } from '../components/meta'
import './ask.css'

type Tint = 'lilac' | 'mint' | 'sky'

const SKIN: { key: string; label: string }[] = [
  { key: 'dry', label: 'Dry' },
  { key: 'oily', label: 'Oily' },
  { key: 'combination', label: 'Combination' },
  { key: 'sensitive', label: 'Sensitive' },
  { key: 'redness', label: 'Redness' },
]
const BUDGETS = [30, 60, 100]
const HOW_MANY: { value: number; label: string }[] = [
  { value: 1, label: 'One' },
  { value: 2, label: 'Two' },
  { value: 4, label: 'A few' },
]

function Chip({
  on,
  tint,
  onClick,
  children,
}: {
  on: boolean
  tint: Tint
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      className={`chip ask-chip ask-chip-${tint}`}
      aria-pressed={on}
      onClick={onClick}
    >
      <span className="ask-chip-tick" aria-hidden="true">
        {on ? <CheckIcon size={16} /> : null}
      </span>
      <span>{children}</span>
    </button>
  )
}

export default function Ask() {
  const navigate = useNavigate()
  const [skin, setSkin] = useState<string[]>([])
  const [budget, setBudget] = useState<number | null>(null)
  const [howMany, setHowMany] = useState<number | null>(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setPageMeta(
      'Ask Maya',
      'Three taps and she tells you what to buy — and what to leave on the shelf.',
    )
  }, [])

  const toggleSkin = (k: string) =>
    setSkin((cur) => (cur.includes(k) ? cur.filter((x) => x !== k) : [...cur, k]))

  const ready = skin.length > 0 && budget !== null && howMany !== null

  const go = async () => {
    if (!ready) return
    setBusy(true)
    const { data } = await postAsk({
      skin,
      budget: budget as number,
      how_many: howMany as number,
      owns: [],
      text: text.trim() ? text.trim() : null,
    })
    setBusy(false)
    navigate(`/c/${data.card_id}`)
  }

  const chosenSkin = SKIN.filter((s) => skin.includes(s.key)).map((s) => s.label.toLowerCase())

  return (
    <div className="ask page">
      <header className="ask-head stagger">
        <h1 className="t-title1 ask-h1">What should I actually buy?</h1>
        <p className="ask-sub">
          Three taps and you get Maya’s answer — the two or three things she would pick, and the
          ones she would tell you to leave on the shelf.
        </p>
      </header>

      <section className="card ask-card stagger after-head">
        <div className="ask-group">
          <h2 className="ask-label">
            Your skin
            <span className="ask-hint">pick as many as you like</span>
          </h2>
          <div className="ask-chips">
            {SKIN.map((s) => (
              <Chip
                key={s.key}
                tint="lilac"
                on={skin.includes(s.key)}
                onClick={() => toggleSkin(s.key)}
              >
                {s.label}
              </Chip>
            ))}
          </div>
          {/* Empty means EMPTY — not a non-breaking space. A space is still a
              text node, so the element stopped matching :empty and held a
              blank line open above the next question whatever was selected. */}
          <p className="ask-multi" aria-live="polite">
            {chosenSkin.length > 1
              ? `${chosenSkin.join(' and ')} — she answers for both, not just the first one.`
              : null}
          </p>
        </div>

        <div className="ask-group">
          <h2 className="ask-label">What you want to spend</h2>
          <div className="ask-chips">
            {BUDGETS.map((b) => (
              <Chip key={b} tint="mint" on={budget === b} onClick={() => setBudget(b)}>
                £{b}
              </Chip>
            ))}
          </div>
        </div>

        <div className="ask-group">
          <h2 className="ask-label">How many things</h2>
          <div className="ask-chips">
            {HOW_MANY.map((h) => (
              <Chip
                key={h.value}
                tint="sky"
                on={howMany === h.value}
                onClick={() => setHowMany(h.value)}
              >
                {h.label}
              </Chip>
            ))}
          </div>
        </div>

        <div className="ask-submit">
          <button
            type="button"
            className="btn btn-primary ask-go"
            disabled={!ready || busy}
            onClick={go}
          >
            {busy ? 'Working it out…' : 'Get her answer'}
          </button>
          <p className="ask-foot">No account. No email. Nothing to fill in.</p>
        </div>
      </section>

      <details className="ask-fallback enter delay-4">
        <summary>Rather just say it in your own words?</summary>
        <label className="sr-only" htmlFor="ask-text">
          Say it in your own words
        </label>
        <textarea
          id="ask-text"
          rows={3}
          placeholder="i have dry skin and redness and about £60. what should i get?"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <p className="ask-fallback-note">
          She reads it the same way she reads a message — then still pick your skin and what you
          want to spend above.
        </p>
      </details>
    </div>
  )
}
