import json

KEY_MAP = {
    "Ability & Aptitude": "A", "Assessment Exercises": "E",
    "Biodata & Situational Judgment": "B", "Competencies": "C",
    "Development & 360": "D", "Knowledge & Skills": "K",
    "Personality & Behavior": "P", "Simulations": "S"
}
LEVEL_MAP = {
    "Director": "Dir", "Entry-Level": "Ent", "Executive": "Exec",
    "Front Line Manager": "FLM", "General Population": "GP",
    "Graduate": "Grad", "Manager": "Mgr", "Mid-Professional": "Mid",
    "Professional Individual Contributor": "PIC", "Supervisor": "Sup"
}

with open("shl_product_catalog.json") as f:
    data = json.load(f)

lines = []
for item in data:
    keys = ",".join(KEY_MAP.get(k, k) for k in item.get("keys", []))
    levels = ",".join(LEVEL_MAP.get(l, l) for l in item.get("job_levels", []))
    langs = item.get("languages", [])
    lang_str = ",".join(langs[:3]) + (f" +{len(langs)-3}" if len(langs) > 3 else "")
    dur = item.get("duration", "") or "-"
    # Truncate description to first 60 words
    desc_words = item.get("description", "").split()
    desc = " ".join(desc_words[:60])
    if len(desc_words) > 60:
        desc += "..."
    
    line = f'[{item["entity_id"]}] {item["name"]} | {keys} | {levels} | {lang_str} | {dur} | {desc}'
    lines.append(line)

full_text = "\n".join(lines)
char_count = len(full_text)
# Rough token estimate: ~4 chars per token for English
token_estimate = char_count / 4

print(f"Total lines: {len(lines)}")
print(f"Total characters: {char_count:,}")
print(f"Estimated tokens (~4 chars/tok): {int(token_estimate):,}")
print(f"Shortest line: {min(len(l) for l in lines)} chars")
print(f"Longest line: {max(len(l) for l in lines)} chars")
print(f"Average line: {sum(len(l) for l in lines) // len(lines)} chars")
print()
print("Sample lines:")
print(lines[0][:200])
print(lines[1][:200])
print(lines[-1][:200])

# Also test with 40-word truncation
lines40 = []
for item in data:
    keys = ",".join(KEY_MAP.get(k, k) for k in item.get("keys", []))
    levels = ",".join(LEVEL_MAP.get(l, l) for l in item.get("job_levels", []))
    dur = item.get("duration", "") or "-"
    desc_words = item.get("description", "").split()
    desc = " ".join(desc_words[:40])
    line = f'[{item["entity_id"]}] {item["name"]} | {keys} | {levels} | {dur} | {desc}'
    lines40.append(line)

full40 = "\n".join(lines40)
print(f"\nWith 40-word desc: {len(full40):,} chars = ~{int(len(full40)/4):,} tokens")

# And no description at all (just metadata)
lines_nodesc = []
for item in data:
    keys = ",".join(KEY_MAP.get(k, k) for k in item.get("keys", []))
    levels = ",".join(LEVEL_MAP.get(l, l) for l in item.get("job_levels", []))
    dur = item.get("duration", "") or "-"
    line = f'[{item["entity_id"]}] {item["name"]} | {keys} | {levels} | {dur}'
    lines_nodesc.append(line)

full_nodesc = "\n".join(lines_nodesc)
print(f"No description: {len(full_nodesc):,} chars = ~{int(len(full_nodesc)/4):,} tokens")
