from pathlib import Path
import re

root = Path(__file__).resolve().parents[1] / "protocol" / "expanded_forms"
for name in [
    "manual_eq_on.html",
    "dialog_level_on.html",
    "dialog_level_before.html",
    "subwoofer_level_on.html",
    "subwoofer_level_before.html",
]:
    p = root / name
    if not p.exists():
        print(name, "missing")
        continue
    h = p.read_text(encoding="utf-8", errors="replace")
    print("====", name, "len", len(h))
    for m in re.finditer(r"<(?:input|select)\b[^>]{0,300}", h, re.I):
        t = m.group(0)
        if "name=" in t.lower() or "type='range'" in t.lower() or 'type="range"' in t.lower():
            print(t[:240])
    mt = re.search(r'class="Title">(.*?)<', h, re.S)
    print("Title:", mt.group(1).strip() if mt else "")
    print()
