/* Types mirror docs/10-API-CONTRACT.md (v2, frozen at H+0) exactly.
   If a field is not in the contract it is not in here. */

export interface Envelope {
  cached: boolean
  ms: number
  live?: boolean
  error?: string
  fallback?: boolean
}

/* ---- 1. GET /api/case ---- */
export interface ShelfItem {
  ref: string
  product: string
  gbp: number
  price: string
  type: string
  skin: string
  finish: string
  maya_rating: number
  maya_note: string
  affiliate: boolean
}
export interface CasePayload extends Envelope {
  case: { id: string; ref: string; operation: string; logline: string }
  creator: {
    name: string
    handle: string
    city: string
    followers_total: number
    dms_per_month: number
    reply_hours_per_month: number
    creed: string
  }
  shelf: ShelfItem[]
  personas: { id: string; name: string; tag: string; says: string }[]
}

/* ---- 2. GET /api/standard ---- */
export interface StandardSide {
  level: string
  value: number
  confidence: number
}
export interface StandardSlot {
  key: string
  label: string
  maya: StandardSide
  derm: StandardSide
  agrees: boolean
  source_caption: string
  evidence_ref: string
  toggleable: boolean
}
export interface StandardPayload extends Envelope {
  extraction_seconds: number
  slot_count: number
  slots: StandardSlot[]
  agree_count: number
  disagree_count: number
  headline: string
}

/* ---- 3. GET /api/queue ---- */
export type Lane = 'answered' | 'asked_back' | 'held' | 'referred'

export interface QueueStats {
  dms: number
  judgments: number
  seconds: number
  answered: number
  asked_back: number
  held: number
  referred: number
  handled_pct: number
  held_pct: number
  referred_pct: number
  at_real_volume: {
    dms_per_month: number
    handled: number
    held_per_day: number
    referred: number
  }
  header_line: string
}
/* Contract §17. A voice note is a message that arrived differently —
   nothing between the transcript and the reply reads `source`. These are
   labels written onto the finished card, never gate inputs.
   The audio is SYNTHETIC: `tts-1` spoke a script we wrote. `disclosure`
   is the wording that ships with the bytes — print it, never paraphrase. */
export interface VoiceNote {
  audio_url: string
  file: string
  seconds: number
  transcript: string
  stt_model: string
  transcribe_ms: number
  tts_model: string
  tts_voice: string
  tts_script: string
  verbatim_match: boolean
  synthetic: boolean
  disclosure: string
  who_did_what: string
}

export interface QueueCard {
  id: string
  ref: string
  from: string
  text: string
  lane: Lane
  confidence: number
  job: string
  draft_reply: string
  question_back: string | null
  hold_reason: string | null
  refusal: { why: string; refer_to: string } | null
  card_id: string | null
  basket_summary: string | null
  source?: 'text' | 'voice'
  voice?: VoiceNote | null
}
export interface QueuePayload extends Envelope {
  stats: QueueStats
  cards: QueueCard[]
}
export interface QueueActionResponse {
  ok: boolean
  action: 'send' | 'edit' | 'hold'
  correction_written: boolean
  standard_moved: string | null
}

/* ---- 4. POST /api/ask ---- */
export interface AskBody {
  skin: string[]
  budget: number
  how_many: number
  owns: string[]
  text: string | null
}
export interface AskResponse {
  card_id: string
  ms: number
}

/* ---- 5. GET /api/card/{id} ---- */
export interface BasketRow {
  product: string
  price: string
  type: string
  ref: string
  maya_note: string
  affiliate: boolean
  why: string
}
export interface LeftOutRow {
  product: string
  price: string
  why: string
  instead: string
}
export interface CardPayload extends Envelope {
  re_decided_at: string
  card_id: string
  parent_card_id: string | null
  asker: {
    name: string
    said: string
    skin: string[]
    budget: number
    owns: string[]
  }
  verdict: { headline: string; in_her_voice: string; is_refusal: boolean }
  basket: BasketRow[]
  total: string
  unspent: { amount: string; line: string }
  left_out: LeftOutRow[]
  ceiling: { band: string; provenance: string; evidence_ref: string }
  money_line: { affiliate_count: number; basket_value: string; note: string }
  indifference_band: string
  og_image: string
  share_url: string
}
export interface RedecideBody {
  skin: string[]
  budget: number
  owns: string[]
}

/* ---- 6. GET /api/onboard ---- */
export interface HeardTrait {
  trait: string
  caption: string
  evidence_ref: string
  confidence: number
  slot_key: string
}
export interface OnboardPayload extends Envelope {
  handle: string
  heard: HeardTrait[]
  accuracy: string
  first_verdict_card_id: string
}
