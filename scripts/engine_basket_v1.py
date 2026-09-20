# THE BASKET ENGINE: Jev judges every FEASIBLE COMBINATION of her shelf, not a ranking.
# Ranking is what a dermatologist does. Choosing a SET under constraints is what Maya does.
import os, asyncio, json, time, httpx, itertools, statistics
from prelude import JEV, SHELF, VOICE
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
BY={p["product"]:p for p in SHELF}

MAYA={"name":"Maya Rao","voice":VOICE["style_rules"],"creed":VOICE["creed"],
 "her_shelf":[{"product":p["product"],"gbp":p["gbp"],"type":p["type"],"skin":p["skin"],
               "finish":p["finish"],"maya_rating":p["maya_rating"],"maya_note":p["maya_note"]} for p in SHELF],
 "how_she_decides":["DRY -> Cloud Cream + Barrier Oil. OILY -> Daily Gel. SENSITIVE -> avoid fragrance. REDNESS -> Red Reset.",
   "She refuses on price even when she rates something highly: 'Good. Not GBP62 good.'",
   "She rewards the unremarkable: 'Boring in the best way.'",
   "Fewer steps beats more steps. She asks 'do you actually care about skincare or do you just want to look hot tomorrow?'",
   "She asks what you are using now BEFORE adding anything. Half her advice is subtraction.",
   "People do not need more products. They need confidence."]}

DERM={"name":"A generic good-taste dermatologist","creed":"Recommend what is clinically sound and well formulated.",
 "her_shelf":MAYA["her_shelf"],
 "how_she_decides":["Prefers well-studied actives and good formulation.","Avoids known irritants.",
   "Values SPF and barrier support.","Builds a complete evidence-based routine."]}

def feasible(budget, owns, max_items, skin_excl=()):
    pool=[p["product"] for p in SHELF if p["product"] not in owns and p["product"] not in skin_excl]
    out=[]
    for k in range(1, max_items+1):
        for combo in itertools.combinations(pool,k):
            if sum(BY[x]["gbp"] for x in combo) <= budget:
                out.append(combo)
    return out

def payload(judge, shopper, combos):
    st={"judge":judge,"shopper":shopper,
        "baskets":{f"b{i}":{"items":[{"product":x,"gbp":BY[x]["gbp"],"type":BY[x]["type"]} for x in c],
                            "total_gbp":sum(BY[x]["gbp"] for x in c)} for i,c in enumerate(combos)}}
    qs={f"b{i}":{"type":"score",
        "instructions":f"Is `baskets.b{i}` the set `judge` would actually give `shopper`? Judge the SET as a whole - what it covers, what it leaves out, whether it is the right number of things for this person, and whether the money is well spent.",
        "criteria":["Wrong for this person","Defensible but not what they would pick",
                    "A reasonable answer","A good answer","Exactly what they would send"]} for i in range(len(combos))}
    return {"model":"jev-latest","state":st,"questions":qs}

async def rank(c, judge, shopper, combos, CH=70):
    chunks=[combos[i:i+CH] for i in range(0,len(combos),CH)]
    rs=await asyncio.gather(*[c.post(URL,headers=H,json=payload(judge,shopper,ch),timeout=120) for ch in chunks])
    out={}
    for ch,r in zip(chunks,rs):
        a=r.json()["answers"]
        for i,combo in enumerate(ch): out[combo]=a[f"b{i}"]["score"]
    return out

SHOPPERS=[
 ("E-01.2 @gracelee", {"says":"i have dry skin + redness and GBP60. tell me what to buy pls",
                       "skin":"dry with redness","budget_gbp":60,"owns":[],"max_items":4}),
 ("E-01.9 @joanna",   {"says":"can you make me a routine but only 2 products bc i will not do 8 steps",
                       "skin":"normal","budget_gbp":120,"owns":[],"max_items":2}),
 ("E-01.5 @jessica",  {"says":"i already have the night serum. do i need the barrier cream too???",
                       "skin":"normal","budget_gbp":80,"owns":["Night Serum"],"max_items":3}),
]

async def main():
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=40)) as c:
        for label,s in SHOPPERS:
            combos=feasible(s["budget_gbp"], s["owns"], s["max_items"])
            t0=time.time()
            m,d=await asyncio.gather(rank(c,MAYA,s,combos), rank(c,DERM,s,combos))
            w=time.time()-t0
            top_m=sorted(m,key=lambda k:-m[k])[:3]; top_d=sorted(d,key=lambda k:-d[k])[:3]
            print(f"\n{'='*74}\n{label}: \"{s['says'][:64]}\"")
            print(f"  {len(combos)} feasible baskets x 2 judges = {len(combos)*2} judgments in {w:.2f}s")
            print(f"  MAYA WOULD SEND : {' + '.join(top_m[0])}  = GBP{sum(BY[x]['gbp'] for x in top_m[0])}  (score {m[top_m[0]]:.2f})")
            print(f"    runner-up     : {' + '.join(top_m[1])}  = GBP{sum(BY[x]['gbp'] for x in top_m[1])}  ({m[top_m[1]]:.2f})")
            print(f"  A DERMATOLOGIST : {' + '.join(top_d[0])}  = GBP{sum(BY[x]['gbp'] for x in top_d[0])}  ({d[top_d[0]]:.2f})")
            same = top_m[0]==top_d[0]
            print(f"  SAME ANSWER? {'YES - generic' if same else 'NO - Maya diverges'}")
            worst=sorted(m,key=lambda k:m[k])[0]
            print(f"  she would NOT send: {' + '.join(worst)} ({m[worst]:.2f})")
        # aggregate divergence over the 3 shoppers
asyncio.run(main())
