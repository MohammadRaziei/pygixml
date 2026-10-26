"""Regenerate the HTML5 named-character-reference table inside src/html.pxi.

The table (Python's html.entities.html5, which mirrors
https://html.spec.whatwg.org/entities.json) lives in a verbatim C++ block of
html.pxi between the BEGIN GENERATED / END GENERATED markers. Run from the
repository root:

    python scripts/gen_html_entities.py
"""
import re
from html.entities import html5
from pathlib import Path

PXI = Path(__file__).resolve().parent.parent / "src" / "html.pxi"

# Octal escapes (max 3 digits) so a following hex-looking letter can't be
# swallowed, which "\xNN" escapes would do in C++. The block is a raw string
# in Cython (r"""), so backslashes reach the C++ compiler untouched.
def lit(s: str) -> str:
    return "".join(f"\\{b:03o}" for b in s.encode("utf-8"))

items = sorted(html5.items(), key=lambda kv: kv[0].encode("ascii"))
rows = "\n".join(f'    {{"{k}", "{lit(v)}"}},' for k, v in items)
table = f"""#include <cstddef>
#include <cstring>
namespace pygixml_html {{
struct Entity {{ const char* name; const char* value; }};
static const Entity kEntities[] = {{
{rows}
}};
static const size_t kEntityCount = {len(items)};

// Binary search; `name` is not NUL-terminated. Keys keep their trailing ';'
// when they have one; legacy references valid without it appear without.
static inline const char* entity_lookup(const char* name, size_t len) {{
    size_t lo = 0, hi = kEntityCount;
    while (lo < hi) {{
        size_t mid = (lo + hi) / 2;
        const char* k = kEntities[mid].name;
        int c = std::strncmp(k, name, len);
        if (c == 0) c = k[len] == '\\0' ? 0 : 1;   // k longer than name sorts after it
        if (c == 0) return kEntities[mid].value;
        if (c < 0) lo = mid + 1; else hi = mid;
    }}
    return nullptr;
}}
}}  // namespace pygixml_html"""

text = PXI.read_text()
pattern = re.compile(r"(// BEGIN GENERATED[^\n]*\n//[^\n]*\n).*?(\n// END GENERATED)", re.S)
assert pattern.search(text), "markers not found in html.pxi"
PXI.write_text(pattern.sub(lambda m: m.group(1) + table + m.group(2), text))
print(f"updated {PXI}: {len(items)} entities")
