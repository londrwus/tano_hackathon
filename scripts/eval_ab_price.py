# Is the PRICE CEILING the part that is actually Maya, rather than a generic good-taste judge?
import asyncio, json, httpx, random, statistics, time
random.seed(21)
from prelude import JEV, SHELF, VOICE
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
W=json.load(open("obf_with_ingredients.json",encoding="utf-8"))
BAD=("body","hand","foot","hair","shampoo","deodorant","baby","shaving")
W=[p for p in W if not any(b in (p.get("product_name","")+" "+" ".join(p.get("categories_tags_en",[]))).lower() for b in BAD)]
S=random.sample(W,16)
RUNGS=list(range(8,92,4))

MAYA={"name":"Maya Rao","voice":VOICE["style_rules"],"creed":VOICE["creed"],
 "her_own_shelf_with_her_price_opinions":[{"product":p["product"],"gbp":p["gbp"],"maya_rating":p["maya_rating"],"maya_note":p["maya_note"]} for p in SHELF],
 "how_she_talks_about_money":("She refuses on price even when she rates something highly: her GBP62 serum is rated 8.1 "
   "and she says 'Good. Not GBP62 good.' She rewards the unremarkable: her GBP22 cleanser is 'Boring in the best way.' "
   "Her SPF is 'Non-negotiable.' She believes people need confidence, not more products.")}
DERM={"name":"A generic good-taste dermatologist","creed":"Recommend what is clinically sound and well formulated.",
 "how_they_talk_about_money":"Prefers good formulation at a reasonable price; sceptical of marketing markups."}

def payload(judge,p):
    st={"judge":judge,"product_under_review":{"name":p["product_name"],"brand":p["brands"],
        "size":p.get("quantity",""),"ingredients":(p.get("_ing") or "")[:800]}}
    return {"model":"jev-latest","state":st,"questions":{f"p{x}":{"type":"noul",
      "instructions":f"If `product_under_review` cost GBP {x}, would `judge` tell their audience to buy it at that price?",
      "criteria":{"true":f"At GBP {x} it is fair for what it does, by their standards",
                  "false":f"At GBP {x} they would say it is not worth that money"}} for x in RUNGS}}

def cross(cur):
    for i in range(1,len(RUNGS)):
        a,b=cur[RUNGS[i-1]],cur[RUNGS[i]]
        if a>=0.5>b: return RUNGS[i-1]+((a-0.5)/(a-b) if a!=b else 0)*(RUNGS[i]-RUNGS[i-1])
    return RUNGS[-1] if cur[RUNGS[0]]>=0.5 else 0

async def main():
    jobs=[(p,"maya",payload(MAYA,p)) for p in S]+[(p,"derm",payload(DERM,p)) for p in S]
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=40)) as c:
        t0=time.time(); rs=await asyncio.gather(*[c.post(URL,headers=H,json=j[2],timeout=120) for j in jobs]); w=time.time()-t0
    M={};D={}
    for (p,who,_),r in zip(jobs,rs):
        j=r.json(); v=cross({x:j["answers"][f"p{x}"]["noul"] for x in RUNGS})
        (M if who=="maya" else D)[p["code"]]=v
    print(f"{len(jobs)*len(RUNGS)} judgments in {w:.2f}s\n")
    print(f"{'PRODUCT':42s} {'MAYA':>6} {'DERM':>6} {'DIFF':>6}")
    diffs=[]
    for p in S:
        c=p["code"]; d=M[c]-D[c]; diffs.append(d)
        print(f"{(p['brands'][:14]+' '+p['product_name'][:26])[:42]:42s} {M[c]:6.0f} {D[c]:6.0f} {d:+6.0f}")
    ka=[M[p['code']] for p in S]; kb=[D[p['code']] for p in S]
    ma,mb=statistics.mean(ka),statistics.mean(kb)
    num=sum((x-ma)*(y-mb) for x,y in zip(ka,kb)); den=(sum((x-ma)**2 for x in ka)*sum((y-mb)**2 for y in kb))**.5
    r=num/den if den else 0
    print(f"\nMean ceiling  Maya GBP{ma:.1f}   Dermatologist GBP{mb:.1f}   Maya is GBP{mb-ma:.1f} {'STRICTER' if ma<mb else 'more generous'}")
    print(f"Mean |diff| per product: GBP{statistics.mean(abs(x) for x in diffs):.1f}")
    print(f"CORRELATION of ceilings: {r:+.3f}")
    print(f"\n=> On TASTE RANKING the two judges agreed 85% (corr +0.86).")
    print(f"=> On PRICE the correlation is {r:+.3f} and Maya is systematically GBP{mb-ma:.0f} stricter.")
asyncio.run(main())
