#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CleanQuant のマーケット用ロゴ(500x500 PNG)を生成。"""
import os
from PIL import Image, ImageDraw

W = 500
NAVY = (11, 13, 18, 255)
GREEN = (74, 222, 128, 255)
GREEN_DIM = (74, 222, 128, 90)

img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 角丸の濃紺背景
d.rounded_rectangle([0, 0, W - 1, W - 1], radius=112, fill=NAVY)

# 上昇する3本のバー(quant/データの象徴)
bar_w, gap = 78, 46
total = bar_w * 3 + gap * 2
x0 = (W - total) // 2
base_y = 372
heights = [120, 195, 272]
tops = []
for i, h in enumerate(heights):
    x = x0 + i * (bar_w + gap)
    top = base_y - h
    d.rounded_rectangle([x, top, x + bar_w, base_y], radius=20, fill=GREEN)
    tops.append((x + bar_w // 2, top))

# バー頂点を結ぶ上昇トレンドライン + ノード
d.line([tops[0], tops[1], tops[2]], fill=GREEN, width=10, joint="curve")
for (cx, cy) in tops:
    d.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], fill=NAVY, outline=GREEN, width=8)
# 右肩上がりを強調する短い延長線
ex, ey = tops[2]
d.line([(ex, ey), (ex + 46, ey - 40)], fill=GREEN, width=10)

# ベースライン(薄い)
d.line([(x0 - 10, base_y + 16), (x0 + total + 10, base_y + 16)], fill=GREEN_DIM, width=6)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cleanquant_logo.png")
img.save(out)
print("saved:", out, img.size)
