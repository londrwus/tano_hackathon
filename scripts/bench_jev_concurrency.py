import asyncio, time, httpx
exec(open('probe.py').read().split('async def one')[0])  # reuse consts

async def one(client, payload, sem):
    async with sem:
        t=time.time()
        for attempt in range(5):
            try:
                r=await client.post(URL,headers=H,json=payload,timeout=120)
            except Exception as e:
                await asyncio.sleep(1.0*(attempt+1)); continue
            if r.status_code in (429,529):
                await asyncio.sleep(1.5*(attempt+1)); continue
            break
        return r.status_code, time.time()-t, (r.json() if r.status_code==200 else r.text[:200])

async def main():
    limits=httpx.Limits(max_connections=200,max_keepalive_connections=200)
    async with httpx.AsyncClient(limits=limits) as c:
        sem=asyncio.Semaphore(200)
        print("=== TEST C: how many questions fit in ONE request? ===")
        for n_personas in [6,12,20]:
            pers=[dict(PERSONAS[i%6], id=f"{PERSONAS[i%6]['id']}{i}") for i in range(n_personas)]
            st,dt,js=await one(c, build(SHELF[2], pers), sem)
            nq=n_personas*3
            if st==200:
                print(f"  {nq:3d} questions -> {dt:.2f}s, in={js['usage']['input_tokens']} out={js['usage']['output_tokens']}, answers={len(js['answers'])}")
            else:
                print(f"  {nq:3d} questions -> HTTP {st}: {js}")

        print()
        print("=== TEST D: 100 concurrent requests (1800 judgments) ===")
        payloads=[build(SHELF[i%4], PERSONAS) for i in range(100)]
        t0=time.time(); res=await asyncio.gather(*[one(c,p,sem) for p in payloads]); wall=time.time()-t0
        ok=[r for r in res if r[0]==200]
        codes={}
        for r in res: codes[r[0]]=codes.get(r[0],0)+1
        lat=sorted(r[1] for r in ok)
        tin=sum(r[2]["usage"]["input_tokens"] for r in ok); tout=sum(r[2]["usage"]["output_tokens"] for r in ok)
        print(f"wall={wall:.2f}s codes={codes} judgments={len(ok)*18} throughput={len(ok)*18/wall:.0f}/s")
        print(f"latency p50={lat[len(lat)//2]:.2f}s p95={lat[int(len(lat)*0.95)-1]:.2f}s max={lat[-1]:.2f}s")
        print(f"tokens in={tin} out={tout}")
        print(f"EXTRAPOLATION: 20,000 judgments ~= {20000/(len(ok)*18/wall):.0f}s wall, {20000*123.1/1e6:.2f}M input tokens")

asyncio.run(main())
