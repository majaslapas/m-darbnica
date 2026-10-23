# M/darbnīca — brand directions (pitch boards)

Six brand directions for the M/darbnīca relaunch, made for the client pitch: A–C (two dark,
one warm paper) and D–F (light mode, movie grain, low-key lit photography).
The live boards are on the Design canvas: https://claude.ai/artifact/Mp18mqQVYto2wVXkxAnnh1

All six use what the client already chose (dark green, reddish/dusty pink, near-black)
and the effect they asked for: black-and-white photography where colour is revealed.
What differs is the vintage reference, how much of each colour is used, and the type.

| | A · Plate | B · Kino | C · Partitūra |
|---|---|---|---|
| Reference | 1950s–60s jazz record sleeves | Old cinema, film, title cards | Printed music scores, workshop print |
| Mood | Bold, graphic, nightlife | Moody, glamorous, cinematic | Warm, community, daytime-friendly |
| Ground | Vinyl Black `#141311` | Projector Black `#0E100F` | Score Paper `#EEE8DC` |
| Green | Bottle Green `#213D2E` | Velvet Green `#173229` | Ink Green `#2F4A3A` |
| Pink | Rouge `#CF5C63`, Blush `#EFC4BE` | Seat Rose `#B8414E`, Powder `#E3B5B0` | Stamp Pink `#D0606A` |
| Other | Sleeve Paper `#EDE7DC` | Silver `#A8A49C`, Screen `#ECE6DA` | Ink `#1C1B19`, Kraft `#C8B596` |
| Type | League Gothic + Libre Franklin | Bodoni Moda + Jost | EB Garamond + Courier Prime |
| Photo | Duotones, one kept colour | Silver B&W, heavy grain, smoke, selective colour | Warm fibre prints with white borders |
| Elements | Record label, ticket stub, tracklist programme, catalogue numbers, coaster | Film strip, intertitle card, cinema ticket, countdown leader, intermission card, letterboard, popcorn box | Staff lines, fermata mark, rubber stamps, cloakroom tag, setlist, kraft tags, gallery label, tote |

| | D · Kadrs | E · Jaunais vilnis | F · Kontaktlapa |
|---|---|---|---|
| Reference | Art-house film stills, festival catalogues | 1960s New Wave cinema posters | Darkroom contact sheets |
| Mood | Quiet, gallery-like, cinematic | Loud, graphic, confident | Hands-on, analog, curious |
| Ground | Screen White `#F2F0EB` | Affiche `#F4F1EA` | Fixer Grey `#E6E3DC`, Print White `#FAF8F3` |
| Green | Fir `#23392F` | Vert `#1F4535` | Developer Green `#2D4A3D` |
| Pink | Cinema Rose `#A9494F` | Rose Rouge `#D8606A`, Pale Rose `#F2CBC5` | Grease Rose `#C7525C` |
| Other | Celluloid `#151514`, Silver `#B8B5AE` | Noir `#111110` | Rebate Black `#121212` |
| Type | Instrument Serif + Instrument Sans | Archivo (62–125% widths) | Fraunces + IBM Plex Mono |
| Photo | Letterboxed low-key stills, subtitles, dust | Hard light, deep blacks, two-colour halftone | Contact frames, one circled frame developed into colour |
| Elements | Subtitles, timecodes, crop-mark frame, slate, chapter numerals, spine, programme booklet | Giant date numerals, colour blocks, end card, halftone, numbered programme, pin badges | Edge codes, grease-pencil marks, loupe, test-strip palette, photo-paper box, timer, film canister |

All fonts are free Google Fonts that include the Latvian characters (Latin Extended).

## Files

- `canvas/` holds the artboard sources (`.dc.html`) and the canvas index. Images are referenced by
  their uploaded `/_blob/…` URLs, so they render only inside the canvas artifact.
- `textures/` holds the generated film grain, dust, smoke, projector beam, light-refraction, paper and
  halftone textures.
- `scripts/process.py` makes the A–C photo treatments (B&W, duotone, selective colour, warm print, reveal
  pairs) and textures; `scripts/process_light.py` makes the D–F movie-grain treatments (two-scale grain,
  halation, split-tone colour for the reveal) and the dust texture; `scripts/halftone.py` makes the E
  halftones. `scripts/photos.txt` lists the source photos from the current site's gallery.

The photos are placeholders taken from the current mdarbnica.lv gallery. Swap them for the new
photographer's shots before anything goes public. The wordmarks are typeset studies; the client's new
logo replaces them.
