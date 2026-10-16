import json

d = json.load(open("data/airdrop_scored.json"))
sorted_items = sorted(d, key=lambda x: x.get("score", 0), reverse=True)
print("total items:", len(d))
print(f"{'score':>5} | {'rec':>4} | {'name':35s} | {'source':18s} | asset")
for it in sorted_items[:15]:
    print(f"{it.get('score','?'):>5} | {it.get('rank','?'):>4} | {str(it.get('name',''))[:35]:35s} | {str(it.get('source',''))[:18]:18s} | {str(it.get('asset',''))[:24]}")
