"""Check .dc.html artboards against the canvas file rules. usage: python3 -I lint_dc.py BLOBMAP FILE..."""
import sys, re, json
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
SVG_SELF = {"path", "use", "rect", "circle", "ellipse", "line", "polyline", "polygon", "stop", "image",
            "feflood", "fecomposite", "fegaussianblur", "feblend", "fecolormatrix", "feoffset", "femerge",
            "femergenode", "feturbulence", "fedisplacementmap", "fefunc", "fefuncr", "fefuncg", "fefuncb", "fefunca"}

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errs, self.ids = [], [], {}
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids[a["id"]] = self.ids.get(a["id"], 0) + 1
        st = a.get("style") or ""
        if "url(" in st and not re.search(r"url\(#", st):
            self.errs.append(f"url() in style attribute on <{tag}>")
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))
    def handle_startendtag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids[a["id"]] = self.ids.get(a["id"], 0) + 1
    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errs.append(f"stray </{tag}> at {self.getpos()}")
            return
        top, pos = self.stack[-1]
        if top == tag:
            self.stack.pop()
            return
        names = [t for t, _ in self.stack]
        if tag in names:
            while self.stack and self.stack[-1][0] != tag:
                t, p = self.stack.pop()
                if t not in SVG_SELF:
                    self.errs.append(f"unclosed <{t}> opened at {p}")
            self.stack.pop()
        else:
            self.errs.append(f"stray </{tag}> at {self.getpos()}")

bm = json.load(open(sys.argv[1]))
bad = 0
for f in sys.argv[2:]:
    t = open(f, encoding="utf-8").read()
    errs = []
    if not t.lstrip().lower().startswith("<!doctype html>"):
        errs.append("missing doctype")
    if '<html lang="lv">' not in t:
        errs.append('missing <html lang="lv">')
    if '<script src="./support.js"></script>' not in t:
        errs.append("missing support.js")
    if not re.search(r"<title>[^<]+ — (zīmols|pielietojums)</title>", t):
        errs.append("title not '<Name> — zīmols/pielietojums'")
    if "<x-dc>" not in t or "<helmet>" not in t:
        errs.append("missing x-dc/helmet")
    if not re.search(r'<script type="text/x-dc" data-dc-script data-props=\'\{"\$preview":\{"width":1920,"height":1280\}\}\'>', t):
        errs.append("tail script block changed")
    if "<!--" in t:
        errs.append("HTML comment")
    if "data:" in re.sub(r"<script.*?</script>", "", t, flags=re.S):
        errs.append("data: URI")
    for m in re.findall(r'(?:src|href)="(https?://[^"]+)"', t):
        if not m.startswith("https://fonts.googleapis.com/"):
            errs.append(f"external url {m[:60]}")
    for i in set(re.findall(r"/_blob/([0-9a-f]{32})", t)):
        if i not in bm:
            errs.append(f"blob not in map {i}")
    if not re.search(r'<div style="width: 1920px; height: 1280px;', t):
        errs.append("root div not 1920x1280 first")
    p = P()
    body = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    p.feed(body)
    errs += p.errs
    errs += [f"unclosed <{tg}> at {ps}" for tg, ps in p.stack if tg not in ("html", "body")]
    errs += [f"duplicate id {k} x{v}" for k, v in p.ids.items() if v > 1]
    name = f.split("/")[-1]
    print(f"{'OK ' if not errs else 'ERR'} {name} {len(t)//1024} KB")
    for e in errs[:12]:
        print("    ", e)
    bad += bool(errs)
sys.exit(1 if bad else 0)
