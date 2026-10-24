"""Rate-limited Met Open Access helper. Every download lands in its own new directory under S/dl/afisa/.
Usage:
  python3 -I met.py search <tag> <query> [extra params]      -> dl/afisa/q_<tag>/r.json (all pages)
  python3 -I met.py objects <id> <id> ...                     -> dl/afisa/o_<id>/obj.json
  python3 -I met.py thumbs <id> ...                           -> dl/afisa/t_<id>/small.jpg (primaryImageSmall)
  python3 -I met.py image <id> <n|primary> ...                -> dl/afisa/i_<id>_<n>/<file>
"""
import json, os, subprocess, sys, time, urllib.parse
S = '/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad'
DL = S + '/dl/afisa'
API = 'https://collectionapi.metmuseum.org/public/collection'
_last = [0.0]


def _get(url, out):
    dt = time.time() - _last[0]
    if dt < 0.25:
        time.sleep(0.25 - dt)
    _last[0] = time.time()
    r = subprocess.run(['curl', '-sS', '-m', '90', '-L', '-o', out, '-w', '%{http_code}', url],
                       capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip()


def newdir(name):
    d = os.path.join(DL, name)
    os.makedirs(d, exist_ok=True)
    return d


def search(tag, q, extra=''):
    d = newdir('q_' + tag)
    ids, offset, total = [], 0, None
    while True:
        url = f'{API}/v1.1/search?q={urllib.parse.quote(q)}&departmentId=18&hasImages=true{extra}&offset={offset}&limit=100'
        out = os.path.join(d, f'p{offset}.json')
        code, err = _get(url, out)
        if code != '200':
            print('search fail', code, err); break
        js = json.load(open(out))
        total = js.get('total', 0)
        page = js.get('objectIDs') or []
        ids += page
        offset += len(page)
        if not page or offset >= total or offset >= 400:
            break
    json.dump({'q': q, 'total': total, 'objectIDs': ids}, open(os.path.join(d, 'r.json'), 'w'))
    print(tag, 'total', total, 'got', len(ids))
    return ids


def obj(i):
    d = os.path.join(DL, f'o_{i}')
    out = os.path.join(d, 'obj.json')
    if os.path.exists(out):
        try:
            return json.load(open(out))
        except Exception:
            pass
    os.makedirs(d, exist_ok=True)
    code, err = _get(f'{API}/v1/objects/{i}', out)
    if code != '200':
        print('obj fail', i, code, err); return None
    return json.load(open(out))


def fetch_file(url, dname):
    d = newdir(dname)
    fn = urllib.parse.unquote(url.split('/')[-1]).replace(' ', '_')
    out = os.path.join(d, fn)
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return out
    code, err = _get(urllib.parse.quote(url, safe=':/%()'), out)
    if code != '200':
        print('file fail', url, code, err); return None
    return out


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'search':
        search(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else '')
    elif cmd == 'objects':
        for i in sys.argv[2:]:
            o = obj(int(i))
            if o:
                print(i, o.get('isPublicDomain'), '|', o.get('title'), '|', o.get('artistDisplayName'), '|',
                      o.get('objectDate'), '|', len(o.get('additionalImages') or []))
    elif cmd == 'thumbs':
        for i in sys.argv[2:]:
            o = obj(int(i))
            if o and o.get('primaryImageSmall'):
                print(fetch_file(o['primaryImageSmall'], f't_{i}'))
    elif cmd == 'image':
        i = int(sys.argv[2]); which = sys.argv[3:]
        o = obj(i)
        urls = [o['primaryImage']] + (o.get('additionalImages') or [])
        for w in which:
            n = 0 if w == 'primary' else int(w)
            print(fetch_file(urls[n], f'i_{i}_{n}'))


def views(i):
    """web-large previews of primary + every additional image -> dl/afisa/v_<id>_<n>/"""
    o = obj(i)
    urls = [o['primaryImage']] + (o.get('additionalImages') or [])
    res = []
    for n, u in enumerate(urls):
        if not u:
            continue
        res.append(fetch_file(u.replace('/original/', '/web-large/'), f'v_{i}_{n}'))
    return res


if __name__ == '__main__' and sys.argv[1] == 'views':
    for i in sys.argv[2:]:
        for r in views(int(i)):
            print(r)
