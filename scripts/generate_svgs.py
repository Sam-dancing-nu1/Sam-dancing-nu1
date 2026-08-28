# -*- coding: utf-8 -*-
"""generate_svgs.py — 从 data/stats.json 生成数据 SVG（深浅双主题）+ 像素化头像。
用法: python generate_svgs.py [--skip-avatar]
失败（数据不合法）退出非 0，Actions 侧不提交。
"""
import json
import os
import struct
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_lib import THEMES, blend, pixel_text, pix, svg_doc, write

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
W = 880


def load_stats():
    p = os.path.join(ROOT, "data", "stats.json")
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    assert isinstance(d["contributions"]["total"], int)
    assert isinstance(d["stars"], int)
    assert d["contributions"]["weeks"], "empty weeks"
    return d


# ---------------- heatmap ----------------
def heatmap(t, s):
    cell, gap = 12, 3
    weeks = s["contributions"]["weeks"]
    grid_w = len(weeks) * (cell + gap) - gap
    grid_h = 7 * (cell + gap) - gap
    x0 = (W - grid_w) // 2
    y0 = 40
    css = (".wk{opacity:0;animation:pop .35s ease forwards}"
           "@keyframes pop{to{opacity:1}}")
    body = pixel_text(16, 20, "CONTRIBUTIONS - LAST 365 DAYS", 8, t["muted"])
    body += pixel_text(W - 16, 20, str(s["contributions"]["total"]), 16, t["acc_deep"], anchor="end")
    for wi, wcol in enumerate(weeks):
        col = ['<g class="wk" style="animation-delay:%dms">' % (wi * 18)]
        for di, day in enumerate(wcol["days"]):
            lv = max(0, min(4, int(day.get("l", 0))))
            col.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"><title>%s %d</title></rect>'
                       % (x0 + wi * (cell + gap), y0 + di * (cell + gap),
                          cell, cell, t["heat"][lv], day.get("d", ""), day.get("c", 0)))
        col.append("</g>")
        body += "".join(col)
    # 图例
    ly = y0 + grid_h + 18
    lx = (W - (5 * 13 + 100)) // 2
    body += pixel_text(lx, ly + 9, "LESS", 8, t["muted"])
    lx += 46
    for i in range(5):
        body += '<rect x="%d" y="%d" width="10" height="10" rx="2" fill="%s"/>' % (lx + i * 13, ly, t["heat"][i])
    body += pixel_text(lx + 5 * 13 + 6, ly + 9, "MORE", 8, t["muted"])
    return svg_doc(W, ly + 20, body, css=css)


# ---------------- languages ----------------
def langs(t, s):
    rows = s["languages"]
    if not rows:
        return None
    mx = max(r["size"] for r in rows)
    bar_x, bar_w_max, bar_h = 150, 600, 12
    y = 40
    body = pixel_text(16, 20, "LANGUAGES - BY BYTE SIZE (INCL. FORKS)", 8, t["muted"])
    for r in rows:
        w = max(4, int(bar_w_max * r["size"] / mx))
        fill = blend(r["color"], t["bg"], 0.4)
        body += pixel_text(16, y + 10, r["name"][:14].upper(), 8, t["ink"])
        body += ('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="%s" stroke-width="2"/>'
                 % (bar_x, y, w, bar_h, fill, t["stroke"]))
        pct = "%.1f%%" % (r["size"] / mx * 100)
        body += pixel_text(W - 16, y + 10, pct, 8, t["muted"], anchor="end")
        y += 26
    return svg_doc(W, y + 6, body, css="")


# ---------------- numbers ----------------
def numbers(t, s):
    cards = [
        ("CONTRIBUTIONS", str(s["contributions"]["total"])),
        ("STARS", str(s["stars"])),
        ("PUBLIC REPOS", str(s["publicRepos"])),
    ]
    cw, ch, gap_, y = 250, 84, 30, 12
    x = (W - (cw * 3 + gap_ * 2)) // 2
    body = ""
    for label, val in cards:
        body += ('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>'  # 硬阴影
                 '<rect x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="%s" stroke-width="2"/>'
                 % (x + 4, y + 4, cw, ch, t["line2"],
                    x, y, cw, ch, t["surface"], t["stroke"]))
        body += pixel_text(x + cw // 2, y + 26, label, 8, t["muted"], anchor="middle")
        body += pixel_text(x + cw // 2, y + 64, val, 24, t["acc_deep"], anchor="middle")
        x += cw + gap_
    return svg_doc(W, y + ch + 16, body, css="")


# ---------------- avatar 像素化 ----------------
def pixelate_avatar(stats):
    try:
        from PIL import Image
    except ImportError:
        print("SKIP avatar: pillow not installed")
        return False
    url = stats.get("avatarUrl", "")
    if not url:
        print("SKIP avatar: no avatarUrl")
        return False
    url = url.split("?")[0] + "?s=200"
    req = urllib.request.Request(url, headers={"User-Agent": "profile-stats/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    import io
    img = Image.open(io.BytesIO(data)).convert("RGB")
    side = min(img.size)
    img = img.crop(((img.width - side) // 2, (img.height - side) // 2,
                    (img.width + side) // 2, (img.height + side) // 2))
    # 逐步折半降采样，避免单步大比例缩放的锯齿
    while side // 2 >= 32:
        side //= 2
        img = img.resize((side, side), Image.BILINEAR)
    img = img.resize((32, 32), Image.BILINEAR)
    out = img.resize((128, 128), Image.NEAREST)
    p = os.path.join(ASSETS, "avatar-photo-pixel.png")
    out.save(p, "PNG", optimize=True)
    print("wrote", p)
    return True


def main():
    skip_avatar = "--skip-avatar" in sys.argv
    s = load_stats()
    for theme, t in THEMES.items():
        write(os.path.join(ASSETS, "stats", "heatmap-%s.svg" % theme), heatmap(t, s))
        lg = langs(t, s)
        if lg:
            write(os.path.join(ASSETS, "stats", "langs-%s.svg" % theme), lg)
        write(os.path.join(ASSETS, "stats", "numbers-%s.svg" % theme), numbers(t, s))
    if not skip_avatar:
        pixelate_avatar(s)
    print("done")


if __name__ == "__main__":
    main()
