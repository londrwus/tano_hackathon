import os
import asyncio, json, time, httpx, random
random.seed(7)
KEY=os.environ["JEV_API_KEY"]
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"}
P=json.load(open(r"C:\Users\Lenovo\Documents\tano_hackathon\data\case-001-maya.json"))
SHELF=P["shelf"]; PERSONAS=P["personas"]

CREATOR={"name":"Maya Rao","voice":P["voice"]["style_rules"],"creed":P["voice"]["creed"],
         "routing_rules":P["decision_rules"]["routing"],"hard_rule":P["decision_rules"]["hard_rule"]}

SKIN=["dry","oily","combination","sensitive","normal, some redness"]
BUDGET=[25,40,60,80,120]
LIFE=["will not do more than 2 steps","loves a long routine","travels constantly","new mum, no time","student"]

def make_audience(n):
    out=[]
    for i in range(n):
        base=PERSONAS[i%len(PERSONAS)]
        out.append({"uid":f"U-{i:03d}","archetype":base["tag"],"quote":base["says"],
                    "skin":SKIN[i%len(SKIN)],"budget_gbp":BUDGET[(i//2)%len(BUDGET)],
                    "life":LIFE[(i//3)%len(LIFE)],
                    "saves":random.randint(0,11),"dms_sent":random.randint(0,4)})
    return out

def payload(chunk):
    st={"creator":CREATOR,"shelf":SHELF,"audience":{m["uid"]:m for m in chunk}}
    qs={}
    for m in chunk:
        for p in SHELF:
            qs[f"{m['uid']}|{p['ref']}"]={"type":"noul",
              "instructions":{"question":f"Would Maya recommend `product` to `audience.{m['uid']}`? Respect her routing rules and her refusal to recommend things that are not worth their price.","product":p},
              "criteria":{"true":"Maya puts it in their basket","false":"Maya leaves it out for this person"}}
    return {"model":"jev-latest","state":st,"questions":qs}

async def call(c,pl,sem):
    async with sem:
        for a in range(4):
            r=await c.post(URL,headers=H,json=pl,timeout=120)
            if r.status_code in (429,529): await asyncio.sleep(1.2*(a+1)); continue
            return r
        return r

async def main(N=300, CHUNK=6):
    aud=make_audience(N)
    chunks=[aud[i:i+CHUNK] for i in range(0,len(aud),CHUNK)]
    lim=httpx.Limits(max_connections=150,max_keepalive_connections=150)
    async with httpx.AsyncClient(limits=lim) as c:
        sem=asyncio.Semaphore(100)
        t0=time.time()
        rs=await asyncio.gather(*[call(c,payload(ch),sem) for ch in chunks])
        wall=time.time()-t0
    ok=[r for r in rs if r.status_code==200]
    codes={}
    for r in rs: codes[r.status_code]=codes.get(r.status_code,0)+1
    M={}; tin=tout=0
    for r in ok:
        j=r.json(); tin+=j["usage"]["input_tokens"]; tout+=j["usage"]["output_tokens"]
        for k,v in j["answers"].items():
            uid,ref=k.split("|"); M.setdefault(uid,{})[ref]=v["noul"]
    n_j=sum(len(v) for v in M.values())
    print(f"audience={N}  products={len(SHELF)}  requests={len(chunks)} ({CHUNK*len(SHELF)} questions each)")
    print(f"codes={codes}  wall={wall:.2f}s  judgments={n_j}  throughput={n_j/wall:.0f}/s")
    print(f"tokens in={tin:,} out={tout:,}")
    print()
    print("SHELF-WIDE RECOMMEND RATE (what fraction of the audience Maya would send each product to):")
    for p in sorted(SHELF,key=lambda p:-sum(M[u].get(p['ref'],0) for u in M)):
        vals=[M[u][p["ref"]] for u in M if p["ref"] in M[u]]
        rate=sum(1 for v in vals if v>=0.5)/len(vals)
        bar="#"*int(rate*40)
        print(f"  {p['product']:14s} GBP{p['gbp']:>3}  rate={rate:5.1%} mean={sum(vals)/len(vals):.2f} |{bar}")
    print()
    print("COVERAGE: audience members with ZERO confident recommendation (Maya's shelf gap):")
    gaps=[u for u in M if max(M[u].values())<0.5]
    print(f"  {len(gaps)}/{len(M)} = {len(gaps)/len(M):.1%}")
asyncio.run(main())
