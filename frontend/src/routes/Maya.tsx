/* /maya — last night's inbox.

   Fifty-four people messaged her while she was asleep. This is the list,
   the way an inbox is a list: one row per person, densest thing on the
   site, scannable in one pass. Anyone who has used Gmail can read it
   without being told how.

   Every number comes from GET /api/queue. Nothing is a constant.
   It never sends. It drafts.

   Two words carry the screen:
     clarify   — she needs to look at this one
     automatic — the reply is ready to send as written
   They are LABELS, not actions. Nothing is sent, nothing changes lane, the
   safety behaviour is untouched: a referred row is marked automatic because
   "ask a pharmacist" is the safest reply on the page, not because a human
   was skipped — and it still shows the refusal and who it was passed on to. */

import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { getCase, getQueue, postQueueAction } from '../api/client'
import type { Lane, QueueCard, QueuePayload, VoiceNote } from '../api/types'
import { MicIcon, PlayIcon, StopIcon } from '../components/bits'
import { setPageMeta } from '../components/meta'
import { OVERRIDE_KEY } from './queueOverride'
import './maya.css'

type Tint = 'mint' | 'sky' | 'butter' | 'blush'

const TINT_OF: Record<Lane, Tint> = {
  answered: 'mint',
  asked_back: 'sky',
  held: 'butter',
  referred: 'blush',
}

/* Plain English only. No lanes, no triage, no gates, no judgments. */
const LANE_TAB: { lane: Lane; label: string }[] = [
  { lane: 'answered', label: 'Wrote her reply' },
  { lane: 'asked_back', label: 'Asked a question' },
  { lane: 'held', label: 'Saved for her' },
  { lane: 'referred', label: 'Said who to ask' },
]

type ActionState = { kind: 'sent' | 'held' | 'corrected' | 'marked'; note: string }

/* ------------------------------------------------------------ the advice
   Two words, and only two. `held` is the one that waits for her. */
type Advice = 'automatic' | 'clarify'
const adviceOf = (lane: Lane): Advice => (lane === 'held' ? 'clarify' : 'automatic')

/* --------------------------------------------------------- how sure it was
   Words and a short bar. The raw number is never printed — not as a
   percentage, not as a decimal. The three bands are stated once, in the
   toolbar. Cut where the real payload clusters: everything it acted on
   sits at 0.88+, the questions it asked back run 0.68–1.0, and the ones it
   saved for her sit at 0.34–0.55. */
const SURE_BANDS: { min: number; word: string; level: 1 | 2 | 3 }[] = [
  { min: 0.85, word: 'Very sure', level: 3 },
  { min: 0.6, word: 'Fairly sure', level: 2 },
  { min: 0, word: 'Not sure', level: 1 },
]
const bandOf = (v: number) => SURE_BANDS.find((b) => v >= b.min) ?? SURE_BANDS[SURE_BANDS.length - 1]
function sureWord(v: number): string {
  return bandOf(v).word
}

/* Three little bars, one two or three of them lit. It has to be findable
   down a column of fifty-four rows without reading a word of it. */
function Segs({ level }: { level: 1 | 2 | 3 }) {
  return (
    <span className="segs" aria-hidden="true">
      <span className={`seg${level >= 1 ? ' seg-on' : ''}`} />
      <span className={`seg${level >= 2 ? ' seg-on' : ''}`} />
      <span className={`seg${level >= 3 ? ' seg-on' : ''}`} />
    </span>
  )
}

/* There is no time column. /api/queue has no timestamps on a card, so any
   clock on a row would be a number we made up sitting on the hero screen.
   The right-hand column carries the evidence ref the payload already has
   instead: real, and citable. */

/* Spelled-out hours, so the sentence reads like a person wrote it and the
   number still comes from the API. Falls back to digits for odd values. */
const TENS = ['', 'ten', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
function inWords(n: number): string {
  return n >= 10 && n < 100 && n % 10 === 0 ? TENS[n / 10] : String(n)
}

/* Some payloads give "a pharmacist or your GP" (a person to ask), others
   give "Ask your midwife or GP before changing anything." (a whole
   instruction). Read it as a sentence in both cases, never "ask Ask". */
function isSentence(s: string): boolean {
  return /[.!?]$/.test(s.trim()) || s.trim().split(/\s+/).length > 5
}
function insteadPhrase(referTo: string): string {
  const t = referTo.trim()
  return isSentence(t) ? t : `Ask ${t}.`
}

/* The reason it stopped, said the way she would say it. The payload signs
   every one of these off with "Maya decides." — true, and already the
   headline of the section, so the row drops it and the open card keeps it. */
function shortWhy(reason: string): string {
  return reason
    .split(/(?<=\.)\s+/)
    .filter((s) => !/^\s*(maya|she)\s+decides\.?\s*$/i.test(s))
    .join(' ')
    .trim()
}

/* Why it stopped, in her register, when the payload has given the same
   sentence to several rows at once. Keyed on what is actually missing from
   the message, so four rows do not read as one template. The payload's own
   wording still shows in full inside the opened row — this only replaces a
   line that would otherwise repeat verbatim down the list. */
function variantWhy(c: QueueCard, fallback: string): string {
  const t = c.text.toLowerCase()
  if (/trust/.test(t)) return 'They want Maya, not an answer.'
  if (/your money|what would you do|if it was you/.test(t)) return 'They want her call, not a product.'
  if (/photo|picture|pic of/.test(t)) return 'She would have to look at it herself.'
  if (/collab|my brand|gifting|\bpr\b/.test(t)) return 'Business. She answers her own brand mail.'
  if (/got the|already have|i have|bought|last month|last week/.test(t))
    return 'Depends what they already own.'
  const budget = /£|\bquid\b|budget|\b\d{2,}\b/.test(t)
  const skin = /dry|oily|combination|sensitive|redness|\bred\b|acne|eczema|texture|dull|spots/.test(t)
  if (!budget && !skin) return 'Nothing to go on. No skin type, no budget.'
  if (!skin) return 'No skin type. She would be guessing.'
  if (!budget) return 'No budget. She would be guessing.'
  return fallback
}

/* The grey continuation after the message, the way an inbox puts a preview
   after a subject. Usually the drafted reply. A refused row shows who it
   was passed on to instead — every one of those drafts opens with the same
   forty characters, so the truncated line would say nothing. */
function previewOf(c: QueueCard, why: string | undefined): string {
  if (c.lane === 'held') return why ?? c.draft_reply
  if (c.lane === 'referred' && c.refusal) return insteadPhrase(c.refusal.refer_to)
  return c.draft_reply
}

/* ------------------------------------------------------------ voice notes
   Four of last night's messages arrived as audio (contract §17). Nothing in
   the pipeline read that: whisper wrote the words down, Jev was handed the
   same `message` field a typed DM fills, and the card that came back is the
   same card. So a voice note is an ordinary row that happens to be playable.

   Provenance is deliberately not printed. The rest of the inbox is equally
   fictional and carries no label. It stays on the wire — `voice.synthetic`,
   `voice.tts_model`, `voice.disclosure`, the `X-Synthetic-Audio` header, the
   ID3 tags inside each mp3 and data/voice-notes.json. Do not delete it from
   any of those. */

/* One player at a time on the page. A module handle rather than state, so
   the pause lands in the same tick the next one starts. */
let nowPlaying: HTMLAudioElement | null = null

function mmss(seconds: number): string {
  const total = Math.max(0, Math.round(seconds || 0))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

/* The player, inside the opened row. If the mp3 is missing it takes itself
   off the screen and the row reads as it always did — the transcript is
   the message. */
function VoicePlayer({ voice, from }: { voice: VoiceNote; from: string }) {
  const ref = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState(false)
  const [broken, setBroken] = useState(false)

  useEffect(() => {
    const el = ref.current
    return () => {
      if (el && nowPlaying === el) {
        el.pause()
        nowPlaying = null
      }
    }
  }, [])

  const toggle = () => {
    const el = ref.current
    if (!el) return
    if (playing) {
      el.pause()
      return
    }
    if (nowPlaying && nowPlaying !== el) nowPlaying.pause()
    nowPlaying = el
    el.currentTime = 0
    void el.play().catch(() => {
      setPlaying(false)
      setBroken(true)
    })
  }

  const length = mmss(voice.seconds)

  return (
    <div className="player">
      {!broken && (
        <button
          type="button"
          className={`voice-play${playing ? ' voice-playing' : ''}`}
          onClick={toggle}
          aria-label={
            playing
              ? `Stop the voice note from ${from}`
              : `Play the voice note from ${from}, ${length}`
          }
        >
          {playing ? <StopIcon size={15} /> : <PlayIcon size={15} />}
        </button>
      )}
      <span className="player-meta">
        <MicIcon size={15} />
        voice note · <span className="num">{length}</span>
      </span>
      <audio
        ref={ref}
        src={voice.audio_url || `/api/voice/${voice.file}`}
        preload="metadata"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onError={() => {
          setPlaying(false)
          setBroken(true)
        }}
      />
    </div>
  )
}

/* ------------------------------------------------------------------- row */
interface RowProps {
  card: QueueCard
  why?: string
  isOpen: boolean
  onToggle: () => void
  picked: boolean
  onPick: (on: boolean) => void
  state?: ActionState
  editing: boolean
  draft: string
  onDraft: (text: string) => void
  onEdit: () => void
  onCancel: () => void
  act: (action: 'send' | 'edit' | 'hold') => void
}

function Row({
  card: c,
  why,
  isOpen,
  onToggle,
  picked,
  onPick,
  state,
  editing,
  draft,
  onDraft,
  onEdit,
  onCancel,
  act,
}: RowProps) {
  const tint = TINT_OF[c.lane]
  const advice = adviceOf(c.lane)
  const voice = c.source === 'voice' ? c.voice ?? null : null

  return (
    <div
      className={`row row-${advice}${isOpen ? ' row-open' : ''}${picked ? ' row-picked' : ''}${
        state ? ' row-done' : ''
      }`}
    >
      <div className="row-line">
        <label className="row-checkwrap">
          <input
            type="checkbox"
            className="row-check"
            checked={picked}
            onChange={(e) => onPick(e.target.checked)}
          />
          <span className="sr-only">Select the message from {c.from}</span>
        </label>

        <button type="button" className="row-main" aria-expanded={isOpen} onClick={onToggle}>
          <span className="row-from">{c.from}</span>

          {/* one line: what they said in bold, then what it drafted, grey,
              running off the end. The two tones are what make it scan. */}
          <span className="row-msg">
            {state ? (
              <span className={`advice advice-done advice-${state.kind}`}>
                {state.kind === 'sent'
                  ? 'approved'
                  : state.kind === 'marked'
                    ? 'ready'
                    : state.kind === 'held'
                      ? 'held'
                      : 'rewritten'}
              </span>
            ) : (
              advice === 'clarify' && <span className="advice advice-clarify">clarify</span>
            )}
            {voice && (
              <span className="row-mic">
                <MicIcon size={13} />
                <span className="num">{mmss(voice.seconds)}</span>
              </span>
            )}
            <span className="row-text">{c.text}</span>
            <span className="row-preview"> - {previewOf(c, why)}</span>
          </span>

          {/* A refusal gets no sureness reading. "Very sure" next to a
              question about eczema medication reads as very sure about the
              medication, which is the opposite of what it means. */}
          {c.lane === 'referred' ? (
            <span className="row-sure row-passed ink-blush">passed on</span>
          ) : (
            <span className={`row-sure ink-${tint}`}>
              <Segs level={bandOf(c.confidence).level} />
              <span className="row-sure-word">{sureWord(c.confidence)}</span>
            </span>
          )}
          <span className="row-ref">{c.ref}</span>
        </button>
      </div>

      {isOpen && (
        <div className="row-detail">
          {voice && <VoicePlayer voice={voice} from={c.from} />}

          <div className="msg-block msg-said">
            <div className="msg-label">
              {voice ? 'Transcript. They spoke this, they did not type it' : 'What they said'}
            </div>
            <p className="msg-quote">“{c.text}”</p>
          </div>

          {c.refusal && (
            <div className="msg-block msg-refuse">
              <div className="msg-label">Why it would not answer</div>
              <p>{c.refusal.why}</p>
              <p className="msg-instead">{insteadPhrase(c.refusal.refer_to)}</p>
            </div>
          )}

          {c.hold_reason && (
            <div className="msg-block msg-hold">
              <div className="msg-label">Why it stopped</div>
              <p>{c.hold_reason}</p>
            </div>
          )}

          {editing ? (
            <div className="msg-block msg-edit">
              <label className="msg-label" htmlFor={`edit-${c.id}`}>
                Rewrite it the way she would say it
              </label>
              <textarea
                id={`edit-${c.id}`}
                rows={3}
                value={draft}
                onChange={(e) => onDraft(e.target.value)}
              />
              <div className="msg-actions">
                <button type="button" className="btn btn-primary" onClick={() => act('edit')}>
                  Save
                </button>
                <button type="button" className="btn btn-secondary" onClick={onCancel}>
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className={`msg-block msg-draft msg-draft-${tint}`}>
              <div className="msg-label">
                {c.lane === 'asked_back'
                  ? 'The question it wrote back'
                  : c.lane === 'held'
                    ? 'What it had so far'
                    : 'The reply it wrote'}
              </div>
              <p className="msg-reply">{draft}</p>
              {c.basket_summary && <p className="msg-basket">{c.basket_summary}</p>}
            </div>
          )}

          {/* how sure it was: the words again, and a bar. Never a number.
              Not on a refusal, for the same reason the row does not. */}
          {c.lane !== 'referred' && (
            <div className={`sure-row ink-${tint}`}>
              <span className="msg-label">How sure it was</span>
              <Segs level={bandOf(c.confidence).level} />
              <span className="sure-word">{sureWord(c.confidence)}</span>
              <span className="meter meter-on-white">
                <span
                  className="meter-fill"
                  style={{ width: `${Math.round(Math.max(0.04, Math.min(1, c.confidence)) * 100)}%` }}
                />
              </span>
            </div>
          )}

          {state ? (
            <p className={`acted acted-${state.kind}`}>{state.note}</p>
          ) : (
            !editing && (
              <div className="msg-actions">
                <button type="button" className="btn btn-primary" onClick={() => act('send')}>
                  Send
                </button>
                <button type="button" className="btn btn-secondary" onClick={onEdit}>
                  Edit
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => act('hold')}>
                  Hold
                </button>
              </div>
            )
          )}

          {c.card_id && (
            <Link className="msg-link" to={`/c/${c.card_id}`}>
              See what she would buy them →
            </Link>
          )}
        </div>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ page */
type Tab = 'all' | 'clarify' | 'automatic' | Lane

export default function Maya() {
  const [payload, setPayload] = useState<QueuePayload | null>(null)
  const [name, setName] = useState('Maya')
  const [hours, setHours] = useState<number | null>(null)
  const [tab, setTab] = useState<Tab>('all')
  const [open, setOpen] = useState<string | null>(null)
  const [picked, setPicked] = useState<Record<string, boolean>>({})
  const [acted, setActed] = useState<Record<string, ActionState>>({})
  const [editing, setEditing] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [fromOverride, setFromOverride] = useState(false)

  useEffect(() => {
    setPageMeta(
      'Last night, 50 people messaged Maya — what happened to all of them',
      'One row is one person. It wrote her replies, asked questions back, saved the unsure ones for her, and refused the ones that were not hers to answer. It never sends. She does.',
    )

    /* If she flipped one of her own rules on /onboard, that recomputed
       queue wins over a fresh fetch. */
    let cached: QueuePayload | null = null
    try {
      const raw = sessionStorage.getItem(OVERRIDE_KEY)
      if (raw) cached = JSON.parse(raw) as QueuePayload
    } catch {
      cached = null
    }

    const queue = cached ? Promise.resolve(cached) : getQueue().then(({ data }) => data)
    if (cached) {
      console.info('[queue] rendering the queue recomputed under her own corrections')
      setFromOverride(true)
    }

    const who = getCase()
      .then(({ data }) => data.creator)
      .catch(() => null)

    Promise.all([queue, who]).then(([q, creator]) => {
      if (creator?.name) setName(creator.name.split(' ')[0])
      if (creator?.reply_hours_per_month) setHours(creator.reply_hours_per_month)
      setPayload(q)
    })
  }, [])

  /* Her work first: everything marked clarify, then everything already
     written. Newest first inside each, the way an inbox reads. */
  const { whyFor, shown, clarifyCount, autoCount } = useMemo(() => {
    const cards = payload?.cards ?? []

    /* Where the payload has already given a row its own reason, print it.
       Where it has handed the same sentence to four rows, say what is
       actually missing from each one instead. */
    const held = cards.filter((c) => c.lane === 'held' && c.hold_reason)
    const seen: Record<string, number> = {}
    held.forEach((c) => {
      const k = shortWhy(c.hold_reason as string)
      seen[k] = (seen[k] ?? 0) + 1
    })
    const whyFor: Record<string, string> = {}
    held.forEach((c) => {
      const k = shortWhy(c.hold_reason as string)
      whyFor[c.id] = seen[k] > 1 ? variantWhy(c, k) : k
    })
    const keep = cards.filter((c) => {
      if (tab === 'all') return true
      if (tab === 'clarify' || tab === 'automatic') return adviceOf(c.lane) === tab
      return c.lane === tab
    })
    return {
      whyFor,
      /* Her work first, then everything already written, each in the order
         the queue returned it. No re-sorting: there is nothing real to sort
         a night of messages by. */
      shown: [
        ...keep.filter((c) => adviceOf(c.lane) === 'clarify'),
        ...keep.filter((c) => adviceOf(c.lane) === 'automatic'),
      ],
      clarifyCount: cards.filter((c) => adviceOf(c.lane) === 'clarify').length,
      autoCount: cards.filter((c) => adviceOf(c.lane) === 'automatic').length,
    }
  }, [payload, tab])

  const act = async (card: QueueCard, action: 'send' | 'edit' | 'hold') => {
    const text = action === 'edit' ? drafts[card.id] ?? card.draft_reply : undefined
    const { data } = await postQueueAction(card.id, action, text)
    if (data.standard_moved) console.info(`[standard] ${data.standard_moved}`)
    setEditing(null)
    setActed((cur) => ({
      ...cur,
      [card.id]:
        action === 'edit'
          ? {
              /* The API returns the delta (e.g. "price_refusal +0.1"). We log
                 it and never print it — no scores on screen. */
              kind: 'corrected',
              note: 'correction written. Her standard moved.',
            }
          : action === 'send'
            ? { kind: 'sent', note: 'approved. Waiting for her to press send.' }
            : { kind: 'held', note: `saved for ${name}` },
    }))
  }

  if (!payload) {
    return (
      <div className="maya page">
        <p className="loading-note">Reading last night’s messages…</p>
      </div>
    )
  }

  const s = payload.stats
  const laneCount = (lane: Lane): number =>
    lane === 'answered'
      ? s.answered
      : lane === 'asked_back'
        ? s.asked_back
        : lane === 'held'
          ? s.held
          : s.referred

  const pickedIds = shown.filter((c) => picked[c.id]).map((c) => c.id)
  const allPicked = shown.length > 0 && pickedIds.length === shown.length

  /* Approve in bulk. Local on purpose: fifty round trips to write the same
     word fifty times would be a worse version of the same thing. Because it
     is local it does NOT wear the word a single approved row wears — that
     one went to the API, these were only marked here. */
  const approveAutomatic = () => {
    const target = (pickedIds.length ? shown.filter((c) => picked[c.id]) : shown).filter(
      (c) => adviceOf(c.lane) === 'automatic' && !acted[c.id],
    )
    if (!target.length) return
    console.info(
      `[queue] marked ${target.length} drafts ready in the UI only. Nothing was sent and nothing was posted`,
    )
    setActed((cur) => {
      const next = { ...cur }
      target.forEach((c) => {
        next[c.id] = {
          kind: 'marked',
          note: 'marked ready in this list. She still presses send.',
        }
      })
      return next
    })
    setPicked({})
  }

  const rowProps = (c: QueueCard) => ({
    card: c,
    why: whyFor[c.id],
    isOpen: open === c.id,
    onToggle: () => setOpen(open === c.id ? null : c.id),
    picked: !!picked[c.id],
    onPick: (on: boolean) => setPicked((p) => ({ ...p, [c.id]: on })),
    state: acted[c.id],
    editing: editing === c.id,
    draft: drafts[c.id] ?? c.draft_reply,
    onDraft: (text: string) => setDrafts((d) => ({ ...d, [c.id]: text })),
    onEdit: () => setEditing(c.id),
    onCancel: () => setEditing(null),
    act: (action: 'send' | 'edit' | 'hold') => act(c, action),
  })

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: s.dms },
    { key: 'clarify', label: 'Clarify', count: clarifyCount },
    { key: 'automatic', label: 'Automatic', count: autoCount },
  ]

  return (
    <div className="maya page">
      <header className="maya-head stagger">
        <h1 className="t-title1 maya-h1">
          Last night, <span className="num">{s.dms}</span> people messaged {name}.
        </h1>
        <p className="maya-sub">
          She was asleep. <span className="num">{s.held}</span> of them need her. The rest are
          written and waiting for her to press send.
        </p>
        {fromOverride && (
          <p className="maya-note">
            This is the same night, re-done after {name} changed one of her own rules.
          </p>
        )}
      </header>

      {/* ---------------------------------------------------------- inbox */}
      <section className="inbox enter delay-3">
        <div className="toolbar">
          <label className="row-checkwrap">
            <input
              type="checkbox"
              className="row-check"
              checked={allPicked}
              onChange={(e) => {
                const on = e.target.checked
                const next: Record<string, boolean> = {}
                if (on) shown.forEach((c) => (next[c.id] = true))
                setPicked(next)
              }}
            />
            <span className="sr-only">Select every message shown</span>
          </label>

          <button type="button" className="btn btn-primary toolbar-go" onClick={approveAutomatic}>
            Approve all automatic
          </button>

          <div className="tabs" role="tablist" aria-label="Filter the inbox">
            {tabs.map((t) => (
              <button
                key={t.key}
                type="button"
                role="tab"
                aria-selected={tab === t.key}
                className={`tab${tab === t.key ? ' tab-on' : ''}`}
                onClick={() => {
                  setTab(t.key)
                  setOpen(null)
                }}
              >
                {t.label} <span className="num tab-n">{t.count}</span>
              </button>
            ))}
          </div>

          {pickedIds.length > 0 && (
            <span className="toolbar-count">
              <span className="num">{pickedIds.length}</span> selected
            </span>
          )}
        </div>

        {/* what the two words mean, said once. The sureness key sits over
            the column it explains. */}
        {/* The strongest claim on the page. It has to be readable without
            scrolling past fifty-four rows to find it. */}
        <p className="claim">
          <b>Nothing was sent.</b> Every reply below is a draft. {name} presses send.
        </p>

        <div className="keys">
          <p className="key-line">
            <b>clarify</b>, she looks at this one. <b>automatic</b>, the reply is ready to send as
            written.
          </p>
          <p className="key-line key-sure">
            how sure it was: <Segs level={1} /> not sure <Segs level={2} /> fairly sure{' '}
            <Segs level={3} /> very sure
          </p>
        </div>

        <div className="list">
          {shown.map((c) => (
            <Row key={c.id} {...rowProps(c)} />
          ))}
          {shown.length === 0 && <p className="list-empty">Nothing in that one.</p>}
        </div>

        {/* ---- what the night came to. It never sends. It drafts. ---- */}
        <p className="key-line key-line-counts">
          {LANE_TAB.map((t, i) => (
            <span key={t.lane}>
              {i > 0 && ' · '}
              <span className="num">{laneCount(t.lane)}</span> {t.label.toLowerCase()}
            </span>
          ))}
        </p>

        <div className="card closer-main">
          <h2 className="t-title2 closer-h">
            {name} wakes up to <span className="num">{s.held}</span> messages to deal with, not{' '}
            <span className="num">{s.dms}</span>.
          </h2>
          {hours !== null && (
            <p className="closer-sub">
              Across a month that is about {inWords(hours)} hours of replying turned into a few
              minutes a day.
            </p>
          )}
        </div>
      </section>
    </div>
  )
}
