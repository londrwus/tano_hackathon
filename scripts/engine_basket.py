# FIX: a DEFENDED CATEGORY (onboarding extracted "spf", confidence 1.00) is a HARD CONSTRAINT
# in the enumeration, not a preference for Jev to weigh. Code enforces her non-negotiables.
import os, asyncio, json, time, httpx, itertools, statistics
from prelude import JEV, SHELF, VOICE
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
BY={p["product"]:p for p in SHELF}
DEFENDED="SPF"                      # <- comes from engine_onboarding.py, conf 1.00
DEF_ITEMS=[p["product"] for p in SHELF if p["type"]==DEFENDED]
CHEAPEST_DEF=min(BY[x]["gbp"] for x in DEF_ITEMS)

ROUTING=[{"condition":"DRY","she_reaches_for":["Cloud Cream","Oil Balm"]},
         {"condition":"OILY","she_reaches_for":["Daily Gel","Clear Wash"]},
         {"condition":"SENSITIVE","rule":"avoid fragrance"},
         {"condition":"REDNESS","she_reaches_for":["Red Reset"]}]
def jstate(name,creed,decides,routing=None,defended=None):
    d={"name":name,"creed":creed,
       "her_shelf":[{"product":p["product"],"gbp":p["gbp"],"type":p["type"],"skin":p["skin"],
                     "maya_rating":p["maya_rating"],"maya_note":p["maya_note"]} for p in SHELF],
       "how_she_decides":decides}
    if routing: d["her_written_routing_rules"]=routing
    if defended: d["her_non_negotiable_category"]=defended
    return d
MAYA=jstate("Maya Rao","People do not need more products. They need confidence.",
 ["Apply `her_written_routing_rules` FIRST - her own handwriting, not optional.",
  "`her_non_negotiable_category` goes in the basket before anything else.",
  "She refuses on price even when she rates something highly.",
  "Fewer steps beats more steps.","She does NOT spend the whole budget just because it is there.",
  "Half her advice is subtraction."], ROUTING, DEFENDED)
MAYA["voice"]=VOICE["style_rules"]
DERM=jstate("A board-certified dermatologist with good taste","Recommend a clinically sound routine.",
 ["Prefers well-studied actives.","Avoids irritants.","Values SPF, cleanser and moisturiser as the base."])

def feasible(budget, owns, mx, enforce=True):
    pool=[p["product"] for p in SHELF if p["product"] not in owns]
    owns_def = any(BY[o]["type"]==DEFENDED for o in owns if o in BY)
    out=[]
    for k in range(1,mx+1):
        for c in itertools.combinations(pool,k):
            if sum(BY[x]["gbp"] for x in c)>budget: continue
            if enforce and not owns_def and budget>=CHEAPEST_DEF:
                if not any(BY[x]["type"]==DEFENDED for x in c): continue   # HARD CONSTRAINT
            out.append(c)
    return out

def spay(judge,sh,combos):
    st={"judge":judge,"shopper":sh,
        "baskets":{f"b{i}":{"items":[{"product":x,"gbp":BY[x]["gbp"],"type":BY[x]["type"],"skin":BY[x]["skin"]} for x in c],
                            "total_gbp":sum(BY[x]["gbp"] for x in c)} for i,c in enumerate(combos)}}
    return {"model":"jev-latest","state":st,"questions":{f"b{i}":{"type":"score",
      "instructions":f"Would `judge` send `baskets.b{i}` to `shopper`? Judge the SET.",
      "criteria":["Wrong for this person","Defensible but not their pick","Reasonable","Good","Exactly what they would send"]} for i in range(len(combos))}}
def cpay(judge,sh,fin):
    return {"model":"jev-latest","state":{"judge":judge,"shopper":sh,
      "finalists":{f"b{i}":{"items":list(c),"total_gbp":sum(BY[x]["gbp"] for x in c)} for i,c in enumerate(fin)}},
      "questions":{"pick":{"type":"choice","instructions":"Which one of `finalists` would `judge` actually send to `shopper`?",
        "criteria":{f"b{i}":" + ".join(c) for i,c in enumerate(fin)}}}}

async def decide(c,judge,sh,enforce):
    combos=feasible(sh["budget_gbp"],sh["owns"],sh["max_items"],enforce)
    if not combos: return None,0,0
    CH=70; chs=[combos[i:i+CH] for i in range(0,len(combos),CH)]
    rs=await asyncio.gather(*[c.post(URL,headers=H,json=spay(judge,sh,ch),timeout=120) for ch in chs])
    sc={}
    for ch,r in zip(chs,rs):
        a=r.json()["answers"]
        for i,cb in enumerate(ch): sc[cb]=a[f"b{i}"]["score"]
    fin=sorted(sc,key=lambda k:-sc[k])[:8]
    r2=await c.post(URL,headers=H,json=cpay(judge,sh,fin),timeout=120)
    a=r2.json()["answers"]["pick"]
    return fin[int(a["choice"][1:])], a["confidence"], len(combos)

SH=[("@gracelee",{"says":"dry skin + redness, GBP60","skin":"dry with redness","budget_gbp":60,"owns":[],"max_items":4}),
    ("@joanna",{"says":"only 2 products","skin":"normal","budget_gbp":120,"owns":[],"max_items":2}),
    ("@jessica",{"says":"already have the night serum","skin":"normal","budget_gbp":80,"owns":["Night Serum"],"max_items":3}),
    ("Priya",{"says":"my face freaks out","skin":"very sensitive","budget_gbp":80,"owns":[],"max_items":3}),
    ("Emily",{"says":"not spending 100 on serum","skin":"combination","budget_gbp":40,"owns":[],"max_items":3}),
    ("@kate",{"says":"first date Friday HELP","skin":"normal","occasion":"wants to look good tomorrow","budget_gbp":70,"owns":[],"max_items":3}),
    ("owns SPF",{"says":"i already use an spf","skin":"combination","budget_gbp":60,"owns":["SPF 50"],"max_items":3}),
    ("tiny budget",{"says":"i only have 20 quid","skin":"oily","budget_gbp":20,"owns":[],"max_items":2})]

async def main():
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=40)) as c:
        print(f"{'SHOPPER':12s} {'MAYA (constraint ON)':40s} {'was (OFF)':28s} DERM")
        mi=[];di=[];mg=[];dg=[];div=0;spf_hits=0;n=0
        for lab,s in SH:
            (on,c1,n1),(off,c2,n2),(dm,c3,n3)=await asyncio.gather(
                decide(c,MAYA,s,True), decide(c,MAYA,s,False), decide(c,DERM,s,False))
            has=any(BY[x]["type"]==DEFENDED for x in on) or any(BY[o]["type"]==DEFENDED for o in s["owns"] if o in BY)
            spf_hits+=has; n+=1
            print(f"{lab:12s} {' + '.join(on)+f' (GBP{sum(BY[x][chr(103)+chr(98)+chr(112)] for x in on)})':40s} "
                  f"{' + '.join(off)[:27]:28s} {' + '.join(dm)}")
            mi.append(len(on)); di.append(len(dm)); mg.append(sum(BY[x]["gbp"] for x in on)); dg.append(sum(BY[x]["gbp"] for x in dm))
            div += (on!=dm)
        print(f"\nHer non-negotiable ({DEFENDED}) present in {spf_hits}/{n} baskets  (was violated before the fix)")
        print(f"DIVERGENCE from dermatologist: {div}/{n}")
        print(f"MAYA avg {statistics.mean(mi):.1f} products GBP{statistics.mean(mg):.0f}  |  DERM avg {statistics.mean(di):.1f} products GBP{statistics.mean(dg):.0f}")
        print(f"-> Maya sends {statistics.mean(di)-statistics.mean(mi):.1f} fewer products and spends GBP{statistics.mean(dg)-statistics.mean(mg):.0f} less.")
asyncio.run(main())
