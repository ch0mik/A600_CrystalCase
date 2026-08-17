"""Deterministic SVG visualization from the generated DXF and A600 KiCad PCB.

This is intentionally not an AI image generator.  It reads the production DXF
contours, reads major component footprints from Amiga600.kicad_pcb and projects
the resulting geometry into an orthographic 3D technical view.
"""

from __future__ import annotations

import argparse
import html
import math
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
W, D = 329.0, 206.0
PCB_X, PCB_Y, PCB_Z, PCB_T = 6.0, 6.0, 18.0, 1.6
GOTEK_CARRIER_X, GOTEK_CARRIER_Y = 203.0, 17.0


@dataclass
class Shape:
    points: list[tuple[float, float, float]]
    fill: str
    stroke: str = "#252b30"
    opacity: float = 1.0
    width: float = 0.8
    dash: str | None = None
    closed: bool = True


def parse_dxf(path: Path):
    lines = path.read_text("ascii").splitlines()
    pairs = [(lines[i].strip(), lines[i + 1].strip())
             for i in range(0, len(lines) - 1, 2)]
    contours = []
    i = 0
    while i < len(pairs):
        code, value = pairs[i]
        if code == "0" and value == "POLYLINE":
            pts = []
            i += 1
            while i < len(pairs):
                c, v = pairs[i]
                if c == "0" and v == "SEQEND":
                    break
                if c == "0" and v == "VERTEX":
                    x = y = None
                    i += 1
                    while i < len(pairs) and pairs[i][0] != "0":
                        if pairs[i][0] == "10": x = float(pairs[i][1])
                        if pairs[i][0] == "20": y = float(pairs[i][1])
                        i += 1
                    if x is not None and y is not None:
                        pts.append((x, y))
                    continue
                i += 1
            contours.append(("poly", pts))
        elif code == "0" and value == "CIRCLE":
            x = y = r = None
            i += 1
            while i < len(pairs) and pairs[i][0] != "0":
                c, v = pairs[i]
                if c == "10": x = float(v)
                if c == "20": y = float(v)
                if c == "40": r = float(v)
                i += 1
            contours.append(("circle", (x, y, r)))
            continue
        i += 1
    return contours


def circle_points(cx, cy, radius, count=40):
    return [(cx + radius * math.cos(2 * math.pi * i / count),
             cy + radius * math.sin(2 * math.pi * i / count))
            for i in range(count)]


def contour_points(contour):
    kind, data = contour
    if kind == "poly":
        return data
    return circle_points(*data)


def add_panel(shapes, dxf_path, mapper, fill="#c9f4ff", opacity=0.13):
    contours = parse_dxf(dxf_path)
    outer = [mapper(x, y) for x, y in contour_points(contours[0])]
    shapes.append(Shape(outer, fill, "#5f7f8d", opacity, 0.9))
    for contour in contours:
        pts = [mapper(x, y) for x, y in contour_points(contour)]
        shapes.append(Shape(pts, "none", "#6f8d98", 0.92, 0.65))


def parse_edge_cuts(pcb_path: Path):
    """Read and stitch the motherboard outline directly from KiCad."""
    text = pcb_path.read_text(errors="replace")
    number = r"(-?[\d.]+)"
    segments = []
    line_re = re.compile(
        rf"\(gr_line \(start {number} {number}\) \(end {number} {number}\) "
        rf"\(layer Edge\.Cuts\)")
    arc_re = re.compile(
        rf"\(gr_arc \(start {number} {number}\) \(end {number} {number}\) "
        rf"\(angle {number}\) \(layer Edge\.Cuts\)")
    for match in line_re.finditer(text):
        x1, y1, x2, y2 = map(float, match.groups())
        segments.append([(x1, y1), (x2, y2)])
    for match in arc_re.finditer(text):
        cx, cy, sx, sy, sweep = map(float, match.groups())
        radius = math.hypot(sx-cx, sy-cy)
        start_angle = math.atan2(sy-cy, sx-cx)
        count = max(8, math.ceil(abs(sweep)/10))
        points = []
        for i in range(count + 1):
            angle = start_angle + math.radians(sweep)*i/count
            points.append((cx+radius*math.cos(angle),
                           cy+radius*math.sin(angle)))
        segments.append(points)
    if not segments:
        raise ValueError("No Edge.Cuts geometry found in the KiCad PCB")

    outline = segments.pop(0)
    tolerance = 0.002
    while segments:
        endpoint = outline[-1]
        for index, segment in enumerate(segments):
            if math.dist(endpoint, segment[0]) <= tolerance:
                outline.extend(segment[1:])
                segments.pop(index)
                break
            if math.dist(endpoint, segment[-1]) <= tolerance:
                outline.extend(reversed(segment[:-1]))
                segments.pop(index)
                break
        else:
            raise ValueError(f"Disconnected Edge.Cuts contour at {endpoint}")
    if math.dist(outline[0], outline[-1]) > tolerance:
        raise ValueError("Edge.Cuts contour is not closed")
    return outline[:-1]


def parse_mounting_holes(pcb_path: Path):
    """Read the five selected through holes and their drills from KiCad."""
    wanted = {"H1", "H2", "H3", "MT5", "MT6"}
    holes = []
    text = pcb_path.read_text(errors="replace")
    for block in extract_module_blocks(text):
        ref_m = re.search(r"\(fp_text reference\s+([^\s\)]+)", block)
        if not ref_m or ref_m.group(1) not in wanted:
            continue
        at_m = re.search(r"^    \(at\s+([-\d.]+)\s+([-\d.]+)", block, re.M)
        drill_m = re.search(r"\(drill\s+([-\d.]+)\)", block)
        if not at_m or not drill_m:
            raise ValueError(f"Missing position/drill for {ref_m.group(1)}")
        holes.append((ref_m.group(1), float(at_m.group(1)),
                      float(at_m.group(2)), float(drill_m.group(1))))
    found = {ref for ref, *_ in holes}
    if found != wanted:
        raise ValueError(f"Missing mounting holes: {sorted(wanted-found)}")
    return sorted(holes)


def add_prism(shapes, footprint, z0, z1, fill, stroke="#15231d",
              opacity=1.0):
    bottom = [(x, y, z0) for x, y in footprint]
    top = [(x, y, z1) for x, y in footprint]
    for i in range(len(footprint)):
        j = (i + 1) % len(footprint)
        shapes.append(Shape([bottom[i], bottom[j], top[j], top[i]],
                            fill, stroke, opacity, 0.45))
    shapes.append(Shape(top, fill, stroke, opacity, 0.65))


def rotated_rect(cx, cy, width, depth, angle):
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for x, y in ((-width/2, -depth/2), (width/2, -depth/2),
                 (width/2, depth/2), (-width/2, depth/2)):
        pts.append((cx + x*ca - y*sa, cy + x*sa + y*ca))
    return pts


def extract_module_blocks(text):
    for match in re.finditer(r"^  \(module ", text, re.M):
        start = match.start() + 2
        depth = 0
        begun = False
        for i in range(start, len(text)):
            if text[i] == "(":
                depth += 1; begun = True
            elif text[i] == ")":
                depth -= 1
            if begun and depth == 0:
                yield text[start:i+1]
                break


def parse_major_components(pcb_path: Path):
    text = pcb_path.read_text(errors="replace")
    components = []
    wanted = ("PLCC", "DIP", "SOJ", "SOIC", "SOP", "DB9", "DB23",
              "DB25", "RCA", "Power", "S-Video", "PCMCIA", "IDE",
              "FFC", "Expansion", "Floppy", "Oscillator", "Crystal")
    for block in extract_module_blocks(text):
        name_m = re.match(r"\(module\s+([^\s]+)", block)
        at_m = re.search(r"^    \(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)",
                         block, re.M)
        ref_m = re.search(r"\(fp_text reference\s+([^\s\)]+)", block)
        if not name_m or not at_m:
            continue
        name = name_m.group(1).split(":")[-1]
        if not any(token in name for token in wanted):
            continue
        coords = []
        for m in re.finditer(r"\(fp_line \(start ([-\d.]+) ([-\d.]+)\) "
                             r"\(end ([-\d.]+) ([-\d.]+)\)", block):
            coords += [(float(m.group(1)), float(m.group(2))),
                       (float(m.group(3)), float(m.group(4)))]
        if not coords:
            continue
        minx = min(x for x, _ in coords); maxx = max(x for x, _ in coords)
        miny = min(y for _, y in coords); maxy = max(y for _, y in coords)
        width = max(1.5, maxx-minx); depth = max(1.5, maxy-miny)
        local_cx = (minx+maxx)/2; local_cy = (miny+maxy)/2
        x, y = float(at_m.group(1)), float(at_m.group(2))
        angle = float(at_m.group(3) or 0)
        a = math.radians(angle)
        cx = x + local_cx*math.cos(a) - local_cy*math.sin(a)
        cy = y + local_cx*math.sin(a) + local_cy*math.cos(a)
        ref = ref_m.group(1) if ref_m else ""
        components.append((ref, name, PCB_X+cx, PCB_Y+cy,
                           width, depth, angle))
    return components


def norm(v):
    length = math.sqrt(sum(x*x for x in v))
    return tuple(x/length for x in v)


def sub(a, b): return tuple(x-y for x, y in zip(a, b))
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def render_svg(shapes, output: Path, camera, title):
    target = (W/2, D/2, 35.0)
    forward = norm(sub(target, camera))
    # Camera basis must preserve the enclosure's left/right orientation.
    # Reversing this cross product mirrors the complete assembly horizontally.
    right = norm(cross((0, 0, 1), forward))
    up = cross(forward, right)
    def raw_project(p): return (dot(p, right), -dot(p, up))
    all_raw = [raw_project(p) for shape in shapes for p in shape.points]
    minx = min(x for x, _ in all_raw); maxx = max(x for x, _ in all_raw)
    miny = min(y for _, y in all_raw); maxy = max(y for _, y in all_raw)
    canvas_w, canvas_h, margin, footer = 1600, 1050, 55, 130
    scale = min((canvas_w-2*margin)/(maxx-minx),
                (canvas_h-footer-2*margin)/(maxy-miny))
    def project(p):
        x, y = raw_project(p)
        return (margin+(x-minx)*scale, margin+(y-miny)*scale)
    ordered = sorted(shapes,
                     key=lambda s: -sum(sum((p[i]-camera[i])**2 for i in range(3))
                                           for p in s.points)/len(s.points))
    body = []
    for s in ordered:
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in map(project, s.points))
        tag = "polygon" if s.closed else "polyline"
        dash = f' stroke-dasharray="{s.dash}"' if s.dash else ""
        body.append(f'<{tag} points="{pts}" fill="{s.fill}" '
                    f'fill-opacity="{s.opacity:.3f}" stroke="{s.stroke}" '
                    f'stroke-opacity="{min(1,s.opacity+0.3):.3f}" '
                    f'stroke-width="{s.width}"{dash}/>' )
    note1 = "TECHNICAL VIEW — NOT AI-GENERATED: production DXF + A600Reborn Amiga600.kicad_pcb"
    note2 = "PiStorm16/CM4 and Gotek electronics are intentionally not rendered: no public mechanical CAD"
    note3 = "Shown exactly: enclosure cuts, finger joints, PCB Edge.Cuts, mounting drills and flat KiCad footprint bounds"
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}">
<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f8fafb"/><stop offset="1" stop-color="#dfe5e8"/></linearGradient></defs>
<rect width="100%" height="100%" fill="url(#bg)"/>
{''.join(body)}
<rect x="35" y="10" width="900" height="45" rx="7" fill="#ffffff" fill-opacity="0.82"/>
<text x="55" y="42" font-family="Segoe UI,Arial" font-size="25" font-weight="600" fill="#182126">{html.escape(title)}</text>
<rect x="35" y="{canvas_h-footer+12}" width="1530" height="105" rx="8" fill="#ffffff" fill-opacity="0.88" stroke="#9ba9af"/>
<text x="55" y="{canvas_h-footer+42}" font-family="Consolas,monospace" font-size="16" fill="#203038">{html.escape(note1)}</text>
<text x="55" y="{canvas_h-footer+70}" font-family="Consolas,monospace" font-size="16" fill="#8a2f2f">{html.escape(note2)}</text>
<text x="55" y="{canvas_h-footer+96}" font-family="Consolas,monospace" font-size="15" fill="#405159">{html.escape(note3)}</text>
</svg>'''
    output.write_text(svg, encoding="utf-8")


def add_enclosure(shapes):
    # Bramble-style finger joints occupy the six outer envelope faces.  The
    # horizontal coordinates show the inner surfaces of the 3 mm plates.
    add_panel(shapes, ROOT/"dxf_simple_joinery/01_bottom_simple_3mm.dxf",
              lambda x, y: (x, y, 3.0), opacity=0.10)
    add_panel(shapes, ROOT/"dxf_simple_joinery/02d_top_simple_gotek_carrier_above_cn11_3mm.dxf",
              lambda x, y: (x, y, 69.0), opacity=0.11)
    add_panel(shapes, ROOT/"dxf_simple_joinery/03_rear_io_simple_3mm.dxf",
              lambda x, z: (x, 0.0, z), opacity=0.12)
    add_panel(shapes, ROOT/"dxf_simple_joinery/06b_front_simple_gotek_oled_rotary_3mm.dxf",
              lambda x, z: (x, D, z), opacity=0.12)
    add_panel(shapes, ROOT/"dxf_simple_joinery/05_left_pcmcia_simple_3mm.dxf",
              lambda y, z: (0.0, y, z), opacity=0.12)
    add_panel(shapes, ROOT/"dxf_simple_joinery/04c_right_io_simple_gotek_usb_3mm.dxf",
              lambda y, z: (W, y, z), opacity=0.12)


def build_scene(pcb_path: Path, view: str):
    shapes = []
    add_enclosure(shapes)

    # Exact motherboard Edge.Cuts and five actual mounting holes.
    board = [(PCB_X+x, PCB_Y+y) for x, y in parse_edge_cuts(pcb_path)]
    add_prism(shapes, board, PCB_Z, PCB_Z+PCB_T, "#16734f", "#0d4b34", 0.96)
    for _ref, x, y, diameter in parse_mounting_holes(pcb_path):
        pts = [(PCB_X+px, PCB_Y+py, PCB_Z+PCB_T+0.05)
               for px, py in circle_points(x, y, diameter/2, 28)]
        shapes.append(Shape(pts, "#172724", "#07100e", 1.0, 0.4))

    # Footprint bounds remain flat: the PCB file does not provide reliable
    # installed-component heights, so no synthetic Z dimensions are added.
    for _ref, _name, cx, cy, width, depth, angle in parse_major_components(pcb_path):
        footprint = [(x, y, PCB_Z+PCB_T+0.05)
                     for x, y in rotated_rect(cx, cy, width, depth, angle)]
        shapes.append(Shape(footprint, "none", "#18352c", 0.72, 0.45))

    # Exact project-designed carrier above CN11.  It shares the H1 and MT6
    # motherboard standoff axes; Gotek electronics remain intentionally absent.
    add_panel(shapes, ROOT/"dxf_screws/07_gotek_carrier_3mm.dxf",
              lambda x, y: (GOTEK_CARRIER_X+x, GOTEK_CARRIER_Y+y, 47.0),
              fill="#87959a", opacity=0.30)

    if view == "front-right":
        camera = (470.0, 360.0, 280.0)
        view_title = "front-right"
    else:
        camera = (-170.0, -220.0, 250.0)
        view_title = "rear-left"
    title = f"A600 acrylic enclosure — simple finger joints, {view_title} view"
    return shapes, camera, title


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcb", type=Path, required=True,
                        help="Path to A600Reborn Amiga600.kicad_pcb")
    parser.add_argument("--out-dir", type=Path, default=ROOT/"renders")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for view in ("front-right", "rear-left"):
        shapes, camera, title = build_scene(args.pcb, view)
        out = args.out_dir/f"assembly_simple_{view}.svg"
        render_svg(shapes, out, camera, title)
        print(out)


if __name__ == "__main__":
    main()
