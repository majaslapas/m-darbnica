# M/darbnīca — brand directions (pitch boards)

Five brand directions for the M/darbnīca relaunch, made for the client pitch. Each has a brand board
(*zīmols*) and an applications board (*pielietojums*). The live boards are on the Design canvas:
https://claude.ai/artifact/Mp18mqQVYto2wVXkxAnnh1

All text on the boards is Latvian. Each board opens with the direction's name and, directly below it, the
characteristics that set it apart from the other four.

All five keep the client's existing logo unchanged and use hard-flash photography of real people at their
concerts and parties. Two habits from the client's own Instagram run through every direction:
- the logo sits by the heading like a superscript (posters, Instagram, print; never in a website hero);
- a small white logo sits top right on some photos.

## The five directions

**Zibspuldze** ("flash", was F): Zibspuldzes fotogrāfija · Eksperimentāla tipogrāfija · Logotips kā fons · Krāsu pārklājumi
- Colour hard-flash photos under colour overlays.
- The logo works as a large background shape and as a window onto photos.
- Experimental type: photo-filled letters, split words, text on a circle.
- Colours: Nakts `#0E0E0D` · Zibsnis `#FBFAF6` · Priede `#1D3B2D` · Rozā `#F2C4C8` · Neons `#D9404C`.
- Type: Helvetica and Futura (see below).

**Plate** ("record", was A): Skaņuplates vāks · Melnbaltas fotogrāfijas · Izplūdusi gaisma · Programma kā dziesmu saraksts · Šauri, augsti burti
- Based on 1950s–60s jazz record sleeves.
- Black-and-white photos only, with colourless blurred light.
- The programme is laid out as a tracklist with catalogue numbers.
- Colours: Vinils `#141311` · Pudele `#213D2E` · Etiķete `#CF5C63` · Pūderis `#EFC4BE` · Papīrs `#EDE7DC`.
- Type: League Gothic and Libre Franklin.

**Mūza** ("muse", replaces C · Jūgends): Antīkā skulptūra · Jūgendstila arhitektūra · Marmors un zibspuldze · Krēmkrāsas, zaļie un rozā toņi
- There are no drawn ornaments.
- Flash photos sit beside Roman and Greek marble and bronze, a Boscoreale fresco, and real Art Nouveau facade details from Alberta iela 13 and Elizabetes iela 33.
- It keeps the colours of the former C.
- Colours: Marmors `#EFE7D8` · Lauri `#1F3A2D` · Freska `#D9A6A1` · Vīns `#B65A61` · Tinte `#151413` · Misiņš `#A9844E`.
- Type: Helvetica.

**Kadrs** ("film frame", was D): Kino kadrs · Subtitri · No melnbalta uz krāsainu · Filmēšanas klapes detaļas · Antikvas virsraksti
- Art-house film stills: subtitles, timecodes, a slate and a screenplay page.
- Black-and-white photos turn to colour.
- Colours: Ekrāns `#F2F0EB` · Celuloīds `#151514` · Egle `#23392F` · Samts `#A9494F` · Sudrabs `#B8B5AE`.
- Type: Instrument Serif for titles, and the client's Helvetica for text and subtitles.

**Afiša** ("poster", was E · Jaunais vilnis): Afišu siena · Fasādes auss · Instrumenti kā grafika · Teksts un fons vienā krāsā · Plati, trekni burti
- A flyposter wall.
- The facade ear, the neon logo sign and museum jazz instruments appear as halftone and stencil graphics.
- Text and ground are shades of one colour, e.g. Ķirsis on Roze.
- Colours, in tone families:
  - Ziedlapa `#F2CBC5` · Roze `#D8606A` · Ķirsis `#9E2F3A`
  - Piparmētra `#BFD6C7` · Salvija `#4F8466` · Sūna `#1F4535`
  - Papīrs `#F4F1EA` · Ogle `#111110`
- Type: Archivo at 62–125% widths.

## The client's fonts

The client's Instagram graphics use two fonts:
- **Helvetica Regular** for headlines and body text, with letter spacing 0 in some posts and about −5% in others.
- **Futura Demi** for the bold all-caps month word ("SEPTEMBER"). It is a different family.

The boards embed free stand-ins:
- TeX Gyre Heros (GUST licence) for Helvetica: `fonts/texgyreheros-*.woff2`.
- Jost (SIL OFL) for Futura: `fonts/jost-var.woff2`.

Jost is self-hosted because Google Fonts' split subset makes Chromium draw Ā, Ī and Ū as a letter plus
a loose macron. If the client has Helvetica and Futura licences, swap the real fonts in.

## Logo

The logo is the client's existing mark. It was vectorised from the 1080 px image on the current site
(`logo/m_logo.svg`) and recoloured per palette (`logo/variants/`). It is never redrawn. Replace the
traced file with the original vector when the client sends it.

## Image credits

**Mūza** (`textures/muza/`; full metadata in `textures/muza/credits.json`):
- **The Metropolitan Museum of Art, Open Access (CC0):**
  - marble head of a woman (253057)
  - bronze statuette of a veiled and masked dancer (255408)
  - tragic theatre mask (247521)
  - marble pilaster capital (252548)
  - wall painting from the villa at Boscoreale (247009)
- **Rīga Art Nouveau facades:** photos by Richardmaackphotography, CC BY 4.0, via Wikimedia Commons. They were cropped and toned. The canvas carries the same credit as a note next to the Mūza boards.
  - Alberta iela 13: [mascaron](https://commons.wikimedia.org/wiki/File:Latvia,_Riga,_Central_Riga,_Art_Nouveau,_Detail_150502-51.jpg), [winged head](https://commons.wikimedia.org/wiki/File:Latvia,_Riga,_Central_Riga,_Art_Nouveau,_Detail_150502-41.jpg), [peacock](https://commons.wikimedia.org/wiki/File:Latvia,_Riga,_Central_Riga,_Art_Nouveau,_Detail_150502-60.jpg).
  - Elizabetes iela 33: [atlas](https://commons.wikimedia.org/wiki/File:Latvia,_Riga,_Central_Riga,_Art_Nouveau,_Detail_150502-53.jpg).

**Afiša** (`textures/afisa/`; full metadata in `textures/afisa/credits.json`):
- **The Metropolitan Museum of Art, Open Access (CC0):**
  - alto saxophone by Adolphe Sax (503909)
  - valve trumpet by Courtois & Mille (503961)
  - trombone (504686)
  - double bass by Bartolomeo Cristofori (503176)
  - clarinet by Buffet Crampon (854790)
  - bass drum by John G. Pike (504262)
- The neon-sign crops come from the client's own event photos, so they are not committed.

## Files

- `canvas/` holds the artboard sources (`.dc.html`) and the canvas index. Images are referenced by
  their uploaded `/_blob/…` URLs, so they render only inside the canvas artifact.
- `fonts/` holds the embedded fonts and their licences.
- `textures/` holds:
  - film grain and dust;
  - the blurred light overlays (`light_*` golden, `light_*_mono` colourless, for `mix-blend-mode: screen`);
  - the ear cutout and halftones from the facade;
  - the Afiša wall, paper and crumple maps and the tape (`tex_c_tape.png`, kept from the old C);
  - `muza/` (sculpture and facade images);
  - `afisa/` (instrument halftones, stencils, line drawings and cutouts, plus logo halftones).
  The halftone and stencil masters are black on transparent and are recoloured in the browser with an SVG
  `feFlood` + `feComposite` filter.
- `scripts/`:
  - `process_flash.py`: the hard-flash colour grade for event photos (frontal pop, background
    falloff, film split tone, halation, grain). `process_bw.py`: its black-and-white version for Plate,
    plus the colourless light textures.
  - `datestamp.py`: the orange seven-segment film date stamp.
  - `ear/`: the facade-ear cutout, halftone and poster scripts. `gen_lights.py`: the blurred light textures.
  - `muza/`: Met and Commons sourcing, cutouts and duotones for Mūza. `afisa/`: instrument cutouts,
    halftones, stencils and line drawings, the neon crops and the logo halftones for Afiša.
  - `preview.py` and `shot.js`: convert a board to plain HTML and screenshot it with Playwright.
    `blobmap.json` maps blob ids to the textures, fonts and logos in this folder. The photos are not
    committed, so they stay blank in local previews.
  - `lint_dc.py`: checks a board against the canvas file rules. `extract_text.py`: lists every visible
    string on a board, for the language check.
  - Earlier rounds: `process.py`, `process_light.py`, `process_v3.py`, `process_c_col.py`,
    `halftone.py`, `trace_logo.py`, `edges.json`.
  - `photos.txt`: the source photos from the current site's gallery.

The photos are placeholders taken from the current mdarbnica.lv gallery. Swap them for the new
photographer's shots before anything goes public.
