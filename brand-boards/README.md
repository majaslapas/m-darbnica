# M/darbnīca — brand directions (pitch boards)

Five brand directions for the M/darbnīca relaunch, made for the client pitch. Each has a brand board and
an applications board. The live boards are on the Design canvas: https://claude.ai/artifact/Mp18mqQVYto2wVXkxAnnh1

All five keep the client's existing logo unchanged and use colour hard-flash photography of real
people at their concerts and parties. Two habits from the client's own Instagram run through every
direction:
- the logo sits by the heading like a superscript (posters, Instagram, print; never in a website hero);
- a small white logo sits top right on some photos.

| | A · Plate | C · Jūgends | D · Kadrs | E · Jaunais vilnis | F · Zibspuldze |
|---|---|---|---|---|---|
| Reference | 1950s–60s jazz record sleeves | Rīga Art Nouveau (Alberta iela), new retro | Art-house film stills | 1960s New Wave posters, flyposter walls | On-camera film flash, their own feed |
| Mood | Bold, nightlife | Artsy, calm, timeless | Quiet, gallery-like | Loud, graphic | Direct, warm, close to the people |
| Ground | Vinyl Black `#141311` | Cream `#EFE7D8` / Deep green `#1F3A2D` | Screen White `#F2F0EB` | Affiche `#F4F1EA` | Night `#0E0E0D` |
| Green | Bottle Green `#213D2E` | Deep green `#1F3A2D` | Fir `#23392F` | Vert `#1F4535` | Pine `#1D3B2D` |
| Pink | Rouge `#CF5C63`, Blush `#EFC4BE` | Dusty rose `#D9A6A1`, Deep rose `#B65A61` | Cinema Rose `#A9494F` | Rose Rouge `#D8606A`, Pale Rose `#F2CBC5` | Pink `#F2C4C8`, Red `#D9404C` |
| Type | League Gothic + Libre Franklin | Their Helvetica (TeX Gyre Heros) + Futura (Jost) | Instrument Serif + Instrument Sans | Archivo 62–125% | Their Helvetica (TeX Gyre Heros) + Futura (Jost) |
| Signature | Sleeve, record label, tracklist, catalogue numbers, blurred golden light | Arched windows, whiplash lines, sunburst behind the logo, Secession bars | Slate, timecodes, screenplay page, credits block | Flyposter wall, the facade ear, jukebox strips, tokens, backstage pass | Frame numbers, orange date stamp, contact-sheet strips |

## The client's fonts

Identified from their Instagram graphics: headlines and body text are **Helvetica Regular** (letter
spacing 0 in some posts, about −5% in others). The bold all-caps month word ("SEPTEMBER") is
**Futura Demi**, a different family. The boards embed free stand-ins:
- TeX Gyre Heros (GUST licence) for Helvetica: `fonts/texgyreheros-*.woff2`;
- Jost (SIL OFL) for Futura: `fonts/jost-var.woff2`.

Jost is self-hosted because Google Fonts' split subset makes Chromium draw Ā, Ī and Ū as a letter plus
a loose macron. If the client has Helvetica and Futura licences, swap the real fonts in.

## Logo

The logo is the client's existing mark, vectorised from the 1080 px image on the current site
(`logo/m_logo.svg`) and recoloured per palette (`logo/variants/`). It is never redrawn. Replace the
traced file with the original vector when the client sends it.

## Files

- `canvas/` holds the artboard sources (`.dc.html`) and the canvas index. Images are referenced by
  their uploaded `/_blob/…` URLs, so they render only inside the canvas artifact.
- `fonts/` holds the embedded fonts and their licences.
- `ornaments/` holds the Art Nouveau kit for C: arch clip paths and outlines, whiplash lines, Secession
  border tile and pilaster, stem and bloom, corners, sunburst.
- `textures/` holds the film grain and dust, the blurred light overlays (`light_*`, for
  `mix-blend-mode: screen`), the ear cutout and halftones from the facade, the C paper stocks and
  the E wall and crumple maps.
- `scripts/`:
  - `process_flash.py`: the hard-flash colour grade for event photos (frontal pop, background
    falloff, film split tone, halation, grain).
  - `datestamp.py`: the orange seven-segment film date stamp used in F.
  - `arch_poly.py`: CSS `clip-path` polygons for arch-topped photo crops.
  - `ornaments/`: the parametric ornament generator. `ear/`: the facade-ear cutout, halftone and
    poster scripts. `gen_lights.py`: the blurred light textures.
  - Earlier rounds: `process.py`, `process_light.py`, `process_v3.py`, `process_c_col.py`,
    `halftone.py`, `trace_logo.py`, `edges.json`.
  - `preview.py` and `shot.js`: convert a board to plain HTML and screenshot it with Playwright.
    `blobmap.json` maps blob ids to the textures, fonts and logos in this folder. The photos are not
    committed, so they stay blank in local previews.
  - `photos.txt`: the source photos from the current site's gallery.

The photos are placeholders taken from the current mdarbnica.lv gallery. Swap them for the new
photographer's shots before anything goes public.
