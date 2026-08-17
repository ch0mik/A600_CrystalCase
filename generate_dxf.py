"""Generate CNC-ready R12 DXF panels for an A600Reborn plexiglass enclosure.

All coordinates and parameters are in millimetres.  The generated part files
contain only closed CUT contours; no dimensions, text, duplicated geometry or
tool-radius compensation is included.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin
from pathlib import Path


OUT = Path(__file__).with_name("dxf_screws")
OUT_SIMPLE = Path(__file__).with_name("dxf_simple_joinery")

# Enclosure envelope and assembly assumptions.
W = 329.0
D = 206.0
H = 72.0
PCB_X = 6.0
PCB_Y = 6.0
PCB_Z = 18.0          # underside of PCB above the bottom plate
PCB_T = 1.6
IO_Z = PCB_Z + PCB_T + 7.0
GOTEK_CARRIER_X = 203.0
GOTEK_CARRIER_Y = 17.0
GOTEK_CARRIER_W = 120.0
GOTEK_CARRIER_D = 95.0
# Right-wall control centres for a bare SFR-series Gotek PCB mounted lengthwise
# on the carrier.  These are deliberately parameters: the supplied product
# photo has no scale and Gotek PCB revisions do not share manufacturing CAD.
GOTEK_USB_Y = 62.0
GOTEK_BUTTON_Y = (86.0, 98.0)
GOTEK_FACE_Z = 50.0

# Bramble-style finger joints.  Each edge is divided into an odd number of
# roughly 16 mm sections so reversing an edge keeps the same phase.  The small
# allowance narrows every finger by 0.12 mm relative to the mating recess.
SIMPLE_FINGER_TARGET = 16.0
SIMPLE_FINGER_CLEARANCE = 0.12
SIMPLE_SHEET_T = 3.0


@dataclass
class Entity:
    kind: str
    data: tuple
    layer: str = "CUT"


def poly(points, layer="CUT"):
    return Entity("POLY", tuple(points), layer)


def circle(x, y, diameter, layer="CUT"):
    return Entity("CIRCLE", (x, y, diameter / 2.0), layer)


def rounded_rect(cx, cy, width, height, radius=1.0, layer="CUT", steps=5):
    """Closed, counter-clockwise rounded rectangle as a segmented polyline."""
    r = min(radius, width / 2, height / 2)
    pts = []
    for ox, oy, a0 in (
        (cx + width / 2 - r, cy + height / 2 - r, 0),
        (cx - width / 2 + r, cy + height / 2 - r, 90),
        (cx - width / 2 + r, cy - height / 2 + r, 180),
        (cx + width / 2 - r, cy - height / 2 + r, 270),
    ):
        for i in range(steps + 1):
            a = (a0 + i * 90 / steps) * pi / 180
            pts.append((ox + r * cos(a), oy + r * sin(a)))
    return poly(pts, layer)


def horizontal_slot(cx, cy, length=12.0, diameter=3.4):
    return rounded_rect(cx, cy, length, diameter, diameter / 2.0)


def panel_outline(width, height):
    return rounded_rect(width / 2, height / 2, width, height, 3.0)


def finger_count(length):
    """Return an odd finger count close to SIMPLE_FINGER_TARGET."""
    count = max(3, round(length / SIMPLE_FINGER_TARGET))
    if count % 2 == 0:
        count += 1
    return count


def finger_transitions(length, count, recessed_first):
    """Transition positions with clearance assigned to the recessed side."""
    step = length / count
    positions = [0.0]
    for i in range(1, count):
        left_recessed = recessed_first if (i - 1) % 2 == 0 else not recessed_first
        # Move the boundary into the full-depth finger, widening its mating
        # recess by the requested total clearance.
        # Both mating contours move, so a quarter of the requested total at
        # each contour gives a finger/recess width difference of `clearance`.
        shift = SIMPLE_FINGER_CLEARANCE / 4
        positions.append(i * step + (shift if left_recessed else -shift))
    positions.append(length)
    return positions


def finger_edge(points, start, end, inward, recessed_first):
    """Append one axis-aligned, internally notched finger-joint edge."""
    x0, y0 = start
    x1, y1 = end
    length = abs(x1 - x0) + abs(y1 - y0)
    count = finger_count(length)
    breaks = finger_transitions(length, count, recessed_first)
    dx = (x1 - x0) / length
    dy = (y1 - y0) / length
    ix, iy = inward
    for i in range(count):
        recessed = recessed_first if i % 2 == 0 else not recessed_first
        offset = SIMPLE_SHEET_T if recessed else 0.0
        sx = x0 + dx * breaks[i] + ix * offset
        sy = y0 + dy * breaks[i] + iy * offset
        ex = x0 + dx * breaks[i + 1] + ix * offset
        ey = y0 + dy * breaks[i + 1] + iy * offset
        if points[-1] != (sx, sy):
            points.append((sx, sy))
        points.append((ex, ey))


def finger_panel_outline(width, height, horizontal_recessed, vertical_recessed):
    """Closed Bramble-style outline with complementary fingers on all edges."""
    points = [(0.0, 0.0)]
    finger_edge(points, (0.0, 0.0), (width, 0.0), (0.0, 1.0),
                horizontal_recessed)
    finger_edge(points, (width, 0.0), (width, height), (-1.0, 0.0),
                vertical_recessed)
    finger_edge(points, (width, height), (0.0, height), (0.0, -1.0),
                horizontal_recessed)
    finger_edge(points, (0.0, height), (0.0, 0.0), (1.0, 0.0),
                vertical_recessed)
    if points[-1] == points[0]:
        points.pop()  # POLYLINE's closed flag supplies this final segment.
    return poly(points)


def corner_holes(width, height, edge=7.0, diameter=3.4):
    return [
        circle(edge, edge, diameter),
        circle(width - edge, edge, diameter),
        circle(width - edge, height - edge, diameter),
        circle(edge, height - edge, diameter),
    ]


def write_dxf(path: Path, entities: list[Entity]):
    def pair(code, value):
        lines.extend((str(code), str(value)))

    lines = []
    pair(0, "SECTION")
    pair(2, "HEADER")
    pair(9, "$ACADVER")
    pair(1, "AC1009")
    pair(9, "$MEASUREMENT")
    pair(70, 1)
    pair(0, "ENDSEC")
    pair(0, "SECTION")
    pair(2, "ENTITIES")
    for e in entities:
        if e.kind == "CIRCLE":
            x, y, r = e.data
            pair(0, "CIRCLE")
            pair(8, e.layer)
            pair(10, f"{x:.4f}")
            pair(20, f"{y:.4f}")
            pair(30, 0)
            pair(40, f"{r:.4f}")
        elif e.kind == "POLY":
            pair(0, "POLYLINE")
            pair(8, e.layer)
            pair(66, 1)
            pair(70, 1)
            for x, y in e.data:
                pair(0, "VERTEX")
                pair(8, e.layer)
                pair(10, f"{x:.4f}")
                pair(20, f"{y:.4f}")
                pair(30, 0)
            pair(0, "SEQEND")
            pair(8, e.layer)
    pair(0, "ENDSEC")
    pair(0, "EOF")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def bottom(include_gotek=False):
    e = [panel_outline(W, D), *corner_holes(W, D)]
    # A600Reborn mounting coordinates taken directly from Amiga600.kicad_pcb.
    # H1, H2, H3 are 3.2 mm NPTH; MT5 and MT6 are 3.5 mm plated holes.
    for x, y, dia in (
        (311.912, 22.352, 3.4),
        (5.080, 188.976, 3.4),
        (282.956, 150.622, 3.4),
        (158.496, 187.960, 3.8),
        (274.066, 96.393, 3.8),
    ):
        e.append(circle(PCB_X + x, PCB_Y + y, dia))
    # Air inlet under the 1 MB trapdoor/Chip-RAM area; 3 mm webs retained.
    for y in range(128, 181, 8):
        e.append(rounded_rect(91.0, float(y), 104.0, 3.0, 1.5))
    # The Gotek carrier shares the H1/MT6 motherboard standoff axes, so the
    # bottom plate needs no separate Gotek mounting holes.
    return e


def top(gotek_controls=False, gotek_external_box=False):
    e = [panel_outline(W, D), *corner_holes(W, D)]
    # Broad intake field above the PiStorm16 CM4 30 mm active cooler.  Its
    # coverage deliberately exceeds the photographed heatsink envelope.
    for y in range(40, 93, 7):
        e.append(rounded_rect(86.0, float(y), 62.0, 3.0, 1.5))
    # Passive exhaust over the right/front half prevents recirculation.  In
    # the integrated Gotek variant it is moved inward to clear the controls.
    exhaust_x = 176.0 if gotek_controls else 254.0
    exhaust_w = 70.0 if gotek_controls else 84.0
    for y in range(121, 178, 8):
        e.append(rounded_rect(exhaust_x, float(y), exhaust_w, 3.0, 1.5))
    if gotek_controls:
        # 0.96-inch 128x64 OLED: generous viewing window for common modules.
        # EC11-style encoder bushing is retained by its own panel nut.
        e.append(rounded_rect(237.0, 176.0, 28.0, 15.0, 1.0))
        e.append(circle(278.0, 176.0, 7.5))
        # Optional activity LED beside the controls.
        e.append(circle(298.0, 176.0, 3.2))
    if gotek_external_box:
        # Ami64-style arrangement: the display/encoder stay in the supplied
        # external box and two flat cables pass through the top panel.
        e.append(rounded_rect(247.0, 178.0, 32.0, 2.2, 1.1))
        e.append(rounded_rect(286.0, 178.0, 14.0, 2.2, 1.1))
    return e


def top_gotek_carrier():
    """Unpierced top above a Gotek carrier mounted to motherboard standoffs."""
    return top()


def rear():
    e = [panel_outline(W, H), *corner_holes(W, H, edge=7.0, diameter=3.4)]

    # Face centres below include the local origin offsets of the KiCad
    # footprints, not merely their module anchors.
    e.append(rounded_rect(PCB_X + 11.510, IO_Z, 18.0, 15.0, 2.0))  # power
    e.append(rounded_rect(PCB_X + 39.878, IO_Z, 16.0, 7.5, 1.0))   # HDMI flex
    e.append(circle(PCB_X + 63.694, IO_Z, 10.5))                   # composite

    dsub(e, PCB_X + 96.779, IO_Z, shell_w=37.5, mount_pitch=44.33) # RGB DB23
    e.append(circle(PCB_X + 129.734, IO_Z, 10.5))                  # audio R
    e.append(circle(PCB_X + 142.434, IO_Z, 10.5))                  # audio L
    dsub(e, PCB_X + 177.656, IO_Z, shell_w=40.5, mount_pitch=47.10)# serial DB25
    dsub(e, PCB_X + 234.586, IO_Z, shell_w=40.5, mount_pitch=47.10)# parallel DB25
    dsub(e, PCB_X + 289.809, IO_Z, shell_w=37.5, mount_pitch=44.33)# floppy DB23
    return e


def dsub(e, cx, cy, shell_w, mount_pitch):
    e.append(rounded_rect(cx, cy, shell_w, 12.5, 2.0))
    e.append(circle(cx - mount_pitch / 2, cy, 3.6))
    e.append(circle(cx + mount_pitch / 2, cy, 3.6))


def right(include_floppy=False):
    e = [panel_outline(D, H), *corner_holes(D, H, edge=7.0, diameter=3.4)]
    # DE-9 centres: module anchors plus the 5.54 mm local face-centre offset.
    for s in (PCB_Y + 117.554, PCB_Y + 149.558):
        dsub(e, s, IO_Z, shell_w=20.5, mount_pitch=25.0)
    if include_floppy:
        # Optional generic side slot.  Verify against the particular drive;
        # the motherboard repository does not define drive mechanics.
        e.append(rounded_rect(178.0, IO_Z, 50.0, 5.0, 2.0))
    return e


def right_gotek():
    e = right(False)
    # Access aligned with the narrow end of the bare Gotek PCB.  USB and both
    # on-board pushbuttons remain on the right wall and clear the DE-9 ports.
    e.append(rounded_rect(GOTEK_USB_Y, GOTEK_FACE_Z,
                          16.5, 8.5, 1.0))
    for y in GOTEK_BUTTON_Y:
        e.append(circle(y, GOTEK_FACE_Z, 6.5))
    return e


def gotek_carrier():
    """Adjustable carrier for a bare Gotek PCB above motherboard CN11."""
    e = [panel_outline(GOTEK_CARRIER_W, GOTEK_CARRIER_D)]
    # Stack this carrier on longer nylon standoffs above H1 and MT6.  Global
    # coordinates include the motherboard's 6 mm enclosure offset.
    for x, y in ((PCB_X + 311.912, PCB_Y + 22.352),
                 (PCB_X + 274.066, PCB_Y + 96.393)):
        e.append(circle(x - GOTEK_CARRIER_X, y - GOTEK_CARRIER_Y, 3.4))
    # Four adjustable fixing slots fit the long bare PCB shown in the supplied
    # reference while allowing for revision-to-revision hole-pitch variation.
    # Install the PCB on four nylon M3 standoffs with its USB/buttons toward
    # the enclosure's right wall; do not clamp the PCB directly to acrylic.
    for x in (20.0, 100.0):
        for y in (14.0, 81.0):
            e.append(horizontal_slot(x, y, 14.0, 3.4))
    # Cable-tie anchors for strain relief of the floppy and power leads.
    e.append(rounded_rect(60.0, 8.0, 12.0, 3.0, 1.5))
    e.append(rounded_rect(60.0, 87.0, 12.0, 3.0, 1.5))
    return e


def simple_plate(base_entities):
    """Replace a horizontal panel outline/fasteners with simple finger joints."""
    return [finger_panel_outline(W, D, True, True), *base_entities[5:]]


def simple_bottom(include_gotek=False):
    return simple_plate(bottom(include_gotek))


def simple_top(gotek_controls=False, gotek_external_box=False):
    return simple_plate(top(gotek_controls, gotek_external_box))


def simple_top_gotek_carrier():
    return simple_plate(top_gotek_carrier())


def simple_rear():
    # Keep the production convention explicit: viewed from the front of the
    # Amiga, the power inlet is at the left end of the rear panel (small X).
    base = rear()
    return [finger_panel_outline(W, H, False, True), *base[5:]]


def simple_front(gotek_controls=False):
    base = front(gotek_controls)
    return [finger_panel_outline(W, H, False, True), *base[5:]]


def simple_side(side, gotek=False, floppy=False):
    if side == "left":
        base = left()
    elif side == "right":
        base = right_gotek() if gotek else right(floppy)
    else:
        raise ValueError(side)
    # Vertical phase is complementary to front/rear corner fingers.
    return [finger_panel_outline(D, H, False, False), *base[5:]]


def left():
    e = [panel_outline(D, H), *corner_holes(D, H, edge=7.0, diameter=3.4)]
    # PCMCIA mouth; centre follows the rotated footprint body.
    e.append(rounded_rect(PCB_Y + 81.885, IO_Z, 60.0, 8.0, 2.0))
    return e


def front(gotek_controls=False):
    e = [panel_outline(W, H), *corner_holes(W, H, edge=7.0, diameter=3.4)]
    vent_end = 215 if gotek_controls else 276
    for x in range(54, vent_end, 16):
        e.append(rounded_rect(float(x), 22.0, 8.0, 3.0, 1.5))
    if gotek_controls:
        e.append(rounded_rect(242.0, 42.0, 28.0, 15.0, 1.0))
        e.append(circle(276.0, 42.0, 7.5))
    # Optional power / floppy activity LED apertures.
    e.extend((circle(299.0, 22.0, 3.2), circle(310.0, 22.0, 3.2)))
    return e


def main():
    OUT.mkdir(exist_ok=True)
    OUT_SIMPLE.mkdir(exist_ok=True)
    parts = {
        "01_bottom_3mm.dxf": bottom(False),
        "01b_bottom_gotek_3mm.dxf": bottom(True),
        "02_top_3mm.dxf": top(),
        "02b_top_gotek_oled_rotary_3mm.dxf": top(gotek_controls=True),
        "02c_top_gotek_external_box_3mm.dxf": top(gotek_external_box=True),
        "02d_top_gotek_carrier_above_cn11_3mm.dxf": top_gotek_carrier(),
        "03_rear_io_1mm.dxf": rear(),
        "04_right_io_3mm.dxf": right(False),
        "04b_right_io_floppy_3mm.dxf": right(True),
        "04c_right_io_gotek_usb_3mm.dxf": right_gotek(),
        "05_left_pcmcia_3mm.dxf": left(),
        "06_front_3mm.dxf": front(),
        "06b_front_gotek_oled_rotary_3mm.dxf": front(gotek_controls=True),
        "07_gotek_carrier_3mm.dxf": gotek_carrier(),
    }
    for name, entities in parts.items():
        write_dxf(OUT / name, entities)
        print(f"{name}: {len(entities)} closed contours")

    simple_parts = {
        "01_bottom_simple_3mm.dxf": simple_bottom(False),
        "01b_bottom_simple_gotek_3mm.dxf": simple_bottom(True),
        "02_top_simple_3mm.dxf": simple_top(),
        "02b_top_simple_gotek_oled_rotary_3mm.dxf":
            simple_top(gotek_controls=True),
        "02c_top_simple_gotek_external_box_3mm.dxf":
            simple_top(gotek_external_box=True),
        "02d_top_simple_gotek_carrier_above_cn11_3mm.dxf":
            simple_top_gotek_carrier(),
        "03_rear_io_simple_3mm.dxf": simple_rear(),
        "04_right_io_simple_3mm.dxf": simple_side("right", False),
        "04b_right_io_simple_floppy_3mm.dxf":
            simple_side("right", floppy=True),
        "04c_right_io_simple_gotek_usb_3mm.dxf":
            simple_side("right", True),
        "05_left_pcmcia_simple_3mm.dxf": simple_side("left"),
        "06_front_simple_3mm.dxf": simple_front(),
        "06b_front_simple_gotek_oled_rotary_3mm.dxf":
            simple_front(gotek_controls=True),
        "07_gotek_carrier_3mm.dxf": gotek_carrier(),
    }
    for name, entities in simple_parts.items():
        write_dxf(OUT_SIMPLE / name, entities)
        print(f"simple_joinery/{name}: {len(entities)} closed contours")


if __name__ == "__main__":
    main()
