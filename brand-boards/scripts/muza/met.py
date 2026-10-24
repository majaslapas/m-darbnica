#!/usr/bin/env python3
"""Met Open Access API helper (search v1.1 paginated + object v1), cached, rate-limited.

usage:
  met.py search "<querystring without limit/offset>" [max]
  met.py obj <id> [<id> ...]
  met.py img <id> <outdir> [all]     download primaryImage (and additionalImages if 'all')
"""
import json, os, sys, time, urllib.request, urllib.parse, ssl

S = "/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad"
CACHE = os.path.join(S, "dl/muza/met-json")
os.makedirs(CACHE, exist_ok=True)
AVOID = {253370, 205719, 253592, 251493, 251476, 437394, 436483, 436105, 435844,
         438417, 336228, 337497, 337060, 358117}
UA = "MdarbnicaBrandBoards/1.0 (design pitch) python-urllib/3"
_last = [0.0]
CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt") if os.path.exists("/root/.ccr/ca-bundle.crt") else ssl.create_default_context()


def get(url, binary=False, tries=4):
    for t in range(tries):
        dt = time.time() - _last[0]
        if dt < 0.25:
            time.sleep(0.25 - dt)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                data = r.read()
            return data if binary else json.loads(data)
        except Exception as e:
            sys.stderr.write(f"retry {t} {url}: {e}\n")
            time.sleep(1.5 * (t + 1))
    raise RuntimeError("failed " + url)


def search(qs, maxn=400):
    ids, off, lim = [], 0, 100
    total = None
    while True:
        url = f"https://collectionapi.metmuseum.org/public/collection/v1.1/search?{qs}&limit={lim}&offset={off}"
        d = get(url)
        total = d.get("total")
        got = d.get("objectIDs") or []
        ids += got
        off += lim
        if not got or off >= (total or 0) or len(ids) >= maxn:
            break
    return total, ids[:maxn]


def obj(i):
    p = os.path.join(CACHE, f"{i}.json")
    if os.path.exists(p):
        return json.load(open(p))
    d = get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{i}")
    json.dump(d, open(p, "w"))
    return d


def line(d):
    return "\t".join(str(x) for x in [
        d.get("objectID"), "PD" if d.get("isPublicDomain") else "--",
        d.get("department", "")[:14], d.get("title", "")[:70], d.get("objectDate", "")[:22],
        len(d.get("additionalImages") or []), "img" if d.get("primaryImage") else "noimg",
        "AVOID" if d.get("objectID") in AVOID else ""])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "search":
        maxn = int(sys.argv[3]) if len(sys.argv) > 3 else 400
        total, ids = search(sys.argv[2], maxn)
        print("total", total, "got", len(ids))
        print(" ".join(map(str, ids)))
    elif cmd == "obj":
        for a in sys.argv[2:]:
            try:
                print(line(obj(int(a))))
            except Exception as e:
                print(a, "ERR", e)
    elif cmd == "objs":  # search then describe
        maxn = int(sys.argv[3]) if len(sys.argv) > 3 else 60
        total, ids = search(sys.argv[2], maxn)
        print("total", total)
        for i in ids:
            try:
                print(line(obj(i)))
            except Exception as e:
                print(i, "ERR", e)
    elif cmd == "img":
        i = int(sys.argv[2]); out = sys.argv[3]
        os.makedirs(out, exist_ok=True)
        d = obj(i)
        assert d.get("isPublicDomain"), "not PD"
        assert i not in AVOID
        urls = [d["primaryImage"]] + ((d.get("additionalImages") or []) if len(sys.argv) > 4 else [])
        for k, u in enumerate(urls):
            if not u:
                continue
            ext = os.path.splitext(urllib.parse.urlparse(u).path)[1] or ".jpg"
            fn = os.path.join(out, f"{i}_{k}{ext.lower()}")
            if not os.path.exists(fn):
                b = get(u.replace(" ", "%20"), binary=True)
                open(fn, "wb").write(b)
            print(fn, os.path.getsize(fn))


def thumbs(ids, out):
    os.makedirs(out, exist_ok=True)
    res = []
    for i in ids:
        d = obj(i)
        if not d.get("isPublicDomain") or i in AVOID:
            continue
        u = d.get("primaryImageSmall") or d.get("primaryImage")
        if not u:
            continue
        fn = os.path.join(out, f"{i}.jpg")
        if not os.path.exists(fn):
            try:
                open(fn, "wb").write(get(u.replace(" ", "%20"), binary=True))
            except Exception as e:
                sys.stderr.write(f"thumb fail {i} {e}\n"); continue
        res.append(fn)
    return res


if __name__ == "__main__" and sys.argv[1] == "thumbs":
    out = sys.argv[2]
    ids = [int(x) for x in sys.argv[3:]]
    for f in thumbs(ids, out):
        print(f)


if __name__ == "__main__" and sys.argv[1] == "views":
    # all views (web-large) of given ids -> outdir/<id>_<k>.jpg
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for i in [int(x) for x in sys.argv[3:]]:
        d = obj(i)
        if not d.get("isPublicDomain") or i in AVOID:
            print("skip", i); continue
        urls = [d.get("primaryImage")] + (d.get("additionalImages") or [])
        for k, u in enumerate(urls):
            if not u:
                continue
            u2 = u.replace("/original/", "/web-large/").replace(" ", "%20")
            fn = os.path.join(out, f"{i}_{k}.jpg")
            if not os.path.exists(fn):
                try:
                    open(fn, "wb").write(get(u2, binary=True))
                except Exception as e:
                    sys.stderr.write(f"view fail {i}_{k} {e}\n"); continue
            print(fn)


if __name__ == "__main__" and sys.argv[1] == "orig":
    # orig <outdir> <id>:<k>,<k> ...
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for spec in sys.argv[3:]:
        i, ks = spec.split(":")
        i = int(i)
        d = obj(i)
        assert d.get("isPublicDomain") and i not in AVOID, i
        urls = [d.get("primaryImage")] + (d.get("additionalImages") or [])
        for k in [int(x) for x in ks.split(",")]:
            u = urls[k].replace(" ", "%20")
            fn = os.path.join(out, f"{i}_{k}.jpg")
            if not os.path.exists(fn):
                try:
                    open(fn, "wb").write(get(u, binary=True))
                except Exception as e:
                    sys.stderr.write(f"orig fail {i}_{k} {e}\n"); continue
            print(fn, os.path.getsize(fn))
