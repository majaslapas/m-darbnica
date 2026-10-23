# M/darbnīca — brand directions (pitch boards)

Four brand directions for the M/darbnīca relaunch, made for the client pitch: A (dark), C (warm paper)
and D–E (light mode, movie grain, low-key lit photography). Each has a brand board and an applications
board. The live boards are on the Design canvas: https://claude.ai/artifact/Mp18mqQVYto2wVXkxAnnh1

All four keep the client's existing logo unchanged and use what the client already chose (dark green,
reddish/dusty pink, near-black). They also use the effect the client asked for: black-and-white
photography where colour is revealed on hover. What differs is the vintage reference, how much of each
colour is used, and the type.

| | A · Plate | C · Partitūra | D · Kadrs | E · Jaunais vilnis |
|---|---|---|---|---|
| Reference | 1950s–60s jazz record sleeves | Printed music scores, rubber stamps, paper goods | Art-house film stills, festival catalogues | 1960s New Wave cinema posters, flyposter walls |
| Mood | Bold, graphic, nightlife | Warm, tactile, community | Quiet, gallery-like, cinematic | Loud, graphic, a night out |
| Ground | Vinyl Black `#141311` | Cotton `#EFE9DD`, Cardstock `#F7F4EC` | Screen White `#F2F0EB` | Affiche `#F4F1EA` |
| Green | Bottle Green `#213D2E` | Ink Green `#2F4A3A` | Fir `#23392F` | Vert `#1F4535` |
| Pink | Rouge `#CF5C63`, Blush `#EFC4BE` | Stamp Pink `#C8565F` | Cinema Rose `#A9494F` | Rose Rouge `#D8606A`, Pale Rose `#F2CBC5` |
| Other | Sleeve Paper `#EDE7DC` | Ink `#1F1D1A`, Kraft `#C2A57B` | Celluloid `#151514`, Silver `#B8B5AE` | Noir `#111110` |
| Type | League Gothic + Libre Franklin | Brygada 1918, roman and italic | Instrument Serif + Instrument Sans | Archivo (62–125% widths) |
| Photo | Duotones, one kept colour, film grain over every element | Warm fibre prints with deckle edges and tape | Letterboxed low-key stills, subtitles, dust, frame lines | Hard light, deep blacks, two-colour halftone, mirror-ball light |
| Elements | Record sleeve with the logo on the label, vinyl, ticket, tracklist, catalogue numbers | Rubber stamp, blind emboss, ticket with torn stub, kraft tag, setlist, gallery label, kraft bag | Slate, screenplay page, timecodes, poster credits block, ticket with barcode, programme booklet | Flyposter wall, sold-out strip, tear-off flyer, jukebox title strips, drink tokens, backstage pass, wristband, badges |

## Logo

The logo is the client's existing mark, vectorised from the 1080 px image on the current site
(`logo/m_logo.svg`) and recoloured for each palette (`logo/variants/`). It is never redrawn. The only
new things built around it are applications of it: a rubber stamp and a blind emboss (C), and a
sticker, drink tokens and a badge (E). Replace the traced file with the original vector when the
client sends it.

## Type and Latvian characters

All fonts are free Google Fonts and render the Latvian characters (ā č ē ģ ī ķ ļ ņ š ū ž) cleanly.
Display lines keep a line height of 1.0 or more so the long marks never collide with the line above.
C uses Brygada 1918 because EB Garamond, Fraunces, Newsreader and Cormorant drew the macrons and
carons poorly at display sizes.

## Files

- `canvas/` holds the artboard sources (`.dc.html`) and the canvas index. Images are referenced by
  their uploaded `/_blob/…` URLs, so they render only inside the canvas artifact.
- `logo/` holds the traced logo and its colour variants.
- `textures/` holds the generated textures: film grain and dust, the C paper stocks (cotton, cardstock,
  kraft, tape, ink voids for the stamps), the E wall, paper and crumple maps, and the E halftones.
- `scripts/`:
  - `process.py`: A and C photo treatments (B&W, duotone, selective colour, warm prints) and the
    grain texture.
  - `process_light.py`: D and E movie-grain treatments (two-scale grain, halation, colour twins for
    the reveal) and the dust texture.
  - `process_v3.py`: the A hero, the grain layer, the C paper stocks, the E party photos, and the wall
    and crumple textures.
  - `process_c_col.py`: the colour twin for the C website reveal.
  - `halftone.py`: the E halftones.
  - `trace_logo.py`: logo vectorisation with potrace.
  - `edges.json`: the deckle and torn paper edges used as clip paths.
  - `preview.py` and `shot.js`: convert a board to plain HTML and screenshot it with Playwright.
    `blobmap.json` maps blob ids to the textures and logos in this folder; the photos are not
    committed, so they stay blank in local previews.
  - `photos.txt`: the source photos from the current site's gallery.

The photos are placeholders taken from the current mdarbnica.lv gallery. Swap them for the new
photographer's shots before anything goes public.
