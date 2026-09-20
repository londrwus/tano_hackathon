/* ============================================================
   /how-it-works — the pipeline animation's data layer.

   Every number the animation puts on screen is read out of a real
   payload here. Nothing downstream is allowed to type a figure in.
   Spec: docs/13-PIPELINE-ANIMATION.md §4, docs/10-API-CONTRACT.md §10-§15.

   Sources
     GET  /api/extract?subject=labmuffin
                                  ACT 1. Michelle Wong — a real cosmetic
                                  chemist, ten of her own posts and the
                                  fifteen pictures in them, read verbatim
                                  off labmuffin.com. Her posts and pictures
                                  were fetched beforehand (scripts/
                                  fetch_corpus.py + scripts/enrich_images.py,
                                  both run by hand); the fourteen questions
                                  are the part that is really run, and
                                  `totals.seconds` is that run measured on
                                  the wire. No `live=1` — see TOKEN FREEZE
                                  below — so it is the committed measured
                                  run, replayed, and the stage says so.
     GET  /api/extract            Maya's own answer to the SAME price
                                  question, for the one-line contrast under
                                  the chips. Nothing else of Maya's is in
                                  act 1 any more.
     GET  /api/queue              ACTS 2 + 3 — still Maya. The @gracelee DM
                                  and the 50-DM lane split.
     POST /api/ask + GET /api/card/{id}
                                  ACT 2 — her card re-decided from the SAME
                                  shopper spec the queue resolved for that
                                  DM, for baskets_considered and the
                                  measured seconds. OFF under the token
                                  freeze (ASK_LIVE_CARD): act 2 runs off the
                                  committed measured card instead.

   Who did what, and the page says it out loud (docs/10 §15):
     gpt-4o-mini reads the pictures. Jev judges the attributes.
     Jev never sees a pixel. Every image on the wire carries `read_by`
     saying exactly that, and it is on the stage once, in words.

   And what we do NOT claim: the pictures did not change her answers.
   Measured 5 runs each way, they moved the two lowest-confidence slots
   and nothing else (docs/10 §15). The claim on screen is about what was
   READ, never about what it moved.

   If any leg fails we fall back to FROZEN, which is a verbatim copy of the
   committed cache (cache/extract-labmuffin.json, cache/extract.json,
   cache/queue.json) plus the measured card values. The page then shows
   `from cache` beside the honesty label. The whole sequence runs with the
   backend switched off — her titles, her chips and her picture metadata
   are all in the frozen copy, so only the hotlinked thumbnails go missing.
   ============================================================ */

/* ------------------------------------------------------------------ wire */

interface WireVision {
  shows: string | null
  readable_text: string | null
  products_named: string[] | null
  is_instructional: string | null
  is_comparison: string | null
  shows_a_result: string | null
}

interface WireImage {
  url: string
  alt: string | null
  found_in: string | null
  source_page: string | null
  vision_model: string | null
  read_by: string | null
  vision: WireVision | null
  error?: string | null
}

interface WireCorpusItem {
  id: string
  text: string
  kind: string
  evidence_ref: string | null
  source_url?: string | null
  published?: string | null
  images?: WireImage[] | null
}

interface SlotSide {
  level: string | number | boolean | null
  confidence: number
}

interface ExtractSlot {
  key: string
  label: string
  /** a named subject's side is keyed `subject`; Maya's own payload keys it `maya` */
  subject?: SlotSide
  maya?: SlotSide
}

interface ExtractPayload {
  live?: boolean
  cached?: boolean
  measured?: boolean
  subject?: string
  handle?: string
  display_name?: string
  what_she_is?: string
  real?: boolean
  provenance?: string
  source?: string
  source_url?: string | null
  fetched_at?: string | null
  corpus: WireCorpusItem[]
  questions: { id: string }[]
  requests: { id: string }[]
  slots: ExtractSlot[]
  totals: {
    questions: number
    requests: number
    seconds: number
    slot_count: number
    input_tokens?: number
  }
  model?: string
}

interface QueuePayload {
  stats: {
    dms: number
    judgments: number
    answered: number
    asked_back: number
    held: number
    referred: number
  }
  cards: {
    id: string
    from: string
    text: string
    lane: string
    job: string | null
    draft_reply: string | null
    refusal: string | null
    skin: string[] | null
    basket_summary: string | null
  }[]
}

interface CardPayload {
  card_id: string
  asker: { budget: number | null }
  verdict: { in_her_voice: string }
  baskets_considered: number
  seconds: number
}

/* ------------------------------------------------------------------ view model */

export type Tint = 'lilac' | 'mint' | 'peach' | 'sky' | 'blush'

export interface Trait {
  /** the short phrase on the chip — derived from the level the slot returned */
  text: string
  tint: Tint
  /** her own confidence in that answer, 0-1, straight off the wire */
  confidence: number
  /** raw provenance, exposed on hover so a judge can check it */
  provenance: string
}

/** one of her posts, by its real title */
export interface Post {
  title: string
  url: string | null
}

/** one picture she published, and what gpt-4o-mini read off it */
export interface Picture {
  url: string
  alt: string | null
  /** the transcription, split into its lines. May be empty. */
  lines: string[]
  /** product | demo | diagram | chart | person | packaging | screenshot | other */
  shows: string | null
  /** the post it was published in */
  page: string | null
  /** the wire's own `read_by` sentence */
  readBy: string | null
  /** false once the browser has told us the hotlink failed */
  ok: boolean
}

export interface Lane {
  count: number
  label: string
  /** css custom property name for the lane's ink */
  ink: string
}

export interface PipelineData {
  source: 'live' | 'cache'
  /** which legs came off the wire, for the console */
  legs: Record<string, 'live' | 'cache'>

  /* ---- act 1 — Michelle Wong */
  subjectName: string
  subjectWhat: string
  subjectHandle: string
  subjectSite: string
  subjectSiteLabel: string
  subjectFetched: string
  subjectReal: boolean
  subjectProvenance: string
  /** true when these fourteen answers were run for this page, not replayed */
  ranLive: boolean
  posts: Post[]
  postCount: number
  pictureCount: number
  /** the small strip that flows into the questions */
  thumbs: Picture[]
  /** the one whose transcription is on screen */
  feature: Picture | null
  /** a second picture, and the line of its transcription worth showing */
  alsoRead: { pic: Picture; line: string } | null
  visionModel: string
  questionCount: number
  requestCount: number
  slotCount: number
  /** what Jev was handed, off totals.input_tokens */
  inputTokens: number
  extractSeconds: number
  traits: Trait[]
  /** Maya's answer to the price question, for the contrast line */
  mayaPrice: string | null

  /* ---- act 2 — back to Maya */
  dmText: string
  dmChips: string[]
  dmSafety: string | null
  dmQuestionCount: number
  optionCount: number
  cardSeconds: number
  replyLine: string

  /* ---- act 3 — Maya's night */
  totalDms: number
  lanes: Lane[]
}

/* ------------------------------------------------------------------ helpers */

/** 0.68 -> "0.68", 0.8 -> "0.8", 1 -> "1". Never a trailing zero. */
export function trimNum(n: number): string {
  return String(Math.round(n * 100) / 100)
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

/** "2026-09-20T13:42:37+00:00" -> "20 September 2026". Never invents a date. */
export function humanDate(iso: string | null | undefined): string {
  if (!iso) return ''
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (!m) return iso
  return `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}`
}

/** "https://labmuffin.com/feed/" -> "labmuffin.com/feed" */
function siteLabel(url: string | null | undefined): string {
  if (!url) return ''
  return url.replace(/^https?:\/\//, '').replace(/\/+$/, '')
}

async function getJson<T>(path: string, timeoutMs: number, init?: RequestInit): Promise<T> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const res = await fetch(path, {
      ...init,
      signal: ctrl.signal,
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return (await res.json()) as T
  } finally {
    clearTimeout(timer)
  }
}

/* -------------------------------------------------- her posts, by their titles

   A fetched post is one string: "Title. The body...". There is no separate
   title field on the wire, so the title is the text up to the first sentence
   break — which lands correctly on all ten of hers, including the two that
   end in a question mark and the two that open with a quoted phrase.        */

function postTitle(text: string): string {
  const cut = text.indexOf('. ')
  let title = cut > 0 ? text.slice(0, cut) : text
  title = title.trim()
  if (title.length > 96) title = `${title.slice(0, 95).trimEnd()}…`
  return title
}

/* -------------------------------------------------- her pictures

   Flattened in payload order, deduped by url for display. A picture we could
   not read carries `vision: null` and an error — it is counted as a candidate
   and never as a read, and it never gets a transcription put in its mouth. */

function picturesOf(corpus: WireCorpusItem[]): { read: Picture[]; count: number } {
  const read: Picture[] = []
  const seen = new Set<string>()
  let count = 0
  for (const item of corpus) {
    for (const img of item.images ?? []) {
      if (!img?.url || !img.vision) continue
      count += 1
      if (seen.has(img.url)) continue
      seen.add(img.url)
      read.push({
        url: img.url,
        alt: img.alt,
        lines: String(img.vision.readable_text ?? '')
          .split('\n')
          .map((l) => l.trim())
          .filter(Boolean),
        shows: img.vision.shows ?? null,
        page: img.source_page ?? item.source_url ?? null,
        readBy: img.read_by ?? null,
        ok: true,
      })
    }
  }
  return { read, count }
}

/* The one whose transcription goes on screen. Legibility at a glance is the
   whole job, so: a transcription short enough to read in a second and long
   enough to be worth reading, and of those the one with the most lines to
   show — a picture that was read line by line makes the point better than a
   picture with three words on it. Ties go to whichever came first on the
   wire, so the same picture is picked every run. Falls back to the longest
   transcription we have. On her corpus this is the hair float test:
   "Low porosity" floats / "High porosity" sinks / BUSTED!                  */
function pickFeature(pics: Picture[]): Picture | null {
  const withText = pics.filter((p) => p.lines.length > 0)
  if (!withText.length) return null
  const glance = withText.filter((p) => {
    const len = p.lines.join(' ').length
    return len >= 20 && len <= 120
  })
  if (glance.length) {
    return glance
      .map((p, i) => ({ p, i, n: Math.min(p.lines.length, 3) }))
      .sort((a, b) => b.n - a.n || a.i - b.i)[0].p
  }
  return withText.slice().sort((a, b) => b.lines.join(' ').length - a.lines.join(' ').length)[0]
}

/* A second thing that was read, text only: the line of a transcribed chart
   that carries its own statistics. On her corpus this is the r² off the
   spurious-correlation chart in the sunscreen post. */
function pickAlsoRead(pics: Picture[], skip: Picture | null): { pic: Picture; line: string } | null {
  for (const p of pics) {
    if (skip && p.url === skip.url) continue
    const line = p.lines.find((l) => /r²|r\^?2\s*=|p\s*<\s*0/.test(l))
    if (line) return { pic: p, line }
  }
  /* no statistics anywhere: fall back to the next picture that was read at
     all, and show its first line */
  for (const p of pics) {
    if (skip && p.url === skip.url) continue
    if (p.lines.length) return { pic: p, line: p.lines.join(' / ') }
  }
  return null
}

/* -------------------------------------------------- trait chips from her answers

   docs/13 §4: the chips are the answers that came back. Each phrase is derived
   from the level the answer actually carried — change the level and the chip
   changes — and each chip carries its own confidence, on the chip, because
   docs/10 §14 is explicit that the low-confidence rows must not be dressed up
   as findings.

   Three of them are fixed because they are the point of the beat: how she
   treats hype, the one category she defends, and price — where she parts
   company with Maya. The other two are the highest-confidence answers left
   that a human can read without a glossary, and only if they clear 0.5.     */

const PHRASE: Record<string, (level: string) => string | null> = {
  hype: (l) => (/scep|skep/i.test(l) ? 'sceptical of hype' : l.toLowerCase()),
  defended_category: (l) => `${l.toUpperCase()} always`,
  price_refusal: (l) =>
    /central/i.test(l)
      ? 'price decides'
      : /occasional/i.test(l)
        ? 'price comes up occasionally'
        : l.toLowerCase(),
  subtraction_scope: (l) =>
    /never/i.test(l) ? 'never says to throw things out' : `throws things out: ${l}`,
  budget_behaviour: (l) =>
    /^no$/i.test(l) ? 'leaves money unspent' : /^yes$/i.test(l) ? 'spends the whole budget' : null,
  routine_size: (l) => (/fewest/i.test(l) ? 'fewest products' : l.toLowerCase()),
  subtraction: (l) =>
    /^yes$/i.test(l) ? 'takes away as often as adds' : /^no$/i.test(l) ? 'adds more than she removes' : null,
}

/* `subtraction` is deliberately not in FILL: on her answers it says the same
   thing as `subtraction_scope` and two chips saying one thing is a lie about
   how much we found out. */
const HEADLINE = ['hype', 'defended_category', 'price_refusal']
const FILL = ['subtraction_scope', 'budget_behaviour', 'routine_size']
const TINTS: Tint[] = ['blush', 'mint', 'peach', 'lilac', 'sky']
const FILL_FLOOR = 0.5

function sideOf(s: ExtractSlot): SlotSide | null {
  return s.subject ?? s.maya ?? null
}

function traitsFromSlots(slots: ExtractSlot[], subject: string): Trait[] {
  const by = new Map<string, ExtractSlot>()
  for (const s of slots) by.set(s.key, s)

  const chosen: { key: string; level: string; confidence: number; text: string }[] = []
  const take = (key: string, floor: number) => {
    const s = by.get(key)
    const side = s ? sideOf(s) : null
    if (!s || !side) return
    const level = String(side.level ?? '')
    if (!level) return
    if (side.confidence < floor) return
    const text = PHRASE[key]?.(level)
    if (!text) return
    chosen.push({ key, level, confidence: side.confidence, text })
  }

  for (const k of HEADLINE) take(k, 0)
  const fills = FILL.map((k) => {
    const side = sideOf(by.get(k) ?? ({} as ExtractSlot))
    return { k, c: side?.confidence ?? -1 }
  })
    .filter((f) => f.c >= FILL_FLOOR)
    .sort((a, b) => b.c - a.c)
  for (const f of fills) {
    if (chosen.length >= 5) break
    take(f.k, FILL_FLOOR)
  }

  return chosen.slice(0, 5).map((c, i) => ({
    text: c.text,
    tint: TINTS[i % TINTS.length],
    confidence: c.confidence,
    provenance: `${c.key} = "${c.level}" · confidence ${trimNum(c.confidence)} · /api/extract?subject=${subject}`,
  }))
}

const JOB_PHRASE: Record<string, string> = {
  pick_for_me: 'wants a pick',
  do_i_need_it: 'wants a yes or no',
  is_it_worth_it: 'wants a verdict',
  what_is_it: 'wants to know what it is',
  diagnose_me: 'wants a diagnosis',
  buying_for_someone_else: 'buying for someone else',
  occasion: 'has an occasion',
  later: 'not urgent',
  not_a_question: 'not a question',
}

const LANE_LABEL: Record<string, string> = {
  answered: 'wrote her reply',
  asked_back: 'asked a question',
  held: 'saved for Maya',
  referred: 'refused',
}

/* ------------------------------------------------------------------ frozen */

/* Act 1 verbatim from cache/extract-labmuffin.json (2026-09-20, `measured:
   true`, jev-latest) — her ten titles, her fifteen pictures, the five answers
   and their confidences. Act 2 and 3 verbatim from cache/queue.json and the
   measured card (POST /api/ask {skin:["dry","redness"], budget:60,
   how_many:4} -> GET /api/card/c-387bee). Maya's price level is from
   cache/extract.json. Nothing here is invented. */

const LM = 'https://labmuffin.com/wp-content/uploads'

const FROZEN_READ_BY =
  'gpt-4o-mini vision, under a strict json_schema. Not Jev - Jev judges these attributes, it does not see the picture.'

export const FROZEN: PipelineData = {
  source: 'cache',
  legs: { extract: 'cache', maya: 'cache', queue: 'cache', card: 'cache' },

  subjectName: 'Michelle Wong',
  subjectWhat: 'Cosmetic chemist, PhD. Writes Lab Muffin Beauty Science.',
  subjectHandle: '@labmuffinbeautyscience',
  subjectSite: 'https://labmuffin.com/feed/',
  subjectSiteLabel: 'labmuffin.com/feed',
  subjectFetched: '20 September 2026',
  subjectReal: true,
  subjectProvenance:
    'Real. Her own public writing, verbatim, fetched from https://labmuffin.com/feed/ on 2026-09-20. Not written by us.',
  ranLive: false,
  posts: [
    { title: 'Why are skin cancer rates rising with more sunscreen?', url: 'https://labmuffin.com/sunscreen-isnt-preventing-cancer/' },
    { title: 'How to Reapply Sunscreen Over Makeup', url: 'https://labmuffin.com/how-to-reapply-sunscreen-over-makeup-with-video/' },
    { title: 'How Much of a Sunscreen Stick Should You Apply?', url: 'https://labmuffin.com/how-to-apply-sunscreen-stick/' },
    { title: 'Hair porosity tests are a lie', url: 'https://labmuffin.com/hair-porosity-tests-are-a-lie/' },
    { title: 'Does water damage hair? The myth of “hygral fatigue”', url: 'https://labmuffin.com/does-water-damage-hair-the-myth-of-hygral-fatigue/' },
    { title: 'Hair, hydration and water: the real science', url: 'https://labmuffin.com/hair-hydration-and-water-the-real-science/' },
    { title: '“Plastic-free” is the new clean beauty: a treatise', url: 'https://labmuffin.com/plastic-free-is-the-new-clean-beauty-a-treatise/' },
    { title: 'What is hyaluronic acid and how does it work in skincare and makeup?', url: 'https://labmuffin.com/what-is-hyaluronic-acid-and-how-does-it-work/' },
    { title: 'Ulike red light mask overview and experience', url: 'https://labmuffin.com/ulike-red-light-mask-overview-and-experience/' },
    { title: 'Investigating the viral heat protectant test', url: 'https://labmuffin.com/investigating-the-viral-heat-protectant-test/' },
  ],
  postCount: 10,
  pictureCount: 15,
  thumbs: [
    {
      url: `${LM}/2025/05/melanoma-mariam-correlation.jpg`,
      alt: 'melanoma mariam correlation',
      lines: [
        'New cases of melanoma in the US',
        'correlates with',
        'Popularity of the first name Mariam',
        '1975-2021, r=0.985, r²=0.971, p<0.01 · tylervigen.com/spurious/custom_correlation/508',
      ],
      shows: 'chart',
      page: 'https://labmuffin.com/sunscreen-isnt-preventing-cancer/',
      readBy: FROZEN_READ_BY,
      ok: true,
    },
    {
      url: `${LM}/2025/05/sunscreen-causing-cancer-364x600.jpg`,
      alt: 'sunscreen causing cancer',
      lines: ['IMMUNE SYSTEM ON', 'SKIN'],
      shows: 'person',
      page: 'https://labmuffin.com/sunscreen-isnt-preventing-cancer/',
      readBy: FROZEN_READ_BY,
      ok: true,
    },
    {
      url: `${LM}/2020/07/reapply-spf-over-makeup-thumbnail.jpg`,
      alt: 'How to Reapply Sunscreen Over Makeup',
      lines: ['REAPPLY SPF OVER MAKEUP?'],
      shows: 'person',
      page: 'https://labmuffin.com/how-to-reapply-sunscreen-over-makeup-with-video/',
      readBy: FROZEN_READ_BY,
      ok: true,
    },
    {
      url: `${LM}/2020/07/foundation-0-2h-600x401.jpg`,
      alt: 'Foundation clumping',
      lines: ['0 HOURS', '2 HOURS'],
      shows: 'demo',
      page: 'https://labmuffin.com/how-to-reapply-sunscreen-over-makeup-with-video/',
      readBy: FROZEN_READ_BY,
      ok: true,
    },
    {
      url: `${LM}/2023/03/sunscreen-spf-stick-experiment.jpg`,
      alt: 'sunscreen spf stick experiment',
      lines: ['HOW MUCH? SPF?'],
      shows: 'person',
      page: 'https://labmuffin.com/how-to-apply-sunscreen-stick/',
      readBy: FROZEN_READ_BY,
      ok: true,
    },
  ],
  feature: {
    url: `${LM}/2026/01/float-test-1.jpg`,
    alt: 'float test',
    lines: ['"Low porosity" floats', '"High porosity" sinks', 'BUSTED!'],
    shows: 'demo',
    page: 'https://labmuffin.com/hair-porosity-tests-are-a-lie/',
    readBy: FROZEN_READ_BY,
    ok: true,
  },
  alsoRead: {
    pic: {
      url: `${LM}/2025/05/melanoma-mariam-correlation.jpg`,
      alt: 'melanoma mariam correlation',
      lines: [
        'New cases of melanoma in the US',
        'correlates with',
        'Popularity of the first name Mariam',
        '1975-2021, r=0.985, r²=0.971, p<0.01 · tylervigen.com/spurious/custom_correlation/508',
      ],
      shows: 'chart',
      page: 'https://labmuffin.com/sunscreen-isnt-preventing-cancer/',
      readBy: FROZEN_READ_BY,
      ok: true,
    },
    line: '1975-2021, r=0.985, r²=0.971, p<0.01 · tylervigen.com/spurious/custom_correlation/508',
  },
  visionModel: 'gpt-4o-mini',
  questionCount: 28,
  requestCount: 2,
  slotCount: 14,
  inputTokens: 13212,
  extractSeconds: 0.9,
  traits: [
    {
      text: 'sceptical of hype',
      tint: 'blush',
      confidence: 0.92,
      provenance: 'hype = "Actively sceptical of hype" · confidence 0.92 · cache/extract-labmuffin.json',
    },
    {
      text: 'SPF always',
      tint: 'mint',
      confidence: 0.71,
      provenance: 'defended_category = "spf" · confidence 0.71 · cache/extract-labmuffin.json',
    },
    {
      text: 'never talks about price',
      tint: 'peach',
      confidence: 0.55,
      provenance:
        'price_refusal = "Never talks about price" · confidence 0.55 · cache/extract-labmuffin.json',
    },
    {
      text: 'never says to throw things out',
      tint: 'lilac',
      confidence: 0.76,
      provenance: 'subtraction_scope = "never" · confidence 0.76 · cache/extract-labmuffin.json',
    },
    {
      text: 'leaves money unspent',
      tint: 'sky',
      confidence: 0.63,
      provenance: 'budget_behaviour = "NO" · confidence 0.63 · cache/extract-labmuffin.json',
    },
  ],
  mayaPrice: 'Price is central to their judgement',

  dmText: 'i have dry skin + redness and £60. tell me what to buy pls',
  dmChips: ['dry + redness', '£60', 'wants a pick'],
  dmSafety: 'not medical · in her scope',
  dmQuestionCount: 20,
  optionCount: 8,
  cardSeconds: 0.81,
  replyLine: 'Two things. The Red Reset and the SPF. Fifty-eight pounds.',

  totalDms: 50,
  lanes: [
    { count: 24, label: 'wrote her reply', ink: 'var(--ok)' },
    { count: 14, label: 'asked a question', ink: 'var(--accent)' },
    { count: 4, label: 'saved for Maya', ink: 'var(--butter-ink)' },
    { count: 8, label: 'refused', ink: 'var(--blush-ink)' },
  ],
}

/* ------------------------------------------------------------------ load */

/** Which real creator act 1 reads. `/api/creators` lists them; this is the one
    with `real: true` — her own public writing, fetched verbatim. */
const SUBJECT = 'labmuffin'

/* TOKEN FREEZE, 2026-09-20: `GET /api/card/{id}` decides the card live on
   every single open, and this page was opening one per visit and per replay
   of the demo. It no longer does. Act 2 runs off the card in the committed
   cache, which is itself a measured run — the same eight baskets, its own
   measured seconds. Flip this to true to go back to deciding it fresh. */
const ASK_LIVE_CARD = false

/* How long we will hold the title card waiting on live inference before we
   start the sequence off the frozen card instead. */
const CARD_DEADLINE_MS = 3000

/* Her pictures are hotlinks to her own server. We warm them before t=0 so the
   sequence never waits on one, and so a 403 is known before the clock starts
   rather than popping a hole in the middle of the act. */
const IMG_DEADLINE_MS = 1400

function preload(pics: Picture[], ms: number): Promise<void> {
  if (typeof window === 'undefined' || typeof Image === 'undefined' || !pics.length) {
    return Promise.resolve()
  }
  const each = pics.map(
    (p) =>
      new Promise<void>((done) => {
        const img = new Image()
        img.onload = () => done()
        img.onerror = () => {
          p.ok = false
          console.warn('[how-it-works] her picture did not load; the act carries on without it', p.url)
          done()
        }
        img.src = p.url
      }),
  )
  return Promise.race([
    Promise.all(each).then(() => undefined),
    new Promise<void>((r) => {
      setTimeout(r, ms)
    }),
  ])
}

/* Memoised for the session: the second visit to the page, and every Replay,
   start instantly. Call warmPipeline() from somewhere earlier in the demo if
   you want the first visit instant too — it costs one live inference per app
   load, which is why it is not wired up by default. */
let inflight: Promise<PipelineData> | null = null

export function warmPipeline(): Promise<PipelineData> {
  if (!inflight) inflight = runLoad()
  return inflight
}

export function loadPipeline(): Promise<PipelineData> {
  return warmPipeline()
}

async function runLoad(): Promise<PipelineData> {
  const data: PipelineData = { ...FROZEN, legs: { ...FROZEN.legs } }
  /* a leg we deliberately do not run is not a leg that fell back, so it does
     not put `from cache` on the stage */
  if (!ASK_LIVE_CARD) delete data.legs.card
  let pics: Picture[] = []

  /* ---- act 1 -------------------------------- /api/extract?subject=labmuffin

     Her posts and her pictures are a prefetch — fetched by hand, before the
     demo, and committed. The fourteen questions are the part that is really
     run, and `totals.seconds` is that run measured on the wire.

     TOKEN FREEZE, 2026-09-20: no `live=1` from this page. The cached payload
     is `measured: true` — a real run of the same fourteen questions, timed on
     the wire — so every number below is still measured, just not re-measured
     on each visit. The page says which it got: `live` off the payload decides
     between "ran live just now" and "this replays that run", and it is never
     allowed to claim the first.                                             */
  const extractLeg = getJson<ExtractPayload>(`/api/extract?subject=${SUBJECT}`, 5000)
    .then((e) => {
      if (!e?.totals || !Array.isArray(e.corpus)) throw new Error('bad shape')

      data.subjectName = e.display_name || data.subjectName
      data.subjectWhat = e.what_she_is || data.subjectWhat
      data.subjectHandle = e.handle || data.subjectHandle
      data.subjectSite = e.source_url || data.subjectSite
      data.subjectSiteLabel = siteLabel(e.source_url) || data.subjectSiteLabel
      data.subjectFetched = humanDate(e.fetched_at) || data.subjectFetched
      data.subjectReal = e.real ?? data.subjectReal
      data.subjectProvenance = e.provenance || data.subjectProvenance
      data.ranLive = e.live === true

      data.posts = e.corpus
        .filter((c) => c.kind === 'post' || !c.kind)
        .map((c) => ({ title: postTitle(c.text), url: c.source_url ?? null }))
      data.postCount = e.corpus.length

      const shot = picturesOf(e.corpus)
      if (shot.count > 0) {
        data.pictureCount = shot.count
        const feature = pickFeature(shot.read)
        data.feature = feature
        data.alsoRead = pickAlsoRead(shot.read, feature)
        data.thumbs = shot.read
          .filter((p) => p.url !== feature?.url && p.url !== data.alsoRead?.pic.url)
          .slice(0, 5)
        data.visionModel =
          shot.read.find((p) => p.readBy)?.readBy?.split(' ')[0] ?? data.visionModel
        pics = [feature, data.alsoRead?.pic ?? null, ...data.thumbs].filter(
          (p): p is Picture => p != null,
        )
      }

      data.questionCount = e.totals.questions ?? e.questions.length
      data.requestCount = e.totals.requests ?? e.requests.length
      data.slotCount = e.totals.slot_count ?? e.slots.length
      if (typeof e.totals.input_tokens === 'number') data.inputTokens = e.totals.input_tokens
      data.extractSeconds = e.totals.seconds
      const traits = traitsFromSlots(e.slots ?? [], e.subject ?? SUBJECT)
      if (traits.length >= 3) data.traits = traits
      data.legs.extract = 'live'
    })
    .catch((err) => {
      console.warn('[how-it-works] her run fell back to the frozen cache', err)
    })

  /* ---- act 1, one line only ---------------------------------- /api/extract

     Maya's own answer to the SAME price question. It is the contrast under
     the chips and nothing else — act 1 is Michelle's now.                   */
  const mayaLeg = getJson<ExtractPayload>('/api/extract', 4000)
    .then((e) => {
      const s = (e?.slots ?? []).find((x) => x.key === 'price_refusal')
      const side = s ? sideOf(s) : null
      if (side?.level != null) data.mayaPrice = String(side.level)
      data.legs.maya = 'live'
    })
    .catch((err) => {
      console.warn('[how-it-works] Maya price line fell back to the frozen cache', err)
    })

  /* ---- acts 2 + 3 -------------------------------------------- /api/queue */
  const queueLeg = getJson<QueuePayload>('/api/queue', 4000)
    .then((q) => {
      if (!q?.stats || !Array.isArray(q.cards)) throw new Error('bad shape')
      const s = q.stats
      data.totalDms = s.dms
      data.lanes = (['answered', 'asked_back', 'held', 'referred'] as const).map((k, i) => ({
        count: s[k],
        label: LANE_LABEL[k],
        ink: ['var(--ok)', 'var(--accent)', 'var(--butter-ink)', 'var(--blush-ink)'][i],
      }))
      /* 1000 judgments over 50 DMs — the measured questions-per-DM. Verified
         against cache/queue-judgments.json: @gracelee carries exactly 20. */
      if (s.judgments && s.dms) data.dmQuestionCount = Math.round(s.judgments / s.dms)

      const dm =
        q.cards.find((c) => c.from === '@gracelee') ?? q.cards.find((c) => c.job === 'pick_for_me')
      let budget: number | null = null
      if (dm) {
        data.dmText = dm.text
        if (dm.draft_reply) data.replyLine = dm.draft_reply
        const chips: string[] = []
        if (dm.skin?.length) chips.push(dm.skin.join(' + '))
        const m = dm.text.match(/£\s?(\d+)/)
        if (m) {
          budget = Number(m[1])
          chips.push(`£${m[1]}`)
        }
        if (dm.job) chips.push(JOB_PHRASE[dm.job] ?? dm.job.replace(/_/g, ' '))
        if (chips.length) data.dmChips = chips
        data.dmSafety =
          dm.refusal === null && dm.lane === 'answered' ? 'not medical · in her scope' : dm.refusal
      }
      data.legs.queue = 'live'
      return budget
    })
    .catch((err) => {
      console.warn('[how-it-works] /api/queue fell back to the frozen cache', err)
      return null as number | null
    })

  /* ---- act 2 -------------------------------------- /api/ask -> /api/card

     The queue's card_id is a triage id, not a decided card, so we re-decide
     that DM from the shopper spec the queue itself resolved for it
     (skin dry+redness, the budget in her message, "a few" = 4).
     baskets_considered and seconds are that run's own measured values.
     This is the slow leg — it is live inference — so it runs beside the
     other two and the page holds the title card until all three are in.   */
  const cardFetch: Promise<CardPayload | null> = queueLeg
    .then(async (budget) => {
      if (!ASK_LIVE_CARD) return null
      const ask = await getJson<{ card_id: string }>('/api/ask', 9000, {
        method: 'POST',
        body: JSON.stringify({
          skin: ['dry', 'redness'],
          budget: budget ?? 60,
          how_many: 4,
          owns: [],
        }),
      })
      if (!ask?.card_id) throw new Error('no card_id')
      const card = await getJson<CardPayload>(`/api/card/${ask.card_id}`, 9000)
      if (typeof card?.baskets_considered !== 'number') throw new Error('bad shape')
      return card
    })
    .catch((err) => {
      console.warn('[how-it-works] /api/ask + /api/card fell back to the frozen cache', err)
      return null
    })

  /* This leg is live inference, so its tail is unbounded — and the page is
     the closing beat of a demo. Past CARD_DEADLINE_MS we stop waiting and
     run act 2 off the frozen card, which is itself a measured run. A late
     answer is discarded rather than applied: nothing on the stage may change
     once the clock is running. */
  const deadline = new Promise<null>((r) => {
    setTimeout(() => r(null), CARD_DEADLINE_MS)
  })

  const [, , , card] = await Promise.all([
    extractLeg,
    mayaLeg,
    queueLeg,
    Promise.race([cardFetch, deadline]),
  ])

  if (card) {
    data.optionCount = card.baskets_considered
    data.cardSeconds = card.seconds
    if (card.verdict?.in_her_voice) data.replyLine = card.verdict.in_her_voice
    if (card.asker?.budget != null) {
      const b = card.asker.budget
      data.dmChips = data.dmChips.map((c) => (/^£/.test(c) ? `£${b}` : c))
    }
    data.legs.card = 'live'
  } else if (ASK_LIVE_CARD) {
    console.warn(
      `[how-it-works] the live card did not land inside ${CARD_DEADLINE_MS}ms; act 2 runs off the frozen measured card`,
    )
  } else {
    console.info('[how-it-works] act 2 runs off the committed measured card (no live decision)')
  }

  /* last, and still before t=0: her photographs */
  await preload(
    pics.length
      ? pics
      : [data.feature, data.alsoRead?.pic ?? null, ...data.thumbs].filter(
          (p): p is Picture => p != null,
        ),
    IMG_DEADLINE_MS,
  )

  data.source = Object.values(data.legs).every((v) => v === 'live') ? 'live' : 'cache'
  console.info('[how-it-works] data legs', data.legs)
  return data
}
