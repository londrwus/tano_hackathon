/* ============================================================
   /how-it-works — one stage, three acts, fifteen seconds, plays itself.

   Spec: docs/13-PIPELINE-ANIMATION.md. The §2 timeline is exact and the
   `t` values below are copied from it.

   ACT 1 IS A REAL PERSON. Michelle Wong — Lab Muffin Beauty Science, a
   cosmetic chemist with a PhD — her own ten posts and the fifteen
   photographs in them, fetched verbatim from labmuffin.com. Her real
   titles are on the cards, her real photographs are hotlinked from her
   own server, and what gpt-4o-mini read off one of them is on the stage
   with it. Acts 2 and 3 are Maya's inbox and Maya's night, unchanged; act
   2 opens by saying so.

   Honesty (docs/13 §1.6, §1.7, docs/10 §15):
     - every number on the stage is read out of `PipelineData`, which is read
       out of the API. There is not one hand-typed figure in this file.
     - the sequence runs far slower than the machine does. It is a replay and
       the label at the bottom says so.
     - the two elapsed pills are measured wire times: /api/extract
       totals.seconds and the card's own seconds.
     - gpt-4o-mini read her pictures; Jev judged the answers and never saw a
       pixel. That sentence is on the stage, once.
     - her posts and pictures are a prefetch; the fourteen questions are the
       part that is really run. Both are labelled, and the label is driven by
       the payload's own `live` flag — under the token freeze the page serves
       the committed measured run and says "this replays that run" rather
       than claiming it happened just now.
     - NOTHING here says the pictures changed her answers, because measured
       over five runs each way they did not (docs/10 §15). What is claimed is
       what was read.

   Motion: transform and opacity only. Nothing here transitions width, top
   or background-color — the option grid and the 50-dot cloud are hundreds of
   nodes and they have to stay on the compositor.
   ============================================================ */

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'

import { loadPipeline, trimNum } from '../api/extract'
import type { PipelineData, Picture } from '../api/extract'

import './howitworks.css'

/* ------------------------------------------------------------------ stage */

/* The stage is a fixed 1280x660 design surface that is scaled to fit. It
   never reflows, so the composition is identical on the projector and on a
   phone — docs/13 §1.1, "the stage never moves, never scrolls, never
   resizes". */
const STAGE_W = 1280
const STAGE_H = 660
const PAD = 48
const BODY_TOP = 150

/* ------------------------------------------------------------------ timeline */

const STEPS = [
  ['a1.title', 0.0],
  ['a1.posts', 0.4],
  ['a1.caption', 1.6],
  ['a1.fan', 2.0],
  ['a1.fanlabel', 2.2],
  ['a1.chips', 3.0],
  ['a1.pill', 4.2],
  ['a1.out', 5.0],
  ['a2.title', 5.2],
  ['a2.bubble', 5.6],
  ['a2.dots', 6.4],
  ['a2.chips', 7.2],
  ['a2.safety', 7.8],
  ['a2.options', 8.4],
  ['a2.collapse', 9.2],
  ['a2.optlabel', 9.6],
  ['a2.reply', 10.0],
  ['a2.pill', 10.4],
  ['a2.out', 11.0],
  ['a3.title', 11.2],
  ['a3.cloud', 11.6],
  ['a3.split', 12.4],
  ['a3.labels', 13.2],
  ['a3.final', 14.0],
] as const satisfies readonly (readonly [string, number])[]

type StepKey = (typeof STEPS)[number][0]

const IDX: Record<string, number> = {}
STEPS.forEach(([k], i) => {
  IDX[k] = i
})

/* Each part starts at its own first beat and stops at its last. docs/13 §2
   still describes the choreography inside a part; the parts no longer chain
   into one another. Nothing on this page advances by itself. */
const ACT_START = [0, 5.0, 11.0]
const ACT_END = [5.0, 11.0, 15.4]
/* stop a hair short of the end so the part's own fade-out beat (a1.out,
   a2.out) never fires: a part holds on its last frame until you move on. */
const EPS = 0.01

/* ------------------------------------------------------------------ maths */

function mulberry32(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function spread(n: number, lo: number, hi: number): number[] {
  if (n <= 1) return [(lo + hi) / 2]
  const step = (hi - lo) / (n - 1)
  return Array.from({ length: n }, (_, i) => lo + i * step)
}

function cx(...parts: (string | false | undefined)[]) {
  return parts.filter(Boolean).join(' ')
}

/* ==================================================================
   ACT 1 — "First, it reads what she has already posted."

   She is Michelle Wong. The cards carry her real post titles, the strip
   carries her real photographs — hotlinked from her own server, never
   re-hosted — and the card beside them carries what was read off one of
   them, word for word.
   ================================================================== */

/* the left block: her titles, then her pictures, then the questions leave.
   The pictures are big on purpose — they are the evidence, and they have to
   read from the back of the room. Two of them, large, beat six postage
   stamps. */
const POST_X = PAD
const POST_W = 300
const POST_H = 32
const POST_GAP = 4
const PIC_X = 364
const PIC_W = 336
const PIC_A_TOP = 170
const PIC_A_H = 196
const PIC_B_TOP = PIC_A_TOP + PIC_A_H + 30
const PIC_B_H = 104
const PIC_IMG_W = 160
const LANE_X0 = 720
const LANE_X1 = 880
const CHIP_X = 908
const BAND_TOP = 552

/** a hotlink to her server can 403. If it does the picture goes, the card
    keeps what was read off it, and the part carries on — docs/10 §15: the
    picture is hers, on her server, and we never re-host it. The dead state
    is held by the act so the caption can say how many are actually up. */
function Thumb({
  p,
  cls,
  style,
  onDead,
}: {
  p: Picture
  cls: string
  style?: React.CSSProperties
  onDead: (url: string) => void
}) {
  return (
    <img
      className={cls}
      style={style}
      src={p.url}
      alt={p.alt ?? ''}
      loading="eager"
      decoding="async"
      referrerPolicy="no-referrer"
      title={p.lines.length ? `read off this picture: ${p.lines.join(' / ')}` : (p.alt ?? '')}
      onError={() => onDead(p.url)}
    />
  )
}

const FAN_T0 = STEPS[IDX['a1.fan']][1]
const FAN_T1 = STEPS[IDX['a1.chips']][1]

function Act1({
  d,
  is,
  on,
  t,
}: {
  d: PipelineData
  is: (k: StepKey) => boolean
  on: boolean
  t: number
}) {
  const postsH = d.posts.length * (POST_H + POST_GAP) - POST_GAP

  /* the count going up. Jev answers all fourteen of a judge's questions in
     ONE response — there is no per-question arrival time and the payload does
     not contain one (docs/10 §12, `replay_note`). So this is a replay of a
     single answer, played over the same second the dots take to fly, and the
     stage says "slowed down so you can see it" underneath. */
  const answered = Math.round(
    d.questionCount * Math.max(0, Math.min(1, (t - FAN_T0) / (FAN_T1 - FAN_T0 - 0.15))),
  )

  const geom = useMemo(() => {
    const n = d.questionCount
    /* the questions leave her posts AND her pictures on the same frame and
       land fanned out down the right of the lane — the 28 lines of
       design/v10b. */
    const from = spread(n, BODY_TOP + 10, BODY_TOP + 350)
    const to = spread(n, BODY_TOP + 2, 520)
    return { from, to, n }
  }, [d.questionCount])

  const fan = is('a1.fan')
  const feature = d.feature
  const second = d.alsoRead

  const [dead, setDead] = useState<Record<string, true>>({})
  const onDead = useCallback((url: string) => {
    setDead((m) => (m[url] ? m : { ...m, [url]: true }))
  }, [])
  const up = (p: Picture | null | undefined) => !!p && p.ok && !dead[p.url]
  const shown = (up(feature) ? 1 : 0) + (up(second?.pic) ? 1 : 0)

  return (
    <div className={cx('hiw-act', on && 'is-on')}>
      <div className={cx('hiw-eyebrow', 'hiw-enter', is('a1.title') && 'is-on')}>
        PART 1 &middot; 0.0 &ndash; 5.0s
      </div>
      <h2 className={cx('hiw-title', 'hiw-enter', is('a1.title') && 'is-on')}>
        First, it reads what she has already posted.
      </h2>

      {/* --- who she is, where it came from, when we took it --- */}
      <div
        className={cx('hiw-who', 'hiw-enter', is('a1.title') && 'is-on')}
        style={{ left: PAD, top: 104 }}
        title={d.subjectProvenance}
      >
        {d.subjectName} &mdash; {d.subjectWhat}
      </div>
      <div
        className={cx('hiw-src', 'hiw-enter', is('a1.title') && 'is-on')}
        style={{ left: PAD, top: 126 }}
      >
        her own posts, word for word, from{' '}
        <a href={d.subjectSite} target="_blank" rel="noreferrer noopener">
          {d.subjectSiteLabel}
        </a>
        {d.subjectFetched && <> &middot; fetched {d.subjectFetched}</>}
      </div>

      <div
        className={cx('hiw-fanlabel', 'hiw-enter', is('a1.fanlabel') && 'is-on')}
        style={{ left: LANE_X0 + 10, top: 108 }}
      >
        Jev answers {d.questionCount} questions at the same moment.
      </div>
      <div
        className={cx('hiw-tally', 'hiw-enter', is('a1.fan') && 'is-on')}
        style={{ left: LANE_X0 + 10, top: 130 }}
        title="Jev answers all fourteen of a judge's questions in one response. The count is a replay of a single answer, not fourteen arrivals."
      >
        <b>{answered}</b> of {d.questionCount} answered
      </div>

      {/* --- her posts, by their real titles, flying in from the left --- */}
      <div className="hiw-posts" style={{ left: POST_X, top: BODY_TOP, width: POST_W }}>
        {d.posts.map((p, i) => (
          <span
            key={p.title}
            className={cx('hiw-post', 'hiw-slide', is('a1.posts') && 'is-on')}
            style={{ transitionDelay: `${i * 40}ms`, height: POST_H }}
            title={p.url ?? undefined}
          >
            {p.title}
          </span>
        ))}
      </div>
      <div
        className={cx('hiw-postcap', 'hiw-enter', is('a1.caption') && 'is-on')}
        style={{ left: POST_X, top: BODY_TOP + postsH + 8 }}
      >
        {d.posts.length} posts, straight off her site
      </div>

      {/* --- her photographs, big, and what was read off each --- */}
      <div
        className={cx('hiw-piclabel', 'hiw-enter', is('a1.caption') && 'is-on')}
        style={{ left: PIC_X, top: 146, width: PIC_W }}
      >
        {shown > 0
          ? `${shown} of her ${d.pictureCount} pictures, and what was read off them`
          : `what was read off 2 of her ${d.pictureCount} pictures`}
      </div>

      {feature && (
        <div
          className={cx('hiw-read', 'hiw-enter', is('a1.posts') && 'is-on')}
          style={{
            left: PIC_X,
            top: PIC_A_TOP,
            width: PIC_W,
            transitionDelay: `${d.posts.length * 40}ms`,
          }}
        >
          {up(feature) && (
            <Thumb
              p={feature}
              cls="hiw-read-i"
              style={{ width: PIC_IMG_W, height: PIC_A_H }}
              onDead={onDead}
            />
          )}
          <div className="hiw-read-t">
            <div className="hiw-read-k">read off this picture</div>
            {feature.lines.slice(0, 4).map((l) => (
              <div key={l} className="hiw-read-l">
                {l}
              </div>
            ))}
            <div className="hiw-read-m" title={feature.readBy ?? undefined}>
              by {d.visionModel}
            </div>
          </div>
        </div>
      )}

      {second && (
        <div
          className={cx('hiw-read', 'hiw-enter', is('a1.posts') && 'is-on')}
          style={{
            left: PIC_X,
            top: PIC_B_TOP,
            width: PIC_W,
            transitionDelay: `${d.posts.length * 40 + 120}ms`,
          }}
        >
          {up(second.pic) && (
            <Thumb
              p={second.pic}
              cls="hiw-read-i"
              style={{ width: PIC_IMG_W, height: PIC_B_H }}
              onDead={onDead}
            />
          )}
          <div className="hiw-read-t">
            <div className="hiw-read-k">and off this one</div>
            <div className="hiw-read-l hiw-read-l-sm">{second.line}</div>
            <div className="hiw-read-m" title={second.pic.readBy ?? undefined}>
              by {d.visionModel}
            </div>
          </div>
        </div>
      )}

      {/* --- the fan-out. All dots leave on the same frame. --- */}
      <svg
        className={cx('hiw-curves', fan && 'is-on')}
        viewBox={`0 0 ${STAGE_W} ${STAGE_H}`}
        aria-hidden="true"
      >
        {geom.from.map((y0, i) => {
          const y1 = geom.to[i]
          return (
            <path
              key={i}
              d={`M ${LANE_X0} ${y0} C ${LANE_X0 + 120} ${y0} ${LANE_X1 - 95} ${y1} ${LANE_X1} ${y1}`}
            />
          )
        })}
      </svg>

      {geom.to.map((y1, i) => {
        const y0 = geom.from[i]
        return (
          <span
            key={i}
            className={cx('hiw-qdot', fan && 'is-on')}
            style={{
              left: LANE_X1,
              top: y1,
              transform: fan
                ? 'translate(-50%, -50%)'
                : `translate(calc(-50% + ${LANE_X0 - LANE_X1}px), calc(-50% + ${y0 - y1}px))`,
            }}
          />
        )
      })}

      {/* --- what came back, and how sure she was --- */}
      <div className="hiw-traits" style={{ left: CHIP_X, top: BODY_TOP }}>
        {d.traits.map((t, i) => (
          <span
            key={t.text}
            className={cx('hiw-trait', `hiw-t-${t.tint}`, 'hiw-pop', is('a1.chips') && 'is-on')}
            style={{ transitionDelay: `${i * 80}ms` }}
            title={t.provenance}
          >
            {t.text}
            <em className="hiw-trait-c" title="how sure it was, 0 to 1">
              {trimNum(t.confidence)}
            </em>
          </span>
        ))}
      </div>

      {d.mayaPrice && (
        <div
          className={cx('hiw-contrast', 'hiw-enter', is('a1.chips') && 'is-on')}
          style={{ left: CHIP_X, top: 436, width: 308, transitionDelay: '400ms' }}
        >
          Maya, asked the same question about price: &ldquo;{d.mayaPrice}.&rdquo;
        </div>
      )}

      <div
        className={cx('hiw-pill', 'hiw-pill-lilac', 'hiw-pop', is('a1.pill') && 'is-on')}
        style={{ right: PAD, top: 470 }}
        title="/api/extract totals.seconds — measured wire time for both requests"
      >
        {trimNum(d.extractSeconds)} seconds
      </div>

      {/* --- the receipts. Every figure here is off the payload. --- */}
      <div
        className={cx('hiw-count', 'hiw-enter', is('a1.pill') && 'is-on')}
        style={{ left: PAD, top: BAND_TOP, width: STAGE_W - PAD * 2 }}
      >
        {d.posts.length} posts &middot; {d.pictureCount} pictures &middot; {d.questionCount}{' '}
        questions &middot; {d.requestCount} requests &middot;{' '}
        {d.inputTokens.toLocaleString('en-GB')} tokens in &middot; {trimNum(d.extractSeconds)}{' '}
        seconds
      </div>
      <div
        className={cx('hiw-note', 'hiw-split', 'hiw-enter', is('a1.title') && 'is-on')}
        style={{ left: PAD, top: BAND_TOP + 26, width: STAGE_W - PAD * 2 }}
      >
        {d.visionModel} read the pictures; Jev answered the questions; Jev never sees a pixel.
      </div>
      <div
        className={cx('hiw-note', 'hiw-enter', is('a1.caption') && 'is-on')}
        style={{ left: PAD, top: BAND_TOP + 46, width: STAGE_W - PAD * 2, transitionDelay: '80ms' }}
      >
        Her posts and her pictures were fetched beforehand;{' '}
        {d.ranLive
          ? 'the fourteen questions ran live just now, and that is the time above'
          : 'the fourteen questions were run and timed for real, and this replays that run'}
        . The pictures did not change her answers &mdash; this is what was read off them, not what
        it moved.
      </div>
    </div>
  )
}

/* ==================================================================
   ACT 2 — "Then, at 3am, someone messages her."
   ================================================================== */

const DM_PITCH = 34
const DM_COLS = 10
const OPT_D = 34
const OPT_PITCH = 52
const OPT_TOP = BODY_TOP
const OPT_MIN_H = 3 * OPT_PITCH + OPT_D

function Act2({ d, is, on }: { d: PipelineData; is: (k: StepKey) => boolean; on: boolean }) {
  const dmDots = Array.from({ length: d.dmQuestionCount }, (_, i) => i)

  const opt = useMemo(() => {
    const n = Math.max(1, d.optionCount)
    const cols = Math.max(1, Math.min(6, Math.min(n, Math.ceil(Math.sqrt(n * 1.6)))))
    const rows = Math.ceil(n / cols)
    const own = (rows - 1) * OPT_PITCH + OPT_D
    const h = Math.max(OPT_MIN_H, own)
    /* keep the grid optically centred in its slot whatever n comes back as,
       so the composition does not lurch when the option count changes */
    const dy = (h - own) / 2
    const chosen = Math.min(
      n - 1,
      Math.round((rows - 1) / 2) * cols + Math.round((cols - 1) / 2),
    )
    return { n, cols, rows, h, dy, chosen }
  }, [d.optionCount])

  const labelTop = OPT_TOP + opt.h + 40
  const cardTop = labelTop + 34
  const collapsed = is('a2.collapse')

  return (
    <div className={cx('hiw-act', on && 'is-on')}>
      <div className={cx('hiw-eyebrow', 'hiw-enter', is('a2.title') && 'is-on')}>
        PART 2 &middot; 5.0 &ndash; 11.0s
      </div>
      <h2 className={cx('hiw-title', 'hiw-enter', is('a2.title') && 'is-on')}>
        Then, at 3am, someone messages her.
      </h2>

      {/* the one bridging line: act 1 was Michelle, the rest is Maya */}
      <div
        className={cx('hiw-bridge', 'hiw-enter', is('a2.title') && 'is-on')}
        style={{ left: PAD, top: 112, transitionDelay: '120ms' }}
      >
        That was Michelle Wong. The rest is Maya &mdash; her shelf, her inbox, her night.
      </div>

      {/* --- the DM --- */}
      <div
        className={cx('hiw-bubble', 'hiw-slide-r', is('a2.bubble') && 'is-on')}
        style={{ left: PAD, top: BODY_TOP, width: 384 }}
      >
        &ldquo;{d.dmText}&rdquo;
      </div>

      {/* --- 20 questions, all on the same frame --- */}
      <div className="hiw-dmdots" style={{ left: PAD, top: 252 }}>
        {dmDots.map((i) => (
          <span
            key={i}
            className={cx('hiw-dmdot', is('a2.dots') && 'is-on')}
            style={{
              left: (i % DM_COLS) * DM_PITCH,
              top: Math.floor(i / DM_COLS) * DM_PITCH,
            }}
          />
        ))}
      </div>
      <div
        className={cx('hiw-dmlabel', 'hiw-enter', is('a2.dots') && 'is-on')}
        style={{ left: PAD, top: 252 + Math.ceil(d.dmQuestionCount / DM_COLS) * DM_PITCH + 6 }}
        title="/api/queue stats — 1,000 judgments over 50 DMs"
      >
        {d.dmQuestionCount} questions, all in one go.
      </div>

      <div className="hiw-dmchips" style={{ left: PAD, top: 366 }}>
        {d.dmChips.map((c, i) => (
          <span
            key={c}
            className={cx('hiw-dmchip', 'hiw-pop', is('a2.chips') && 'is-on')}
            style={{ transitionDelay: `${i * 90}ms` }}
          >
            {c}
          </span>
        ))}
      </div>

      {d.dmSafety && (
        <div
          className={cx('hiw-safety', 'hiw-enter', is('a2.safety') && 'is-on')}
          style={{ left: PAD, top: 522 }}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 2.6 4.8 5.5v6.1c0 4.5 3.1 8.2 7.2 9.8 4.1-1.6 7.2-5.3 7.2-9.8V5.5Z" />
          </svg>
          {d.dmSafety}
        </div>
      )}

      {/* --- every basket she could have sent, then the one she did --- */}
      <div className="hiw-opts" style={{ left: 548, top: OPT_TOP, height: opt.h }}>
        {Array.from({ length: opt.n }, (_, i) => {
          const chosen = i === opt.chosen
          return (
            <span
              key={i}
              className={cx(
                'hiw-opt',
                is('a2.options') && 'is-on',
                collapsed && (chosen ? 'is-chosen' : 'is-dim'),
              )}
              style={{
                left: (i % opt.cols) * OPT_PITCH,
                top: opt.dy + Math.floor(i / opt.cols) * OPT_PITCH,
                transitionDelay: collapsed ? '0ms' : `${i * 20}ms`,
              }}
            >
              <span className="hiw-opt-a" />
              <span className="hiw-opt-b" />
            </span>
          )
        })}
      </div>

      <div
        className={cx('hiw-optlabel', 'hiw-enter', is('a2.optlabel') && 'is-on')}
        style={{ left: 548, top: labelTop }}
        title="/api/card baskets_considered"
      >
        {d.optionCount} {d.optionCount === 1 ? 'option' : 'options'} priced up. One chosen.
      </div>

      <div
        className={cx('hiw-reply', 'hiw-enter', is('a2.reply') && 'is-on')}
        style={{ left: 548, top: cardTop, width: 600 }}
      >
        <div className="hiw-reply-k">It writes it her way</div>
        <p className="hiw-reply-v">&ldquo;{d.replyLine}&rdquo;</p>
      </div>

      <div
        className={cx('hiw-pill', 'hiw-pill-accent', 'hiw-pop', is('a2.pill') && 'is-on')}
        style={{ right: PAD, top: 556 }}
        title="/api/card seconds — measured wire time for that decision"
      >
        {trimNum(d.cardSeconds)} seconds
      </div>
    </div>
  )
}

/* ==================================================================
   ACT 3 — "It did that for everyone who messaged, all night."
   ================================================================== */

const G_COLS = 5
const G_PITCH = 30
const G_X0 = PAD
const G_PITCH_X = 296
const CLOUD_CX = 640
const CLOUD_CY = 222

function Act3({ d, is, on }: { d: PipelineData; is: (k: StepKey) => boolean; on: boolean }) {
  const dots = useMemo(() => {
    const rand = mulberry32(20260920)
    const out: { x: number; y: number; cx: number; cy: number; ink: string }[] = []
    d.lanes.forEach((lane, g) => {
      for (let i = 0; i < lane.count; i += 1) {
        out.push({
          x: G_X0 + g * G_PITCH_X + (i % G_COLS) * G_PITCH,
          y: BODY_TOP + Math.floor(i / G_COLS) * G_PITCH,
          cx: 0,
          cy: 0,
          ink: lane.ink,
        })
      }
    })
    /* the pre-split cloud: a deterministic scatter, so a screenshot taken
       twice is the same screenshot. */
    for (const dot of out) {
      const a = rand() * Math.PI * 2
      const r = Math.sqrt(rand())
      dot.cx = CLOUD_CX + Math.cos(a) * r * 235
      dot.cy = CLOUD_CY + Math.sin(a) * r * 88
    }
    return out
  }, [d.lanes])

  const split = is('a3.split')

  return (
    <div className={cx('hiw-act', on && 'is-on')}>
      <div className={cx('hiw-eyebrow', 'hiw-enter', is('a3.title') && 'is-on')}>
        PART 3 &middot; 11.0 &ndash; 15.0s
      </div>
      <h2 className={cx('hiw-title', 'hiw-enter', is('a3.title') && 'is-on')}>
        It did that for everyone who messaged, all night.
      </h2>

      {dots.map((dot, i) => (
        <span
          key={i}
          className={cx('hiw-n', is('a3.cloud') && 'is-on', split && 'is-split')}
          style={{
            left: dot.x,
            top: dot.y,
            transform: split ? 'translate(0,0)' : `translate(${dot.cx - dot.x}px, ${dot.cy - dot.y}px)`,
            transitionDelay: split ? '0ms' : `${(i % 25) * 12}ms`,
          }}
        >
          <span className="hiw-n-a" />
          <span className="hiw-n-b" style={{ background: dot.ink }} />
        </span>
      ))}

      {d.lanes.map((lane, g) => (
        <div
          key={lane.label}
          className={cx('hiw-lane', 'hiw-enter', is('a3.labels') && 'is-on')}
          style={{ left: G_X0 + g * G_PITCH_X, top: 322, transitionDelay: `${g * 90}ms` }}
        >
          <div className="hiw-lane-n" style={{ color: lane.ink }}>
            {lane.count}
          </div>
          <div className="hiw-lane-l">{lane.label}</div>
        </div>
      ))}

      <div
        className={cx('hiw-final', 'hiw-enter', is('a3.final') && 'is-on')}
        style={{ left: PAD, top: 428, width: STAGE_W - PAD * 2 }}
      >
        <p className="hiw-final-h">Every one of them is a draft. Maya presses send.</p>
        <p className="hiw-final-s">It never messages anybody by itself.</p>
      </div>
    </div>
  )
}

/* ==================================================================
   The page
   ================================================================== */

const ALWAYS_ON = () => true

export default function HowItWorks() {
  const [data, setData] = useState<PipelineData | null>(null)
  /* which part is on the stage. It only ever changes because somebody said
     so — a button, a dot, or an arrow key. */
  const [act, setAct] = useState(0)
  /* whether this part's own beats are currently playing out. It is never
     true on mount: the page opens on part 1, finished and still. */
  const [playing, setPlaying] = useState(false)
  const [epoch, setEpoch] = useState(0)
  const [t, setT] = useState(ACT_END[0] - EPS)

  const rafRef = useRef(0)

  const reduced = useMemo(
    () =>
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    [],
  )

  /* ---- prefetch everything before the first beat. Nothing waits on a
     network call once a part is running (docs/13 §4). */
  useEffect(() => {
    let alive = true
    loadPipeline().then((d) => {
      if (alive) setData(d)
    })
    return () => {
      alive = false
    }
  }, [])

  /* ---- one clock, and it only runs inside the part you are on.

     It starts at that part's first beat and stops dead at its last one. It
     cannot walk into the next part: that is a decision, and the person on
     stage makes it. Every visual state is still a pure function of `t`, so
     there are no per-element timers to orphan when you jump. */
  useEffect(() => {
    if (!data || reduced || !playing) return
    const from = ACT_START[act]
    const cap = ACT_END[act] - EPS
    const t0 = performance.now()
    let stopped = false

    const tick = (now: number) => {
      if (stopped) return
      const cur = Math.min(cap, from + (now - t0) / 1000)
      setT(cur)
      if (cur < cap) rafRef.current = requestAnimationFrame(tick)
      else setPlaying(false)
    }
    rafRef.current = requestAnimationFrame(tick)

    return () => {
      stopped = true
      cancelAnimationFrame(rafRef.current)
    }
  }, [data, reduced, playing, act, epoch])

  /* go to a part and play its beats from the top. This is the only way the
     stage ever moves. */
  const go = useCallback((i: number) => {
    const n = Math.max(0, Math.min(ACT_START.length - 1, i))
    cancelAnimationFrame(rafRef.current)
    setAct(n)
    setT(ACT_START[n])
    setPlaying(true)
    setEpoch((e) => e + 1)
  }, [])

  /* left and right walk the parts, space is next. A presenter should never
     have to find a button with a mouse. */
  useEffect(() => {
    if (reduced) return
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null
      if (el && /^(input|textarea|select)$/i.test(el.tagName)) return
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault()
        if (act < ACT_START.length - 1) go(act + 1)
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        if (act > 0) go(act - 1)
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault()
        go(act)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [act, go, reduced])

  const phase = useMemo(() => {
    let p = -1
    for (let i = 0; i < STEPS.length; i += 1) {
      if (t >= STEPS[i][1]) p = i
      else break
    }
    return p
  }, [t])

  const is = useCallback((k: StepKey) => IDX[k] <= phase, [phase])

  /* ---- scale the fixed stage to whatever the room gives us */
  const hostRef = useRef<HTMLDivElement>(null)
  const [k, setK] = useState(1)
  useLayoutEffect(() => {
    const el = hostRef.current
    if (!el) return
    const fit = () => {
      const w = el.clientWidth
      const h = window.innerHeight - 200
      setK(Math.min(1, w / STAGE_W, reduced ? 1 : Math.max(0.28, h / STAGE_H)))
    }
    fit()
    const ro = new ResizeObserver(fit)
    ro.observe(el)
    window.addEventListener('resize', fit)
    return () => {
      ro.disconnect()
      window.removeEventListener('resize', fit)
    }
  }, [reduced, data])

  const stage = (children: ReactNode, key?: string) => (
    <div key={key} className="hiw-scaler" style={{ height: STAGE_H * k }}>
      <div
        className="hiw-stage"
        style={{ width: STAGE_W, height: STAGE_H, transform: `scale(${k})` }}
      >
        {children}
      </div>
    </div>
  )

  if (!data) {
    return (
      <div className="hiw" ref={hostRef}>
        <div className="hiw-hold">
          <div className="hiw-hold-k">The whole pipeline</div>
          <div className="hiw-hold-t">How it works</div>
          <div className="hiw-hold-s">Three parts. You move it on.</div>
          <div className="hiw-hold-n">reading the run&hellip;</div>
        </div>
      </div>
    )
  }

  const LAST = ACT_START.length - 1

  return (
    <div className={cx('hiw', reduced && 'hiw-static')} ref={hostRef}>
      {reduced ? (
        <>
          {stage(<Act1 d={data} is={ALWAYS_ON} on t={ACT_END[0]} />, 'a1')}
          {stage(<Act2 d={data} is={ALWAYS_ON} on />, 'a2')}
          {stage(<Act3 d={data} is={ALWAYS_ON} on />, 'a3')}
        </>
      ) : (
        stage(
          <>
            <Act1 d={data} is={is} on={act === 0} t={t} />
            <Act2 d={data} is={is} on={act === 1} />
            <Act3 d={data} is={is} on={act === 2} />
          </>,
        )
      )}

      <div className="hiw-controls" style={{ maxWidth: STAGE_W * k }}>
        {!reduced && (
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => go(act - 1)}
              disabled={act === 0}
            >
              Back
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => go(act + 1)}
              disabled={act === LAST}
            >
              Next
            </button>
            <button type="button" className="btn btn-tertiary" onClick={() => go(act)}>
              Play this part again
            </button>
          </>
        )}
        <div className="hiw-scrub" role="group" aria-label="Jump to a part">
          {ACT_START.map((start, i) => (
            <button
              key={start}
              type="button"
              className={cx('hiw-scrub-b', !reduced && act === i && 'is-on')}
              onClick={() => go(i)}
              aria-label={`Part ${i + 1}`}
              aria-current={!reduced && act === i ? 'true' : undefined}
            >
              <span />
            </button>
          ))}
        </div>
        <div className="hiw-honesty">
          {!reduced && <span className="hiw-keys">&larr; &rarr; or space</span>}
          slowed down so you can see it
          {data.source === 'cache' && <span className="hiw-cache">from cache</span>}
        </div>
      </div>
    </div>
  )
}
