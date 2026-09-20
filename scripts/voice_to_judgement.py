import os
import json, time, httpx
JEV=os.environ["JEV_API_KEY"]
P=json.load(open(r"C:\Users\Lenovo\Documents\tano_hackathon\data\case-001-maya.json"))
SHELF=P["shelf"]

# The exact transcript OpenAI returned from the synthesised voice note.
TRANSCRIPT=("Honestly, the glass drop is good. It's just not 62 quid good. If you have dry skin "
            "and redness and \u00a360, I would get the cloud cream and the red reset and skip it.")

state={"creator":"Maya Rao","new_voice_note":TRANSCRIPT,"shelf":SHELF}
qs={}
for p in SHELF:
    k=p["product"].lower().replace(" ","_")
    qs[k+"__mentioned"]={"type":"noul","instructions":{"question":"Does `new_voice_note` express a judgement about `product`?","product":p},
        "criteria":{"true":"She refers to this product","false":"She does not mention it"}}
    qs[k+"__verdict"]={"type":"choice","instructions":{"question":"Given `new_voice_note`, what is Maya's standing verdict on `product`?","product":p},
        "criteria":{"endorse":"She would recommend it","endorse_with_caveat":"Good but with a stated reservation such as price",
                    "reject":"She would tell people to skip it","no_signal":"The note says nothing about it"}}
t0=time.time()
r=httpx.post("https://api.typesafe.ai/v1/systemone",headers={"Authorization":f"Bearer {JEV}"},
             json={"model":"jev-latest","state":state,"questions":qs},timeout=60)
dt=time.time()-t0
a=r.json()["answers"]; u=r.json()["usage"]
print(f"HTTP {r.status_code}  {len(qs)} questions in {dt:.2f}s  ({u['input_tokens']} in / {u['output_tokens']} out)\n")
print(f"{'PRODUCT':14s} {'MENTIONED':>9}  VERDICT (confidence)")
for p in SHELF:
    k=p["product"].lower().replace(" ","_")
    m=a[k+"__mentioned"]["noul"]; v=a[k+"__verdict"]
    if m>0.4 or v["choice"]!="no_signal":
        print(f"{p['product']:14s} {m:9.2f}  {v['choice']:22s} ({v['confidence']:.2f})")
