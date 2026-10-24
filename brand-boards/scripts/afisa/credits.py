"""Write assets8/afisa/credits.json from the downloaded Met object records + the client-material sources."""
import sys, json, os, glob
sys.path.insert(0, '/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad/work/afisa')
from common import *

NOTES = {
    'sax': 'Adolphe Sax alto saxophone, frontal view.',
    'trumpet': 'Valve trumpet with an unusual long-loop wrap; see-through gaps between the valve casings and slide tubes were opened up by hand-placed hints.',
    'trombone': 'Slide trombone, side view.',
    'bass': 'Double bass attributed to Bartolomeo Cristofori, frontal view (view 4 of 4 on the object page).',
    'clarinet': 'Clarinet in B-flat, frontal view.',
    'drum': 'Rope-tensioned bass drum; archival black-and-white photograph. Stencil and line versions redraw the rope lacing from the photo.',
    'cymbals': 'Chinese bo (pair of cymbals). The maker\'s/owner\'s painted character on the front flange was retouched out '
               '(patch rotated from the same flange ring) before the cutout, halftone, stencil and line were made.',
}


def derived(name):
    out = []
    for f in sorted(os.listdir(OUT)):
        if f.startswith(f'afisa_{name}_'):
            out.append(f)
    return out


def main():
    items = []
    for name, (oid, view) in INST.items():
        o = meta(oid)
        urls = [o['primaryImage']] + (o.get('additionalImages') or [])
        maker = o.get('artistDisplayName') or ''
        items.append({
            'subject': name,
            'derived_files': derived(name),
            'title': o.get('title'),
            'maker': maker if maker else f"Unknown maker ({o.get('culture') or 'culture not recorded'})",
            'maker_nationality': o.get('artistNationality') or None,
            'culture': o.get('culture') or None,
            'date': o.get('objectDate'),
            'medium': o.get('medium') or None,
            'accession_number': o.get('accessionNumber'),
            'credit_line': o.get('creditLine'),
            'met_object_id': oid,
            'object_url': o.get('objectURL'),
            'source_image_url': urls[view],
            'is_public_domain': o.get('isPublicDomain'),
            'licence': 'CC0 1.0 Universal (The Metropolitan Museum of Art Open Access)',
            'licence_url': 'https://creativecommons.org/publicdomain/zero/1.0/',
            'notes': NOTES[name],
        })
    for tag, src, desc in [('066', 'S/dl/flash_src/066.jpg', 'Singer at the microphone in front of the red neon M logo sign (logo top-centre-left).'),
                           ('076', 'S/dl/flash_src/076.jpg', 'Guitarist in front of the red neon M logo sign (sign partly hidden by his head, top-left).')]:
        items.append({
            'subject': f'neon{tag}',
            'derived_files': [f for f in sorted(os.listdir(OUT)) if f.startswith(f'afisa_neon{tag}')],
            'title': desc,
            'maker': 'M/darbnica event photography (photographer not recorded in this project)',
            'date': None,
            'source_file': src,
            'source_size': '3500x2336',
            'met_object_id': None,
            'object_url': None,
            'is_public_domain': False,
            'licence': 'Client-owned material, NOT CC0. Use only for M/darbnica work; confirm photographer credit with the client.',
            'notes': 'Tight crops of the neon sign; duotones map a red-weighted brightness (the neon counts as light) '
                     'through dark -> mid -> light tones of each family.',
        })
    items.append({
        'subject': 'logo',
        'derived_files': [f for f in sorted(os.listdir(OUT)) if f.startswith('afisa_logo')],
        'title': 'M/darbnica logo: circle with a single-line M wave',
        'maker': 'M/darbnica (client mark)',
        'source_file': 'S/logo/m_logo.svg',
        'met_object_id': None,
        'object_url': None,
        'is_public_domain': False,
        'licence': 'Client trademark/logo, NOT CC0.',
        'notes': 'Rasterised at 1400 px in the browser, then screened (cell 12 px, 45 deg).',
    })
    doc = {
        'collection': 'M/darbnica brand board, direction "Afisa" - image assets (assets8/afisa)',
        'generated': '2026-10-24',
        'halftone_masters': 'Black #000000 dots on transparent RGBA PNG; recolour in the browser (e.g. SVG feFlood + feComposite in). '
                            '*_halftone_rose.png are pre-coloured #9E2F3A examples; *_halftone_inv.png put dots on the highlights '
                            '(for light dots on a dark ground).',
        'items': items,
    }
    json.dump(doc, open(OUT + 'credits.json', 'w'), ensure_ascii=False, indent=2)
    print('credits.json', len(items), 'items', os.path.getsize(OUT + 'credits.json'), 'bytes')


if __name__ == '__main__':
    main()
