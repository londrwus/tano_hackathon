/* /c/:id — THE VERDICT CARD. The thing people forward.
   560px, phone-first. Money is whatever string the API returned — it is
   never formatted, rounded or recomputed here, so a decimal pound can
   never appear. Confidence is never printed.

   The refusal is the emotional centre of the card: a calm blush tile
   with her own words and the thing she would buy instead. Not a stamp. */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { getCard, postRedecide } from '../api/client'
import type { CardPayload, LeftOutRow } from '../api/types'
import { ArrowIcon, CheckIcon, MinusIcon, ShieldIcon } from '../components/bits'
import { setCardMeta } from '../components/meta'
import './card.css'

/* The live API sends a little more than the frozen contract lists. We
   read the extras when they are there and never depend on them. */
interface LeftOutRowPlus extends LeftOutRow {
  reason_code?: string
  ref?: string
}

const SKIN: { key: string; label: string }[] = [
  { key: 'dry', label: 'Dry' },
  { key: 'oily', label: 'Oily' },
  { key: 'combination', label: 'Combination' },
  { key: 'sensitive', label: 'Sensitive' },
  { key: 'redness', label: 'Redness' },
]
const BUDGETS = [30, 60, 100]
const NOTHING = 'Nothing yet'
const OWNS = [NOTHING, 'SPF 50', 'Night Serum']

/* The cold-open card is shown clean: the verdict and nothing to fiddle
   with. Every other card — Priya, her sister, her mum, and any child card
   minted by a re-decide — keeps "Do it for me instead", because working
   the answer out again for whoever is reading is a beat we still need.

   This is an id, not a property, because the payload has none to hang it
   on: c-jessica and c-priya come back structurally identical. The contract
   is where the distinction lives (docs/10-API-CONTRACT.md § fixtures:
   "c-jessica — Beat 1, the cold-open refusal"). Matching on the card's OWN
   id and not the route param is what keeps a child of c-jessica — which is
   minted with a fresh hashed id — on the normal path. */
const COLD_OPEN_CARD = 'c-jessica'

/* Whole pounds, straight off the payload's integer. Never a decimal. */
const pounds = (n: number) => `£${Math.round(n)}`

/* The no that carries the card. First choice is the one she turned down
   on price — her verbatim "Good. Not £62 good." — by the reason the API
   gave, or by her own wording when this copy of the API sends no reason.
   Failing both, the dearest thing she still said no to. The digits are
   only ever used to sort; the price on screen is the API's own string. */
const pence = (price: string) => Number((price.match(/\d[\d,]*/) ?? ['0'])[0].replace(/,/g, ''))

function heroIndex(rows: LeftOutRowPlus[]): number {
  const byCode = rows.findIndex((r) => r.reason_code === 'over_her_price_line')
  if (byCode >= 0) return byCode
  const byWords = rows.findIndex((r) => /\bnot\s+£/i.test(r.why))
  if (byWords >= 0) return byWords
  if (!rows.length) return -1
  return rows.reduce((best, r, i) => (pence(r.price) > pence(rows[best].price) ? i : best), 0)
}

export default function Card() {
  const { id = 'c-jessica' } = useParams()
  const navigate = useNavigate()

  const [data, setData] = useState<CardPayload | null>(null)
  const [busy, setBusy] = useState(false)

  const [skin, setSkin] = useState<string[]>([])
  const [budget, setBudget] = useState<number | null>(null)
  const [owns, setOwns] = useState<string[]>([])

  useEffect(() => {
    let alive = true
    setData(null)
    setSkin([])
    setBudget(null)
    setOwns([])
    getCard(id).then(({ data }) => {
      if (!alive) return
      setData(data)
    })
    return () => {
      alive = false
    }
  }, [id])

  /* Per-card share preview, so a forwarded link has its own image. */
  useEffect(() => {
    if (!data) return
    setCardMeta({
      title: `${data.verdict.headline} — Maya’s answer`,
      description: data.verdict.in_her_voice,
      ogImage: data.og_image,
      url: data.share_url,
    })
  }, [data])

  const toggleSkin = useCallback((s: string) => {
    setSkin((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]))
  }, [])
  const toggleOwns = useCallback((o: string) => {
    if (o === NOTHING) {
      setOwns([])
      return
    }
    setOwns((cur) => (cur.includes(o) ? cur.filter((x) => x !== o) : [...cur, o]))
  }, [])

  const canRedecide = skin.length > 0 && budget !== null

  const redecide = async () => {
    if (!data || !canRedecide) return
    setBusy(true)
    const { data: child } = await postRedecide(data.card_id, {
      skin,
      budget: budget as number,
      owns,
    })
    setBusy(false)
    if (child.card_id && child.card_id !== data.card_id) {
      navigate(`/c/${child.card_id}`)
    } else {
      setData(child)
    }
  }

  const askedFor = useMemo(() => {
    if (!data) return ''
    const bits: string[] = []
    if (data.asker.skin.length) bits.push(data.asker.skin.join(' and ') + ' skin')
    bits.push(`${pounds(data.asker.budget)} to spend`)
    if (data.asker.owns.length) bits.push(`already has ${data.asker.owns.join(', ')}`)
    return bits.join(' · ')
  }, [data])

  if (!data) {
    return (
      <div className="cardpage">
        <p className="loading-note">Working out her answer…</p>
      </div>
    )
  }

  const leftOut = data.left_out as LeftOutRowPlus[]
  const heroIdx = heroIndex(leftOut)
  const hero = heroIdx >= 0 ? leftOut[heroIdx] : null
  const rest = leftOut.filter((_, i) => i !== heroIdx)
  const refused = data.verdict.is_refusal
  const offerRedecide = data.card_id !== COLD_OPEN_CARD

  return (
    <div className={`cardpage${offerRedecide ? '' : ' cardpage-solo'}`}>
      <article className="vcard stagger" aria-label="Maya’s answer">
        {/* ---- who asked, and what they asked ---- */}
        <header className="v-who">
          <span className="v-who-name">{data.asker.name}</span>
          <p className="v-who-said">“{data.asker.said}”</p>
          <p className="v-who-meta">{askedFor}</p>
          {data.parent_card_id && (
            <p className="v-who-meta">Worked out again from an earlier answer.</p>
          )}
        </header>

        {/* ---- the verdict ---- */}
        <section className={`v-verdict tile ${refused ? 'tile-blush' : 'tile-mint'}`}>
          <span className={`v-verdict-tag ${refused ? 'ink-blush' : 'ink-mint'}`}>
            {refused ? <ShieldIcon size={16} /> : <CheckIcon size={16} />}
            <span>{refused ? 'She said no to most of it' : 'What she would buy you'}</span>
          </span>
          <h1 className="v-verdict-h">{data.verdict.headline}</h1>
          <p className="v-verdict-voice">“{data.verdict.in_her_voice}”</p>
        </section>

        {/* ---- the basket ---- */}
        <section className="v-block">
          <h2 className="v-h">What she would put in the bag</h2>
          <ul className="v-basket">
            {data.basket.map((b) => (
              <li className="v-buy" key={b.ref + b.product}>
                <div className="v-buy-top">
                  <span className="v-buy-name">{b.product}</span>
                  <span className="v-buy-price num">{b.price}</span>
                </div>
                <p className="v-buy-note">“{b.maya_note}”</p>
                <p className="v-buy-ref">
                  {b.type} · {b.ref} ·{' '}
                  {b.affiliate ? 'she earns on this one' : 'she earns nothing on this one'}
                </p>
              </li>
            ))}
          </ul>
          <div className="v-total">
            <span>Total</span>
            <span className="v-total-value num">{data.total}</span>
          </div>
        </section>

        {/* ---- what she left unspent ---- */}
        <section className="v-unspent tile tile-butter">
          <span className="v-unspent-label ink-butter">
            <MinusIcon size={16} />
            <span>Left unspent</span>
          </span>
          <span className="v-unspent-amount ink-butter num">{data.unspent.amount}</span>
          <p className="v-unspent-line">{data.unspent.line}</p>
        </section>

        {/* ---- what she left out, always with the alternative ---- */}
        <section className="v-block">
          <h2 className="v-h">What she left out — and what instead</h2>

          {hero && (
            <div className="v-no tile tile-blush">
              <span className="v-no-tag ink-blush">
                <ShieldIcon size={16} />
                <span>She turned this one down</span>
              </span>
              <div className="v-no-top">
                <span className="v-no-name">{hero.product}</span>
                <span className="v-no-price num">{hero.price}</span>
              </div>
              <p className="v-no-why">“{hero.why}”</p>
              <p className="v-no-instead">
                <span className="v-no-arrow" aria-hidden="true">
                  <ArrowIcon size={16} />
                </span>
                <span>{hero.instead}</span>
              </p>
            </div>
          )}

          <ul className="v-outs">
            {rest.map((l) => (
              <li className="v-out" key={l.product}>
                <div className="v-out-top">
                  <span className="v-out-name">{l.product}</span>
                  <span className="v-out-price num">{l.price}</span>
                </div>
                <p className="v-out-why">{l.why}</p>
                <p className="v-out-instead">
                  <span className="v-no-arrow" aria-hidden="true">
                    <ArrowIcon size={14} />
                  </span>
                  <span>{l.instead}</span>
                </p>
              </li>
            ))}
          </ul>
        </section>

        {/* ---- her ceiling, and where the number came from ---- */}
        <section className="v-block v-ceiling">
          <h2 className="v-h">The most she would ever pay for this</h2>
          <div className="v-band tile tile-lilac">
            <span className="v-band-value ink-lilac num">{data.ceiling.band}</span>
          </div>
          <p className="v-prov">
            {data.ceiling.provenance} · <span className="ref">{data.ceiling.evidence_ref}</span>
          </p>
        </section>

        {/* ---- the money line ---- */}
        <section className="v-money">
          <h2 className="v-h">Where the money goes</h2>
          <p className="v-money-note">{data.money_line.note}</p>
          <p className="v-money-strip">
            <span>What she picked comes to</span>
            <span className="num">{data.money_line.basket_value}</span>
          </p>
        </section>

        {/* ---- the band where her answer stops changing ---- */}
        <p className="v-indiff">{data.indifference_band}</p>
      </article>

      {/* ---- do it for me instead: every card but the cold open ---- */}
      {offerRedecide && (
        <section className="card vredo enter delay-4" aria-label="Do it for me instead">
          <h2 className="t-title3 vredo-h">Do it for me instead</h2>
          <p className="vredo-sub">Same answer, worked out for your skin and your money.</p>

          <div className="vredo-group">
            <h3 className="vredo-label">
              Your skin <span className="vredo-hint">pick as many as you like</span>
            </h3>
            <div className="vredo-chips">
              {SKIN.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  className="chip vredo-chip"
                  aria-pressed={skin.includes(s.key)}
                  onClick={() => toggleSkin(s.key)}
                >
                  <span className="vredo-tick" aria-hidden="true">
                    {skin.includes(s.key) ? <CheckIcon size={15} /> : null}
                  </span>
                  <span>{s.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="vredo-group">
            <h3 className="vredo-label">What you want to spend</h3>
            <div className="vredo-chips">
              {BUDGETS.map((b) => (
                <button
                  key={b}
                  type="button"
                  className="chip vredo-chip vredo-chip-mint"
                  aria-pressed={budget === b}
                  onClick={() => setBudget(b)}
                >
                  <span className="vredo-tick" aria-hidden="true">
                    {budget === b ? <CheckIcon size={15} /> : null}
                  </span>
                  <span>{pounds(b)}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="vredo-group">
            <h3 className="vredo-label">What you already have</h3>
            <div className="vredo-chips">
              {OWNS.map((o) => (
                <button
                  key={o}
                  type="button"
                  className="chip vredo-chip vredo-chip-sky"
                  aria-pressed={o === NOTHING ? owns.length === 0 : owns.includes(o)}
                  onClick={() => toggleOwns(o)}
                >
                  <span className="vredo-tick" aria-hidden="true">
                    {(o === NOTHING ? owns.length === 0 : owns.includes(o)) ? (
                      <CheckIcon size={15} />
                    ) : null}
                  </span>
                  <span>{o}</span>
                </button>
              ))}
            </div>
          </div>

          <button
            type="button"
            className="btn btn-primary vredo-go"
            disabled={!canRedecide || busy}
            onClick={redecide}
          >
            {busy ? 'Working it out…' : 'Get my own answer'}
          </button>
        </section>
      )}
    </div>
  )
}
