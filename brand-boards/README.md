# M/darbnīca — brand directions (pitch boards)

Three brand directions for the M/darbnīca relaunch, made for the client pitch.
The live boards are on the Design canvas: https://claude.ai/artifact/Mp18mqQVYto2wVXkxAnnh1

All three use what the client already chose (dark green, reddish/dusty pink, near-black)
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

All fonts are free Google Fonts that include the Latvian characters (Latin Extended).

## Files

- `canvas/` holds the artboard sources (`.dc.html`) and the canvas index. Images are referenced by
  their uploaded `/_blob/…` URLs, so they render only inside the canvas artifact.
- `textures/` holds the generated film grain, smoke, projector beam, light-refraction and paper textures.
- `scripts/process.py` makes every photo treatment (B&W, duotone, selective colour, warm print, reveal pairs)
  and the textures. `scripts/photos.txt` lists the source photos from the current site's gallery.

The photos are placeholders taken from the current mdarbnica.lv gallery. Swap them for the new
photographer's shots before anything goes public. The wordmarks are typeset studies; the client's new
logo replaces them.
