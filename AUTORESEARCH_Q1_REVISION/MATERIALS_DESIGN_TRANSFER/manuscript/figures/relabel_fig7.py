"""fig7_design_mechanism.png: panel (b) title 'optimized graded' -> the paper's
term. Raster patch (the PDF version has no text layer). Writes *_v7.png."""
from PIL import Image, ImageDraw, ImageFont

im = Image.open("fig7_design_mechanism.png").convert("RGB")
d = ImageDraw.Draw(im)
d.rectangle([985, 148, 1545, 212], fill="white")
f = ImageFont.truetype("times.ttf", 50)
txt = "(b) unconstrained design"
w = d.textlength(txt, font=f)
d.text((1260 - w / 2, 152), txt, fill="black", font=f)
im.save("fig7_design_mechanism_v7.png")
im.crop((700, 100, 1800, 260)).save("../../../_deep_review/preview/fig7_crop_v7.png")
print("ok")
