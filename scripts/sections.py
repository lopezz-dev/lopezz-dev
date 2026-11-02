"""Genera las secciones del perfil (todas en SVG, oscuras y animadas).

    python3 scripts/sections.py

Escribe en assets/:
  h-cuervos.svg, h-arsenal.svg, h-codigo.svg, h-batallas.svg   cabeceras
  huginn.svg, muninn.svg                                        los dos cuervos
  arsenal.svg                                                   las tecnologias
  codigo.svg                                                    el bushido del oficio
"""
from __future__ import annotations

import html
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ascii_samurai import (BG, FONT, KANJI, SEAL, SERIF, TONES, Piece,  # noqa: E402
                           piece_svg)

ASSETS = Path(__file__).resolve().parent.parent / "assets"
BONE = TONES[3]
DIM = TONES[0]
MID = TONES[1]

BASE_CSS = f"""
text{{font-family:{FONT};fill:{MID};white-space:pre}}
.t1{{fill:{TONES[0]}}}.t2{{fill:{TONES[1]}}}.t3{{fill:{TONES[2]}}}.t4{{fill:{TONES[3]}}}
.kj{{font-family:{KANJI}}}.sf{{font-family:{SERIF};font-style:italic}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
"""


def svg(w: int, h: int, label: str, css: str, body: str, defs: str = "") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{html.escape(label)}">'
            f"<defs><style>{BASE_CSS}{css}</style>"
            '<filter id="soft" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="1.4"/></filter>'
            f"{defs}</defs>"
            f'<rect width="{w}" height="{h}" fill="{BG}"/>{body}</svg>')


def brush(x0: float, x1: float, y: float, thick: float, seed: int) -> str:
    """Trazo de pincel: grueso al entrar, se deshilacha al salir."""
    rnd = random.Random(seed)
    n = 90
    top, bot = [], []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        # presion: entra fuerte, se mantiene y se seca al final
        p = min(1, t * 9) * (1 - t ** 3) * (0.85 + 0.15 * math.sin(t * 17 + seed))
        w = thick * p + rnd.uniform(-0.25, 0.25) * thick * (t > 0.6)
        wob = math.sin(t * 6.0 + seed) * 1.2
        top.append(f"{x:.1f},{y + wob - w / 2:.1f}")
        bot.append(f"{x:.1f},{y + wob + w / 2:.1f}")
    return "M" + " L".join(top) + " L" + " L".join(reversed(bot)) + "Z"


# ---- cabeceras -------------------------------------------------------------
def header(kanji: str, label: str, num: str, seed: int) -> str:
    W, H = 1200, 120
    css = f"""
@keyframes draw{{0%{{transform:scaleX(0)}}100%{{transform:scaleX(1)}}}}
.ink{{fill:{BONE};opacity:.85;transform-origin:40px 0;animation:draw 1.8s cubic-bezier(.7,0,.2,1) .2s both}}
@keyframes rise{{0%{{opacity:0;transform:translateY(8px)}}100%{{opacity:1;transform:translateY(0)}}}}
.ti{{font-size:40px;fill:{BONE};animation:rise 1.2s ease-out .2s both}}
.la{{font-size:13px;fill:{MID};letter-spacing:6px;animation:rise 1.2s ease-out .45s both}}
.sn{{font-size:20px;fill:{BG}}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.75}}}}
.seal{{fill:{SEAL};animation:pulse 3s ease-in-out infinite}}
"""
    body = f"""
<text class="ti kj" x="40" y="60">{kanji}</text>
<text class="la" x="{40 + 44 * len(kanji) + 18}" y="58">{html.escape(label)}</text>
<path class="ink" d="{brush(40, 1110, 92, 5.5, seed)}"/>
<rect class="seal" x="1126" y="72" width="38" height="38" rx="3"/>
<text class="sn kj" x="1145" y="98" text-anchor="middle">{num}</text>
"""
    return svg(W, H, f"{kanji} · {label}", css, body)


# ---- los dos cuervos -------------------------------------------------------
def crow_card(name: str, piece: Piece, eye: tuple[int, int], kanji: str, role: str,
              lore: list[str], project: str, desc: list[str], delay: float) -> str:
    W, H = 600, 520
    art = piece_svg(piece)
    ex, ey = piece.to_canvas(*eye)
    lore_svg = "".join(f'<text class="lore sf" x="40" y="{420 + i * 19}">{html.escape(t)}</text>'
                       for i, t in enumerate(lore))
    desc_svg = "".join(f'<text class="desc" x="40" y="{478 + i * 16}">{html.escape(t)}</text>'
                       for i, t in enumerate(desc))
    kx = 548
    css = f"""
.art text{{font-size:{5.9}px}}
@keyframes wash{{0%{{transform:translateY(-105%)}}100%{{transform:translateY(0)}}}}
.wash{{animation:wash 2.2s cubic-bezier(.6,0,.2,1) {delay}s both}}
@keyframes eye{{0%,100%{{opacity:.95}}45%{{opacity:.3}}50%{{opacity:1}}}}
.eye{{fill:{SEAL};filter:url(#soft);animation:eye 3.4s ease-in-out infinite;animation-delay:{delay}s}}
.kb{{font-size:54px;fill:{SEAL}}}
.nm{{font-size:15px;fill:{BONE};letter-spacing:7px}}
.rl{{font-size:11px;fill:{MID};letter-spacing:4px}}
.lore{{font-size:16px;fill:{TONES[2]}}}
.pj{{font-size:13px;fill:{BONE};letter-spacing:3px}}
.desc{{font-size:12px;fill:{MID}}}
.fr{{fill:none;stroke:{DIM};stroke-width:1}}
"""
    defs = f"""
<linearGradient id="wg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/><stop offset=".88" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>
<mask id="rv" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect class="wash" x="0" y="0" width="{W}" height="{H}" fill="url(#wg)"/></mask>
"""
    corner = 14
    frame = (f'<path class="fr" d="M10,{10 + corner} V10 H{10 + corner} M{W - 10 - corner},10 H{W - 10} V{10 + corner} '
             f'M{W - 10},{H - 10 - corner} V{H - 10} H{W - 10 - corner} M{10 + corner},{H - 10} H10 V{H - 10 - corner}"/>')
    body = f"""
{frame}
<g mask="url(#rv)"><g class="art">{art}</g>
<circle class="eye" cx="{ex:.1f}" cy="{ey:.1f}" r="2.2"/></g>
<text class="kb kj" x="{kx}" y="80" text-anchor="middle">{kanji[0]}</text>
<text class="kb kj" x="{kx}" y="142" text-anchor="middle">{kanji[1]}</text>
<line x1="{kx}" y1="160" x2="{kx}" y2="330" stroke="{SEAL}" stroke-width="1" opacity=".5"/>
<text class="nm" x="40" y="392">{name}</text>
<text class="rl" x="{40 + len(name) * 16 + 14}" y="391">· {html.escape(role)}</text>
{lore_svg}
<text class="pj" x="40" y="{462}">{html.escape(project)}</text>
{desc_svg}
"""
    return svg(W, H, f"{name}, {role}. {' '.join(lore)} {project}: {' '.join(desc)}", css, body, defs)


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
    blade_len = 92                         # caracteres de hoja
    tsuka = "x=x=x=x=x=x=x"
    lines, glints = [], []
    for i, (name, kj) in enumerate(ARSENAL):
        y = top + i * row + 22
        eng = "[ " + " ".join(name) + " ]"
        pre = 6
        rest = blade_len - pre - len(eng)
        blade_a = "=" * pre
        blade_b = "=" * (rest - 2) + "-_"
        cx = x0
        parts = [
            f'<tspan class="t2">({tsuka}</tspan>',
            f'<tspan class="t3">{{@}}</tspan>',
            f'<tspan class="t4">|{blade_a}</tspan>',
            f'<tspan class="eng">{html.escape(eng)}</tspan>',
            f'<tspan class="t4">{blade_b}</tspan>',
            f'<tspan class="t3">\\</tspan>',
        ]
        n = 1 + len(tsuka) + 3 + 1 + len(blade_a) + len(eng) + len(blade_b) + 1
        lines.append(f'<text class="kt" x="{cx}" y="{y}" textLength="{n * cw:.1f}" '
                     f'lengthAdjust="spacing" xml:space="preserve">{"".join(parts)}</text>')
        # hamon: la linea de temple bajo la hoja
        hx0 = cx + (1 + len(tsuka) + 4) * cw
        hx1 = cx + (n - 2) * cw
        wave = " ".join(f"{hx0 + k * 6:.1f},{y + 7 + math.sin(k * .9 + i) * 1.6:.1f}"
                        for k in range(int((hx1 - hx0) / 6)))
        lines.append(f'<polyline class="hamon" points="{wave}"/>')
        lines.append(f'<text class="kjr kj" x="{hx1 + 40:.0f}" y="{y + 1}">{kj}</text>')
        gx = hx0
        glints.append(
            f'<g transform="translate({gx:.1f},{y - 4})"><g class="gl" style="animation-delay:{i * .55:.2f}s">'
            f'<ellipse rx="34" ry="2.6" class="g1"/><ellipse rx="12" ry="1" class="g2"/></g></g>')
        glints_len = hx1 - hx0
    # el soporte: dos postes de madera en ASCII
    rack = []
    for px in (x0 + 40, x0 + 40 + 560):
        for r in range(len(ARSENAL) * 2 + 1):
            yy = top - 6 + r * row / 2
            rack.append(f'<text class="post" x="{px}" y="{yy:.0f}">||</text>')
    css = f"""
.kt{{font-size:{fs}px}}
.eng{{fill:{SEAL};font-weight:bold}}
.hamon{{fill:none;stroke:{DIM};stroke-width:1}}
.kjr{{font-size:22px;fill:{DIM}}}
.post{{font-size:{fs}px;fill:#2a2826}}
@keyframes glint{{0%{{transform:translateX(0);opacity:0}}4%{{opacity:1}}22%{{transform:translateX({glints_len:.0f}px);opacity:1}}24%,100%{{transform:translateX({glints_len:.0f}px);opacity:0}}}}
.gl{{opacity:0;animation:glint 7s cubic-bezier(.5,0,.3,1) infinite}}
.g1{{fill:#fff;opacity:.5;filter:url(#soft)}}.g2{{fill:#fff}}
.lbl{{font-size:11px;fill:{DIM};letter-spacing:5px}}
"""
    body = "".join(rack) + "".join(lines) + "".join(glints)
    label = "Arsenal: " + ", ".join(n.title() for n, _ in ARSENAL)
    return svg(W, H, label, css, body)


# ---- codigo ----------------------------------------------------------------
CODE = [
    ("義", "GI", "RECTITUD", ["Sin atajos."]),
    ("勇", "YŪ", "CORAJE", ["Romper para", "aprender."]),
    ("仁", "JIN", "COMPASIÓN", ["Código que otro", "pueda leer."]),
    ("礼", "REI", "RESPETO", ["Por quien", "vino antes."]),
    ("誠", "MAKOTO", "SINCERIDAD", ["Si falla,", "se dice."]),
    ("名誉", "MEIYO", "HONOR", ["Lo firmo con", "mi nombre."]),
    ("忠義", "CHŪGI", "LEALTAD", ["Al oficio,", "no a la moda."]),
]


def codigo() -> str:
    W, H = 1200, 330
    n = len(CODE)
    colw = (W - 80) / n
    step = 1.3
    cycle = step * n
    on = step / cycle * 100
    cols = []
    for i, (kj, ro, vi, rule) in enumerate(CODE):
        cx = 40 + colw * (i + .5)
        d = i * step
        rule_svg = "".join(f'<text class="ru sf" x="{cx:.1f}" y="{246 + k * 20}" text-anchor="middle">{html.escape(t)}</text>'
                           for k, t in enumerate(rule))
        cols.append(f"""
<g class="col" style="animation-delay:{d:.2f}s">
<text class="kc kj" x="{cx:.1f}" y="120" text-anchor="middle">{kj}</text>
</g>
<g class="sub" style="animation-delay:{d:.2f}s">
<text class="ro" x="{cx:.1f}" y="168" text-anchor="middle">{ro}</text>
<text class="vi" x="{cx:.1f}" y="196" text-anchor="middle">{vi}</text>
<line x1="{cx - 14:.1f}" y1="216" x2="{cx + 14:.1f}" y2="216" class="dash"/>
{rule_svg}
</g>""")
        if i:
            x = 40 + colw * i
            cols.append(f'<line x1="{x:.1f}" y1="60" x2="{x:.1f}" y2="290" stroke="{DIM}" stroke-dasharray="1 6"/>')
    css = f"""
.kc{{font-size:58px;fill:#3a3835}}
.ro{{font-size:11px;fill:{DIM};letter-spacing:4px}}
.vi{{font-size:13px;fill:{MID};letter-spacing:4px}}
.ru{{font-size:16px;fill:{MID}}}
.dash{{stroke:{DIM}}}
@keyframes lit{{0%{{fill:#3a3835}}3%{{fill:{SEAL}}}{on:.1f}%{{fill:{SEAL}}}{on + 6:.1f}%,100%{{fill:#3a3835}}}}
.col text{{animation:lit {cycle:.1f}s ease-out infinite;animation-delay:inherit}}
@keyframes sub{{0%{{opacity:.55}}3%{{opacity:1}}{on:.1f}%{{opacity:1}}{on + 6:.1f}%,100%{{opacity:.55}}}}
.sub{{opacity:.55;animation:sub {cycle:.1f}s ease-out infinite}}
"""
    label = "Código: " + "; ".join(f"{kj} {vi.lower()}: {' '.join(r)}" for kj, _, vi, r in CODE)
    return svg(W, H, label, css, "".join(cols))


def main() -> None:
    out = {
        "h-cuervos.svg": header("二羽の烏", "LOS DOS CUERVOS", "二", 3),
        "h-arsenal.svg": header("刀掛", "ARSENAL", "三", 5),
        "h-codigo.svg": header("武士道", "CÓDIGO", "四", 7),
        "h-batallas.svg": header("戦歴", "BATALLAS", "五", 11),
        "huginn.svg": crow_card(
            "HUGINN",
            Piece("huginn.webp", (20, 600, 750, 1300), rows=60, x=36, y=24, invert=True),
            (470, 686), "思考", "EL PENSAMIENTO",
            ["Levanta el vuelo, recorre el mundo", "y vuelve con lo que ha visto."],
            "HUGINNDB",
            ["Gestor de bases de datos de escritorio, conectado a IA."],
            0,
        ),
        "muninn.svg": crow_card(
            "MUNINN",
            Piece("muninn.webp", (20, 540, 768, 1260), rows=60, x=36, y=24, invert=True),
            (283, 588), "記憶", "LA MEMORIA",
            ["Guarda todo lo vivido", "para que nada se pierda."],
            "MUNINN",
            ["Sistema operativo personal: tareas, notas y automatización."],
            .6,
        ),
        "arsenal.svg": arsenal(),
        "codigo.svg": codigo(),
    }
    for name, content in out.items():
        (ASSETS / name).write_text(content, encoding="utf-8")
        print(f"assets/{name}  ({len(content) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
