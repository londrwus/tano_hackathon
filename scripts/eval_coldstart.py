import os
import json, time, httpx, asyncio
JEV=os.environ["JEV_API_KEY"]
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
P=json.load(open(r"C:\Users\Lenovo\Documents\tano_hackathon\data\case-001-maya.json"))
SHELF=P["shelf"]

# ONLY things Maya already produced without being asked: her post titles + engagement, and her DMs.
# NO ratings, NO per-product notes, NO routing rules, NO voice note.
ORGANIC={
 "her_post_titles_and_engagement":[{"title":b["title"],"views":b["views"],"saves":b["saves"],
    **({"affiliate_conversions":b["affiliate_conversions"]} if "affiliate_conversions" in b else {})}
    for b in P["broadcast_log"]],
 "questions_her_audience_sends_her":[d["text"] for d in P["inbox"]],
}
# products stripped of ALL her subjective layer
BARE=[{k:v for k,v in p.items() if k not in ("maya_rating","maya_note","ref","is_contradiction")} for p in SHELF]

async def run(label, state, note):
    qs={}
    for p in BARE:
        k=p["product"].lower().replace(" ","_")
        qs[k]={"type":"score","instructions":{"question":f"How enthusiastically would this creator recommend `product` to her audience? {note}","product":p},
          "criteria":["She would warn people off it","Nothing to say about it","Only if asked",
                      "She would recommend it to the right person","She would champion it"]}
    t=time.time()
    async with httpx.AsyncClient() as c:
        r=await c.post(URL,headers=H,json={"model":"jev-latest","state":state,"questions":qs},timeout=90)
    a=r.json()["answers"]
    out={p["product"]:a[p["product"].lower().replace(" ","_")]["score"] for p in BARE}
    print(f"\n--- {label}  ({time.time()-t:.2f}s) ---")
    for n,v in sorted(out.items(),key=lambda x:-x[1]):
        gt=next(s for s in SHELF if s["product"]==n)
        print(f"   {v:.2f}  {n:13s} (her real rating {gt['maya_rating']}, note: {gt['maya_note'][:34]})")
    return out

def corr(a,b):
    import statistics
    ka=[a[p["product"]] for p in SHELF]; kb=[b[p["product"]] for p in SHELF]
    ma,mb=statistics.mean(ka),statistics.mean(kb)
    num=sum((x-ma)*(y-mb) for x,y in zip(ka,kb))
    den=(sum((x-ma)**2 for x in ka)*sum((y-mb)**2 for y in kb))**.5
    return num/den if den else 0

async def main():
    # A: cold start - only organic content she already made
    A=await run("A. COLD START (only her post titles + her DMs - zero annotation)",
        {"creator":{"name":"Maya Rao","niche":"beauty/skincare, 50K followers"},"organic_signals":ORGANIC},
        "You must infer her taste ONLY from `organic_signals` - the posts she chose to make and the questions her audience sends her.")
    # B: full evidence (ground truth-ish) - her notes and ratings present
    B=await run("B. FULL (her per-product notes + ratings present)",
        {"creator":{"name":"Maya Rao","voice":P["voice"]["style_rules"],"creed":P["voice"]["creed"]},
         "shelf_with_her_notes":[{"product":p["product"],"gbp":p["gbp"],"maya_rating":p["maya_rating"],"maya_note":p["maya_note"]} for p in SHELF]},
        "Use her own notes and ratings.")
    r=corr(A,B)
    print(f"\n=== CORRELATION between zero-annotation cold start and full-evidence: {r:+.3f} ===")
    ra=sorted(A,key=lambda k:-A[k]); rb=sorted(B,key=lambda k:-B[k])
    print(f"top-3 cold : {ra[:3]}")
    print(f"top-3 full : {rb[:3]}")
    print(f"overlap in top-3: {len(set(ra[:3])&set(rb[:3]))}/3   in top-5: {len(set(ra[:5])&set(rb[:5]))}/5")
    print(f"bottom-2 cold: {ra[-2:]}   bottom-2 full: {rb[-2:]}")
asyncio.run(main())
