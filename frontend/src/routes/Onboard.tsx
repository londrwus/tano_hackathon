/* /onboard — the approved v7f screen (design/v7f/P5zMC.png).

   One idea: she never filled in a form. It read what she had already
   posted and worked out how she decides.

   Everything on this screen is read from GET /api/standard — the quotes
   are her own captions (source_caption), the conclusions are the
   sentences the API renders (statement), and the agree / disagree counts
   are counted off the payload. Nothing here is a constant.

   Plain English only: no slots, no extraction, no confidence gates. */

import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { getCase, getOnboard, getStandard, postStandardOverride } from '../api/client'
import type {
  CasePayload,
  OnboardPayload,
  QueuePayload,
  StandardPayload,
  StandardSlot,
} from '../api/types'
import { ArrowIcon, CheckIcon } from '../components/bits'
import { setPageMeta } from '../components/meta'
import { OVERRIDE_KEY } from './queueOverride'
import './onboard.css'

/* The API may or may not ship a rendered sentence per line. When it does
   we print it. When it does not we build one out of the label and the
   level it gave us. Either way the words come from the payload. */
interface SlotWithSentence extends StandardSlot {
  statement?: string
  /* Not in the frozen contract — the engine only sends this for a slot it
     knows is shaky across repeats. Read it if it is there; a slot that
     never carries it is treated as stable. */
  stability?: number
}

type Tint = 'lilac' | 'mint' | 'peach' | 'blush'

/* Spelled out, so the sentence reads like a person wrote it and the
   number still comes off the payload. Falls back to digits. */
const WORDS = [
  'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
  'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
  'seventeen', 'eighteen', 'nineteen', 'twenty',
]
function inWords(n: number): string {
  return n >= 0 && n < WORDS.length ? WORDS[n] : String(n)
}

/* Typography only: the payload writes its arrows as "->". Print a real
   one. The words themselves are never changed. */
const prose = (t: string) => t.replace(/\s->\s/g, ' → ')

/* Levels arrive as machine-ish strings now and then (YES, crowded_routine_only).
   Read them out as English. Never invent a value — only tidy the one given. */
function readable(level: string): string {
  const t = prose(level.trim().replace(/_/g, ' '))
  if (/^yes$/i.test(t)) return 'yes'
  if (/^no$/i.test(t)) return 'no'
  if (t === t.toUpperCase() && t.length <= 5) return t.toLowerCase()
  return t
}

/* The payload writes Maya's own sentences in third-person-plural now and
   then ("their judgement", "they agreed") — a leftover of how the slot was
   extracted. She is one named woman, not a committee, so on her side of the
   screen we read it back as "her" / "she". This never touches the doctor's
   side, or the payload itself — display only. */
function herVoice(text: string): string {
  return text
    .replace(/\btheir\b/g, 'her')
    .replace(/\bTheir\b/g, 'Her')
    .replace(/\bthey\b/g, 'she')
    .replace(/\bThey\b/g, 'She')
}

function sentenceFor(s: SlotWithSentence): string {
  if (s.statement && s.statement.trim()) return herVoice(prose(s.statement.trim()))
  return herVoice(`${s.label}: ${readable(s.maya.level)}.`)
}

/* skippable_category flipped between "makeup" and "serum" across five
   identical extraction runs (stability 0.60) — see docs/11-honest-headline.md
   §5.8. The project rule (docs/09-GO.md §2, docs/12-DESIGN-LIGHT.md) is that
   it appears nowhere on any screen. Suppress by the payload's own stability
   signal where one is sent, and hard-exclude the key by name so it cannot
   come back if that signal is absent. */
const UNSTABLE_KEYS = new Set(['skippable_category'])
const STABILITY_FLOOR = 0.9
function isShowable(s: SlotWithSentence): boolean {
  if (UNSTABLE_KEYS.has(s.key)) return false
  if (typeof s.stability === 'number' && s.stability < STABILITY_FLOOR) return false
  return true
}

/* The four lines the screen leads on. We prefer these four ideas when the
   payload has them, then top up with whatever else it sent — always
   skipping a caption we have already quoted, so no quote appears twice. */
const LEAD_KEYS = ['routine_size', 'defended_category', 'price_refusal', 'subtraction']
const TINTS: Tint[] = ['lilac', 'mint', 'peach', 'blush']

function leadRows(slots: SlotWithSentence[]): SlotWithSentence[] {
  const picked: SlotWithSentence[] = []
  const seen = new Set<string>()
  const take = (s?: SlotWithSentence) => {
    if (!s || picked.length >= 4) return
    const cap = (s.source_caption ?? '').trim()
    if (!cap || seen.has(cap)) return
    seen.add(cap)
    picked.push(s)
  }
  LEAD_KEYS.forEach((k) => take(slots.find((s) => s.key === k)))
  slots.forEach((s) => take(s))
  return picked
}

/* Plain-English versions of the questions both of them were asked. The
   answers on either side are always the payload's own words. A question
   we do not have a phrasing for falls back to the payload's label. */
const QUESTION: Record<string, string> = {
  routine_size: 'How many products?',
  price_refusal: 'Does price matter?',
  budget_behaviour: 'Spend the whole budget?',
  subtraction: 'Add something, or take something away?',
  subtraction_scope: 'Who gets told to buy less?',
  hype: 'What about the thing everyone is posting?',
  defended_category: 'What never gets left out?',
  interchangeable_category: 'What can be any brand?',
  starting_from_zero: 'Starting with nothing?',
  route_reacting: 'Skin reacting to everything?',
  route_redness: 'Red, angry skin?',
  route_dry: 'Dry, tight skin?',
  route_oily: 'Oily, shiny skin?',
}
function questionFor(s: StandardSlot): string {
  const q = QUESTION[s.key]
  if (q) return q
  const l = s.label.trim()
  return /[?]$/.test(l) ? l : `${l}?`
}

/* The three skin types we hold it to. Her own answer comes from the
   payload — first from the question it was asked, and if this copy of the
   API does not carry that question, from her own shelf. */
const MARKED: { word: string; slotKey: string; shelf: RegExp }[] = [
  { word: 'Dry skin', slotKey: 'route_dry', shelf: /dry/i },
  { word: 'Oily skin', slotKey: 'route_oily', shelf: /oily|combo/i },
  { word: 'Red, angry skin', slotKey: 'route_redness', shelf: /sensitive/i },
]

export default function Onboard() {
  const [handle, setHandle] = useState('@mayarao')
  const [submitted, setSubmitted] = useState('@mayarao')
  const [onboard, setOnboard] = useState<OnboardPayload | null>(null)
  const [standard, setStandard] = useState<StandardPayload | null>(null)
  const [shelf, setShelf] = useState<CasePayload['shelf']>([])
  const [off, setOff] = useState<Record<string, boolean>>({})
  const [reranked, setReranked] = useState<QueuePayload | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setPageMeta(
      'Maya never filled in a form',
      'It read the things she has already posted, and worked out how she makes decisions.',
    )
  }, [])

  useEffect(() => {
    let alive = true
    setOnboard(null)
    getOnboard(submitted).then(({ data }) => alive && setOnboard(data))
    return () => {
      alive = false
    }
  }, [submitted])

  useEffect(() => {
    getStandard().then(({ data }) => setStandard(data))
    getCase()
      .then(({ data }) => setShelf(data.shelf ?? []))
      .catch(() => setShelf([]))
  }, [])

  const slots = useMemo<SlotWithSentence[]>(
    () => (standard?.slots ?? []) as SlotWithSentence[],
    [standard],
  )

  const rows = useMemo(() => leadRows(slots), [slots])

  /* Every question actually shown on this screen — the unstable slot is
     dropped before either the list or the counts are built, so the two
     always describe the same rows. */
  const comparable = useMemo(() => slots.filter(isShowable), [slots])
  const disagreements = useMemo(() => comparable.filter((s) => !s.agrees), [comparable])
  const agreeCount = useMemo(
    () => comparable.filter((s) => s.agrees).length,
    [comparable],
  )
  const disagreeCount = disagreements.length

  const marked = useMemo(
    () =>
      MARKED.map((m) => {
        const slot = slots.find((s) => s.key === m.slotKey)
        const fromShelf = shelf.find((p) => m.shelf.test(p.skin))
        const product = slot ? readable(slot.maya.level) : fromShelf?.product ?? null
        return { word: m.word, product }
      }),
    [slots, shelf],
  )
  const markedHit = marked.filter((m) => m.product).length

  const dermValue = useMemo(() => {
    const m: Record<string, number> = {}
    slots.forEach((s) => {
      m[s.key] = s.derm.value
    })
    return m
  }, [slots])

  const flip = async (slotKey: string) => {
    const nextOff = { ...off, [slotKey]: !off[slotKey] }
    if (!nextOff[slotKey]) delete nextOff[slotKey]
    setOff(nextOff)
    const overrides: Record<string, number> = {}
    Object.keys(nextOff).forEach((k) => {
      overrides[k] = dermValue[k] ?? 0
    })
    setBusy(true)
    const { data } = await postStandardOverride(overrides)
    setBusy(false)
    setReranked(Object.keys(overrides).length ? data : null)
    try {
      if (Object.keys(overrides).length === 0) {
        sessionStorage.removeItem(OVERRIDE_KEY)
      } else {
        sessionStorage.setItem(OVERRIDE_KEY, JSON.stringify(data))
      }
    } catch {
      /* private mode — the night just will not carry the change across */
    }
  }

  return (
    <div className="onboard page">
      {/* ---------- the headline ---------- */}
      {/* The headline leads. The paste bar is a utility and follows it —
          when it came first the eye landed on an input box and the claim
          this page is making came second. */}
      <header className="ob-head stagger">
        <h1 className="t-title1 ob-h1">Maya never filled in a form.</h1>
        <p className="ob-sub">
          It read the things she has already posted, and worked out how she makes decisions.
        </p>
      </header>

      {/* ---------- small and calm: paste a handle ---------- */}
      <form
        className="ob-paste enter delay-2"
        onSubmit={(e) => {
          e.preventDefault()
          setSubmitted(handle.trim() || '@mayarao')
        }}
      >
        <label className="ob-paste-label" htmlFor="ob-handle">
          Paste a creator’s link
        </label>
        <input
          id="ob-handle"
          className="ob-input"
          value={handle}
          onChange={(e) => setHandle(e.target.value)}
          placeholder="@mayarao"
        />
        <button type="submit" className="btn btn-secondary ob-paste-go">
          Read her posts
        </button>
        {onboard && (
          <span className="ob-paste-note">
            {onboard.handle} · nothing signed up for, nothing filled in
          </span>
        )}
      </form>

      {/* ---------- what she wrote → what it worked out ---------- */}
      <section className="card ob-heard enter delay-3" aria-labelledby="ob-heard-h">
        <h2 className="sr-only" id="ob-heard-h">
          What she wrote, and what it worked out
        </h2>
        <div className="ob-cols">
          <div className="ob-col-head">What she wrote</div>
          <div className="ob-col-head ob-col-head-right">What it worked out</div>
        </div>

        {!standard ? (
          <p className="ob-loading">Reading her posts…</p>
        ) : (
          <ul className="ob-pairs">
            {rows.map((s, i) => (
              <li className="ob-pair" key={s.key}>
                <p className={`ob-quote tile tile-${TINTS[i % TINTS.length]}`}>
                  “{s.source_caption}”
                </p>
                <p className="ob-worked">
                  <span className="ob-arrow" aria-hidden="true">
                    <ArrowIcon size={18} />
                  </span>
                  <span className="ob-worked-text">{sentenceFor(s)}</span>
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ---------- the doctor, and the marking ---------- */}
      <div className="ob-two stagger">
        <section className="card ob-derm">
          <h2 className="t-title2 ob-card-h">We asked a skin doctor the same questions.</h2>
          {!standard ? (
            <p className="ob-loading">Asking…</p>
          ) : (
            <>
              <p className="ob-card-sub">
                They agreed with Maya on {inWords(agreeCount)} of them. On{' '}
                {inWords(disagreeCount)}, they want different things — and that difference is the
                whole point of asking her and not a doctor.
              </p>
              <ul className="ob-diffs">
                {disagreements.map((s) => (
                  <li className="ob-diff" key={s.key}>
                    <span className="ob-diff-q">{questionFor(s)}</span>
                    <span className="ob-diff-maya">Maya: {herVoice(readable(s.maya.level))}</span>
                    <span className="ob-diff-derm">Doctor: {readable(s.derm.level)}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <section className="tile tile-mint ob-marked">
          <div className="ob-marked-head">
            <h2 className="t-title2 ob-card-h">Then we marked it</h2>
            <span className="ob-pill">
              <CheckIcon size={14} />
              <span className="num">
                {markedHit} out of {marked.length}
              </span>
            </span>
          </div>
          <p className="ob-card-sub ob-card-sub-mint">
            Maya has her own notes on what she reaches for. We never showed them to it. Then we
            compared.
          </p>
          <ul className="ob-marks">
            {marked.map((m) => (
              <li className="ob-mark" key={m.word}>
                <span className="ob-mark-word">{m.word}</span>
                <span className="ob-mark-product">{m.product ?? 'no note of her own'}</span>
                <span className={`ob-mark-tick${m.product ? '' : ' is-miss'}`}>
                  {m.product ? (
                    <>
                      <CheckIcon size={16} />
                      <span className="sr-only">same as her own note</span>
                    </>
                  ) : (
                    <span className="sr-only">no note of her own to compare</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      {/* ---------- below the fold: she corrects it ---------- */}
      <section className="card ob-fix enter delay-4" aria-labelledby="ob-fix-h">
        <h2 className="t-title3 ob-fix-h" id="ob-fix-h">
          Not her? Turn one off.
        </h2>
        <p className="ob-card-sub">
          She writes none of this. She only tells it when it has her wrong — and last night gets
          worked out again, in front of her.
        </p>

        {!onboard ? (
          <p className="ob-loading">Reading her posts…</p>
        ) : (
          <ul className="ob-rules">
            {onboard.heard.map((h) => {
              const isOff = !!off[h.slot_key]
              return (
                <li key={h.slot_key} className={`ob-rule${isOff ? ' is-off' : ''}`}>
                  <span className="ob-rule-text">{herVoice(prose(h.trait))}</span>
                  <button
                    type="button"
                    className="ob-switch"
                    role="switch"
                    aria-checked={!isOff}
                    aria-label={`${h.trait} — ${isOff ? 'not her' : 'that is her'}`}
                    disabled={busy}
                    onClick={() => flip(h.slot_key)}
                  >
                    <span className="ob-switch-word">{isOff ? 'not her' : 'that is her'}</span>
                    <span className="ob-switch-track" aria-hidden="true">
                      <span className="ob-switch-knob" />
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}

        {reranked && (
          <div className="tile tile-peach ob-rerank" aria-live="polite">
            <h3 className="t-title3 ink-peach ob-rerank-h">Last night just came out different.</h3>
            <p className="ob-rerank-sub">{reranked.stats.header_line}</p>
            <Link className="btn btn-primary ob-rerank-go" to="/maya">
              See last night again
            </Link>
          </div>
        )}
      </section>
    </div>
  )
}
