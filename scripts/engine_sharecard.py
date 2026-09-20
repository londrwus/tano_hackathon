# THE SHARE: 41% of high-value buyers arrive via a private forward (E-09.4). The receiver has
# never heard of Maya. Does the verdict RE-DECIDE itself for whoever opens it?
import os, asyncio, json, time, httpx, itertools
from prelude import JEV, SHELF, VOICE
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
BY={p["product"]:p for p in SHELF}
MAYA={"name":"Maya Rao","voice":VOICE["style_rules"],"creed":VOICE["creed"],
 "her_shelf":[{"product":p["product"],"gbp":p["gbp"],"type":p["type"],"skin":p["skin"],
               "maya_rating":p["maya_rating"],"maya_note":p["maya_note"]} for p in SHELF],
 "her_routing":[{"c":"DRY","x":["Cloud Cream","Oil Balm"]},{"c":"OILY","x":["Daily Gel","Clear Wash"]},
                {"c":"SENSITIVE","rule":"avoid fragrance"},{"c":"REDNESS","x":["Red Reset"]}],
 "how_she_decides":["Fewer steps beats more.","She does not spend the whole budget just because it is there.",
                    "Half her advice is subtraction.","She refuses on price even when she rates something highly."]}

def feasible(b,owns,mx):
    pool=[p["product"] for p in SHELF if p["product"] not in owns]
    return [c for k in range(1,mx+1) for c in itertools.combinations(pool,k) if sum(BY[x]["gbp"] for x in c)<=b]

def pay(shopper,combos):
    st={"judge":MAYA,"shopper":shopper,
        "baskets":{f"b{i}":{"items":[{"product":x,"gbp":BY[x]["gbp"],"type":BY[x]["type"],"skin":BY[x]["skin"]} for x in c],
                            "total_gbp":sum(BY[x]["gbp"] for x in c)} for i,c in enumerate(combos)}}
    qs={f"b{i}":{"type":"score","instructions":f"Would Maya send `baskets.b{i}` to `shopper`? Judge the SET.",
        "criteria":["Wrong for this person","Defensible but not her pick","Reasonable","Good","Exactly what she would send"]} for i in range(len(combos))}
    return {"model":"jev-latest","state":st,"questions":qs}

PEOPLE=[
 ("SENDER  Priya (sensitive, GBP80)",       {"says":"my face freaks out with everything","skin":"sensitive, reactive","budget_gbp":80,"owns":[],"max_items":3}),
 ("RECEIVER her sister (oily, GBP40)",      {"says":"sent by a friend. oily skin, breakouts, student budget","skin":"oily","budget_gbp":40,"owns":[],"max_items":3}),
 ("RECEIVER her mum (dry, GBP100)",         {"says":"sent by my daughter. dry, mature skin","skin":"dry","budget_gbp":100,"owns":[],"max_items":3}),
 ("RECEIVER colleague (owns SPF, GBP60)",   {"says":"a friend sent me this. i already use an spf","skin":"combination","budget_gbp":60,"owns":["SPF 50"],"max_items":3}),
]
async def main():
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=30)) as c:
        t0=time.time(); tot=0
        for label,s in PEOPLE:
            combos=feasible(s["budget_gbp"],s["owns"],s["max_items"]); tot+=len(combos)
            CH=70; chs=[combos[i:i+CH] for i in range(0,len(combos),CH)]
            rs=await asyncio.gather(*[c.post(URL,headers=H,json=pay(s,ch),timeout=120) for ch in chs])
            sc={}
            for ch,r in zip(chs,rs):
                a=r.json()["answers"]
                for i,cb in enumerate(ch): sc[cb]=a[f"b{i}"]["score"]
            top=sorted(sc,key=lambda k:-sc[k])[0]
            print(f"{label:38s} -> {' + '.join(top):34s} GBP{sum(BY[x]['gbp'] for x in top):3d}")
        print(f"\n{tot} baskets judged in {time.time()-t0:.2f}s")
        print("The SAME shared card resolves to a DIFFERENT answer for each receiver.")
asyncio.run(main())
