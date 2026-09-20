import json, asyncio, httpx, statistics, random
random.seed(11)
from prelude import *
import base64, time
UA={"User-Agent":"tano-hackathon/1.0"}
SAMPLE=random.sample(CAND,60)
SCHEMA={"name":"p","schema":{"type":"object","additionalProperties":False,"properties":{
 "product_name":{"type":"string"},"brand":{"type":"string"},"category":{"type":"string"},
 "texture_or_finish":{"type":"string"},"claims_on_pack":{"type":"array","items":{"type":"string"}},
 "likely_skin_types":{"type":"array","items":{"type":"string"}},
 "fragranced":{"type":"string","enum":["yes","no","unknown"]},
 "positioning":{"type":"string","enum":["drugstore","mid","premium","luxury"]},
 "is_face_skincare":{"type":"boolean"},
 "label_legible":{"type":"boolean","description":"Could you actually read the packaging text?"}},
 "required":["product_name","brand","category","texture_or_finish","claims_on_pack","likely_skin_types","fragranced","positioning","is_face_skincare","label_legible"]},"strict":True}

async def see(c,p,sem):
    async with sem:
        try:
            b=(await c.get(p["image_url"],headers=UA,follow_redirects=True,timeout=60)).content
            if len(b)>4_000_000: return None
            d="data:image/jpeg;base64,"+base64.b64encode(b).decode()
            r=await c.post("https://api.openai.com/v1/chat/completions",headers={"Authorization":f"Bearer {OA}"},timeout=120,
              json={"model":"gpt-4o-mini","messages":[{"role":"user","content":[
                {"type":"text","text":"Extract product attributes. Read packaging text. Set label_legible honestly."},
                {"type":"image_url","image_url":{"url":d,"detail":"low"}}]}],
                "response_format":{"type":"json_schema","json_schema":SCHEMA}})
            j=r.json()
            if "choices" not in j: return None
            a=json.loads(j["choices"][0]["message"]["content"]); a["_code"]=p["code"]; return a
        except Exception: return None

def jev(items):
    st={"creator":{"name":"Maya Rao","voice":VOICE["style_rules"],"creed":VOICE["creed"],
        "context":"A brand sent Maya these hoping she'll feature them."},
        "her_shelf_for_taste_reference":[{"product":x["product"],"gbp":x["gbp"],"maya_rating":x["maya_rating"],"maya_note":x["maya_note"]} for x in SHELF],
        "candidates":{i["_code"]:{k:v for k,v in i.items() if k!="_code"} for i in items}}
    qs={}
    for i in items:
        c=i["_code"]
        qs[c+"|fit"]={"type":"score","instructions":f"How enthusiastically would Maya tell her audience about `candidates.{c}`?",
          "criteria":["She would actively warn people off it","She would ignore it","Only if asked",
                      "She would recommend it to the right person","She would champion it"]}
        qs[c+"|enough"]={"type":"noul","instructions":f"Is there enough information about `candidates.{c}` for Maya to give an honest verdict at all?",
          "criteria":{"true":"Enough to judge responsibly","false":"She would need to try it or read the full ingredients first"}}
    return httpx.post("https://api.typesafe.ai/v1/systemone",headers={"Authorization":f"Bearer {JEV}"},
        json={"model":"jev-latest","state":st,"questions":qs},timeout=120).json()

async def main():
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=80)) as c:
        sem=asyncio.Semaphore(40)
        seen=[x for x in await asyncio.gather(*[see(c,p,sem) for p in SAMPLE]) if x]
    seen=[s for s in seen if s.get("is_face_skincare")]
    A={}
    for i in range(0,len(seen),20):
        A.update(jev(seen[i:i+20])["answers"])
    confs=[A[s["_code"]+"|fit"]["confidence"] for s in seen]
    enough=[A[s["_code"]+"|enough"]["noul"] for s in seen]
    print(f"n={len(seen)} face-skincare products\n")
    print(f"SCORE CONFIDENCE : min {min(confs):.2f}  p25 {statistics.quantiles(confs,n=4)[0]:.2f}  median {statistics.median(confs):.2f}  max {max(confs):.2f}")
    print(f"'ENOUGH INFO'    : min {min(enough):.2f}  median {statistics.median(enough):.2f}  max {max(enough):.2f}")
    # does illegible packaging correlate with 'not enough info'?
    leg=[s for s in seen if s.get("label_legible")]; ill=[s for s in seen if not s.get("label_legible")]
    def m(g,k): 
        v=[A[s["_code"]+k]["noul" if "enough" in k else "confidence"] for s in g]
        return statistics.mean(v) if v else float('nan')
    print(f"\nlabel legible   n={len(leg):2d}  mean 'enough info' {m(leg,'|enough'):.2f}   mean confidence {m(leg,'|fit'):.2f}")
    print(f"label illegible n={len(ill):2d}  mean 'enough info' {m(ill,'|enough'):.2f}   mean confidence {m(ill,'|fit'):.2f}")
    gate=[s for s in seen if A[s["_code"]+"|enough"]["noul"]<0.5 or A[s["_code"]+"|fit"]["confidence"]<0.45]
    print(f"\nWOULD ROUTE TO 'ASK MAYA' (not enough info OR low confidence): {len(gate)}/{len(seen)} = {len(gate)/len(seen):.0%}")
    for s in gate[:6]:
        print(f"   enough={A[s['_code']+'|enough']['noul']:.2f} conf={A[s['_code']+'|fit']['confidence']:.2f}  {s['brand'][:16]:18s} {s['product_name'][:30]}")
asyncio.run(main())
