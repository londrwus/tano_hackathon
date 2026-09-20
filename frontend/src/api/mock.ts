/* ============================================================
   MOCK PAYLOADS — the stage safety net.
   Hand-written against docs/10-API-CONTRACT.md (v2) and the real
   evidence in data/case-001-maya.json. Every endpoint in the
   contract has an entry here. client.ts falls back to this on ANY
   failure, so the frontend is never blocked on lane A.
   Money is ALWAYS a preformatted string. Never a float on screen.
   ============================================================ */

import type {
  AskResponse,
  CardPayload,
  CasePayload,
  Lane,
  OnboardPayload,
  QueueActionResponse,
  QueueCard,
  QueuePayload,
  StandardPayload,
} from './types'

/* ---------------------------------------------------------- 1. CASE */

export const mockCase: CasePayload = {
  cached: true,
  ms: 2,
  case: {
    id: '001',
    ref: 'SHD-001',
    operation: 'OPERATION SHADE',
    logline:
      'A single creator. Four thousand eight hundred messages a month. One person answering them.',
  },
  creator: {
    name: 'Maya Rao',
    handle: '@mayarao',
    city: 'London',
    followers_total: 50000,
    dms_per_month: 4800,
    reply_hours_per_month: 70,
    creed: 'People do not need more products. They need confidence.',
  },
  shelf: [
    { ref: 'E-04.1', product: 'Cloud Cream', gbp: 38, price: '£38', type: 'Moisturiser', skin: 'Dry', finish: 'Rich', maya_rating: 9.2, maya_note: 'My winter skin saviour.', affiliate: true },
    { ref: 'E-04.2', product: 'Daily Gel', gbp: 24, price: '£24', type: 'Moisturiser', skin: 'Oily / Combo', finish: 'Light', maya_rating: 8.1, maya_note: 'Easy. No drama.', affiliate: true },
    { ref: 'E-04.3', product: 'Red Reset', gbp: 32, price: '£32', type: 'Serum', skin: 'Sensitive', finish: 'Calm', maya_rating: 9.5, maya_note: 'For angry skin days.', affiliate: false },
    { ref: 'E-04.4', product: 'Night Serum', gbp: 42, price: '£42', type: 'Serum', skin: 'All', finish: 'Glow', maya_rating: 8.8, maya_note: 'Best for texture.', affiliate: true },
    { ref: 'E-04.5', product: 'SPF 50', gbp: 26, price: '£26', type: 'SPF', skin: 'All', finish: 'Invisible', maya_rating: 9.6, maya_note: 'Non-negotiable.', affiliate: true },
    { ref: 'E-04.6', product: 'Glass Drop', gbp: 62, price: '£62', type: 'Serum', skin: 'All', finish: 'Dewy', maya_rating: 8.1, maya_note: 'Good. Not £62 good.', affiliate: false },
    { ref: 'E-04.7', product: 'Soft Clean', gbp: 22, price: '£22', type: 'Cleanser', skin: 'All', finish: 'Cream', maya_rating: 8.6, maya_note: 'Boring in the best way.', affiliate: true },
    { ref: 'E-04.8', product: 'Oil Balm', gbp: 29, price: '£29', type: 'Balm', skin: 'Dry', finish: 'Glow', maya_rating: 7.7, maya_note: 'Beautiful, but too much for me.', affiliate: false },
    { ref: 'E-04.9', product: 'Clear Wash', gbp: 20, price: '£20', type: 'Cleanser', skin: 'Oily', finish: 'Foam', maya_rating: 8.0, maya_note: 'Great after gym.', affiliate: true },
    { ref: 'E-04.10', product: 'Tint Veil', gbp: 34, price: '£34', type: 'Base', skin: 'All', finish: 'Skin-like', maya_rating: 9.0, maya_note: 'Best on camera.', affiliate: true },
  ],
  personas: [
    { id: 'emily', name: 'Emily', tag: 'PRICE SENSITIVE', says: 'I trust you, but I am not spending £100 on serum.' },
    { id: 'priya', name: 'Priya', tag: 'SENSITIVE SKIN', says: 'Every time I try something new my face freaks out.' },
    { id: 'sophie', name: 'Sophie', tag: 'BEAUTY OBSESSIVE', says: 'Forget the brand. What would YOU buy?' },
    { id: 'hannah', name: 'Hannah', tag: 'OVERWHELMED', says: 'There are 500 versions of this. Just tell me.' },
    { id: 'grace', name: 'Grace', tag: 'BUSY', says: 'I have 5 mins. Give me the two things that matter.' },
    { id: 'alex', name: 'Alex', tag: 'SILENT BROWSER', says: '(Saves almost everything. Sends almost nothing.)' },
  ],
}

/* ---------------------------------------------------------- 2. STANDARD */

export const mockStandard: StandardPayload = {
  cached: true,
  ms: 670,
  extraction_seconds: 0.67,
  slot_count: 6,
  slots: [
    {
      key: 'routine_size',
      label: 'How many products',
      maya: { level: 'The fewest possible products', value: 0.1, confidence: 0.94 },
      derm: { level: 'A small routine', value: 1.16, confidence: 0.88 },
      agrees: false,
      source_caption: 'my 5 minute morning routine. two products. that is it.',
      evidence_ref: 'E-03.5',
      toggleable: true,
    },
    {
      key: 'price_refusal',
      label: 'How much price matters',
      maya: { level: 'Price is central to their judgement', value: 2.8, confidence: 0.91 },
      derm: { level: 'Mentions price occasionally', value: 0.69, confidence: 0.83 },
      agrees: false,
      source_caption: 'luxury vs drugstore: where should your money go?',
      evidence_ref: 'E-03.4',
      toggleable: true,
    },
    {
      key: 'subtraction',
      label: 'Will they tell you to stop',
      maya: { level: 'Yes — removes before adding', value: 0.62, confidence: 0.86 },
      derm: { level: 'No — adds to the routine', value: 0.11, confidence: 0.79 },
      agrees: false,
      source_caption: 'if your face freaks out, stop adding things.',
      evidence_ref: 'E-03.3',
      toggleable: true,
    },
    {
      key: 'budget_behaviour',
      label: 'Do they spend the budget',
      maya: { level: 'Leaves money unspent', value: 0.21, confidence: 0.88 },
      derm: { level: 'Leaves money unspent', value: 0.32, confidence: 0.74 },
      agrees: true,
      source_caption: '3 things i would repurchase with £50',
      evidence_ref: 'E-03.1',
      toggleable: true,
    },
    {
      key: 'hype',
      label: 'How they treat hype',
      maya: { level: 'Actively sceptical of hype', value: 0.01, confidence: 0.96 },
      derm: { level: 'Actively sceptical of hype', value: 0.13, confidence: 0.9 },
      agrees: true,
      source_caption: 'things i bought because tiktok told me to',
      evidence_ref: 'E-03.2',
      toggleable: true,
    },
    {
      key: 'defended_category',
      label: 'The one they will not cut',
      maya: { level: 'SPF', value: 1.0, confidence: 1.0 },
      derm: { level: 'SPF', value: 0.92, confidence: 0.92 },
      agrees: true,
      source_caption: 'spend it on sunscreen. everything else is negotiable.',
      evidence_ref: 'E-04.5',
      toggleable: false,
    },
  ],
  agree_count: 3,
  disagree_count: 3,
  headline: 'Same six questions. They agree on three and disagree on three.',
}

/* ---------------------------------------------------------- 3. QUEUE */

type Row = [
  handle: string,
  text: string,
  job: string,
  conf: number,
  reply: string,
  extra?: string,
  basket?: string,
  cardId?: string,
]

const answeredRows: Row[] = [
  ['@jessica', 'i already have the night serum. do i need the barrier cream too???', 'do_i_need_it', 0.94, 'No. Just the SPF. Twenty-six pounds.', undefined, 'SPF 50 · £26', 'c-jessica'],
  ['@gracelee', 'i have dry skin + redness and £60. tell me what to buy pls', 'recommendation', 0.91, 'Red Reset and the SPF. Fifty-eight. Keep the rest.', undefined, 'Red Reset + SPF 50 · £58', 'c-priya'],
  ['@sarah', 'is the cloud cream actually worth £38 or am i being influenced', 'value', 0.89, 'For dry skin in January, yes. In July, no. Which one are you?', undefined, 'Cloud Cream · £38'],
  ['@ameliaxo', 'okay but if u could only keep ONE of these which one', 'judgement', 0.93, 'The SPF. It is not even close.', undefined, 'SPF 50 · £26'],
  ['@joanna', 'can you make me a routine but only 2 products bc i will not do 8 steps', 'constraint', 0.95, 'Two is what I do. A cleanser you like, and SPF you will actually wear.', undefined, 'Soft Clean + SPF 50 · £48'],
  ['@roisin', 'can you send me the one you would buy if you were me', 'personalisation', 0.87, 'SPF 50 and nothing else this month. Twenty-six pounds.', undefined, 'SPF 50 · £26'],
  ['@olivia', 'i trust you more than Sephora tbh', 'trust', 0.9, 'Then let me save you money: you do not need the third serum.'],
  ['@tashkxo', 'is the glass drop worth it', 'value', 0.96, 'Good. Not £62 good. Buy the Night Serum instead and keep twenty.', undefined, 'Night Serum · £42'],
  ['@beccaj', 'what spf do you use under makeup', 'info', 0.97, 'SPF 50. Invisible. It is the only one I never skip.', undefined, 'SPF 50 · £26'],
  ['@harriet.w', 'oily skin, £30, what do i get', 'recommendation', 0.92, 'Daily Gel. Twenty-four. Do not spend the last six.', undefined, 'Daily Gel · £24'],
  ['@fionn', 'do i need a toner', 'do_i_need_it', 0.94, 'No.'],
  ['@lauren_b', 'is a £9 cleanser fine', 'value', 0.93, 'Yes. The cleanser genuinely does not matter. Spend it on sunscreen.'],
  ['@maddy', 'i keep buying stuff and my skin is worse', 'diagnosis', 0.85, 'Stop adding things. Two weeks, cleanser and SPF only.'],
  ['@aoifeh', 'best moisturiser for winter?', 'recommendation', 0.9, 'Cloud Cream if you are dry. Otherwise you are buying a feeling.', undefined, 'Cloud Cream · £38'],
  ['@niamh.k', 'can i use the red reset every day', 'usage', 0.86, 'On the angry days. Not as a habit.'],
  ['@zaraq', 'combination skin and £100 — go', 'recommendation', 0.88, 'Daily Gel and SPF. Fifty. You are keeping the other fifty.', undefined, 'Daily Gel + SPF 50 · £50'],
  ['@elliep', 'what shade of lip liner is that', 'info', 0.91, 'Brown. The one I wear when I have five minutes.'],
  ['@sinead', 'the tint veil for a wedding?', 'recommendation', 0.89, 'Yes. It is the best thing I own on camera.', undefined, 'Tint Veil · £34'],
  ['@holly.m', 'is the oil balm worth £29', 'value', 0.87, 'Beautiful, but too much for me. Probably too much for you.'],
  ['@nadia', 'do i need a separate eye cream', 'do_i_need_it', 0.92, 'No. Use whatever is already on your hands.'],
  ['@kirsty', 'i got the soft clean, whats next', 'sequencing', 0.9, 'Nothing, for a month. Then SPF if you have been skipping it.'],
  ['@ruby.t', 'gym twice a day, what cleanser', 'recommendation', 0.93, 'Clear Wash. Twenty pounds. Great after gym.', undefined, 'Clear Wash · £20'],
  ['@amber', '£150 budget, build me the full routine', 'constraint', 0.84, 'I am not spending £150 of yours. Sixty-four buys everything you need.', undefined, 'Cloud Cream + SPF 50 · £64', 'c-mum'],
  ['@leah', 'does the night serum actually do anything', 'value', 0.88, 'For texture, yes. For everything else it is marketing.'],
  ['@priyanka', 'can i wear spf indoors, be honest', 'usage', 0.9, 'If you sit by a window, yes. Otherwise stop worrying about it.'],
  ['@caitlin', 'whats the one product you regret', 'judgement', 0.91, 'The £62 serum. I still use it. It is still not £62 good.'],
  ['@morgan', 'dry skin, £40', 'recommendation', 0.92, 'Cloud Cream. Thirty-eight. Two pounds left and that is fine.', undefined, 'Cloud Cream · £38'],
  ['@steph', 'is double cleansing necessary', 'do_i_need_it', 0.94, 'No. It is one more thing to sell you.'],
  ['@ines', 'i only care about looking good friday', 'relationship', 0.86, 'Tint Veil and sleep. Skincare will not do it by Friday.', undefined, 'Tint Veil · £34'],
  ['@georgia', 'cheapest thing on your shelf that is actually good', 'value', 0.93, 'Clear Wash, twenty pounds. Boring. Works.', undefined, 'Clear Wash · £20'],
]

const askedRows: Row[] = [
  ['@ellie.mp', 'what shade are u wearing in todays video???', 'shade', 0.82, 'Happy to tell you — one thing first.', 'What foundation are you wearing now?'],
  ['@kate', 'Maya I have a first date Friday HELP', 'relationship', 0.79, 'I can do this in one product.', 'Do you actually care about skincare or do you just want to look hot tomorrow?'],
  ['@niamh', 'i dont even know what my skin type is lol', 'diagnosis', 0.81, 'Easy to work out.', 'By 3pm, is your face shiny, tight, or fine?'],
  ['@erin', 'recommend me something please', 'recommendation', 0.76, 'Tell me one thing and I will pick.', 'What are you using now?'],
  ['@bea', 'my skin is being weird', 'diagnosis', 0.74, 'Before I guess —', 'What did you change in the last two weeks?'],
  ['@martha', 'which serum', 'recommendation', 0.78, 'Depends entirely on one answer.', 'What do you hate about your skin right now?'],
  ['@yasmin', 'is it worth it', 'value', 0.72, 'Worth it compared to what?', 'What is your budget?'],
  ['@dani', 'i want to look glowy', 'recommendation', 0.8, 'Glow means three different things.', 'What finish do you like — dewy, skin-like, or invisible?'],
  ['@robyn', 'starting from zero, no products at all', 'onboarding', 0.83, 'Genuinely the best position to be in.', 'Skin type?'],
]

const heldRows: Row[] = [
  ['@lucy', 'not a beauty question but what would you do if it was your money?', 'transfer_of_trust', 0.25, 'Draft withheld — this one is asking for Maya, not for a product.', 'She is being asked to make a life decision, not to pick a product.'],
  ['@mia', 'I saw the thing you recommended last week. buying it payday', 'delayed_intent', 0.38, 'Draft withheld — unclear whether this wants a reply at all.', 'Not a question. Could be a nudge, could be nothing.'],
  ['@fern', 'can i send you a photo of my face', 'diagnosis', 0.31, 'Draft withheld — this needs Maya to actually look.', 'She would have to look at the photo herself.'],
  ['@alexis', 'would you ever do a collab with my brand', 'business', 0.19, 'Draft withheld — commercial.', 'Business. Maya answers her own brand mail.'],
]

const referredRows: Row[] = [
  ['@hannah.r', 'im 6 weeks pregnant, can i keep using retinol?', 'medical', 0.97, 'I am not the person for this one. Ask your midwife or GP before you change anything.', 'Pregnancy plus a prescription-strength active. This is not a product question.', 'Ask your midwife or GP before changing anything.'],
  ['@sophie_l', 'my derm put me on tretinoin, should i stop it for the night serum', 'medical', 0.96, 'Not my call. Go back to the dermatologist who prescribed it.', 'Prescription medication. Changing it is a clinical decision.', 'Go back to the dermatologist who prescribed it.'],
  ['@tanya', 'starting accutane next month, what do i buy', 'medical', 0.95, 'Nothing from me until you have spoken to them. Your routine on accutane is prescribed, not recommended.', 'Isotretinoin course. Skin care during it is prescribed, not recommended.', 'Your prescribing dermatologist will give you the routine.'],
  ['@lorna', 'i have perioral dermatitis, which of your products helps', 'medical', 0.94, 'None of them, honestly. See a GP or a dermatologist first.', 'A diagnosed skin condition that products commonly make worse.', 'See a GP or dermatologist first.'],
  ['@keziah', 'can i put the cloud cream over my steroid eczema cream', 'medical', 0.93, 'Ask the pharmacist who dispensed it — I do not know how they interact.', 'Layering over prescribed topical medication.', 'Ask the pharmacist who dispensed it.'],
  ['@millie', 'im 12 and my mum said i can get one thing', 'safeguarding', 0.92, 'Sunscreen from a pharmacy, and nothing else. Ask a parent first.', 'Under 16. Not somebody she will sell to.', 'Sunscreen from a pharmacy, nothing else — and ask a parent.'],
  ['@rosa', 'this mole has changed colour, is that the serum', 'medical', 0.99, 'Please do not wait on this. See a GP this week.', 'A changing mole. This needs a doctor today, not a reply from a shelf.', 'See a GP this week. Please do not wait.'],
]

function build(rows: Row[], lane: Lane, startIndex: number): QueueCard[] {
  return rows.map((r, i) => {
    const n = startIndex + i
    const [handle, text, job, confidence, reply, extra, basket, cardId] = r
    return {
      id: `q-${String(n).padStart(3, '0')}`,
      ref: `E-01.${((n - 1) % 12) + 1}`,
      from: handle,
      text,
      lane,
      confidence,
      job,
      draft_reply: reply,
      question_back: lane === 'asked_back' ? extra ?? null : null,
      hold_reason: lane === 'held' ? extra ?? null : null,
      refusal:
        lane === 'referred'
          ? { why: extra ?? '', refer_to: basket ?? 'A clinician.' }
          : null,
      card_id: cardId ?? null,
      basket_summary: lane === 'referred' ? null : basket ?? null,
    }
  })
}

/* ---- the four that arrived as audio (contract §17) ----
   Verbatim from data/voice-notes.json and cache/queue.json, so the offline
   path shows the same four messages, transcripts and disclosure the live
   one does. The mp3s live behind /api/voice/*, so with the API blocked the
   player hides itself and the transcript carries the card. */
const DISCLOSURE =
  'Synthetic demo audio. Spoken by OpenAI tts-1 from a script we wrote, transcribed by ' +
  'OpenAI whisper-1. It is not a recording of a real person and no real audience audio ' +
  'exists in this repo.'
const WHO_DID_WHAT =
  'OpenAI tts-1 spoke it, OpenAI whisper-1 transcribed it, Jev decides what to do about ' +
  'it. Jev never hears audio - it is handed the transcript in the same `state.message` ' +
  'field a typed DM uses.'

type VoiceRow = [
  id: string,
  ref: string,
  handle: string,
  transcript: string,
  lane: Lane,
  job: string,
  reply: string,
  file: string,
  seconds: number,
  ttsVoice: string,
  transcribeMs: number,
  ttsScript: string,
]

const voiceRows: VoiceRow[] = [
  [
    'v-001', 'S-VN.1', '@noor',
    "Yeah, so my skin's been really dry and a bit red. Lately, I've got about 60 quid, what should I actually get?",
    'answered', 'pick_for_me', 'Two things. The Red Reset and the SPF. Fifty-eight pounds.',
    'synthetic-v-001-nova.mp3', 6.93, 'nova', 3590,
    "hiya, so my skin's been really dry and a bit red lately, I've got about sixty quid, what should I actually get",
  ],
  [
    'v-002', 'S-VN.2', '@bexm',
    'Is the glass drop actually worth 62 pounds or am I being silly?',
    'answered', 'is_it_worth_it', 'Good. Not £62 good. Her line on it is about £40–45.',
    'synthetic-v-002-shimmer.mp3', 4.63, 'shimmer', 2098,
    'is the glass drop actually worth sixty-two pounds or am I being silly',
  ],
  [
    'v-003', 'S-VN.3', '@harrietj',
    "So I'm about six weeks pregnant and I just wanted to check if any of this is safe to keep using.",
    'referred', 'pick_for_me',
    'I am not the right person for this one. Please ask a pharmacist or your GP. I would rather send you there than guess with your skin.',
    'synthetic-v-003-alloy.mp3', 6.19, 'alloy', 2576,
    "um so I'm about six weeks pregnant and I just wanted to check if any of this is safe to keep using",
  ],
  [
    'v-004', 'S-VN.4', '@sana.k',
    "Honestly, you're the only person I trust on this stuff. Just wanted to say thanks.",
    'held', 'not_a_question', 'Thank you. Genuinely. Nothing to buy today.',
    'synthetic-v-004-fable.mp3', 5.18, 'fable', 3011,
    "honestly you're the only person I trust on this stuff, just wanted to say thanks",
  ],
]

const voiceCards: QueueCard[] = voiceRows.map((r) => {
  const [id, ref, from, transcript, lane, job, reply, file, seconds, ttsVoice, ms, script] = r
  return {
    id,
    ref,
    from,
    text: transcript,
    lane,
    confidence: 1,
    job,
    draft_reply: reply,
    question_back: null,
    hold_reason:
      id === 'v-004'
        ? 'This person wants Maya specifically, not a good answer. Maya decides.'
        : null,
    refusal:
      id === 'v-003'
        ? {
            why: 'They are pregnant or nursing and asking what is safe. Maya is not the person to answer that.',
            refer_to: 'a pharmacist or your GP',
          }
        : null,
    card_id: null,
    basket_summary: id === 'v-001' ? 'Red Reset £32 · SPF 50 £26 · £58' : null,
    source: 'voice',
    voice: {
      audio_url: `/api/voice/${file}`,
      file,
      seconds,
      transcript,
      stt_model: 'whisper-1',
      transcribe_ms: ms,
      tts_model: 'tts-1',
      tts_voice: ttsVoice,
      tts_script: script,
      verbatim_match: id === 'v-004',
      synthetic: true,
      disclosure: DISCLOSURE,
      who_did_what: WHO_DID_WHAT,
    },
  }
})

const queueCards: QueueCard[] = [
  ...build(answeredRows, 'answered', 1),
  ...build(askedRows, 'asked_back', 31),
  ...build(heldRows, 'held', 40),
  ...build(referredRows, 'referred', 44),
  ...voiceCards,
]

export const mockQueue: QueuePayload = {
  cached: true,
  ms: 850,
  /* 54, not 50: the four voice notes are ordinary messages and they count.
     These have to agree with queueCards or the tabs and the list disagree. */
  stats: {
    dms: 54,
    judgments: 270,
    seconds: 0.92,
    answered: 32,
    asked_back: 9,
    held: 5,
    referred: 8,
    handled_pct: 76,
    held_pct: 9,
    referred_pct: 15,
    at_real_volume: {
      dms_per_month: 4800,
      handled: 3648,
      held_per_day: 15,
      referred: 720,
    },
    header_line: 'you approved 32 replies in 4 minutes',
  },
  cards: queueCards,
}

export const mockQueueAction = (
  action: 'send' | 'edit' | 'hold',
): QueueActionResponse => ({
  ok: true,
  action,
  correction_written: action === 'edit',
  standard_moved: action === 'edit' ? 'price_refusal +0.1' : null,
})

/* ---------------------------------------------------------- 5. CARDS */

const mockCards: Record<string, CardPayload> = {
  'c-jessica': {
    cached: false,
    ms: 610,
    re_decided_at: new Date().toISOString(),
    card_id: 'c-jessica',
    parent_card_id: null,
    asker: {
      name: '@jessica',
      said: 'I already have the night serum. Do I need the barrier cream too?',
      skin: ['normal'],
      budget: 80,
      owns: ['Night Serum'],
    },
    verdict: {
      headline: 'No. Just the SPF.',
      in_her_voice: 'No. Just the SPF. Twenty-six pounds.',
      is_refusal: true,
    },
    basket: [
      { product: 'SPF 50', price: '£26', type: 'SPF', ref: 'E-04.5', maya_note: 'Non-negotiable.', affiliate: true, why: 'Her defended category. The one thing she will not cut.' },
    ],
    total: '£26',
    unspent: { amount: '£54', line: 'She left £54 of your £80 on the table.' },
    left_out: [
      { product: 'Barrier Cream', price: '£34', why: 'You already have the night serum doing that job.', instead: 'Nothing. Save it.' },
      { product: 'Glass Drop', price: '£62', why: 'She rates it 8 out of 10 and still will not tell you to buy it.', instead: 'Her words: "Good. Not £62 good."' },
    ],
    ceiling: {
      band: 'about £50–55',
      provenance: "Estimated from Maya's own posts — she sets the line",
      evidence_ref: 'E-04.6',
    },
    money_line: { affiliate_count: 1, basket_value: '£26', note: '1 of 1 products is affiliate-linked.' },
    indifference_band: 'Between £40 and £80 her answer does not change.',
    og_image: '/api/card/c-jessica/og.png',
    share_url: '/c/c-jessica',
  },
  'c-sister': {
    cached: false,
    ms: 580,
    re_decided_at: new Date().toISOString(),
    card_id: 'c-sister',
    parent_card_id: 'c-jessica',
    asker: {
      name: 'Her sister',
      said: 'Forwarded from @jessica — oily skin, £40 to spend.',
      skin: ['oily'],
      budget: 40,
      owns: [],
    },
    verdict: {
      headline: 'Same card. Different answer.',
      in_her_voice: 'SPF 50. Twenty-six pounds. You do not need the gel yet.',
      is_refusal: false,
    },
    basket: [
      { product: 'SPF 50', price: '£26', type: 'SPF', ref: 'E-04.5', maya_note: 'Non-negotiable.', affiliate: true, why: 'Oily or not, this is the one she defends.' },
    ],
    total: '£26',
    unspent: { amount: '£14', line: 'She left £14 of your £40 on the table.' },
    left_out: [
      { product: 'Daily Gel', price: '£24', why: 'Adding a moisturiser to oily skin before you have worn SPF for a month is guessing.', instead: 'Come back in a month. If you are still shiny, Daily Gel.' },
      { product: 'Clear Wash', price: '£20', why: 'The cleanser genuinely does not matter.', instead: 'Whatever is already in your shower.' },
    ],
    ceiling: { band: 'about £50–55', provenance: "Estimated from Maya's own posts — she sets the line", evidence_ref: 'E-04.6' },
    money_line: { affiliate_count: 1, basket_value: '£26', note: '1 of 1 products is affiliate-linked.' },
    indifference_band: 'Between £26 and £60 her answer does not change.',
    og_image: '/api/card/c-sister/og.png',
    share_url: '/c/c-sister',
  },
  'c-mum': {
    cached: false,
    ms: 640,
    re_decided_at: new Date().toISOString(),
    card_id: 'c-mum',
    parent_card_id: 'c-jessica',
    asker: {
      name: 'Her mum',
      said: 'Forwarded from @jessica — dry skin, £100 to spend.',
      skin: ['dry'],
      budget: 100,
      owns: [],
    },
    verdict: {
      headline: 'Two things. Keep the rest.',
      in_her_voice: 'Cloud Cream and the SPF. Sixty-four. Keep the other thirty-six.',
      is_refusal: false,
    },
    basket: [
      { product: 'Cloud Cream', price: '£38', type: 'Moisturiser', ref: 'E-04.1', maya_note: 'My winter skin saviour.', affiliate: true, why: 'Dry skin is the one case where she spends on moisturiser.' },
      { product: 'SPF 50', price: '£26', type: 'SPF', ref: 'E-04.5', maya_note: 'Non-negotiable.', affiliate: true, why: 'Her defended category.' },
    ],
    total: '£64',
    unspent: { amount: '£36', line: 'She left £36 of your £100 on the table.' },
    left_out: [
      { product: 'Glass Drop', price: '£62', why: 'It fits the budget and she still will not recommend it.', instead: 'Her words: "Good. Not £62 good."' },
      { product: 'Oil Balm', price: '£29', why: 'Beautiful, but too much on top of Cloud Cream.', instead: 'Nothing. Two products is the routine.' },
    ],
    ceiling: { band: 'about £50–55', provenance: "Estimated from Maya's own posts — she sets the line", evidence_ref: 'E-04.6' },
    money_line: { affiliate_count: 2, basket_value: '£64', note: '2 of 2 products are affiliate-linked.' },
    indifference_band: 'Between £64 and £120 her answer does not change.',
    og_image: '/api/card/c-mum/og.png',
    share_url: '/c/c-mum',
  },
  'c-priya': {
    cached: false,
    ms: 655,
    re_decided_at: new Date().toISOString(),
    card_id: 'c-priya',
    parent_card_id: null,
    asker: {
      name: '@priya',
      said: 'Every time I try something new my face freaks out. Sensitive, quite red, £80.',
      skin: ['sensitive', 'redness'],
      budget: 80,
      owns: [],
    },
    verdict: {
      headline: 'Calm it first. Then nothing for a month.',
      in_her_voice: 'Red Reset and the SPF. Fifty-eight. Then stop adding things.',
      is_refusal: false,
    },
    basket: [
      { product: 'Red Reset', price: '£32', type: 'Serum', ref: 'E-04.3', maya_note: 'For angry skin days.', affiliate: false, why: 'Redness fires her one hard routing rule.' },
      { product: 'SPF 50', price: '£26', type: 'SPF', ref: 'E-04.5', maya_note: 'Non-negotiable.', affiliate: true, why: 'Her defended category — and redness gets worse in sun.' },
    ],
    total: '£58',
    unspent: { amount: '£22', line: 'She left £22 of your £80 on the table.' },
    left_out: [
      { product: 'Night Serum', price: '£42', why: 'Texture work on angry skin is how you end up back here.', instead: 'Nothing yet. Ask again in a month.' },
      { product: 'Cloud Cream', price: '£38', why: 'Rich and fragranced is the wrong bet on sensitive skin.', instead: 'If you are tight after cleansing, Daily Gel at £24.' },
    ],
    ceiling: { band: 'about £50–55', provenance: "Estimated from Maya's own posts — she sets the line", evidence_ref: 'E-04.6' },
    money_line: { affiliate_count: 1, basket_value: '£58', note: '1 of 2 products is affiliate-linked.' },
    indifference_band: 'Between £58 and £100 her answer does not change.',
    og_image: '/api/card/c-priya/og.png',
    share_url: '/c/c-priya',
  },
}

export function mockCard(cardId: string): CardPayload {
  const hit = mockCards[cardId]
  if (hit) return { ...hit, re_decided_at: new Date().toISOString() }
  /* Unknown id — serve the cold-open card under the requested id so
     nothing on stage can 404. */
  return {
    ...mockCards['c-jessica'],
    card_id: cardId,
    re_decided_at: new Date().toISOString(),
    og_image: `/api/card/${cardId}/og.png`,
    share_url: `/c/${cardId}`,
  }
}

/* "Do it for me instead" and POST /api/ask both mint a child card.
   Offline we pick the frozen card that matches the constraints. */
export function mockDecideCardId(skin: string[], budget: number): string {
  if (skin.includes('redness') || skin.includes('sensitive')) return 'c-priya'
  if (skin.includes('oily') || skin.includes('combination')) return 'c-sister'
  if (skin.includes('dry')) return budget >= 100 ? 'c-mum' : 'c-mum'
  return 'c-jessica'
}

export function mockRedecide(parentId: string, skin: string[], budget: number): CardPayload {
  const base = mockCard(mockDecideCardId(skin, budget))
  return { ...base, parent_card_id: parentId }
}

export function mockAsk(skin: string[], budget: number): AskResponse {
  return { card_id: mockDecideCardId(skin, budget), ms: 620 }
}

/* ---------------------------------------------------------- 6. ONBOARD */

export const mockOnboard: OnboardPayload = {
  cached: true,
  ms: 670,
  handle: '@mayarao',
  heard: [
    { trait: 'The fewest possible products', caption: 'my 5 minute morning routine. two products. that is it.', evidence_ref: 'E-03.5', confidence: 0.94, slot_key: 'routine_size' },
    { trait: 'Price is central to her judgement', caption: 'luxury vs drugstore: where should your money go?', evidence_ref: 'E-03.4', confidence: 0.91, slot_key: 'price_refusal' },
    { trait: 'She subtracts before she adds', caption: 'if your face freaks out, stop adding things.', evidence_ref: 'E-03.3', confidence: 0.86, slot_key: 'subtraction' },
    { trait: 'She leaves money unspent', caption: '3 things i would repurchase with £50', evidence_ref: 'E-03.1', confidence: 0.88, slot_key: 'budget_behaviour' },
    { trait: 'Actively sceptical of hype', caption: 'things i bought because tiktok told me to', evidence_ref: 'E-03.2', confidence: 0.96, slot_key: 'hype' },
    { trait: 'SPF is the category she defends', caption: 'spend it on sunscreen. everything else is negotiable.', evidence_ref: 'E-04.5', confidence: 1.0, slot_key: 'defended_category' },
  ],
  accuracy: '89% correct against her documented self',
  first_verdict_card_id: 'c-jessica',
}

/* An override re-ranks the queue. Offline we reorder honestly: turning
   routine_size up promotes multi-product baskets, turning price_refusal
   down moves the value questions out of the top. */
export function mockOverride(overrides: Record<string, number>): QueuePayload {
  const keys = Object.keys(overrides)
  if (keys.length === 0) return mockQueue
  const weight = (c: QueueCard) => {
    let w = c.confidence
    if ('routine_size' in overrides) {
      const items = (c.basket_summary ?? '').split('+').length
      w += (overrides.routine_size > 1 ? 0.2 : -0.2) * (items - 1)
    }
    if ('price_refusal' in overrides) {
      w += (overrides.price_refusal > 1 ? 0.25 : -0.25) * (c.job === 'value' ? 1 : 0)
    }
    if ('subtraction' in overrides) {
      w += (overrides.subtraction > 0.5 ? 0.2 : -0.2) * (c.job === 'do_i_need_it' ? 1 : 0)
    }
    return w
  }
  const cards = [...mockQueue.cards].sort((a, b) => weight(b) - weight(a))
  return {
    ...mockQueue,
    cached: true,
    ms: 120,
    cards,
    stats: { ...mockQueue.stats, header_line: 'her standard moved — the queue re-ranked' },
  }
}
