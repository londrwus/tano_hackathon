import asyncio, base64, json, time, httpx, random
exec(open('scale.py').read().split('async def see')[0].replace('N=60','N=70'))
# curate: face skincare only
BAD=("body","hand","foot","feet","hair","shampoo","deodorant","soap bar","lip balm","baby","shaving")
CAND=[p for p in CAT if not any(b in (p.get("product_name","")+" "+" ".join(p.get("categories_tags_en",[]))).lower() for b in BAD)]
SAMPLE=random.sample(CAND,min(70,len(CAND)))
print(f"catalogue {len(CAT)} -> curated {len(CAND)} -> sampling {len(SAMPLE)}")
UA={"User-Agent":"tano-hackathon/1.0"}
SCHEMA={"name":"p","schema":{"type":"object","additionalProperties":False,"properties":{
 "product_name":{"type":"string"},"brand":{"type":"string"},"category":{"type":"string"},
 "texture_or_finish":{"type":"string"},"claims_on_pack":{"type":"array","items":{"type":"string"}},
 "likely_skin_types":{"type":"array","items":{"type":"string"}},
 "fragranced":{"type":"string","enum":["yes","no","unknown"]},
 "positioning":{"type":"string","enum":["drugstore","mid","premium","luxury"]},
 "is_face_skincare":{"type":"boolean"}},
 "required":["product_name","brand","category","texture_or_finish","claims_on_pack","likely_skin_types","fragranced","positioning","is_face_skincare"]},"strict":True}

async def see(c,p,sem,stats):
    async with sem:
        try:
            b=(await c.get(p["image_url"],headers=UA,follow_redirects=True,timeout=60)).content
            if len(b)>4_000_000: return None
            d="data:image/jpeg;base64,"+base64.b64encode(b).decode()
            r=await c.post("https://api.openai.com/v1/chat/completions",headers={"Authorization":f"Bearer {OA}"},timeout=120,
              json={"model":"gpt-4o-mini","messages":[{"role":"user","content":[
                {"type":"text","text":"Extract product attributes from this photo. Read text on the packaging."},
                {"type":"image_url","image_url":{"url":d,"detail":"low"}}]}],
                "response_format":{"type":"json_schema","json_schema":SCHEMA}})
            j=r.json()
            if "choices" not in j: return None
            stats["in"]+=j["usage"]["prompt_tokens"]; stats["out"]+=j["usage"]["completion_tokens"]
            a=json.loads(j["choices"][0]["message"]["content"]); a["_code"]=p["code"]; return a
        except Exception: return None

def jev_batch(items):
    universe=[{"product":x["product"],"gbp":x["gbp"],"type":x["type"],"maya_rating":x["maya_rating"],"maya_note":x["maya_note"]} for x in SHELF]
    st={"creator":{"name":"Maya Rao","voice":VOICE["style_rules"],"creed":VOICE["creed"],
        "context":("A brand has sent Maya these products hoping she will feature them. She does not have to "
                   "prefer them over her own shelf - she is judging whether each is genuinely good enough that "
                   "she would happily tell her audience about it.")},
        "her_shelf_for_taste_reference":universe,
        "candidates":{it["_code"]:{k:v for k,v in it.items() if k!="_code"} for it in items}}
    qs={}
    for it in items:
        c=it["_code"]
        qs[c+"|fit"]={"type":"score","instructions":f"How enthusiastically would Maya tell her audience about `candidates.{c}`?",
          "criteria":["She would actively warn people off it","She would ignore it, nothing to say",
                      "She would mention it only if asked","She would recommend it to the right person",
                      "She would champion it, this is exactly her kind of thing"]}
        qs[c+"|why"]={"type":"choice","instructions":f"What is Maya's single biggest reservation about `candidates.{c}`?",
          "criteria":{"not_her_lane":"Not face skincare / outside what she covers","fragrance_risk":"Fragranced, risky for sensitive skin",
                      "generic":"Nothing distinctive, any brand makes this","unproven":"Marketing claims she would not repeat",
                      "no_reservation":"She has no real reservation about it"}}
    return httpx.post("https://api.typesafe.ai/v1/systemone",headers={"Authorization":f"Bearer {JEV}"},
                 json={"model":"jev-latest","state":st,"questions":qs},timeout=120).json()

async def main():
    stats={"in":0,"out":0}
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=80)) as c:
        sem=asyncio.Semaphore(40); t0=time.time()
        seen=[x for x in await asyncio.gather(*[see(c,p,sem,stats) for p in SAMPLE]) if x]; tv=time.time()-t0
    seen=[s for s in seen if s.get("is_face_skincare")]
    print(f"VISION : {len(seen)} face-skincare products in {tv:.1f}s  ~${stats['in']/1e6*0.15+stats['out']/1e6*0.60:.3f}")
    CH=20; chunks=[seen[i:i+CH] for i in range(0,len(seen),CH)]
    t0=time.time(); res=[jev_batch(ch) for ch in chunks]; tj=time.time()-t0
    A={}; tin=0
    for r in res: A.update(r["answers"]); tin+=r["usage"]["input_tokens"]
    print(f"JEV    : {len(A)} judgments in {tj:.2f}s  ~${tin/1e6*0.042:.4f}\n")
    rank=sorted(seen,key=lambda s:-A[s["_code"]+"|fit"]["score"])
    print("TOP - she would champion / recommend:")
    for s in rank[:6]:
        f=A[s["_code"]+"|fit"]; print(f"  {f['score']:.2f}  {s['brand'][:16]:18s} {s['product_name'][:32]:34s} {f['legend'][str(round(f['score']))][:44]}")
    print("\nBOTTOM - she would warn people off:")
    for s in rank[-4:]:
        f=A[s["_code"]+"|fit"]; w=A[s["_code"]+"|why"]
        print(f"  {f['score']:.2f}  {s['brand'][:16]:18s} {s['product_name'][:32]:34s} {w['choice']}")
    import statistics
    sc=[A[s["_code"]+"|fit"]["score"] for s in seen]
    print(f"\nDISTRIBUTION: min {min(sc):.2f}  median {statistics.median(sc):.2f}  max {max(sc):.2f}  spread {max(sc)-min(sc):.2f}")
    print(f"  >=3.0 (would recommend): {sum(1 for x in sc if x>=3)}/{len(sc)}")
    print(f"  <=1.0 (would warn off) : {sum(1 for x in sc if x<=1)}/{len(sc)}")
asyncio.run(main())
