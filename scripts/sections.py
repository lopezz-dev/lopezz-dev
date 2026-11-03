"""Genera las secciones del perfil en SVG, oscuras y estaticas.

    python3 scripts/sections.py

Escribe en assets/:
  h-arsenal.svg, h-batallas.svg   cabeceras
  arsenal.svg                     las tecnologias, grabadas en hojas
"""
from __future__ import annotations

import html
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ascii import BG, FONT, KANJI, SEAL, SERIF, TONES  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "assets"
BONE = TONES[3]
LIGHT = TONES[2]
MID = TONES[1]
DIM = TONES[0]

BASE_CSS = f"""
text{{font-family:{FONT};fill:{MID};white-space:pre}}
.kj{{font-family:{KANJI}}}.sf{{font-family:{SERIF};font-style:italic}}
"""


def svg(w: int, h: int, label: str, css: str, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{html.escape(label)}">'
            f"<defs><style>{BASE_CSS}{css}</style></defs>"
            f'<rect width="{w}" height="{h}" fill="{BG}"/>{body}</svg>')


def brush(x0: float, x1: float, y: float, thick: float, seed: int) -> str:
    """Trazo de pincel: entra con fuerza y se seca al final."""
    rnd = random.Random(seed)
    n = 90
    top, bot = [], []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        p = min(1, t * 9) * (1 - t ** 3) * (0.85 + 0.15 * math.sin(t * 17 + seed))
        w = thick * p + rnd.uniform(-0.25, 0.25) * thick * (t > 0.6)
        wob = math.sin(t * 6.0 + seed) * 1.2
        top.append(f"{x:.1f},{y + wob - w / 2:.1f}")
        bot.append(f"{x:.1f},{y + wob + w / 2:.1f}")
    return "M" + " L".join(top) + " L" + " L".join(reversed(bot)) + "Z"


# ---- cabeceras -------------------------------------------------------------
def header(kanji: str, label: str, num: str, seed: int) -> str:
    css = f"""
.ti{{font-size:40px;fill:{BONE}}}
.la{{font-size:13px;fill:{MID};letter-spacing:6px}}
.sn{{font-size:20px;fill:{BG}}}
"""
    body = f"""
<text class="ti kj" x="40" y="60">{kanji}</text>
<text class="la" x="{40 + 44 * len(kanji) + 18}" y="58">{html.escape(label)}</text>
<path d="{brush(40, 1110, 92, 5.5, seed)}" fill="{BONE}" opacity=".85"/>
<rect x="1126" y="72" width="38" height="38" rx="3" fill="{SEAL}"/>
<text class="sn kj" x="1145" y="98" text-anchor="middle">{num}</text>
"""
    return svg(1200, 120, f"{kanji} · {label}", css, body)


# ---- arsenal ---------------------------------------------------------------
ARSENAL = [
    ("RUST", "錆"),
    ("TYPESCRIPT", "型"),
    ("REACT", "反応"),
    ("TAURI", "鳥居"),
    ("SPRING", "春"),
]


def arsenal() -> str:
    W = 1200
    row = 52
    top = 46
    H = top + row * len(ARSENAL) + 30
    fs = 14
    cw = fs * 0.6
    x0 = 150
    blade_len = 92
    tsuka = "x=x=x=x=x=x=x"
    lines = []
    for i, (name, kj) in enumerate(ARSENAL):
        y = top + i * row + 22
        eng = "[ " + " ".join(name) + " ]"
        pre = 6
        rest = blade_len - pre - len(eng)
        blade_a = "=" * pre
        blade_b = "=" * (rest - 2) + "-_"
        parts = [
            f'<tspan fill="{MID}">({tsuka}</tspan>',
            f'<tspan fill="{LIGHT}">{{@}}</tspan>',
            f'<tspan fill="{BONE}">|{blade_a}</tspan>',
            f'<tspan class="eng">{html.escape(eng)}</tspan>',
            f'<tspan fill="{BONE}">{blade_b}</tspan>',
            f'<tspan fill="{LIGHT}">\\</tspan>',
        ]
        n = 1 + len(tsuka) + 3 + 1 + len(blade_a) + len(eng) + len(blade_b) + 1
        lines.append(f'<text class="kt" x="{x0}" y="{y}" textLength="{n * cw:.1f}" '
                     f'lengthAdjust="spacing" xml:space="preserve">{"".join(parts)}</text>')
        hx0 = x0 + (1 + len(tsuka) + 4) * cw
        hx1 = x0 + (n - 2) * cw
        wave = " ".join(f"{hx0 + k * 6:.1f},{y + 7 + math.sin(k * .9 + i) * 1.6:.1f}"
                        for k in range(int((hx1 - hx0) / 6)))
        lines.append(f'<polyline class="hamon" points="{wave}"/>')
        lines.append(f'<text class="kjr kj" x="{hx1 + 40:.0f}" y="{y + 1}">{kj}</text>')
    rack = []
    for px in (x0 + 40, x0 + 600):
        for r in range(len(ARSENAL) * 2 + 1):
            yy = top - 6 + r * row / 2
            rack.append(f'<text class="post" x="{px}" y="{yy:.0f}">||</text>')
    css = f"""
.kt{{font-size:{fs}px}}
.eng{{fill:{SEAL};font-weight:bold}}
.hamon{{fill:none;stroke:{DIM};stroke-width:1}}
.kjr{{font-size:22px;fill:{DIM}}}
.post{{font-size:{fs}px;fill:#2a2826}}
"""
    label = "Arsenal: " + ", ".join(n.title() for n, _ in ARSENAL)
    return svg(W, H, label, css, "".join(rack) + "".join(lines))


def main() -> None:
    out = {
        "h-arsenal.svg": header("刀掛", "ARSENAL", "一", 5),
        "h-batallas.svg": header("戦歴", "BATTLES", "二", 11),
        "arsenal.svg": arsenal(),
    }
    for name, content in out.items():
        (ASSETS / name).write_text(content, encoding="utf-8")
        print(f"assets/{name}  ({len(content) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
