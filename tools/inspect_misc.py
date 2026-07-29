from pathlib import Path
import re

raws = list(Path("tools/scrape_out/raw").glob("*FRONTSPEAKER*d_speakersetup*"))
print("raws", raws)
for p in raws:
    h = p.read_text(encoding="utf-8", errors="replace")
    print("file", p.name, "len", len(h))
    i = h.find("Title")
    print(h[i : i + 700] if i >= 0 else h[:500])
    print("names", sorted(set(re.findall(r"name=['\"]([^'\"]+)['\"]", h))))

h = Path("protocol/expanded_forms/dialog_level_on.html").read_text(
    encoding="utf-8", errors="replace"
)
print("dialog options", re.findall(r"<OPTION[^>]*>([^<]+)", h, re.I))
print(
    "dialog selected",
    re.findall(r"<OPTION[^>]*selected[^>]*>([^<]+)|<OPTION value='([^']+)'[^>]*selected", h, re.I),
)

# zone2 names denser
for p in Path("tools/scrape_out/raw").glob("*ZONE2SETUP*d_general*"):
    h = p.read_text(encoding="utf-8", errors="replace")
    print("zone2 names", sorted(set(re.findall(r"name=['\"]([^'\"]+)['\"]", h))))
