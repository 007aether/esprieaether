import json

d = json.load(open("data/airdrop_scored.json"))
items = d.get("items", [])
print("total:", d.get("total"), "| A:", d.get("by_grade",{}).get("A"), "| scams_blocked:", d.get("scams_blocked"))
print(f"{'score':>5} | {'rec':>4} | {'name':35s} | {'source':18s} | asset")
for it in sorted(items, key=lambda x: x.get("score",0), reverse=True)[:15]:
    print(f"{it.get('score','?'):>5} | {it.get('rank','?'):>4} | {str(it.get('title',''))[:35]:35s} | {str(it.get('source',''))[:18]:18s} | {str(it.get('asset',''))[:24]}")
