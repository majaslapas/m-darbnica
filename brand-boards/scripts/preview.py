"""Turn a static .dc.html artboard into a plain local HTML page for screenshots."""
import sys, os, re, json, hashlib, subprocess
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
blobs = json.load(open(os.path.join(S, "scripts", "blobmap.json")))
FONTDIR = os.path.join(S, "fontcache")
os.makedirs(FONTDIR, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

def curl(url, out=None):
    args = ["curl", "-sS", "-A", UA, url]
    if out:
        args += ["-o", out]
        subprocess.run(args, check=True)
        return None
    return subprocess.run(args, check=True, capture_output=True).stdout.decode()

def local_fonts(href):
    href = href.replace("&amp;", "&")
    key = hashlib.md5(href.encode()).hexdigest()[:10]
    cssp = os.path.join(FONTDIR, key + ".css")
    if not os.path.exists(cssp):
        css = curl(href)
        def rep(m):
            u = m.group(1)
            fn = hashlib.md5(u.encode()).hexdigest()[:12] + ".woff2"
            p = os.path.join(FONTDIR, fn)
            if not os.path.exists(p):
                curl(u, p)
            return f"url({fn})"
        css = re.sub(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", rep, css)
        open(cssp, "w").write(css)
    return "file://" + cssp

def convert(src, dst):
    t = open(src).read()
    helmet = re.search(r"<helmet>(.*?)</helmet>", t, re.S).group(1)
    body = re.search(r"<x-dc>(.*?)</x-dc>", t, re.S).group(1)
    body = re.sub(r"<helmet>.*?</helmet>", "", body, flags=re.S)
    links = re.findall(r'<link[^>]+href="([^"]+)"[^>]*>', helmet)
    style = "".join(re.findall(r"<style>(.*?)</style>", helmet, re.S))
    def blob(m):
        f = blobs.get(m.group(1))
        return ("file://" + os.path.join(S, f)) if f else m.group(0)
    body = re.sub(r"/_blob/([0-9a-f]{32})", blob, body)
    style = re.sub(r"/_blob/([0-9a-f]{32})", blob, style)
    head = "".join(f'<link rel="stylesheet" href="{local_fonts(h)}">' for h in links if "fonts.googleapis" in h)
    html = f'<!doctype html><html><head><meta charset="utf-8">{head}<style>{style}</style></head><body style="margin:0">{body}</body></html>'
    open(dst, "w").write(html)

for src in sys.argv[1:]:
    dst = os.path.join(S, "preview", os.path.basename(src).replace(".dc.html", ".html"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    convert(src, dst)
    print(dst)
