# A600Reborn + PiStorm16 CM4 acrylic enclosure

[Polska wersja](CZYTAJTO.md)

Flat CNC-cut enclosure panels for an Amiga 600 motherboard compatible with the
[A600Reborn](https://github.com/istedman/A600Reborn) project, a PiStorm16/CM4
with active cooling, a bottom-mounted 1 MB Chip RAM expansion and a
FrameThrower 600. Video is exposed through a full-size HDMI ribbon adapter and
bracket installed in place of the RF modulator.

> **Status: mechanical prototype.** The motherboard outline and connector
> positions come from KiCad, but no manufacturing drawings are publicly
> available for the HDMI bracket, Ami64 Gotek assembly or the exact CM4 cooler.
> Before cutting the final acrylic, make a test I/O panel from 1 mm cardboard
> or HDF and verify the dimensions listed below.

## Repository contents

```text
.
├── dxf_screws/          screw-fastened CNC files at 1:1 scale
├── dxf_simple_joinery/  simple Bramble Pi-style finger-joint variant
├── generate_dxf.py      dependency-free parametric generator
├── visualize_assembly.py deterministic DXF/KiCad 3D projection
├── renders/             generated SVG and PNG assembly views
├── .gitignore
├── README.md            English documentation
└── CZYTAJTO.md          Polish documentation
```

The generated DXF files are intentionally committed so they can be sent to a
manufacturer without installing Python. After changing parameters, regenerate
them with:

```powershell
python generate_dxf.py
```

The technical views in `renders/` are generated deterministically from the DXF
and source PCB rather than by an image generator. Rebuild both views with:

```powershell
python visualize_assembly.py --pcb C:\path\to\Amiga600.kicad_pcb
```

The command rebuilds both views of the finger-joint enclosure.

![Front-right assembly preview](renders/assembly_simple_front-right.png)

![Rear-left assembly preview](renders/assembly_simple_rear-left.png)

> **AI disclosure:** The conceptual photorealistic image below was generated
> by AI from the supplied assembled A600 photo. It is visibly labelled in the
> image in line with the transparency principle described in the
> [European Commission's AI regulatory framework](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai).

![AI-generated conceptual photorealistic enclosure preview](renders/assembly_realistic.png)

The AI-generated image is illustrative only; use the non-AI SVG/DXF technical
views for dimensions and manufacturing decisions.

Only geometry confirmed by the DXF/KiCad sources is shown. The PCB `Edge.Cuts`,
mounting-drill diameters and flat footprint bounds are read directly from the
KiCad file. No arbitrary component heights are assigned. PiStorm16/CM4 and
Gotek electronics are deliberately omitted because no public mechanical CAD
is available; the visualizer does not replace them with invented models.

## Production files

The `dxf_screws/` directory contains the screw-fastened variant:

- `01_bottom_3mm.dxf` — bottom plate, five motherboard mounting points and
  ventilation below the RAM expansion;
- `01b_bottom_gotek_3mm.dxf` — compatible Gotek bottom; the carrier shares
  motherboard H1/MT6 standoff axes and needs no extra bottom holes;
- `02_top_3mm.dxf` — top plate with PiStorm16 intake and exhaust ventilation;
- `02b_top_gotek_oled_rotary_3mm.dxf` — top with a 0.96-inch OLED window,
  rotary encoder and activity LED;
- `02c_top_gotek_external_box_3mm.dxf` — top with two ribbon-cable passages for
  the Ami64 external display box;
- `02d_top_gotek_carrier_above_cn11_3mm.dxf` — unpierced top for a Gotek
  mounted above CN11 on motherboard standoffs;
- `03_rear_io_1mm.dxf` — power, HDMI, composite, RGB, audio, serial, parallel
  and external floppy ports;
- `04_right_io_3mm.dxf` — two DE-9 mouse/joystick ports;
- `04b_right_io_floppy_3mm.dxf` — alternative side panel with a generic floppy
  drive opening;
- `04c_right_io_gotek_usb_3mm.dxf` — Gotek side panel with rear-positioned
  USB-A access and two 6.5 mm control-button openings;
- `05_left_pcmcia_3mm.dxf` — PCMCIA opening;
- `06_front_3mm.dxf` — ventilated front panel with two 3 mm LED openings;
- `06b_front_gotek_oled_rotary_3mm.dxf` — front panel with the 0.96-inch OLED
  and rotary encoder;
- `07_gotek_carrier_3mm.dxf` — adjustable universal Gotek PCB carrier.

The files use ASCII AutoCAD R12 DXF, **millimetres**, and **1:1 scale**. Every
production file contains closed contours on the `CUT` layer only. Tool-radius
compensation is not included and must be applied on the correct side of each
contour in CAM.

All Ø3.4 mm M3 holes are **clearance holes**, not threads. Neither 1 mm nor
3 mm acrylic is thick enough to retain an M3 thread reliably. Use through
bolts with nuts and washers, threaded metal/nylon standoffs, or corner blocks.
Never drive an M3 screw directly into an acrylic panel. The 1 mm rear panel
also requires load-spreading washers and support from a bracket or standoff;
do not countersink the 1 mm sheet.

## Dimensions and assembly

- horizontal plate envelope: 329 × 206 mm;
- vertical panel height: 72 mm;
- top, bottom and side panels: 3 mm acrylic;
- rear I/O panel: 1 mm PETG or polycarbonate is safer than brittle 1 mm PMMA;
- motherboard underside: 18 mm above the bottom plate, using nylon M3
  standoffs;
- top/bottom corner standoffs: four M3 × 72 mm;
- H1–H3 mounting points: M3 screws installed without stressing the PCB;
- MT5–MT6 mounting points: M3 screws with insulating washers.

MT1–MT4 are intentionally unused. They are 3.75 × 1.50 mm slots on the PCB,
not M3 mounting holes. MT7 is not drilled through. H1–H3 and MT5–MT6 provide
five stable mounting points without modifying the motherboard.

Standard, current front-mounted OLED/encoder, and legacy top-ribbon variants
are provided. The carrier in `dxf_screws/07_gotek_carrier_3mm.dxf` is shared by all
enclosure construction methods.

## Simple finger-joint variant

The `dxf_simple_joinery/` directory contains a simpler design inspired by the
[BRAMBLE Pi case](https://www.tindie.com/products/Nick/bramble-pi-raspberry-pi-case/).
Its six panels press together directly with complementary rectangular fingers;
there are no separate through-tenons or locking wedges. All I/O openings and
the standard and two Gotek configurations are retained.

Every wall, including the rear panel, uses **3 mm** sheet. Fingers are roughly
16 mm wide and the generator gives each finger/recess pair 0.12 mm total
clearance (`SIMPLE_FINGER_CLEARANCE`). Treat this as a starting value: cut a
small fit sample from the production sheet and tune it for the actual kerf.
Sharp internal corners suit laser cutting; add dog-bones in CAM when routing.

Rear-panel orientation is stated from the user's position in front of the
Amiga: the power inlet is on the left (small X coordinate).

## Ami64 OLED + Rotary Gotek variant

The current arrangement uses panels `01`, `02d`, `04c`, `06b`, and carrier `07`.
The Gotek carrier sits above floppy connector CN11 in the motherboard's rear
right area. Longer nylon standoffs share the motherboard H1 and MT6 mounting
axes, so neither the top nor bottom receives separate carrier holes. The
0.96-inch OLED and rotary encoder are installed in the right side of the front
panel.

The OLED window is 28 × 15 mm and the encoder-bushing hole is 7.5 mm. The
`04c` provides a 16.5 × 8.5 mm USB-A opening and two 6.5 mm button holes on
the rear portion of the right side, away from the DE-9 ports. The 120 × 95 mm carrier has adjustable slots
for different PCB revisions. Ami64 supplies a 3D-printed internal mount but
does not publish its manufacturing drawing, so compare the holes with the
actual part and verify standoff height above motherboard components before CNC.

Vertical panels in the screw-fastened version may be attached using 15 × 15 mm
angle brackets or 3D-printed corner blocks. Corner holes are Ø3.4 mm clearance
holes for M3 through-bolts; the nut or thread belongs in the bracket/standoff,
never in 1 or 3 mm acrylic. Do not glue the panels before a trial assembly and
D-sub plug-clearance check.

## HDMI and FrameThrower

The design assumes the Archi-TECH kit containing a full-size HDMI connector
PCB, flex cable, mini-HDMI connector and printed bracket fitted in place of the
RF modulator. The rear panel has a 16.0 × 7.5 mm aperture centred on the
A600Reborn X2/RF position. The bracket remains attached to the motherboard;
the thin rear panel acts only as a bezel.

FrameThrower 600 clips onto Denise and connects to the PiStorm through CSI, so
it does not require a separate enclosure opening.

## Checks required before machining

The motherboard and port geometry comes from the source
`Amiga600.kicad_pcb`. Mechanical drawings are not published for every floppy
drive, HDMI bracket, RAM expansion or Gotek revision. Make a trial rear panel
from 1 mm cardboard or HDF and verify:

1. Connector centre height — this design uses 26.6 mm from the lower panel
   edge in the screw-fastened variant.
2. The 16.0 × 7.5 mm HDMI aperture and its centre position.
3. At least 15 mm clearance below the motherboard for the RAM expansion.
4. Floppy slot position before using the `04b` panel.
5. Gotek USB position and encoder-bushing diameter before using `02b`/`04c`.
6. Actual acrylic thickness with callipers before cutting the finger joints.

If measurements differ, edit `PCB_Z`, `IO_Z`, `SIMPLE_FINGER_CLEARANCE`, or the relevant
opening parameters in `generate_dxf.py`, then run `python generate_dxf.py`.

## Dimensional sources

- [A600Reborn](https://github.com/istedman/A600Reborn), KiCad PCB and connector
  footprints: maximum outline 316.992 × 194.056 mm;
- H1 `(311.912; 22.352)`, H2 `(5.080; 188.976)`, H3
  `(282.956; 150.622)`, MT5 `(158.496; 187.960)`, and MT6
  `(274.066; 96.393)` relative to the PCB origin;
- [PiStorm16 CM4](https://programatory.archi-tech.com.pl/pl/p/Pistorm16-RPi-CM4-Gotowy-do-pracy/359)
  — active cooling and ribbon-mounted HDMI;
- [HDMI bracket replacing RF](https://programatory.archi-tech.com.pl/pl/p/Mocowanie-portu-HDMI-w-miejscu-modulatora-Amiga-600/354);
- [FrameThrower 600](https://programatory.archi-tech.com.pl/pl/p/Framethrower-600-FT600-Pistorm/375)
  — Denise mounting and CSI connection;
- [Ami64 OLED + Rotary Gotek](https://www.ami64.com/product-page/internal-amiga-a600-gotek-with-oled-rotary)
  — internal floppy emulator and external 0.96-inch OLED/encoder unit.

## Manufacturing notes

- Apply cutter compensation toward the waste side; DXFs do not include tool
  compensation.
- Use a single-flute plastic-cutting bit for acrylic and leave the protective
  film attached while machining.
- PETG or polycarbonate is preferable to brittle PMMA for the 1 mm rear panel.
- Use nylon screws or insulating washers near the motherboard.
- Never connect a second power supply to the Raspberry Pi/PiStorm while the
  Amiga is also supplying power.
