#!/usr/bin/env python3
"""Wikimedia Commons helper. ~1 request/second, descriptive UA, cached JSON.

usage:
  commons.py cat "Category:Foo" [file|subcat|both] [max]
  commons.py search "text" [max]                       (File namespace)
  commons.py info "File:A.jpg" ["File:B.jpg" ...]      licence/author/size summary
  commons.py thumb <outdir> <width> "File:A.jpg" ...    download thumbnails
"""
import json, os, re, sys, time, hashlib, urllib.request, urllib.parse, ssl, html

S = "/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad"
CACHE = os.path.join(S, "dl/muza/commons-json")
os.makedirs(CACHE, exist_ok=True)
UA = "MdarbnicaBrandBoards/1.0 (design pitch; contact via commons) python-urllib/3"
API = "https://commons.wikimedia.org/w/api.php"
CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt") if os.path.exists("/root/.ccr/ca-bundle.crt") else ssl.create_default_context()
_last = [0.0]
DELAY = 2.5


def fetch(url, binary=False, tries=5):
    for t in range(tries):
        dt = time.time() - _last[0]
        if dt < DELAY:
            time.sleep(DELAY - dt)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90, context=CTX) as r:
                data = r.read()
            return data if binary else json.loads(data)
        except urllib.error.HTTPError as e:
            sys.stderr.write(f"HTTP {e.code} try {t} {url[:120]}\n")
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                time.sleep(float(ra) if ra and ra.isdigit() else 10 * (t + 1))
            elif e.code in (403, 404):
                raise
            else:
                time.sleep(3 * (t + 1))
        except Exception as e:
            sys.stderr.write(f"ERR try {t} {url[:120]}: {e}\n")
            time.sleep(3 * (t + 1))
    raise RuntimeError("failed " + url)


def api(params):
    params = dict(params, format="json", formatversion="2")
    qs = urllib.parse.urlencode(params)
    key = hashlib.sha1(qs.encode()).hexdigest()[:20]
    p = os.path.join(CACHE, key + ".json")
    if os.path.exists(p):
        return json.load(open(p))
    d = fetch(API + "?" + qs)
    json.dump(d, open(p, "w"))
    return d


def catmembers(cat, typ="file", maxn=500):
    out, cont = [], {}
    while True:
        d = api(dict(action="query", list="categorymembers", cmtitle=cat, cmlimit="500",
                     cmtype=typ if typ != "both" else "file|subcat", **cont))
        out += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
        if "continue" in d and len(out) < maxn:
            cont = {"cmcontinue": d["continue"]["cmcontinue"]}
        else:
            break
    return out[:maxn]


def strip(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return html.unescape(s).strip()


def info(titles, width=None):
    res = {}
    for i in range(0, len(titles), 40):
        chunk = titles[i:i + 40]
        params = dict(action="query", titles="|".join(chunk), prop="imageinfo",
                      iiprop="url|extmetadata|size|mime")
        if width:
            params["iiurlwidth"] = str(width)
        d = api(params)
        for pg in d.get("query", {}).get("pages", []):
            ii = (pg.get("imageinfo") or [{}])[0]
            em = ii.get("extmetadata", {})
            g = lambda k: strip(em.get(k, {}).get("value", ""))
            res[pg["title"]] = dict(
                title=pg["title"], url=ii.get("url"), thumburl=ii.get("thumburl"),
                width=ii.get("width"), height=ii.get("height"), mime=ii.get("mime"),
                descurl=ii.get("descriptionurl"), license=g("LicenseShortName"),
                license_url=g("LicenseUrl"), artist=g("Artist"), credit=g("Credit"),
                date=g("DateTimeOriginal"), desc=g("ImageDescription")[:300],
                usage=g("UsageTerms"), restrictions=g("Restrictions"))
    return res


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "cat":
        typ = sys.argv[3] if len(sys.argv) > 3 else "file"
        maxn = int(sys.argv[4]) if len(sys.argv) > 4 else 500
        for t in catmembers(sys.argv[2], typ, maxn):
            print(t)
    elif cmd == "search":
        maxn = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        d = api(dict(action="query", list="search", srsearch=sys.argv[2], srnamespace="6", srlimit=str(maxn)))
        for r in d.get("query", {}).get("search", []):
            print(r["title"])
    elif cmd == "info":
        titles = sys.argv[2:]
        if len(titles) == 1 and os.path.exists(titles[0]):
            titles = [l.strip() for l in open(titles[0]) if l.strip()]
        r = info(titles)
        for t in titles:
            x = r.get(t) or next((v for k, v in r.items() if k.replace(" ", "_") == t.replace(" ", "_")), None)
            if not x:
                print(t, "MISSING"); continue
            print(f"{x['width']}x{x['height']}\t{x['license']}\t{x['artist'][:40]}\t{x['date'][:20]}\t{t}")
    elif cmd == "infojson":
        titles = [l.strip() for l in open(sys.argv[2]) if l.strip()]
        r = info(titles)
        json.dump(r, open(sys.argv[3], "w"), indent=1, ensure_ascii=False)
        print("wrote", len(r))
    elif cmd == "thumb":
        out = sys.argv[2]; w = int(sys.argv[3]); titles = sys.argv[4:]
        if len(titles) == 1 and os.path.exists(titles[0]):
            titles = [l.strip() for l in open(titles[0]) if l.strip()]
        os.makedirs(out, exist_ok=True)
        r = info(titles, width=w)
        norm = {k.replace("_", " "): v for k, v in r.items()}
        for t in titles:
            x = r.get(t) or norm.get(t.replace("_", " "))
            if not x:
                print("MISSING", t); continue
            u = x.get("thumburl") or x.get("url")
            if not u:
                continue
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", t[5:])[:120]
            ext = os.path.splitext(urllib.parse.urlparse(u).path)[1].lower() or ".jpg"
            fn = os.path.join(out, os.path.splitext(safe)[0] + ext)
            if not os.path.exists(fn):
                try:
                    open(fn, "wb").write(fetch(u, binary=True))
                except Exception as e:
                    print("FAIL", t, e); continue
            print(fn)


if __name__ == "__main__" and sys.argv[1] == "orig":
    out = sys.argv[2]; titles = sys.argv[3:]
    os.makedirs(out, exist_ok=True)
    r = info(titles)
    norm = {k.replace("_", " "): v for k, v in r.items()}
    for t in titles:
        x = r.get(t) or norm.get(t.replace("_", " "))
        if not x or not x.get("url"):
            print("MISSING", t); continue
        lic = x["license"]
        if any(b in lic.upper() for b in ("NC", "ND")):
            print("SKIP licence", lic, t); continue
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", t[5:])[:120]
        fn = os.path.join(out, safe)
        if not os.path.exists(fn):
            try:
                open(fn, "wb").write(fetch(x["url"], binary=True))
            except Exception as e:
                print("FAIL", t, e); continue
        print(fn, os.path.getsize(fn), lic)
