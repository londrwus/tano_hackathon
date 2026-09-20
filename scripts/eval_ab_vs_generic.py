# "How do I know this isn't ChatGPT?" -> run the SAME wall with Maya's standard vs a generic
# good-taste dermatologist. If the top-20 overlap is high, Maya is decoration.
import asyncio, json, httpx, random, statistics, time
random.seed(21)
from prelude import JEV, SHELF, VOICE
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
W=json.load(open("obf_with_ingredients.json",encoding="utf-8"))
BAD=("body","hand","foot","hair","shampoo","deodorant","baby","shaving")
W=[p for p in W if not any(b in (p.get("product_name","")+" "+" ".join(p.get("categories_tags_en",[]))).lower() for b in BAD)]
S=random.sample(W,50)

MAYA={"name":"Maya Rao","voice":VOICE["style_rules"],"creed":VOICE["creed"],
      "her_own_shelf":[{"product":p["product"],"gbp":p["gbp"],"maya_rating":p["maya_rating"],"maya_note":p["maya_note"]} for p in SHELF],
      "how_she_decides":["Refuses on price even when she rates something highly - 'Good. Not GBP62 good.'",
        "Rewards the unremarkable - her cleanser note is 'Boring in the best way.'",
        "Avoids fragrance for sensitive skin.","Answers a shade question with a question: what are you using now?",
        "Diagnoses by complaint: what do you HATE about your current one?",
        "People do not need more products. They need confidence."]}
DERM={"name":"A generic good-taste dermatologist","voice":["evidence-based","cautious","thorough"],
      "creed":"Recommend what is clinically sound and well formulated.",
      "how_she_decides":["Prefers well-studied actives and good formulation.","Avoids irritants.",
        "Values SPF and barrier support.","Sceptical of unsupported marketing claims."]}

def payload(judge, items):
    st={"judge":judge,"candidates":{p["code"]:{"name":p["product_name"],"brand":p["brands"],
        "size":p.get("quantity",""),"ingredients":(p.get("_ing") or "")[:800]} for p in items}}
    qs={p["code"]:{"type":"score","instructions":f"How enthusiastically would `judge` tell their audience about `candidates.{p['code']}`?",
        "criteria":["Would warn people off it","Nothing to say about it","Only if asked",
                    "Would recommend it to the right person","Would champion it"]} for p in items}
    return {"model":"jev-latest","state":st,"questions":qs}

async def run(c,judge):
    out={}
    chunks=[S[i:i+25] for i in range(0,len(S),25)]
    rs=await asyncio.gather(*[c.post(URL,headers=H,json=payload(judge,ch),timeout=120) for ch in chunks])
    for r in rs:
        for k,v in r.json()["answers"].items(): out[k]=v["score"]
    return out

async def main():
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=30)) as c:
        t0=time.time(); m,d=await asyncio.gather(run(c,MAYA),run(c,DERM)); w=time.time()-t0
    names={p["code"]:f"{p['brands'][:14]} {p['product_name'][:26]}" for p in S}
    print(f"{len(S)} real products judged twice ({len(S)*2} judgments) in {w:.2f}s\n")
    for k in [10,20]:
        mt=set(sorted(m,key=lambda x:-m[x])[:k]); dt=set(sorted(d,key=lambda x:-d[x])[:k])
        ov=len(mt&dt)/k
        print(f"TOP-{k} OVERLAP: {len(mt&dt)}/{k} = {ov:.0%}   {'<-- MAYA IS DECORATION' if ov>0.7 else '<-- genuinely different judge'}")
    ka=[m[x] for x in m]; kb=[d[x] for x in m]
    ma,mb=statistics.mean(ka),statistics.mean(kb)
    num=sum((x-ma)*(y-mb) for x,y in zip(ka,kb)); den=(sum((x-ma)**2 for x in ka)*sum((y-mb)**2 for y in kb))**.5
    print(f"CORRELATION: {num/den:+.3f}\n")
    diff=sorted(m,key=lambda x:-(m[x]-d[x]))
    print("MAYA LIKES IT MUCH MORE THAN THE DERMATOLOGIST DOES:")
    for x in diff[:5]: print(f"   maya {m[x]:.2f} vs derm {d[x]:.2f}  ({m[x]-d[x]:+.2f})  {names[x]}")
    print("\nTHE DERMATOLOGIST LIKES IT MUCH MORE THAN MAYA DOES:")
    for x in diff[-5:]: print(f"   maya {m[x]:.2f} vs derm {d[x]:.2f}  ({m[x]-d[x]:+.2f})  {names[x]}")
asyncio.run(main())
