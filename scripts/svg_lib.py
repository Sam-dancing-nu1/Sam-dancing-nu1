# -*- coding: utf-8 -*-
"""svg_lib.py — SVG 公共库：照搬 www 主站（sam-dancing.work）的视觉体系。

设计规则（勿改，值全部实测自主站 index.html :root）：
- 色板 = 主站令牌：--bg:#0a0a0b / --ink:#ededed / --accent:#d8a25a 等
- 背景 = 主站同款：照片 Ken Burns 30s 缩放 + 双层 scrim 渐变遮罩 + feTurbulence 噪点
- 字体 = 系统等宽栈（JetBrains Mono 优先），中文走 PingFang/雅黑 fallback
"""
import base64
import os

MONO = ("'JBM','JetBrains Mono','SFMono-Regular','SF Mono',Consolas,"
        "'Liberation Mono','PingFang SC','Microsoft YaHei',monospace")
DISPLAY = "'Space Grotesk',system-ui,'PingFang SC','Microsoft YaHei',sans-serif"

_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "fonts")


def font_face_css():
    """内嵌 JetBrains Mono（latin 子集 400/700），不靠系统字体。"""
    out = []
    for wt in (400, 700):
        with open(os.path.join(_FONT_DIR, "jetbrains-mono-latin-%d.woff2" % wt),
                  "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        out.append("@font-face{font-family:'JBM';font-weight:%d;"
                   "src:url(data:font/woff2;base64,%s) format('woff2');}"
                   % (wt, b64))
    return "".join(out)

# ---------------- 主站色板（sam-dancing.work :root 实测值） ----------------
DARK = {
    "bg":      "#0a0a0b",
    "ink":     "#ededed",
    "ink2":    "#c7c7c7",
    "muted":   "#8a8a8a",
    "faint":   "#5d5d61",
    "line":    "rgba(255,255,255,.09)",
    "line2":   "rgba(255,255,255,.17)",
    "acc":     "#d8a25a",
    "acc2":    "#e7bd84",
    "ok":      "#74d39a",
    "panel":   "rgba(255,255,255,.022)",
    "surface2": "rgba(255,255,255,.045)",
    # 热力 5 级（金色系，空格色贴近 bg）
    "heat": ["#17181a", "#4a3a22", "#7a5a2c", "#b07a32", "#e8a84c"],
}

THEMES = {"dark": DARK}


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def svg_doc(w, h, body, css="", defs=""):
    style = "<style>%s%s</style>" % (font_face_css(), css)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d" role="img">' % (w, h, w, h)
        + ("<defs>%s</defs>" % defs if defs else "")
        + style + body + "</svg>"
    )


_BG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "assets", "img")
BG_NAMES = ["bg-01", "bg-02", "bg-03", "bg-04", "bj1", "bj2"]
BG_INTERVAL = 7.0        # 主站同款：7s 切换，2s 淡入淡出


def bg_layers(w, h):
    """主站同款背景轮播：6 张照片交叉淡入淡出（7s/张）+ Ken Burns 缩放
    + scrim 双层渐变 + grain 噪点。返回 (defs, svg_body)。"""
    imgs = []
    for n in BG_NAMES:
        with open(os.path.join(_BG_DIR, n + ".webp"), "rb") as f:
            imgs.append(base64.b64encode(f.read()).decode("ascii"))
    defs = (
        # scrim：照搬主站 .bg-scrim 双层渐变
        '<linearGradient id="scrim-h" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="rgba(8,8,9,.80)"/>'
        '<stop offset="0.48" stop-color="rgba(8,8,9,.44)"/>'
        '<stop offset="1" stop-color="rgba(8,8,9,.18)"/></linearGradient>'
        '<linearGradient id="scrim-v" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="rgba(8,8,9,.58)"/>'
        '<stop offset="0.32" stop-color="rgba(8,8,9,.34)"/>'
        '<stop offset="1" stop-color="rgba(8,8,9,.84)"/></linearGradient>'
        # grain：照搬主站 feTurbulence 噪点
        '<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".9" '
        'numOctaves="2"/></filter>'
    )
    n = len(imgs)
    cycle = n * BG_INTERVAL          # 42s 一整圈
    # 单层时间轴：0→2s 淡入，保持到 7s，→9s 淡出，此后熄灭到圈末
    k = [0, 2 / cycle, BG_INTERVAL / cycle, (BG_INTERVAL + 2) / cycle, 1]
    body = '<rect width="%d" height="%d" fill="#0a0a0b"/>' % (w, h)
    for i, b64 in enumerate(imgs):
        body += (
            '<g class="kb" opacity="0">'
            '<animate attributeName="opacity" values="0;1;1;0;0" '
            'keyTimes="0;%.4f;%.4f;%.4f;1" dur="%.1fs" begin="%.1fs" '
            'repeatCount="indefinite"/>'
            '<image href="data:image/webp;base64,%s" x="-40" y="-40" '
            'width="%d" height="%d" preserveAspectRatio="xMidYMid slice"/>'
            '</g>'
            % (k[1], k[2], k[3], cycle, -i * BG_INTERVAL, b64, w + 80, h + 80)
        )
    body += (
        '<rect width="%d" height="%d" fill="url(#scrim-h)"/>'
        '<rect width="%d" height="%d" fill="url(#scrim-v)"/>'
        '<rect width="%d" height="%d" filter="url(#grain)" opacity=".035" '
        'style="mix-blend-mode:overlay"/>'
        % (w, h, w, h, w, h)
    )
    return defs, body


KB_CSS = (".kb{transform-origin:center;animation:kb 30s ease-in-out infinite alternate}"
          "@keyframes kb{from{transform:scale(1.03)}to{transform:scale(1.13)}}")


def mono_text(x, y, text, size, color, anchor="start", weight=400, spacing=0,
              font=None):
    sp = ' letter-spacing="%s"' % spacing if spacing else ""
    return (
        '<text x="%s" y="%s" font-family="%s" font-size="%s" font-weight="%s"'
        ' fill="%s" text-anchor="%s"%s>%s</text>'
        % (x, y, font or MONO, size, weight, color, anchor, sp, esc(text))
    )


def card(x, y, w, h, t, fill=None, stroke=None, rx=12):
    """主站 panel：rgba 白底 + 细线 + 12px 圆角。"""
    return (
        '<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="%s" stroke="%s"/>'
        % (x, y, w, h, rx, fill or t["panel"], stroke or t["line"])
    )


def eyebrow(x, y, text, t):
    """主站 eyebrow：24px 金线 + 小金字（宽字距）。"""
    return (
        '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>'
        % (x, y - 3, x + 24, y - 3, t["acc"])
        + mono_text(x + 35, y, text, 10, t["acc"], spacing=3)
    )


def write(out_path, content):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", out_path, len(content), "bytes")
