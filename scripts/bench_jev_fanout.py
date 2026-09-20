import os
import asyncio, time, json, httpx

KEY=os.environ["JEV_API_KEY"]
URL="https://api.typesafe.ai/v1/systemone"
H={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"}

# Real evidence from Case 001
SHELF=[
 {"ref":"E-04.1","product":"Cloud Cream","gbp":38,"type":"Moisturiser","skin":"Dry","finish":"Rich","maya":9.2,"note":"My winter skin saviour."},
 {"ref":"E-04.3","product":"Red Reset","gbp":32,"type":"Serum","skin":"Sensitive","finish":"Calm","maya":9.5,"note":"For angry skin days."},
 {"ref":"E-04.6","product":"Glass Drop","gbp":62,"type":"Serum","skin":"All","finish":"Dewy","maya":8.1,"note":"Good. Not 62 quid good."},
 {"ref":"E-04.5","product":"SPF 50","gbp":26,"type":"SPF","skin":"All","finish":"Invisible","maya":9.6,"note":"Non-negotiable."},
]
PERSONAS=[
 {"id":"emily","age":22,"tag":"price sensitive","says":"I trust you, but I am not spending 100 pounds on serum."},
 {"id":"priya","age":31,"tag":"sensitive skin","says":"Every time I try something new my face freaks out."},
 {"id":"sophie","age":27,"tag":"beauty obsessive","says":"Forget the brand. What would YOU buy?"},
 {"id":"hannah","age":24,"tag":"overwhelmed","says":"There are 500 versions of this. Just tell me."},
 {"id":"grace","age":33,"tag":"busy","says":"I have 5 mins. Give me the two things that matter."},
 {"id":"alex","age":28,"tag":"silent browser","says":"(saves almost everything, sends almost nothing)"},
]
MAYA_RULES="DRY -> Cloud Cream + Barrier Oil. OILY -> Daily Gel. SENSITIVE -> avoid fragrance. REDNESS -> Red Reset. Shade questions -> ask current foundation. Rule: do not recommend retinol to everyone. Belief: people do not need more products, they need confidence. She will say a product is not worth its price even when she likes it."

def build(product, personas):
    state={"creator":{"name":"Maya Rao","voice":"dry, funny, decisive","hates":"generic automation","decision_rules":MAYA_RULES},
           "product":product,"shoppers":{p["id"]:p for p in personas}}
    qs={}
    for p in personas:
        i=p["id"]
        qs[f"{i}__buy"]={"type":"noul","instructions":f"Would Maya tell `shoppers.{i}` to buy `product`?","criteria":{"true":"Maya says buy it","false":"Maya steers them away"}}
        qs[f"{i}__act"]={"type":"choice","instructions":f"What would `shoppers.{i}` actually do after Maya's verdict on `product`?","criteria":{"buy_now":"Buys within a day","save_for_later":"Saves it, buys days later","share":"Sends it to a friend instead","scroll_past":"Ignores it"}}
        qs[f"{i}__trust"]={"type":"score","instructions":f"If Maya recommended `product` to `shoppers.{i}`, what happens to their trust in her?","criteria":["Trust grows, this is exactly right for them","Neutral","Mild mismatch they would notice","They would feel sold to"]}
    return {"model":"jev-latest","state":state,"questions":qs}

async def one(client, payload):
    t=time.time()
    for attempt in range(4):
        r=await client.post(URL,headers=H,json=payload,timeout=90)
        if r.status_code in (429,529):
            await asyncio.sleep(1.5*(attempt+1)); continue
        break
    return r.status_code, time.time()-t, r.json() if r.status_code==200 else r.text

async def main():
    async with httpx.AsyncClient(http2=False) as c:
        print("=== TEST A: fan-out, 18 questions in ONE request ===")
        st,dt,js=await one(c, build(SHELF[2], PERSONAS))
        print(f"status={st} latency={dt:.2f}s")
        if st==200:
            u=js["usage"]; print(f"usage in={u['input_tokens']} out={u['output_tokens']} questions={len(js['answers'])}")
            print(f"model={js['model']}")
            for p in PERSONAS:
                a=js["answers"]
                print(f"  {p['id']:7s} buy={a[p['id']+'__buy']['noul']:.2f}  act={a[p['id']+'__act']['choice']:15s}(c={a[p['id']+'__act']['confidence']:.2f})  trust={a[p['id']+'__trust']['score']:.2f}")
        else:
            print(js[:500]); return

        print()
        print("=== TEST B: concurrency, 24 requests (4 products x 6 chunks) in parallel ===")
        payloads=[build(p, PERSONAS) for p in SHELF for _ in range(6)]
        t0=time.time()
        res=await asyncio.gather(*[one(c,p) for p in payloads])
        wall=time.time()-t0
        ok=[r for r in res if r[0]==200]
        lat=sorted(r[1] for r in ok)
        tin=sum(r[2]["usage"]["input_tokens"] for r in ok); tout=sum(r[2]["usage"]["output_tokens"] for r in ok)
        codes={}
        for r in res: codes[r[0]]=codes.get(r[0],0)+1
        print(f"wall={wall:.2f}s  requests={len(res)}  codes={codes}")
        print(f"judgments={len(ok)*18}  throughput={len(ok)*18/wall:.1f} judgments/sec")
        print(f"latency p50={lat[len(lat)//2]:.2f}s p95={lat[int(len(lat)*0.95)-1]:.2f}s max={lat[-1]:.2f}s")
        print(f"tokens in={tin} out={tout}  -> per judgment: in={tin/(len(ok)*18):.1f} out={tout/(len(ok)*18):.1f}")

asyncio.run(main())
