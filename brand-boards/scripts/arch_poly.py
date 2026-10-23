"""Print a CSS clip-path polygon() for an arch-topped box of W x H pixels.

Usage: python3 -I arch_poly.py W H [round|pointed|keyhole] [steps]
round   - semicircular head (radius W/2), straight jambs
pointed - two-centred Gothic/Jugendstil point (centres at 0.15W and 0.85W)
keyhole - full circle head slightly wider than the jambs (horseshoe)
The head keeps its true circular shape for any box ratio.
"""
import sys, math

W, H = float(sys.argv[1]), float(sys.argv[2])
kind = sys.argv[3] if len(sys.argv) > 3 else "round"
n = int(sys.argv[4]) if len(sys.argv) > 4 else 36
pts = []
if kind == "round":
    r = W / 2
    pts.append((0, H))
    for i in range(n + 1):
        a = math.pi - math.pi * i / n
        pts.append((W / 2 + r * math.cos(a), r - r * math.sin(a)))
    pts.append((W, H))
elif kind == "pointed":
    r = W * 0.85
    cy = r * math.sin(math.acos(0.35 * W / r)) if False else None
    # left arc centred at (0.85W, h0), from (0, h0) up to the apex at x = W/2
    dx = 0.85 * W - W / 2
    h_apex = math.sqrt(r * r - dx * dx)
    h0 = h_apex
    pts.append((0, H))
    a0 = math.pi
    a1 = math.pi - math.acos(dx / r)
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        pts.append((0.85 * W + r * math.cos(a), h0 - r * math.sin(a)))
    a0 = math.acos(dx / r)
    for i in range(n + 1):
        a = a0 - a0 * i / n
        pts.append((0.15 * W + r * math.cos(a), h0 - r * math.sin(a)))
    pts.append((W, H))
elif kind == "keyhole":
    r = W / 2
    j = 0.12 * W
    cyc = r
    ang = math.asin((r - j) / r)
    pts.append((j, H))
    pts.append((j, cyc + r * math.cos(ang)))
    start = math.pi / 2 + ang
    for i in range(n * 2 + 1):
        a = start + (2 * math.pi - 2 * ang) * i / (n * 2)
        pts.append((W / 2 - r * math.sin(a - math.pi / 2) if False else W / 2 + r * math.cos(a), cyc + r * math.sin(a)))
    pts.append((W - j, H))
print("polygon(" + ", ".join(f"{x / W * 100:.2f}% {y / H * 100:.2f}%" for x, y in pts) + ")")
