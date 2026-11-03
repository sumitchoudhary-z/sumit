# Talk-To-CAD

**Bolke CAD banao.** Type or speak a part in Hindi, Hinglish or English - get a 3D model, a dimensioned 2D drawing, and files that open in AutoCAD.

Final Year Mechanical Engineering Project by **Sumit Choudhary**, B.Tech Mechanical (2023-2027), SKIT Jaipur.

## Live App

- **Live on GitHub Pages: https://sumitchoudhary-z.github.io/sumit/talk-to-cad/**
- Or open `index.html` in any browser - it is a single self-contained file, no install or server needed.

## Try These Examples

- `Ek flange banao 100mm ka, 6 holes ke saath, 12mm thick, centre bore 40mm, hole diameter 10mm, PCD 80mm`
- `Make a plate 150mm long, 100mm wide, 10mm thick, 4 holes of 8mm hole diameter`
- `Make a gear 80mm diameter, chaubees teeth, 12mm thick, bore 20mm`
- `Make a shaft 30mm diameter, 200mm long`
- A larger flange: 120mm, 8 holes, PCD 100mm, bore 50mm, hole 12mm, 14mm thick

Tap an example card in the app, or type / speak your own command (mic button, Chrome recommended).

## What It Generates

- **STL** - 3D model for Fusion 360 / SolidWorks / 3D printing
- **DXF** - 2D drawing that opens directly in AutoCAD (layers: OUTLINE / HOLES / CENTER / PCD)
- **SCR** - AutoCAD script: run `SCRIPT` in AutoCAD and it draws the part itself
- **PNG / SVG** - dimensioned engineering drawing sheet
- **JSON** - parsed specification

Supported parts: **Flange, Plate, Gear, Shaft**.

## Use It Inside AutoCAD

- `TalkToCAD.lsp` - load with `APPLOAD` in AutoCAD, then use commands `TALKFLANGE`, `TALKPLATE`, `TALKGEAR`, `TALKSHAFT`. TALKFLANGE can also build a native 3D solid (CYLINDER + SUBTRACT).
- `flange_demo.scr` - ready demo script for the flange example.

## Python Engine

`talk_to_cad.py` is the original engine the app is based on:

```bash
python3 -m venv .venv
.venv/bin/pip install ezdxf matplotlib numpy shapely trimesh mapbox-earcut
.venv/bin/python talk_to_cad.py "Ek flange banao 100mm ka, 6 holes ke saath"
```

## Verified Demo Output

Flange Ø100 x 12mm, 6 x Ø10 holes, bore Ø40, PCD Ø80 - STL verified watertight with exact 100 x 100 x 12 mm bounds, volume 73,460.8 mm3.
