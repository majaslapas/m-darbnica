#!/usr/bin/env python3
"""Write assets8/muza/credits.json (one entry per source image)."""
import json, os, glob
from PIL import Image

S = "/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad"
A = S + "/assets8/muza"
MJ = S + "/dl/muza/met-json"
CF = json.load(open(S + "/work/muza/commons_final.json"))


def files_for(prefix):
    out = []
    for f in sorted(glob.glob(f"{A}/{prefix}_*")):
        im = Image.open(f)
        out.append(dict(file=os.path.basename(f), width=im.width, height=im.height,
                        bytes=os.path.getsize(f), alpha=im.mode in ("RGBA", "LA") or "transparency" in im.info))
    return out


def met(prefix, oid, img_index, kind, use, crop_note):
    d = json.load(open(f"{MJ}/{oid}.json"))
    assert d["isPublicDomain"]
    urls = [d["primaryImage"]] + (d.get("additionalImages") or [])
    artist = (d.get("artistPrefix", "") + " " + d.get("artistDisplayName", "")).strip() if d.get("artistDisplayName") else \
        f"Unknown artist ({d.get('culture') or 'Classical'})"
    date = d["objectDate"]
    if not date:
        yr = lambda v: f"{-v} BCE" if v < 0 else f"{v} CE"
        date = f"undated (Met lists no date; catalogue range {yr(d['objectBeginDate'])}–{yr(d['objectEndDate'])})"
    return dict(
        id=prefix, kind=kind, files=files_for(prefix),
        title=d["title"], artist=artist, date=date,
        culture=d.get("culture"), period=d.get("period") or None, medium=d.get("medium"),
        institution="The Metropolitan Museum of Art, New York",
        department=d.get("department"), accession_number=d.get("accessionNumber"), credit_line=d.get("creditLine"),
        source=dict(type="Met Open Access", objectID=oid, objectURL=d["objectURL"], image_url=urls[img_index],
                    image_view=("primary image" if img_index == 0 else f"additionalImages[{img_index - 1}]")),
        license="CC0 1.0 (Met Open Access, public domain)", license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        attribution=f"{d['title']}" + (f", {d['objectDate']}" if d['objectDate'] else "") + f". The Metropolitan Museum of Art, {d.get('creditLine')} (CC0).",
        attribution_required=False,
        processing=crop_note, suggested_use=use)


def commons(prefix, title, subject, building, architect, subject_date, use, crop_note, local_res):
    c = CF[title]
    lic = c["license"]
    sa = "SA" in lic
    return dict(
        id=prefix, kind="facade detail (rectangular crop)", files=files_for(prefix),
        title=subject, artist=f"{c['artist']} (photographer); facade: {architect}",
        photographer=c["artist"], date=f"photo {c['date'][:10]}; building {subject_date}",
        building=building, architect=architect,
        source=dict(type="Wikimedia Commons", file=title, file_page=c["page"], original_url=c["url"],
                    original_size=f"{c['w']}x{c['h']}", downloaded_rendition=local_res,
                    description=c["desc"][:200]),
        license=lic, license_url=c["license_url"],
        attribution=f"Photo: {c['artist']}, {lic}, via Wikimedia Commons ({c['page']}). Cropped and colour-graded.",
        attribution_required=True,
        share_alike=sa,
        license_note=("ShareAlike: these graded crops are adaptations; if published they must be credited and "
                      "offered under CC BY-SA 4.0 (the rest of a layout is not affected when the image is used as a "
                      "separate, credited element)." if sa else
                      "Credit the photographer and licence wherever the image is published; note that it was modified."),
        processing=crop_note, suggested_use=use)


E = []
E.append(met("muza_head_profile", 253057, 2, "sculpture cutout (RGBA)",
             "Hero cutout: pure right-facing profile; place type in the space in front of the face; works huge and cropped off an edge.",
             "Additional view 2 (strict profile). Background removed (watershed+GrabCut, guided-filter edge); mount rod removed; resized to ~1400 px."))
E.append(met("muza_dancer_bronze", 255408, 0, "sculpture cutout (RGBA)",
             "Signature figure for music/dance nights: tall, veiled, in motion. Use full-height on posters or as a narrow column beside text.",
             "Primary view. Background removed; foot and hem kept; floor shadow removed."))
E.append(met("muza_bust_veiled", 253055, 0, "sculpture cutout (RGBA)",
             "Quiet portrait for cinema/gallery programmes and 'about' pages; three-quarter view, downcast gaze to the left.",
             "Primary view. Background and modern plinth removed."))
E.append(met("muza_mask_tragic", 247521, 0, "sculpture cutout (RGBA)",
             "Theatre/cinema motif; frontal and graphic. Eye and mouth openings are transparent, so a colour or photo can show through.",
             "Primary view. Background removed; through-holes (eyes, mouth, suspension hole) made transparent; red museum inventory number retouched out."))
E.append(met("muza_capital_pilaster", 252548, 0, "architecture cutout (RGBA)",
             "Architectural accent: a crown above a headline or a footer anchor; volutes, acanthus and a small central head.",
             "Primary view. Background and cast shadow removed."))
E.append(met("muza_sphinx_archaic", 248501, 0, "sculpture cutout (RGBA)",
             "Guardian figure that rhymes with the sphinxes at Alberta iela 2a; strong wing silhouette; straight base for sitting on a baseline.",
             "Primary (full-object) view, cut at the bottom edge of the sphinx's own plinth slab (the lyre-shaped capital below is omitted). Tail loop and belly gap transparent."))
E.append(met("muza_vase_kitharode", 254896, 6, "vase detail (rectangular crop)",
             "Music image: a singer with a kithara (concert/jazz programmes). The black glaze becomes deep green or ink in the duotones, so it can run full-bleed.",
             "Detail view of the painted kitharode (additionalImages[5]); cropped to exclude a specular reflection on the glaze."))
E.append(met("muza_fresco_kithara", 247009, 2, "wall-painting detail (rectangular crop)",
             "Narrative image: seated woman with a kithara and a girl behind her chair; Pompeian red; works as a large editorial picture.",
             "Detail view (additionalImages[1]) of the Boscoreale Room H panel; slight trims at the sides."))
E.append(met("muza_fresco_redfield", 247009, 0, "colour field / texture (rectangular crop)",
             "Colour field: cracked Pompeian red plaster with no figures; use as a band, backdrop or texture behind type.",
             "Crop of the plain red wall in the upper right of the same panel (above the figures, below the painted cornice)."))
E.append(commons("muza_facade_alberta13_mask", "File:Latvia, Riga, Central Riga, Art Nouveau, Detail 150502-51.jpg",
                 "Screaming mascaron with turban-like headdress", "Alberta iela 13, Rīga", "Mikhail Eisenstein", "1904",
                 "Most striking facade image: the open-mouthed face suits jazz/DJ nights; crop tighter to the face for avatars.",
                 "Crop of the head and headdress (top 7% and bottom 17% trimmed).", "1920 px rendition (full-size original was rate-limited by Commons)"))
E.append(commons("muza_facade_alberta2a_sphinx", "File:Art Nouveau Riga 31.jpg",
                 "Sphinx at the entrance", "Alberta iela 2a, Rīga", "Mikhail Eisenstein", "1906",
                 "Rīga's counterpart to the Greek sphinx: hard sun, a shadow over half the face; pairs with muza_sphinx_archaic.",
                 "Crop of head and chest; the neighbouring Isaiah Berlin memorial plaque is excluded.", "3840 px rendition"))
E.append(commons("muza_facade_alberta13_peacock", "File:Latvia, Riga, Central Riga, Art Nouveau, Detail 150502-60.jpg",
                 "Peacock relief with fanned tail under stylised buds", "Alberta iela 13, Rīga", "Mikhail Eisenstein", "1904",
                 "Vertical ornament for narrow layouts (stories, side columns, ticket stubs); the peacock tail is the hero.",
                 "Crop of the relief and its buds, cornice bands trimmed.", "1920 px rendition (full-size original was rate-limited by Commons)"))
E.append(commons("muza_facade_alberta13_winged", "File:Latvia, Riga, Central Riga, Art Nouveau, Detail 150502-41.jpg",
                 "Winged female head (crowned) on a console", "Alberta iela 13, Rīga", "Mikhail Eisenstein", "1904",
                 "The 'muse' of the facade: frontal female face with crown and wings; good for the Mūza name lock-up or covers.",
                 "Crop of the head, crown and upper wings (upper 44% of the photo).", "3840 px rendition"))
E.append(commons("muza_facade_elizabetes33_atlas", "File:Latvia, Riga, Central Riga, Art Nouveau, Detail 150502-53.jpg",
                 "Atlas (male caryatid) carrying the cornice", "Elizabetes iela 33, Rīga", "Mikhail Eisenstein", "1901",
                 "Weight and effort: the bearded atlas carrying the cornice; strong as a full-bleed portrait or for heavy-music nights.",
                 "Crop from the cornice to the knotted drapery.", "1920 px rendition (full-size original was rate-limited by Commons)"))

meta = dict(
    set="Mūza brand direction (M/darbnīca) - classical and Rīga Art Nouveau image set",
    generated="2026-10-24",
    palette=dict(cream="#EFE7D8", deep_green="#1F3A2D", dusty_rose="#D9A6A1", deep_rose="#B65A61", ink="#151413", brass="#A9844E"),
    treatments=dict(
        natural="'_cut.png' (cutouts) or '_natural.jpg' (crops): warm photographic grade; blacks lifted to ink #151413, whites rolled to warm off-white",
        green="'_green': duotone deep green #1F3A2D (shadows) to cream #EFE7D8 (highlights), interpolated in OKLab",
        rose="'_rose': duotone ink #151413 (shadows) to dusty rose #D9A6A1 (highlights), interpolated in OKLab"),
    formats="Cutouts: 8-bit indexed PNG with full alpha (223 colours, plus 32 semi-transparent edge entries in 8 alpha steps, and 1 transparent). Crops: progressive JPG at quality 85, max 1400 px.",
    avoided_object_ids="All Met objectIDs in haralds-brand credits.json were excluded (none used).",
    entries=E)
json.dump(meta, open(A + "/credits.json", "w"), indent=1, ensure_ascii=False)
print("entries", len(E), "files", sum(len(e["files"]) for e in E))
for e in E:
    print(e["id"], len(e["files"]), e["license"])
