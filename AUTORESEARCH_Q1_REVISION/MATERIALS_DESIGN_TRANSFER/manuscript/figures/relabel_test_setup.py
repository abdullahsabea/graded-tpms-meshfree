"""Relabel the coupon figure: the original says "Topology-optimised design
(green)"; the paper's term is the band-and-smoothness-restricted design.
Also adds nominal dimension lines to the top views of panel (a).
Writes test_setup_v7.png; the original file is untouched.

Scale: the two witness grooves (validation/make_dogbone_stl.py, MARK_X1 =
30 and 130 mm) are at pixel columns 943.5 and 1207 of the top views, so
2.635 px/mm; the 60 mm gauge is centred between them (x1 = 50-110 mm).
Checked against the 30 mm gauge width, which renders 78-80 px tall."""
from PIL import Image, ImageDraw, ImageFont

im = Image.open("test_setup.png").convert("RGB")
d = ImageDraw.Draw(im)
d.rectangle([0, 64, 372, 114], fill="white")
try:
    f = ImageFont.truetype("arialbd.ttf", 20)
    fs = ImageFont.truetype("arial.ttf", 14)
except OSError:
    f = fs = ImageFont.load_default()
for y, txt in ((66, "Band-restricted graded"), (90, "design (green)")):
    w = d.textlength(txt, font=f)
    d.text(((372 - w) / 2, y), txt, fill="black", font=f)

G1, G2 = 943.5, 1207.0                        # groove centres, x1 = 30 and 130 mm
PX_MM = (G2 - G1) / 100.0
X0 = G1 - 30.0 * PX_MM                        # x1 = 0
gauge = (X0 + 50.0 * PX_MM, X0 + 110.0 * PX_MM)


def dim(x1, x2, y, label, text_y, ticks=None):
    d.line([(x1, y), (x2, y)], fill="black", width=1)
    for x, s in ((x1, 1), (x2, -1)):          # arrowheads
        d.polygon([(x, y), (x + 7 * s, y - 3), (x + 7 * s, y + 3)], fill="black")
    if ticks:
        for x in (x1, x2):
            d.line([(x, ticks[0]), (x, ticks[1])], fill="black", width=1)
    w = d.textlength(label, font=fs)
    d.text(((x1 + x2) / 2 - w / 2, text_y), label, fill="black", font=fs)


dim(G1, G2, 24, "100 mm span (grooves), nominal", 4, ticks=(18, 32))
dim(gauge[0], gauge[1], 163, "60 mm gauge, nominal", 140)
im.save("test_setup_v7.png")
print(f"ok: {PX_MM:.3f} px/mm, gauge {gauge[0]:.1f}-{gauge[1]:.1f} px")
