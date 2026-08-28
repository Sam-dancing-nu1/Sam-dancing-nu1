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
from svg_lib import THEMES, blend, pixel_text, sans_text, pix, svg_doc, write

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


# ---------------- heatmap（卡片底 + 系统字体标签） ----------------
def heatmap(t, s):
    cell, gap = 12, 3
    weeks = s["contributions"]["weeks"]
    grid_w = len(weeks) * (cell + gap) - gap
    grid_h = 7 * (cell + gap) - gap
    x0 = (W - grid_w) // 2
    y0 = 52
    css = (".wk{opacity:0;animation:pop .35s ease forwards}"
           "@keyframes pop{to{opacity:1}}")
    # 卡片底（不透明：主题切换失效时依然可读）
    body = ('<rect x="0" y="0" width="%d" height="%d" fill="%s" stroke="%s" stroke-width="2" rx="12"/>'
            % (W, 196, t["surface"], t["line2"]))
    body += sans_text(24, 32, "CONTRIBUTIONS · LAST 365 DAYS · 更新于 %s"
                      % s.get("generatedAt", "")[:10], 13, t["muted"])
    body += pixel_text(W - 24, 34, str(s["contributions"]["total"]), 16, t["acc_deep"], anchor="end")
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
    ly = y0 + grid_h + 20
    lx = (W - (5 * 13 + 110)) // 2
    body += sans_text(lx, ly + 10, "LESS", 12, t["muted"], weight=500)
    lx += 48
    for i in range(5):
        body += '<rect x="%d" y="%d" width="11" height="11" rx="2" fill="%s"/>' % (lx + i * 14, ly, t["heat"][i])
    body += sans_text(lx + 5 * 14 + 8, ly + 10, "MORE", 12, t["muted"], weight=500)
    return svg_doc(W, ly + 24, body, css=css)


# ---------------- languages（右列窄版：卡片底 + 系统字体） ----------------
def langs(t, s):
    rows = s["languages"]
    if not rows:
        return None
    NW, y = 600, 46
    mx = max(r["size"] for r in rows)
    bar_x, bar_w_max, bar_h = 170, 330, 14
    # 卡片底
    H = y + len(rows) * 28 + 14
    body = ('<rect x="0" y="0" width="%d" height="%d" fill="%s" stroke="%s" stroke-width="2" rx="12"/>'
            % (NW, H, t["surface"], t["line2"]))
    body += sans_text(20, 30, "LANGUAGES · 含 fork · 更新于 %s" % s.get("generatedAt", "")[:10], 13, t["muted"])
    for r in rows:
        w = max(5, int(bar_w_max * r["size"] / mx))
        fill = blend(r["color"], t["bg"], 0.4)
        body += sans_text(20, y + 12, r["name"][:12], 13, t["ink"])
        body += ('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="%s" stroke-width="2"/>'
                 % (bar_x, y, w, bar_h, fill, t["stroke"]))
        pct = "%.1f%%" % (r["size"] / mx * 100)
        body += sans_text(NW - 20, y + 12, pct, 13, t["muted"], anchor="end")
        y += 28
    return svg_doc(NW, H, body, css="")


# ---------------- stats-mini（左列横排小卡：CONTRIBUTIONS / REPOS） ----------------
def stats_mini(t, s):
    cards = [
        ("CONTRIB", str(s["contributions"]["total"])),
        ("REPOS", str(s["publicRepos"])),
    ]
    NW, cw, ch, y = 240, 112, 72, 10
    x = (NW - (cw * 2 + 16)) // 2
    body = ""
    for label, val in cards:
        body += ('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>'  # 硬阴影
                 '<rect x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="%s" stroke-width="2" rx="8"/>'
                 % (x + 4, y + 4, cw, ch, t["line2"],
                    x, y, cw, ch, t["surface"], t["stroke"]))
        body += sans_text(x + 12, y + 26, label, 12, t["muted"])
        body += pixel_text(x + cw - 12, y + 56, val, 16, t["acc_deep"], anchor="end")
        x += cw + 16
    return svg_doc(NW, y + ch + 6, body, css="")


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
        write(os.path.join(ASSETS, "stats", "numbers-%s.svg" % theme), stats_mini(t, s))
    if not skip_avatar:
        pixelate_avatar(s)
    print("done")


if __name__ == "__main__":
    main()
