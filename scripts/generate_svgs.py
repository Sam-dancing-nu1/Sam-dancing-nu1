# -*- coding: utf-8 -*-
"""generate_svgs.py — 生成 profile 主图：一张 4:3 横屏 dashboard-dark.svg。

视觉照搬 www 主站：背景照片轮播（6 张 / 7s 切换 / Ken Burns）+ scrim 遮罩 + grain、
eyebrow 小金字 + Space Grotesk 大字 + 金竖线座右铭 + panel 玻璃卡片。
热力图上跑一条智能贪吃蛇：贪心最近邻寻路追有贡献的格子，吃光后从画外绕回起点，
循环连续无瞬移。右列数据卡底部带贡献趋势曲线图。
数据从 data/stats.json 读，Actions 每日刷新。
用法: python generate_svgs.py
失败（数据不合法）退出非 0，Actions 侧不提交。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_lib import (DARK, DISPLAY, KB_CSS, bg_layers, card, eyebrow, mono_text,
                     svg_doc, write)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
W, H = 960, 720          # 4:3 横屏
T = DARK
L, R = 36, 924           # 内容左右边距

CSS = (KB_CSS
       + ".cur{animation:blink 1.1s step-end infinite}"
         "@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}"
         ".fade{opacity:0;animation:fade .7s cubic-bezier(.22,.61,.36,1) forwards}"
         "@keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}")

AI_TOOLS = ["HERMES", "MIMO CODE", "OPENCODE"]
LINKS = ["GitHub", "哔哩哔哩", "邮箱", "博客"]
INTERESTS = ["独立开发者", "AI 智能体建造师", "安卓逆向玩家"]
ABOUT_CN = [
    "一年开发周期，从设计到上线一个人闭环。",
    "AI Agent 工作流 · Android ROM 与逆向 · 全栈 Web · 主站 sam-dancing.work",
]

SNAKE_SHADES = ["#ffe9c4", "#e8c078", "#d8a25a", "#b07a32", "#7a5a2c", "#4a3a22"]
SNAKE_SIZES = [11, 10, 9, 8, 7, 6]     # 头到尾递减


def load_stats():
    p = os.path.join(ROOT, "data", "stats.json")
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    assert isinstance(d["contributions"]["total"], int)
    assert isinstance(d["stars"], int)
    assert d["contributions"]["weeks"], "empty weeks"
    return d


def typewriter_clip(clip_id, x, y, width, height, chars, dur=1.2, begin=0.0):
    """等宽字打字机：clipPath 矩形按字符宽度离散增长，逐字显现。"""
    step = width / chars
    values = ";".join(str(round(step * i)) for i in range(chars + 1))
    times = ";".join("%.3f" % (i / chars) for i in range(chars + 1))
    return (
        '<clipPath id="%s"><rect x="%s" y="%s" width="0" height="%s">'
        '<animate attributeName="width" values="%s" keyTimes="%s" '
        'calcMode="discrete" dur="%.2fs" begin="%.2fs" fill="freeze"/>'
        '</rect></clipPath>'
        % (clip_id, x, y, height, values, times, dur, begin)
    ), 'clip-path="url(#%s)"' % clip_id


def _walk(path, cur, f):
    """从 cur 横纵交替阶梯步进到 f（网格内），返回新位置。顺路追加进 path。"""
    while cur != f:
        dx, dy = f[0] - cur[0], f[1] - cur[1]
        if dx and dy:
            if len(path) % 2 == 0:
                cur = (cur[0] + (1 if dx > 0 else -1), cur[1])
            else:
                cur = (cur[0], cur[1] + (1 if dy > 0 else -1))
        elif dx:
            cur = (cur[0] + (1 if dx > 0 else -1), cur[1])
        else:
            cur = (cur[0], cur[1] + (1 if dy > 0 else -1))
        path.append(cur)
    return cur


def smart_snake_path(levels, cols, rows):
    """智能贪吃蛇：网格内活动，永不出界。
    阶段1：贪心最近邻追食物（横纵交替阶梯，到边自然掉头）；
    阶段2：吃光后之字巡场扫到右下，再扫回起点 (0,3)，闭合循环无瞬移。"""
    food = {p for p, lv in levels.items() if lv > 0}
    path = [(0, 3)]
    cur = (0, 3)
    while food:
        f = min(food, key=lambda p: (abs(p[0] - cur[0]) + abs(p[1] - cur[1]),
                                     -levels[p]))
        cur = _walk(path, cur, f)
        food = {p for p in food if p not in path}
    # 阶段2：直接回家（不巡场），到家后停留约 2.5s 再开下一圈
    _walk(path, cur, (0, 3))
    path.extend([(0, 3)] * 25)
    return path


def snake_svg(path, x0, y0, step, cell, dur):
    """蛇身：每节 rect 沿路径 paced 匀速滑动；头 begin 最负，尾 begin=0。"""
    n = len(path)
    cell_t = dur / n
    vals = ";".join("%d,%d" % (x0 + c * step + cell // 2, y0 + r * step + cell // 2)
                    for c, r in path)
    nseg = len(SNAKE_SIZES)
    body = ""
    for i, sz in enumerate(SNAKE_SIZES):
        begin = (i - (nseg - 1)) * cell_t
        body += (
            '<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="3" fill="%s">'
            '<animateTransform attributeName="transform" type="translate" '
            'values="%s" calcMode="paced" dur="%.1fs" begin="%.3fs" '
            'repeatCount="indefinite"/></rect>'
            % (-sz / 2, -sz / 2, sz, sz, SNAKE_SHADES[i], vals, dur, begin)
        )
    return body, cell_t, n


def sparkline(daily_cum, x, y, w, h):
    """累计贡献曲线：逐日累加（单调递增阶梯，真实反映活跃段），
    金色折线 + 面积渐变 + 末点圆点。"""
    mx = max(daily_cum) or 1
    n = len(daily_cum)
    pts = [(x + i * w / (n - 1), y + h - (v / mx) * (h - 2))
           for i, v in enumerate(daily_cum)]
    line = "M %.1f,%.1f L " % pts[0] + " L ".join("%.1f,%.1f" % p for p in pts[1:])
    area = line + " L %.1f,%.1f L %.1f,%.1f Z" % (pts[-1][0], y + h, pts[0][0], y + h)
    return (
        '<path d="%s" fill="url(#area-fill)"/>'
        '<path d="%s" fill="none" stroke="%s" stroke-width="1.5" '
        'stroke-linejoin="round" stroke-linecap="round"/>'
        '<circle cx="%.1f" cy="%.1f" r="2.5" fill="%s"/>'
        % (area, line, T["acc2"], pts[-1][0], pts[-1][1], T["acc"])
    )


def dashboard(s):
    defs, bg = bg_layers(W, H)
    defs += (
        '<linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0.42" stop-color="#d8a25a"/>'
        '<stop offset="0.5" stop-color="#ffe9c4"/>'
        '<stop offset="0.58" stop-color="#d8a25a"/>'
        '<animateTransform attributeName="gradientTransform" type="translate" '
        'values="-1.2 0; 1.2 0" dur="3.2s" repeatCount="indefinite"/>'
        '</linearGradient>'
        '<linearGradient id="area-fill" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#d8a25a" stop-opacity=".22"/>'
        '<stop offset="1" stop-color="#d8a25a" stop-opacity="0"/></linearGradient>'
    )

    body = bg

    # ── 左列 hero：eyebrow + 等宽金字大标题（打字机+光标）+ 金竖线座右铭 ──
    tw, tw_attr = typewriter_clip("tw-name", L - 2, 82, 342, 56, 11, dur=1.2, begin=0.3)
    defs += tw
    body += eyebrow(L, 64, "GITHUB PROFILE", T)
    body += mono_text(L, 126, "SAM-DANCING", 46, T["acc"], weight=700, spacing=2) \
        .replace("<text ", '<text %s ' % tw_attr, 1)
    body += '<rect class="cur" x="366" y="94" width="11" height="38" fill="%s"/>' % T["acc"]
    # 座右铭：金竖线 + 大字（主站 hero-lead 同款）
    body += '<g class="fade" style="animation-delay:1.5s">'
    body += '<rect x="%d" y="150" width="2" height="34" fill="%s"/>' % (L, T["acc"])
    body += mono_text(L + 20, 174, "风雨吹我两三年，归来仍是顺风局。", 18, T["ink"],
                      spacing=2, font=DISPLAY)
    body += "</g>"
    # interests：竖线分隔（主站 .interests 同款）
    body += '<g class="fade" style="animation-delay:1.8s">'
    x = L
    for i, it in enumerate(INTERESTS):
        body += mono_text(x, 212, it, 12, T["muted"], spacing=1)
        x += len(it) * 13 + 12
        if i < len(INTERESTS) - 1:
            body += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>' \
                    % (x - 6, 202, x - 6, 213, T["line2"])
    body += "</g>"
    body += '<g class="fade" style="animation-delay:2.1s">'
    for i, line in enumerate(ABOUT_CN):
        body += mono_text(L, 240 + i * 20, line, 13, T["muted"])
    body += "</g>"

    # ── 右列：年度数据三卡加高铺满（贡献卡底部内嵌累计曲线） ──
    RX = 616
    body += eyebrow(RX, 64, "年度数据", T)
    # 贡献卡：h126，label+数字在上半，累计曲线在卡内底部
    body += card(RX, 70, R - RX, 126, T)
    body += mono_text(RX + 18, 94, "贡献", 11, T["muted"], spacing=2)
    body += mono_text(R - 18, 96, str(s["contributions"]["total"]), 22, T["acc"],
                      anchor="end", weight=600)
    cum, run = [], 0
    for wcol in s["contributions"]["weeks"]:
        for d in wcol["days"]:
            run += int(d.get("c", 0))
            cum.append(run)
    body += sparkline(cum, RX + 14, 108, R - RX - 28, 66)
    # 仓库 / Stars 卡：紧凑高度，内容垂直居中
    for i, (label, val) in enumerate([("公开仓库", str(s["publicRepos"])),
                                      ("STARS 数", str(s["stars"]))]):
        cy = 212 + i * 66
        body += card(RX, cy, R - RX, 56, T)
        body += mono_text(RX + 18, cy + 23, label, 11, T["muted"], spacing=2)
        body += mono_text(R - 18, cy + 41, val, 24, T["acc"],
                          anchor="end", weight=600)

    # ── 编程语言宣言 + AI 工具 ──
    body += eyebrow(L, 358, "编程语言", T)
    body += mono_text(L, 394, "VIBE CODING · ALL IN", 26, "url(#sheen)",
                      weight=700, spacing=2)
    body += mono_text(L, 416, "// 不忠于一门语言 —— AI 搭伙，我负责设计与交付。",
                      12, T["muted"])
    x = L
    for tool in AI_TOOLS:
        tw_ = int(len(tool) * 12 * 0.62) + 34
        body += card(x, 430, tw_, 28, T, fill=T["surface2"], rx=14)
        body += mono_text(x + tw_ // 2, 430 + 19, tool, 12, T["acc"],
                          anchor="middle", weight=600, spacing=1)
        x += tw_ + 10

    # ── 贡献热力图 panel + 智能贪吃蛇 ──
    px, py, pw, ph = 24, 470, W - 48, 152
    body += card(px, py, pw, ph, T)
    body += eyebrow(px + 24, py + 28, "贡献热力图 · 近一年", T)
    body += mono_text(px + pw - 24, py + 28, "更新于 %s" % s.get("generatedAt", "")[:10],
                      10, T["faint"], anchor="end", spacing=1)
    cell, step = 11, 14
    weeks = s["contributions"]["weeks"]
    cols = len(weeks)
    levels = {}
    for wi, wcol in enumerate(weeks):
        for di, day in enumerate(wcol["days"]):
            levels[(wi, di)] = max(0, min(4, int(day.get("l", 0))))
    grid_w = cols * step - 3
    x0 = (W - grid_w) // 2
    y0 = py + 40
    path = smart_snake_path(levels, cols, 7)
    dur = round(max(15.0, len(path) * 0.10), 1)   # 每格约 100ms
    cell_t = dur / len(path)
    order = {}
    for idx, p in enumerate(path):
        order.setdefault(p, idx)
    for wi, wcol in enumerate(weeks):
        for di, day in enumerate(wcol["days"]):
            lv = levels[(wi, di)]
            rect = ('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s">'
                    % (x0 + wi * step, y0 + di * step, cell, cell, T["heat"][lv]))
            if lv > 0:
                # 蛇头到达瞬间被吃掉（无过渡，直接跳变成空格色），每圈重演
                t0 = order[(wi, di)] * cell_t
                k1 = t0 / dur
                rect += ('<animate attributeName="fill" values="%s;%s;%s" '
                         'keyTimes="0;%.4f;1" calcMode="discrete" dur="%.1fs" '
                         'repeatCount="indefinite"/>'
                         % (T["heat"][lv], T["heat"][0], T["heat"][0], k1, dur))
            rect += '<title>%s %d</title></rect>' % (day.get("d", ""), day.get("c", 0))
            body += rect
    body += snake_svg(path, x0, y0, step, cell, dur)[0]
    # 图例（上移 5px）
    ly = y0 + 7 * step + 3
    lxv = (W - (5 * 13 + 56)) // 2
    body += mono_text(lxv, ly + 10, "少", 11, T["muted"], spacing=1)
    for i in range(5):
        body += '<rect x="%d" y="%d" width="10" height="10" rx="2" fill="%s"/>' \
                % (lxv + 22 + i * 13, ly, T["heat"][i])
    body += mono_text(lxv + 22 + 5 * 13 + 6, ly + 10, "多", 11, T["muted"], spacing=1)

    # ── 联系方式胶囊（展示用，可点链接在 README 层） ──
    body += eyebrow(L, 646, "联系方式", T)
    bw, bh, bgap = 200, 28, 15
    x = (W - (bw * 4 + bgap * 3)) // 2
    for label in LINKS:
        body += card(x, 656, bw, bh, T, fill=T["surface2"], rx=14)
        body += mono_text(x + bw // 2, 656 + 19, label + "  →", 12, T["ink"],
                          anchor="middle", weight=500)
        x += bw + bgap

    # ── 版权行 ──
    body += mono_text(W // 2, 706,
                      "© 2024-2026 Sam-Dancing™ · All Rights Reserved · Lead Developer: Sam-Dancing",
                      11, T["faint"], anchor="middle")
    return svg_doc(W, H, body, css=CSS, defs=defs)


def main():
    s = load_stats()
    write(os.path.join(ASSETS, "stats", "dashboard-dark.svg"), dashboard(s))
    print("done")


if __name__ == "__main__":
    main()
