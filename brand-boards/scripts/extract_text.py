"""List every visible text string (plus alt / aria-label / title) in .dc.html boards.

Usage: python3 -I extract_text.py board1.dc.html [board2 ...]
Skips <helmet>, <style>, <script>, <defs> and SVG path data.
"""
import sys, re
from html.parser import HTMLParser

SKIP = {"style", "script", "helmet", "defs", "title"}


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
        for k, v in attrs:
            if k in ("alt", "aria-label") and v and v.strip():
                self.out.append(f"[{k}] {v.strip()}")

    def handle_endtag(self, tag):
        if tag in SKIP and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if self.skip:
            return
        t = re.sub(r"\s+", " ", data).strip()
        if t:
            self.out.append(t)


for f in sys.argv[1:]:
    s = open(f, encoding="utf-8").read()
    s = s[s.find("<x-dc>"):s.find("</x-dc>")]
    p = P()
    p.feed(s)
    seen = []
    for t in p.out:
        if t not in seen:
            seen.append(t)
    print(f"=== {f.split('/')[-1]} ({len(seen)} strings)")
    for t in seen:
        print("  " + t)
