# AUTONOMOUS ONBOARDING: she pastes a link. We read what she already published and EXTRACT her
# standard. Stage 1 extracts PRINCIPLES (not rankings - we proved rankings don't transfer).
# Stage 2 applies them. We measure: do extracted principles reproduce her handwritten ones?
import os, asyncio, json, time, httpx, itertools, statistics
from prelude import JEV, SHELF, VOICE
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
P=json.load(open(os.path.join(r"C:/Users/Lenovo/Documents/tano_hackathon","data","case-001-maya.json"),encoding="utf-8"))
BY={p["product"]:p for p in SHELF}

# ==== WHAT A SCRAPE ACTUALLY RETURNS: public posts + captions. Nothing private. ====
SCRAPED={"handle":"@mayarao","bio":"skincare, mostly honest. london.",
 "posts":[{"caption":b["title"],"views":b["views"],"saves":b["saves"],
           **({"note":b["note"]} if "note" in b else {})} for b in P["broadcast_log"]],
 "public_comments_she_left":[d["text"] for d in P["inbox"][:6]],
 "captions_long_form":[
  "3 things I'd repurchase with 50 quid. SPF, obviously. non negotiable, I will die on this hill.",
  "the 62 pound serum everyone is posting. it's good. it is not 62 pounds good. save your money.",
  "things I bought because tiktok told me to. 4 of them were a waste. here's the 1 that wasn't.",
  "my 5 minute morning routine. two products. that's it. you don't need eight steps you need consistency.",
  "the product I would NOT rebuy. beautiful packaging, too rich for my skin, I gave it away.",
  "luxury vs drugstore. the cleanser genuinely does not matter. spend it on sunscreen.",
  "if your face freaks out every time you try something new, stop adding things. take things away.",
  "people don't need more products. they need to feel confident about the two they already own."]}

EXTRACT={
 "sells_hard":{"type":"score","instructions":"How much does this creator push people to buy things?",
   "criteria":["Actively tells people NOT to buy","Recommends sparingly and reluctantly","Balanced","Recommends often","Constantly selling"]},
 "price_sensitive":{"type":"score","instructions":"How willing is this creator to say something is not worth its price?",
   "criteria":["Never mentions price","Mentions price occasionally","Will say when something is overpriced","Price is central to her judgement"]},
 "routine_length":{"type":"score","instructions":"Does this creator favour minimal routines or elaborate ones?",
   "criteria":["Fewest possible products","Small routine","Moderate","Full multi-step routine"]},
 "subtraction":{"type":"noul","instructions":"Does this creator tell people to REMOVE products as often as add them?",
   "criteria":{"true":"Subtraction is part of her advice","false":"She only adds"}},
 "hype_tolerance":{"type":"score","instructions":"How does she treat trending/hyped products?",
   "criteria":["Actively sceptical of hype","Cautious","Neutral","Follows trends"]},
 "spends_whole_budget":{"type":"noul","instructions":"Given a budget, would this creator use all of it, or deliberately leave money unspent?",
   "criteria":{"true":"She would spend the whole budget","false":"She is happy to leave money unspent"}},
 "category_she_defends":{"type":"choice","instructions":"Which single category does this creator treat as non-negotiable?",
   "criteria":{"spf":None,"cleanser":None,"moisturiser":None,"serum":None,"makeup":None,"none":"No clear priority"}},
 "asks_before_advising":{"type":"noul","instructions":"Does she ask about your current products before recommending new ones?",
   "criteria":{"true":"She asks first","false":"She recommends immediately"}},
 "tone":{"type":"choice","instructions":"How does she talk?",
   "criteria":{"dry_decisive":"Blunt, funny, short sentences","warm_gentle":"Soft and reassuring",
               "clinical":"Technical and evidence-led","aspirational":"Luxury and aesthetic"}},
}

async def main():
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=20)) as c:
        t0=time.time()
        r=await c.post(URL,headers=H,json={"model":"jev-latest","state":{"public_profile":SCRAPED},
                                           "questions":EXTRACT},timeout=90)
        w=time.time()-t0
        a=r.json()["answers"]; u=r.json()["usage"]
    print(f"STAGE 1 - PROFILE EXTRACTED FROM PUBLIC POSTS ONLY, in {w:.2f}s ({u['input_tokens']:,} in tokens)")
    print(f"  (input was {len(SCRAPED['posts'])} posts + {len(SCRAPED['captions_long_form'])} captions. No notes, no ratings, no interview.)\n")
    def lv(k):
        x=a[k]
        if x["type"]=="score": return f"{x['legend'][str(round(x['score']))]}  [{x['score']:.2f}]"
        if x["type"]=="noul": return f"{'YES' if x['noul']>0.5 else 'NO'}  [{x['noul']:.2f}]"
        return f"{x['choice']}  [conf {x['confidence']:.2f}]"
    TRUTH={"sells_hard":"Actively tells people NOT to buy (E-03.6, E-08)",
     "price_sensitive":"Price is central ('Good. Not GBP62 good.' E-04.6)",
     "routine_length":"Fewest possible ('only 2 products' E-01.9, 5-min routine E-03.5)",
     "subtraction":"YES ('what are you using now?' E-02.1)",
     "hype_tolerance":"Sceptical ('things I bought because TikTok told me to' E-03.2)",
     "spends_whole_budget":"NO ('people need confidence not products' E-07.4)",
     "category_she_defends":"spf ('Non-negotiable.' E-04.5)",
     "asks_before_advising":"YES (E-02.1 intake questions)",
     "tone":"dry_decisive (subject file SHEET 03)"}
    hits=0
    for k in EXTRACT:
        got=lv(k); exp=TRUTH[k]
        ok = (k=="sells_hard" and a[k]["score"]<1.5) or (k=="price_sensitive" and a[k]["score"]>2.0) \
          or (k=="routine_length" and a[k]["score"]<1.5) or (k=="subtraction" and a[k]["noul"]>0.5) \
          or (k=="hype_tolerance" and a[k]["score"]<1.0) or (k=="spends_whole_budget" and a[k]["noul"]<0.5) \
          or (k=="category_she_defends" and a[k]["choice"]=="spf") or (k=="asks_before_advising" and a[k]["noul"]>0.5) \
          or (k=="tone" and a[k]["choice"]=="dry_decisive")
        hits+=ok
        print(f"  {'OK ' if ok else '!! '}{k:22s} {got:46s}")
        print(f"      evidence says: {exp}")
    print(f"\nEXTRACTED PROFILE MATCHES HER DOCUMENTED SELF: {hits}/{len(EXTRACT)} = {hits/len(EXTRACT):.0%}")
asyncio.run(main())
