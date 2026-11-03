#!/usr/bin/env python3
"""
Talk-To-CAD - Final Year Project by Sumit Choudhary, SKIT Jaipur
Speak / type in Hindi, Hinglish or English -> get a real CAD model.

Example commands:
  "Ek flange banao 100mm ka, 6 holes ke saath, 12mm thick, centre bore 40mm, hole diameter 10mm, PCD 80mm"
  "Make a plate 150mm long, 100mm wide, 10mm thick, 4 holes of 8mm"
  "Make a gear 80mm diameter, 24 teeth, 12mm thick, bore 20mm"
  "Make a shaft 30mm diameter, 200mm long"

Outputs (per part):
  .stl  - 3D model, opens in Fusion 360 / SolidWorks / slicers, 3D-printable
  .dxf  - 2D AutoCAD file, opens directly in AutoCAD
  .png / .pdf - Engineering drawing sheet with dimensions + title block
  .json - Parsed specification (proof of what the AI understood)
"""
import argparse, json, math, re, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
import numpy as np

# ---------------------------------------------------------------- parser
HINDI_NUM = {
    "ek":1,"do":2,"teen":3,"char":4,"chaar":4,"paanch":5,"panch":5,
    "chhe":6,"chhah":6,"che":6,"chay":6,"saat":7,"aath":8,"nau":9,"das":10,
    "gyarah":11,"barah":12,"chaudah":14,"pandrah":15,"solah":16,"bees":20,
    "chaubees":24,"tees":30,"chalis":40,"pachas":50,
}
PART_WORDS = {
    "flange": ["flange","flenj","flanj"],
    "plate": ["plate","plet"],
    "gear": ["gear","giyar","geyar"],
    "shaft": ["shaft","saft"],
}

def words_to_digits(text: str) -> str:
    for w, d in sorted(HINDI_NUM.items(), key=lambda x: -len(x[0])):
        text = re.sub(rf"\b{w}\b", str(d), text)
    return text

def find_labelled(text, labels):
    """Find the mm number closest to a label word, e.g. '12mm thick' or 'thick 12mm'."""
    for lab in labels:
        best = None
        for m in re.finditer(re.escape(lab), text):
            centre = (m.start() + m.end()) / 2
            for nm in re.finditer(r"(\d+(?:\.\d+)?)\s*mm", text):
                dist = abs(((nm.start() + nm.end()) / 2) - centre)
                if dist <= 28 and (best is None or dist < best[0]):
                    best = (dist, float(nm.group(1)))
        if best: return best[1]
    return None

def parse_command(raw: str) -> dict:
    original = raw
    text = words_to_digits(raw.lower())
    text = text.replace(",", " ")

    part = None
    for name, variants in PART_WORDS.items():
        if any(v in text for v in variants):
            part = name; break
    if not part:
        part = "flange"  # default demo part

    def num_before(word_pat):
        m = re.search(rf"(\d+(?:\.\d+)?)\s*{word_pat}", text)
        return float(m.group(1)) if m else None

    holes = num_before(r"(?:holes?|chhed|holes\s*ke)")
    if holes is None:
        m = re.search(r"(\d+)\s*x\b", text)
        holes = float(m.group(1)) if m else None

    teeth = num_before(r"(?:teeth|tooth|daant|teeth\s*ka)")
    thickness = find_labelled(text, ["thick","thickness","motai","moti"])
    bore = find_labelled(text, ["bore","centre bore","center bore","beech","centre hole","center hole"])
    hole_dia = find_labelled(text, ["hole diameter","hole dia","chhed ka diameter"])
    pcd = find_labelled(text, ["pcd","pitch circle"])
    length = find_labelled(text, ["long","length","lamba","lambai"])
    width = find_labelled(text, ["wide","width","chauda","chaudai"])

    # all mm numbers in order (for outer diameter fallback)
    all_mm = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*mm", text)]
    used = {v for v in [thickness, bore, hole_dia, pcd, length, width] if v is not None}
    rest = [v for v in all_mm if v not in used]
    outer = max(rest) if rest else None

    spec = {"part": part, "command_original": original, "command_normalised": text}
    if part == "flange":
        spec.update(
            outer_dia=outer or 100.0,
            thickness=thickness or 12.0,
            bore_dia=bore or round((outer or 100.0)*0.4),
            holes=int(holes) if holes else 6,
            hole_dia=hole_dia or 10.0,
            pcd=pcd or round((outer or 100.0)*0.8),
        )
    elif part == "plate":
        dims = sorted(rest, reverse=True)
        spec.update(
            length=length or (dims[0] if dims else 150.0),
            width=width or (dims[1] if len(dims)>1 else 100.0),
            thickness=thickness or 10.0,
            holes=int(holes) if holes else 4,
            hole_dia=hole_dia or 8.0,
            corner_offset=15.0,
        )
    elif part == "gear":
        spec.update(
            outer_dia=outer or 80.0,
            teeth=int(teeth) if teeth else 24,
            thickness=thickness or 12.0,
            bore_dia=bore or 20.0,
        )
    elif part == "shaft":
        # diameter is the smaller mm value, length the larger
        spec.update(
            dia=(min(rest) if rest else 30.0),
            length=length or (max(rest) if len(rest)>1 else 200.0),
        )
    return spec

# ---------------------------------------------------------------- 3D STL
def circle_poly(x, y, r, res=96):
    from shapely.geometry import Point
    return Point(x, y).buffer(r, resolution=res//4)

def build_stl(spec, out_path: Path):
    import trimesh
    from shapely.geometry import Polygon
    p = spec["part"]
    if p == "flange":
        from shapely.ops import unary_union
        shape = circle_poly(0,0,spec["outer_dia"]/2)
        shape = shape.difference(circle_poly(0,0,spec["bore_dia"]/2))
        for i in range(spec["holes"]):
            a = 2*math.pi*i/spec["holes"]
            hx, hy = spec["pcd"]/2*math.cos(a), spec["pcd"]/2*math.sin(a)
            shape = shape.difference(circle_poly(hx,hy,spec["hole_dia"]/2))
        mesh = trimesh.creation.extrude_polygon(shape, height=spec["thickness"])
    elif p == "plate":
        from shapely.geometry import box
        L,W,o = spec["length"], spec["width"], spec["corner_offset"]
        shape = box(-L/2,-W/2,L/2,W/2)
        for sx in (-1,1):
            for sy in (-1,1):
                shape = shape.difference(circle_poly(sx*(L/2-o), sy*(W/2-o), spec["hole_dia"]/2))
        mesh = trimesh.creation.extrude_polygon(shape, height=spec["thickness"])
    elif p == "gear":
        R, teeth = spec["outer_dia"]/2, spec["teeth"]
        root_r = R*0.88
        pts=[]
        steps = teeth*4
        for i in range(steps):
            phase = i % 4
            r = R if phase in (1,2) else root_r
            a = 2*math.pi*i/steps
            pts.append((r*math.cos(a), r*math.sin(a)))
        shape = Polygon(pts).difference(circle_poly(0,0,spec["bore_dia"]/2))
        mesh = trimesh.creation.extrude_polygon(shape, height=spec["thickness"])
    elif p == "shaft":
        mesh = trimesh.creation.cylinder(radius=spec["dia"]/2, height=spec["length"], sections=64)
        mesh.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[0,1,0]))
    else:
        raise ValueError(p)
    mesh.export(out_path)
    return {"volume_mm3": round(float(mesh.volume),1), "watertight": bool(mesh.is_watertight),
            "bounds_mm": [[round(float(v),1) for v in row] for row in mesh.bounds]}

# ---------------------------------------------------------------- 2D DXF
def build_dxf(spec, out_path: Path):
    import ezdxf
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    for name, colour in [("OUTLINE",7),("HOLES",1),("CENTER",3),("PCD",5)]:
        if name not in doc.layers: doc.layers.add(name, color=colour)
    doc.layers.get("CENTER").dxf.linetype = "CENTER"
    doc.layers.get("PCD").dxf.linetype = "DASHED"
    msp = doc.modelspace()
    p = spec["part"]
    if p == "flange":
        msp.add_circle((0,0), spec["outer_dia"]/2, dxfattribs={"layer":"OUTLINE"})
        msp.add_circle((0,0), spec["bore_dia"]/2, dxfattribs={"layer":"OUTLINE"})
        msp.add_circle((0,0), spec["pcd"]/2, dxfattribs={"layer":"PCD"})
        for i in range(spec["holes"]):
            a=2*math.pi*i/spec["holes"]
            msp.add_circle((spec["pcd"]/2*math.cos(a), spec["pcd"]/2*math.sin(a)),
                           spec["hole_dia"]/2, dxfattribs={"layer":"HOLES"})
        msp.add_line((-spec["outer_dia"]/2-10,0),(spec["outer_dia"]/2+10,0),dxfattribs={"layer":"CENTER"})
        msp.add_line((0,-spec["outer_dia"]/2-10),(0,spec["outer_dia"]/2+10),dxfattribs={"layer":"CENTER"})
        msp.add_text(f"FLANGE OD {spec['outer_dia']} PCD {spec['pcd']} {spec['holes']}x HOLE {spec['hole_dia']} BORE {spec['bore_dia']} THK {spec['thickness']}",
                     dxfattribs={"height":4}).set_placement((0,-spec["outer_dia"]/2-18))
    elif p == "plate":
        L,W,o = spec["length"], spec["width"], spec["corner_offset"]
        msp.add_lwpolyline([(-L/2,-W/2),(L/2,-W/2),(L/2,W/2),(-L/2,W/2)], close=True, dxfattribs={"layer":"OUTLINE"})
        for sx in (-1,1):
            for sy in (-1,1):
                msp.add_circle((sx*(L/2-o),sy*(W/2-o)), spec["hole_dia"]/2, dxfattribs={"layer":"HOLES"})
    elif p == "gear":
        R, teeth = spec["outer_dia"]/2, spec["teeth"]; root_r=R*0.88; pts=[]
        for i in range(teeth*4):
            r = R if i%4 in (1,2) else root_r; a=2*math.pi*i/(teeth*4)
            pts.append((r*math.cos(a), r*math.sin(a)))
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer":"OUTLINE"})
        msp.add_circle((0,0), spec["bore_dia"]/2, dxfattribs={"layer":"HOLES"})
    elif p == "shaft":
        L,d = spec["length"], spec["dia"]
        msp.add_lwpolyline([(-L/2,-d/2),(L/2,-d/2),(L/2,d/2),(-L/2,d/2)], close=True, dxfattribs={"layer":"OUTLINE"})
        msp.add_circle((L/2+ d,0), d/2, dxfattribs={"layer":"OUTLINE"})
    doc.saveas(out_path)

# ---------------------------------------------------------------- drawing sheet
def dim_h(ax, x1, x2, y, text, offset=0):
    ax.annotate("", xy=(x1,y), xytext=(x2,y), arrowprops=dict(arrowstyle="<->", color="black", lw=0.9))
    ax.text((x1+x2)/2, y+offset, text, ha="center", va="bottom", fontsize=8, family="monospace",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none"))

def build_drawing(spec, png_path: Path, pdf_path: Path):
    p = spec["part"]
    fig = plt.figure(figsize=(11.69, 8.27))  # A4 landscape
    ax = fig.add_axes([0.04,0.10,0.62,0.84]); ax.set_aspect("equal"); ax.axis("off")
    ax2 = fig.add_axes([0.68,0.55,0.28,0.39]); ax2.set_aspect("equal"); ax2.axis("off")
    fig.patches.append(plt.Rectangle((0.01,0.01),0.98,0.98, transform=fig.transFigure, fill=False, lw=1.5))

    if p == "flange":
        OD, PCD, B, HD, N, T = spec["outer_dia"], spec["pcd"], spec["bore_dia"], spec["hole_dia"], spec["holes"], spec["thickness"]
        ax.add_patch(Circle((0,0), OD/2, fill=False, lw=1.6))
        ax.add_patch(Circle((0,0), B/2, fill=False, lw=1.4))
        ax.add_patch(Circle((0,0), PCD/2, fill=False, lw=0.8, ls=(0,(6,4)), color="#2563eb"))
        for i in range(N):
            a=2*math.pi*i/N
            ax.add_patch(Circle((PCD/2*math.cos(a), PCD/2*math.sin(a)), HD/2, fill=False, lw=1.3, color="#dc2626"))
        ax.plot([-OD/2-12,OD/2+12],[0,0], color="green", lw=0.7, ls="-.")
        ax.plot([0,0],[-OD/2-12,OD/2+12], color="green", lw=0.7, ls="-.")
        ax.set_xlim(-OD/2-28, OD/2+28); ax.set_ylim(-OD/2-30, OD/2+22)
        ax.set_title("TOP VIEW", fontsize=10, weight="bold")
        dim_h(ax, -OD/2, OD/2, -OD/2-20, f"Ø{OD:g}")
        ax.text(PCD/2*0.72, PCD/2*0.72+4, f"PCD Ø{PCD:g}", fontsize=8, color="#2563eb", family="monospace")
        ax.text(0, B/2+5, f"BORE Ø{B:g}", ha="center", fontsize=8, family="monospace")
        # side view
        ax2.add_patch(Rectangle((-OD/2,-T/2), OD, T, fill=False, lw=1.5))
        ax2.add_patch(Rectangle((-B/2,-T/2), B, T, fill=True, fc="white", ec="black", lw=1.0, hatch="///"))
        ax2.set_xlim(-OD/2-15, OD/2+38); ax2.set_ylim(-22,22); ax2.set_title("SIDE VIEW (SECTION)", fontsize=10, weight="bold")
        dim_h(ax2, OD/2+6, OD/2+6, 0, "", 0)
        ax2.annotate("", xy=(OD/2+8,-T/2), xytext=(OD/2+8,T/2), arrowprops=dict(arrowstyle="<->", lw=0.9))
        ax2.text(OD/2+11, 0, f"{T:g} THK", fontsize=8, va="center", family="monospace")
        notes = [f"1. ALL DIMENSIONS ARE IN MM.", f"2. {N} x Ø{HD:g} HOLES EQUALLY SPACED ON PCD Ø{PCD:g}.",
                 "3. MATERIAL: MILD STEEL (ASSUMED).", "4. REMOVE ALL SHARP EDGES.", "5. GENERATED BY TALK-TO-CAD FROM VOICE / TEXT COMMAND."]
        spec_rows = [["Outer Diameter", f"Ø{OD:g} mm"],["PCD", f"Ø{PCD:g} mm"],["Centre Bore", f"Ø{B:g} mm"],
                     ["Bolt Holes", f"{N} x Ø{HD:g} mm"],["Thickness", f"{T:g} mm"]]
    elif p == "plate":
        L,W,T = spec["length"], spec["width"], spec["thickness"]
        ax.add_patch(Rectangle((-L/2,-W/2),L,W,fill=False,lw=1.6))
        for sx in (-1,1):
            for sy in (-1,1):
                ax.add_patch(Circle((sx*(L/2-15),sy*(W/2-15)), spec["hole_dia"]/2, fill=False, lw=1.3, color="#dc2626"))
        ax.set_xlim(-L/2-25,L/2+25); ax.set_ylim(-W/2-30,W/2+20); ax.set_title("TOP VIEW", fontsize=10, weight="bold")
        dim_h(ax,-L/2,L/2,-W/2-20,f"{L:g}")
        ax2.add_patch(Rectangle((-L/2,-T/2),L,T,fill=False,lw=1.5)); ax2.set_xlim(-L/2-15,L/2+15); ax2.set_ylim(-22,22)
        ax2.set_title("SIDE VIEW", fontsize=10, weight="bold")
        notes=["1. ALL DIMENSIONS ARE IN MM.","2. 4 CORNER HOLES.","3. MATERIAL: MILD STEEL (ASSUMED).","4. GENERATED BY TALK-TO-CAD."]
        spec_rows=[["Length",f"{L:g} mm"],["Width",f"{W:g} mm"],["Thickness",f"{T:g} mm"],["Holes",f"4 x Ø{spec['hole_dia']:g} mm"]]
    elif p == "gear":
        OD,T = spec["outer_dia"], spec["thickness"]
        R=OD/2; root=R*0.88; xs,ys=[],[]
        for i in range(spec["teeth"]*4):
            r=R if i%4 in (1,2) else root; a=2*math.pi*i/(spec["teeth"]*4)
            xs.append(r*math.cos(a)); ys.append(r*math.sin(a))
        ax.plot(xs+[xs[0]],ys+[ys[0]],color="black",lw=1.4); ax.add_patch(Circle((0,0),spec["bore_dia"]/2,fill=False,lw=1.3))
        ax.set_xlim(-R-25,R+25); ax.set_ylim(-R-30,R+20); ax.set_title("TOP VIEW", fontsize=10, weight="bold")
        dim_h(ax,-R,R,-R-20,f"Ø{OD:g}")
        ax2.add_patch(Rectangle((-R,-T/2),OD,T,fill=False,lw=1.5)); ax2.set_xlim(-R-15,R+15); ax2.set_ylim(-22,22); ax2.set_title("SIDE VIEW", fontsize=10, weight="bold")
        notes=["1. ALL DIMENSIONS ARE IN MM.","2. SIMPLIFIED TOOTH PROFILE FOR CONCEPT MODEL.","3. MATERIAL: MILD STEEL (ASSUMED).","4. GENERATED BY TALK-TO-CAD."]
        spec_rows=[["Outer Diameter",f"Ø{OD:g} mm"],["Teeth",f"{spec['teeth']}"],["Bore",f"Ø{spec['bore_dia']:g} mm"],["Thickness",f"{T:g} mm"]]
    else:  # shaft
        L,d = spec["length"], spec["dia"]
        ax.add_patch(Rectangle((-L/2,-d/2),L,d,fill=False,lw=1.6)); ax.plot([-L/2-12,L/2+12],[0,0],color="green",lw=0.7,ls="-.")
        ax.set_xlim(-L/2-25,L/2+25); ax.set_ylim(-d-25,d+20); ax.set_title("SIDE VIEW", fontsize=10, weight="bold")
        dim_h(ax,-L/2,L/2,-d/2-18,f"{L:g}")
        ax2.add_patch(Circle((0,0),d/2,fill=False,lw=1.5)); ax2.set_xlim(-d,d); ax2.set_ylim(-d,d); ax2.set_title("END VIEW", fontsize=10, weight="bold")
        notes=["1. ALL DIMENSIONS ARE IN MM.","2. MATERIAL: MILD STEEL (ASSUMED).","3. GENERATED BY TALK-TO-CAD."]
        spec_rows=[["Diameter",f"Ø{d:g} mm"],["Length",f"{L:g} mm"]]

    # spec table + notes + title block (figure coords)
    tx, ty = 0.68, 0.48
    fig.text(tx, ty, "SPECIFICATION", fontsize=10, weight="bold")
    y=ty-0.035
    for k,v in spec_rows:
        fig.text(tx, y, f"{k}:", fontsize=8.5, family="monospace"); fig.text(tx+0.15, y, v, fontsize=8.5, family="monospace"); y-=0.028
    y-=0.015; fig.text(tx, y, "NOTES:", fontsize=9, weight="bold"); y-=0.03
    for n in notes:
        fig.text(tx, y, n, fontsize=7, wrap=True); y-=0.026
    # title block
    fig.patches.append(plt.Rectangle((0.62,0.025),0.36,0.105, transform=fig.transFigure, fill=False, lw=1.2))
    fig.text(0.635,0.115,"TALK-TO-CAD  |  AI GENERATED DRAWING", fontsize=8, weight="bold")
    fig.text(0.635,0.092,f"PART: {p.upper()}    SCALE: NTS    UNITS: MM    SHEET: 1 OF 1", fontsize=7.5, family="monospace")
    fig.text(0.635,0.069,"DESIGNED BY: SUMIT CHOUDHARY, SKIT JAIPUR (2023-2027)", fontsize=7.5, family="monospace")
    cmd_disp = spec["command_original"]
    if len(cmd_disp) > 62: cmd_disp = cmd_disp[:62] + "..."
    fig.text(0.635,0.046,f'COMMAND: "{cmd_disp}"', fontsize=6.5, style="italic")
    fig.text(0.04,0.045,"FINAL YEAR PROJECT - MECHANICAL ENGINEERING", fontsize=7.5, color="#555555")
    fig.savefig(png_path, dpi=300); fig.savefig(pdf_path); plt.close(fig)

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", nargs="?", default="Ek flange banao 100mm ka, 6 holes ke saath, 12mm thick, centre bore 40mm, hole diameter 10mm, PCD 80mm")
    ap.add_argument("--out", default="output")
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    spec = parse_command(args.command)
    print("STEP 1 - Command understood:"); print(json.dumps(spec, indent=2, ensure_ascii=False))
    stem = f"{spec['part']}_talk_to_cad"
    stl, dxf, png, pdf, js = out/f"{stem}.stl", out/f"{stem}.dxf", out/f"{stem}_drawing.png", out/f"{stem}_drawing.pdf", out/f"{stem}_spec.json"
    info = build_stl(spec, stl); print(f"STEP 2 - 3D STL built: {stl} {info}")
    build_dxf(spec, dxf); print(f"STEP 3 - 2D AutoCAD DXF built: {dxf}")
    build_drawing(spec, png, pdf); print(f"STEP 4 - Engineering drawing built: {png} + {pdf}")
    spec["mesh_info"]=info
    js.write_text(json.dumps(spec, indent=2, ensure_ascii=False))
    print(f"STEP 5 - Spec saved: {js}")
    print("DONE - All outputs ready.")
    return spec

if __name__ == "__main__":
    main()
