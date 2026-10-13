"""Reference renderer for the value-rendering rule in agent-design/data.md §2h.
Every example in that section is produced by `python3 bench/render.py`.

One rule: the OUTER structure is line-oriented text (tab-separated rows, `key: value`
lines); every CELL is either a bare scalar or compact JSON. Nothing is ever backslash-
or quote-escaped except by JSON itself, and a cell is only JSON when bare would be
ambiguous or unsafe.
"""
import json, math, re, datetime

_JSON_SCALAR = re.compile(r'^-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?$')
_LITERALS = {"true", "false", "null", "NaN", "Infinity", "-Infinity"}
_CONTROL = re.compile(r"[\x00-\x1f\x7f  ]")

def dump(v):                       # compact JSON, UTF-8 not \u-escaped
    return json.dumps(v, separators=(",", ":"), ensure_ascii=False)

def cell(v, cap=None):
    """Render one value as a cell. `cap` truncates strings (marker stays inside the quotes)."""
    if v is None: return ""
    if v is True: return "true"
    if v is False: return "false"
    if isinstance(v, int): return str(v)
    if isinstance(v, float):
        if math.isnan(v): return "NaN"
        if math.isinf(v): return "Infinity" if v > 0 else "-Infinity"
        return repr(v)
    if isinstance(v, (datetime.datetime, datetime.date)): return v.isoformat()
    if isinstance(v, (list, tuple, dict)): return dump(v)
    if isinstance(v, (bytes, bytearray)): raise TypeError("bytes never go inline: return a ref")
    s = str(v)
    if cap is not None and len(s) > cap: return dump(s[:cap] + f"…[+{len(s) - cap} chars]")
    bare = (s != "" and s == s.strip() and not _CONTROL.search(s)
            and s[0] not in '[{"' and not _JSON_SCALAR.match(s) and s not in _LITERALS)
    return s if bare else dump(s)

def table(rows, cols=None, cap=None):
    cols = cols or list(dict.fromkeys(k for r in rows for k in r))
    head = "\t".join(cell(c) if isinstance(c, str) and cell(c) == c else dump(c) for c in cols)
    return "\n".join([head] + ["\t".join(cell(r.get(c), cap) for c in cols) for r in rows])

def record(d, cap=None):
    return "\n".join(f"{cell(k)}: {cell(v, cap)}" for k, v in d.items() if v is not None)

def render(value, cap=None):
    """Pick the shape. Scalar -> cell; list of scalars -> one per line; uniform-enough
    list of dicts -> table; sparse list of dicts -> record blocks; dict -> record; else JSON."""
    if isinstance(value, list) and value and all(isinstance(r, dict) for r in value):
        cols = list(dict.fromkeys(k for r in value for k in r))
        fill = sum(1 for r in value for c in cols if r.get(c) is not None) / (len(value) * len(cols))
        if fill >= 0.5: return table(value, cols, cap)
        return "\n\n".join(record(r, cap) for r in value)
    if isinstance(value, list) and all(not isinstance(x, (list, dict)) for x in value):
        return "\n".join(cell(x, cap) for x in value)
    if isinstance(value, dict): return record(value, cap)
    if isinstance(value, (list, tuple)): return dump(value)
    return cell(value, cap)

if __name__ == "__main__":
    def show(title, value, **kw):
        print(f"### {title}\n"); print(render(value, **kw)); print()
    show("scalars", ["plain", "", "007", "7", "true", "null", "NaN", " padded ", "[not json", "say \"hi\"", "a,b", "tab\there", "two\nlines", "naïve ☕", None, True, 3.0, 1e21, float("nan")])
    show("table, nested cells", [
        {"id": 1, "name": "Acme, Inc.", "tags": ["a", "b"], "meta": {"tier": 2, "regions": ["EMEA", "NA"]}, "note": None},
        {"id": 2, "name": 'Zoë "Z" Café', "tags": [], "meta": {}, "note": "line1\nline2"},
        {"id": 3, "name": "007", "tags": [["x", 1], ["y", 2]], "meta": None, "note": ""}])
    show("record", {"order_id": 4001, "customer": "Acme, Inc.", "lines": [{"sku": "A1", "qty": 2}, {"sku": "B7", "qty": 1}], "ship": {"city": "Leeds", "geo": [53.8, -1.55]}, "refunded": False, "note": None})
    show("sparse list of records", [{"id": 1, "a": 1}, {"id": 2, "b": "x"}, {"id": 3, "c": [1, 2]}, {"id": 4, "d": None, "e": "y"}])
    show("list of scalars", ["alpha", "be\ttа", 3, None])
    show("truncation", [{"id": 1, "body": "x" * 60}], cap=20)
