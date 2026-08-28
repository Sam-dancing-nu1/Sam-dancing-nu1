# -*- coding: utf-8 -*-
"""svg_lib.py — 8-bit 像素治愈风 SVG 公共库（静态素材与 Actions 生成共用）。

设计规则（勿改）：
- 8-bit 三件套：2px 描边 + 直角 + 偏移硬阴影（零模糊）
- 像素字：Press Start 2P，字号只用 8 的整数倍，坐标取整
- SVG 内只放英文/数字；中文一律放 README 骨架层
- 金色 #D8A25A 只做填充/描边；当文字色用时 light 主题必须用 acc_deep（对比度已验证）
"""
import base64
import os

_FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts", "press-start-2p.woff2")

def font_base64():
    with open(_FONT_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def font_face_css():
    b64 = font_base64()
    return (
        "@font-face{font-family:'PSP2';"
        "src:url(data:font/woff2;base64,%s) format('woff2');"
        "font-weight:400;font-style:normal;}" % b64
    )

# ---------------- 色板（对比度已实测） ----------------
LIGHT = {
    "bg":       "#FDFBF7",   # 奶油白页面底
    "surface":  "#FFFFFF",
    "surface2": "#F5F0E7",
    "ink":      "#2E2A26",   # 13.77:1 AAA
    "muted":    "#6B6358",   #  5.72:1 AA
    "line":     "#E9E1D4",
    "line2":    "#D9CDBC",
    "stroke":   "#2E2A26",   # 8-bit 硬描边
    "acc":      "#D8A25A",   # 只做填充/描边/装饰
    "acc_deep": "#7E5517",   # 金色文字专用（bg 上 6.35:1）
    "acc_lite": "#F3DDB4",
    "pink":     "#FBE3E8",  "pink_deep":  "#A83F5B",
    "mint":     "#DFF2E6",  "mint_deep":  "#26724F",
    "sky":      "#E2F0F9",  "sky_deep":   "#25618F",
    "gold":     "#F3DDB4",  "gold_deep":  "#7E5517",
    # 热力 5 级（浅色：从米色到深金）
    "heat": ["#EDE7DC", "#F5E3C0", "#EDCB8E", "#D8A25A", "#B07A32"],
    "title_main": "#7E5517",   # 标题主色
    "title_shadow": "#D8A25A", # 标题硬阴影
}

DARK = {
    "bg":       "#0B0C0F",   # 与 www 主站同源
    "surface":  "#15161B",
    "surface2": "#1B1C22",
    "ink":      "#E8EAEF",
    "muted":    "#8A90A0",
    "line":     "#23242A",
    "line2":    "#2C2E35",
    "stroke":   "#3A3E48",
    "acc":      "#D8A25A",   # 深底上金色对比充足，可直接当文字
    "acc_deep": "#E8A84C",
    "acc_lite": "#5A431F",
    "pink":     "#3A2429",  "pink_deep":  "#E8A0B0",
    "mint":     "#1E3229",  "mint_deep":  "#8FCFB2",
    "sky":      "#1E2C3A",  "sky_deep":   "#8FB8DC",
    "gold":     "#3A2F1A",  "gold_deep":  "#E8C078",
    "heat": ["#23242A", "#4A3A22", "#7A5A2C", "#B07A32", "#E8A84C"],
    "title_main": "#D8A25A",
    "title_shadow": "#5A3E14",
}

THEMES = {"light": LIGHT, "dark": DARK}

# 徽章轮换语义色（浅底, 深字/描边）
_BADGE_CYCLE = [("mint", "mint_deep"), ("sky", "sky_deep"), ("pink", "pink_deep"), ("gold", "gold_deep")]


def blend(hex_color, hex_bg, ratio=0.4):
    """把 hex_color 与 hex_bg 按 ratio 混合（用于把 GitHub 语言色降饱和）。"""
    def ch(c, i):
        c = c.lstrip("#")
        return int(c[i * 2:i * 2 + 2], 16)
    r = round(ch(hex_color, 0) * (1 - ratio) + ch(hex_bg, 0) * ratio)
    g = round(ch(hex_color, 1) * (1 - ratio) + ch(hex_bg, 1) * ratio)
    b = round(ch(hex_color, 2) * (1 - ratio) + ch(hex_bg, 2) * ratio)
    return "#%02X%02X%02X" % (r, g, b)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def svg_doc(w, h, body, bg=None, css=""):
    """SVG 文档骨架。bg=None 表示透明底。"""
    bg_rect = '<rect x="0" y="0" width="%d" height="%d" fill="%s"/>' % (w, h, bg) if bg else ""
    style = "<style>%s %s</style>" % (font_face_css(), css) if (font_face_css() or css) else ""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d" role="img">' % (w, h, w, h)
        + style + bg_rect + body + "</svg>"
    )


def pixel_text(x, y, text, size, color, anchor="start"):
    """像素文本。y 为基线；调用方负责取整。"""
    return (
        '<text x="%d" y="%d" font-family="PSP2,monospace" font-size="%d" '
        'fill="%s" text-anchor="%s">%s</text>'
        % (int(x), int(y), size, color, anchor, esc(text))
    )


def hard_rect(x, y, w, h, fill, stroke, shadow, off=3):
    """像素块 = 偏移硬阴影 + 2px 描边直角矩形。"""
    return (
        '<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>'
        '<rect x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="%s" stroke-width="2"/>'
        % (x + off, y + off, w, h, shadow,
           x, y, w, h, fill, stroke)
    )


def pixel_badge(x, y, text, size, fill, deep, stroke, shadow, pad_x=12, h=None):
    """单个像素徽章，返回 (svg, width)。size 为字号（8 的整数倍）。"""
    if h is None:
        h = size + 14
    w = len(text) * size + pad_x * 2
    body = hard_rect(x, y, w, h, fill, deep if deep else stroke, shadow)
    ty = y + (h + size) // 2 - 2
    body += pixel_text(x + pad_x, ty, text, size, deep)
    return body, w


def badge_row(texts, y, size, t, shadow, gap=18, total_w=880, h=None):
    """一行像素徽章，整体居中。返回 (svg, 行高)。"""
    if h is None:
        h = size + 14
    widths = [len(t_) * size + 24 for t_ in texts]
    row_w = sum(widths) + gap * (len(texts) - 1)
    x = (total_w - row_w) // 2
    parts = []
    for i, t_ in enumerate(texts):
        fill_k, deep_k = _BADGE_CYCLE[i % len(_BADGE_CYCLE)]
        s, w = pixel_badge(x, y, t_, size, t[fill_k], t[deep_k], t["stroke"], shadow, h=h)
        parts.append(s)
        x += w + gap
    return "".join(parts), h


def pix(x, y, s, color):
    """单个小像素方块（装饰用）。"""
    return '<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>' % (x, y, s, s, color)


def deco_row(cx, y, s=6, gap=6, colors=None, n=9):
    """中点对称的装饰像素行。"""
    if colors is None:
        colors = ["acc", "mint_deep", "sky_deep", "pink_deep", "acc_deep"]
    parts = []
    step = s + gap
    start = cx - (n // 2) * step
    for i in range(n):
        k = abs(i - n // 2)
        c = colors[k % len(colors)]
        parts.append(pix(start + i * step, y, s, c))
    return "".join(parts)


def write(out_path, content):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", out_path, len(content), "bytes")
