"""Print an inline SVG of an orange seven-segment film date stamp, e.g. "'27 1 13".

Usage: python3 -I datestamp.py "'27 1 13" HEIGHT_PX [colour]
"""
import sys

text, H = sys.argv[1], float(sys.argv[2])
col = sys.argv[3] if len(sys.argv) > 3 else "#FF8A3D"
W, T, G = 20.0, 3.6, 0.7          # digit width, segment thickness, gap (in 34-unit-high digit space)
DH = 34.0
SEG = {"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg", "5": "acdfg", "6": "acdefg",
       "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def seg_poly(s, x0):
    h2 = DH / 2
    t = T / 2
    def hseg(y):
        return [(x0 + G + t, y), (x0 + G + 2 * t, y - t), (x0 + W - G - 2 * t, y - t), (x0 + W - G - t, y),
                (x0 + W - G - 2 * t, y + t), (x0 + G + 2 * t, y + t)]
    def vseg(x, y0, y1):
        return [(x, y0 + G + t), (x + t, y0 + G + 2 * t), (x + t, y1 - G - 2 * t), (x, y1 - G - t),
                (x - t, y1 - G - 2 * t), (x - t, y0 + G + 2 * t)]
    return {"a": hseg(t), "g": hseg(h2), "d": hseg(DH - t),
            "f": vseg(x0 + t, 0, h2), "b": vseg(x0 + W - t, 0, h2),
            "e": vseg(x0 + t, h2, DH), "c": vseg(x0 + W - t, h2, DH)}[s]


polys = []
x = 0.0
for ch in text:
    if ch.isdigit():
        for s in SEG[ch]:
            pts = seg_poly(s, x)
            # 8 degree italic slant
            pts = [(px + (DH - py) * 0.14, py) for px, py in pts]
            polys.append(" ".join(f"{px:.2f},{py:.2f}" for px, py in pts))
        x += W + 5
    elif ch == "'":
        polys.append(f"{x + 3 + 4.6:.2f},0 {x + 7 + 4.6:.2f},0 {x + 4 + 3.4:.2f},9 {x + 1.5 + 3.4:.2f},9")
        x += 9
    elif ch == " ":
        x += 10
total = x + DH * 0.14
scale = H / DH
print(f'<svg width="{total * scale:.0f}" height="{H:.0f}" viewBox="0 0 {total:.1f} {DH}" aria-hidden="true" '
      f'style="display: block; overflow: visible; filter: drop-shadow(0 0 2px rgba(255,120,40,0.85)) drop-shadow(0 0 6px rgba(255,90,20,0.45));">'
      f'<g fill="{col}" opacity="0.92">' + "".join(f'<polygon points="{p}"></polygon>' for p in polys) + "</g></svg>")
