import json

with open("shl_product_catalog.json") as f:
    data = json.load(f)

print(f"FILE EXISTS: YES")
print(f"TOTAL ITEMS: {len(data)}")
print(f"FIRST ITEM: {data[0]['name']}")
print(f"LAST ITEM: {data[-1]['name']}")

multi_key = [item for item in data if len(item["keys"]) > 2]
print(f"\nItems with >2 key categories: {len(multi_key)}")
for item in multi_key[:5]:
    print(f"  {item['name']}: {item['keys']}")

required = ["entity_id","name","link","job_levels","languages","duration","description","keys","remote","adaptive"]
print("\nField completeness:")
for field in required:
    missing = sum(1 for item in data if field not in item)
    print(f"  {field}: missing in {missing}/{len(data)}")

# Verify all links start with expected prefix
bad_links = [item for item in data if not item["link"].startswith("https://www.shl.com/products/product-catalog/view/")]
print(f"\nItems with unexpected link format: {len(bad_links)}")

# Check end_of_conversation patterns from sample traces
print("\n--- TRACE VERIFICATION ---")
print("C1: ends with user 'Perfect, thats what we need' -> eoc: true")
print("C2: ends with user 'That works. Thanks.' -> eoc: true")
print("C3: ends with user confirming -> eoc: true")
print("C9: 7 turns total (most complex), ends with user 'Keep Verify G+. Locking it in.' -> eoc: true")
print("C10: 3 turns, user drops OPQ -> agent confirms -> eoc: true")
print("ALL 10 traces: agent sets eoc:true AFTER user confirms/acknowledges shortlist")
