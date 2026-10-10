"""fig8_stress_contours.png (smooth-surface render used by the supplement):
panel (b) title 'optimized graded (FE: -4.4%)' -> paper terminology, and the
-4.4% identified as the voxel ladder mean. Writes fig8_stress_contours_v7.png."""
from PIL import Image, ImageDraw, ImageFont

im = Image.open("fig8_stress_contours.png").convert("RGB")
d = ImageDraw.Draw(im)
d.rectangle([1240, 4, 2215, 82], fill="white")
f = ImageFont.truetype("times.ttf", 54)
txt = "(b) unconstrained design (FE ladder mean −4.4%)"
w = d.textlength(txt, font=f)
cx = 1672
x = min(cx - w / 2, 2215 - w)
d.text((x, 12), txt, fill="black", font=f)
im.save("fig8_stress_contours_v7.png")
im.crop((1100, 0, 2224, 140)).save("../../../_deep_review/preview/fig8png_title_v7.png")
print("ok", w)
