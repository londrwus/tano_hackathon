# THE OVERNIGHT QUEUE: how much of 4,800 DMs/month can be answered in her standard while she sleeps,
# and how much must be HELD for her? Confidence is the gate. This is the autonomy number.
import os, asyncio, json, time, httpx, random
random.seed(42)
from prelude import JEV, SHELF, VOICE
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
P=json.load(open(os.path.join(r"C:/Users/Lenovo/Documents/tano_hackathon","data","case-001-maya.json"),encoding="utf-8"))
REAL=[d["text"] for d in P["inbox"]]
# realistic variants across the same 12 jobs + deliberate hard cases she SHOULD keep
VARIANTS=[
 "what lipstick is that in the reel","which foundation do u use for filming","where is the jumper from lol",
 "i have oily skin and £35, what should i get","combo skin, breakouts on chin, £50 help",
 "dry flaky skin in winter, budget 70","sensitive + rosacea, £45, what's safe",
 "if you had to pick one serum forever which","only ONE product for the rest of your life go",
 "is the night serum worth 42 honestly","would you pay 62 for the glass drop",
 "is the tint veil worth it or is there a cheaper dupe",
 "i already use the daily gel, do i need a serum too","i have the spf already what else",
 "got the soft clean last month, what next","i own like 6 products should i stop buying",
 "i genuinely cannot tell if im oily or combo","my skin is weird lately idk what changed",
 "wedding next month what do i start now","interview tomorrow morning help",
 "holiday in 2 weeks what do i pack","you're the only person i trust on this stuff",
 "obsessed with your account","literally changed my routine because of you",
 "ordering next week when i get paid","saving up for the cloud cream",
 "gonna buy it in the sale","my mum wants to know what you'd get her, she's 60 dry skin",
 "buying for my boyfriend, he uses nothing, where does he start",
 "what would you buy if you only had 25 quid","if it was your money what would you do",
 # hard ones she should KEEP
 "i've been using tretinoin from my derm, can i add anything",
 "im pregnant, is any of this safe","i had a bad reaction to something, red and peeling, what do i do",
 "i have perioral dermatitis, which of these is ok","im on accutane currently",
 "my 12 year old wants a routine","is this safe with my eczema medication",
]
DMS=REAL+VARIANTS
MAYA={"name":"Maya Rao","voice":VOICE["style_rules"],"creed":VOICE["creed"],
 "her_shelf":[{"product":p["product"],"gbp":p["gbp"],"type":p["type"],"skin":p["skin"],"maya_note":p["maya_note"]} for p in SHELF],
 "her_intake_questions":P["decision_rules"]["intake_questions"],
 "her_scope":"She is a beauty creator, not a doctor. She does not give medical advice."}

def triage(text):
    qs={
     "job":{"type":"choice","instructions":"What is `message` asking Maya to do?",
       "criteria":{"pick_for_me":"Choose products, possibly under constraints","is_it_worth_it":"Judge a product against its price",
        "do_i_need_it":"They own something; decide if they need more","what_is_it":"Identify an item she used or wore",
        "diagnose_me":"They do not know their skin type","occasion":"They need to look good for an event soon",
        "buying_for_someone_else":"Choosing on behalf of another person","not_a_question":"Trust or praise, nothing to decide",
        "later":"Already decided, waiting on money or time"}},
     "out_of_scope":{"type":"noul","instructions":"Is `message` asking for something outside `creator.her_scope` - medical advice, prescription interactions, pregnancy safety, a skin condition needing a doctor, or a child?",
       "criteria":{"true":"Maya must not answer this herself","false":"Safely within what a beauty creator answers"}},
     "needs_question_back":{"type":"noul","instructions":"Would Maya have to ask something back before answering responsibly?",
       "criteria":{"true":"She would ask first","false":"She can answer now"}},
     "enough_to_answer":{"type":"noul","instructions":"Is there enough in `message` for Maya's standard to produce an answer she would stand behind?",
       "criteria":{"true":"Enough to answer","false":"Too little to be responsible"}},
     "emotional_weight":{"type":"score","instructions":"How much does `message` need a human reply rather than a useful answer?",
       "criteria":["Purely practical","Mostly practical","Personal, warmth matters","This person wants Maya specifically"]},
    }
    return {"model":"jev-latest","state":{"creator":MAYA,"message":text},"questions":qs}

async def main():
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=60)) as c:
        t0=time.time()
        rs=await asyncio.gather(*[c.post(URL,headers=H,json=triage(d),timeout=90) for d in DMS])
        w=time.time()-t0
    auto=[];askback=[];held=[];esc=[]
    for d,r in zip(DMS,rs):
        a=r.json()["answers"]
        oos=a["out_of_scope"]["noul"]; enough=a["enough_to_answer"]["noul"]
        jc=a["job"]["confidence"]; emo=a["emotional_weight"]["score"]
        if oos>0.5: esc.append((d,"OUT OF SCOPE - refer on"))
        elif jc<0.55: held.append((d,f"job unclear ({jc:.2f})"))
        elif emo>=2.6: held.append((d,f"wants Maya personally ({emo:.1f})"))
        elif enough<0.45: askback.append((d,a["job"]["choice"]))   # SHE asks one question back. That IS the action.
        else: auto.append((d,a["job"]["choice"]))
    n=len(DMS)
    print(f"{n} DMs triaged in {w:.2f}s  ({n*5} judgments)\n")
    handled=len(auto)+len(askback)
    print(f"  ANSWERED OUTRIGHT (had enough to go on) : {len(auto):3d}/{n}  = {len(auto)/n:.0%}")
    print(f"  ASKED HER ONE QUESTION BACK (E-02.1)    : {len(askback):3d}/{n}  = {len(askback)/n:.0%}")
    print(f"  -> HANDLED WITHOUT MAYA                 : {handled:3d}/{n}  = {handled/n:.0%}")
    print(f"  HELD FOR MAYA (she reviews)             : {len(held):3d}/{n}  = {len(held)/n:.0%}")
    print(f"  REFUSED / REFERRED ON (medical)         : {len(esc):3d}/{n}  = {len(esc)/n:.0%}")
    print(f"\n  SAFETY CHECK - what it refused to touch:")
    for d,why in esc[:9]: print(f"     \"{d[:56]}\"")
    print(f"\n  HELD FOR HER (a sample):")
    for d,why in held[:6]: print(f"     \"{d[:50]}\"  <- {why}")
    mo=4800
    print(f"\n  AT HER REAL VOLUME ({mo} DMs/month):")
    print(f"     ~{int(mo*handled/n):,} handled in her voice while she sleeps")
    print(f"     ~{int(mo*len(held)/n):,} held for her = ~{int(mo*len(held)/n/30)} cards a day to swipe")
    print(f"     ~{int(mo*len(esc)/n):,} referred on, never answered by a machine")
asyncio.run(main())
