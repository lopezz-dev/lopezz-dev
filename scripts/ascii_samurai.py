"""Convierte la ilustracion del samurai en un SVG animado de ASCII.

    python3 scripts/ascii_samurai.py

Lee  assets/ref/samurai.webp  y escribe  assets/samurai.svg
Requiere Pillow y numpy.
"""
from __future__ import annotations

import html
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "ref" / "samurai.webp"
OUT = ROOT / "assets" / "samurai.svg"

# ---- encuadre y rejilla -------------------------------------------------
CROP = (150, 470, 690, 1190)      # x0, y0, x1, y1 sobre la ilustracion
MASK_GROW = 9
COLS = 164                         # caracteres por linea
FS = 5.9                           # tamano de letra en el SVG
CW = FS * 0.6                      # ancho de celda
LH = FS                            # alto de celda (interlineado)

# ---- paleta (la de la web: tinta, papel, sello) -------------------------
BG = "#0b0b0b"
TONES = ["#55514b", "#9d968b", "#d9d1c3", "#fbf5ea"]   # de tenue a brillante
SEAL = "#c8372d"

# rampa de densidad: de vacio a lleno
RAMP = " .:-=+*#%@"


def load_ink() -> np.ndarray:
    """Devuelve la luz de la figura (0 = negro, 1 = papel) con el fondo a 0."""
    im = Image.open(SRC).convert("L").crop(CROP)
    a = np.asarray(im, dtype=np.float32)
    paper = np.percentile(a, 85)
    dark = np.percentile(a, 0.5)
    ink = np.clip((paper - a) / (paper - dark), 0, 1)
    ink[ink < 0.10] = 0                       # fuera el grano del papel

    # silueta: engorda la tinta, rellena desde los bordes y lo que queda es figura
    solid = Image.fromarray(((ink > 0.18) * 255).astype(np.uint8))
    solid = solid.filter(ImageFilter.MaxFilter(MASK_GROW)).convert("L")
    w, h = solid.size
    canvas = Image.new("L", (w + 2, h + 2), 0)
    canvas.paste(solid, (1, 1))
    ImageDraw.floodfill(canvas, (0, 0), 128)
    fig = np.asarray(canvas, dtype=np.uint8)[1:-1, 1:-1] != 128
    fig_im = Image.fromarray((fig * 255).astype(np.uint8))
    fig_im = fig_im.filter(ImageFilter.MinFilter(MASK_GROW - 4))
    fig = np.asarray(fig_im.filter(ImageFilter.GaussianBlur(2)), dtype=np.float32) / 255

    light = (1 - ink) * fig
    # suaviza el rayado del dibujo para que cada zona tenga un tono limpio
    light = np.asarray(Image.fromarray((light * 255).astype(np.uint8))
                       .filter(ImageFilter.MedianFilter(3))
                       .filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255
    # realza el trazo
    li = Image.fromarray((light * 255).astype(np.uint8))
    blur = np.asarray(li.filter(ImageFilter.GaussianBlur(7)), dtype=np.float32) / 255
    light = np.clip(light + 1.6 * (light - blur), 0, 1) * (fig > 0.05)
    return light


def resize(a: np.ndarray, w: int, h: int) -> np.ndarray:
    im = Image.fromarray((a * 255).astype(np.uint8))
    return np.asarray(im.resize((w, h), Image.LANCZOS), dtype=np.float32) / 255


def conv(a, k):
    p = np.pad(a, 1, mode="edge")
    out = np.zeros_like(a)
    for dy in range(3):
        for dx in range(3):
            out += k[dy, dx] * p[dy:dy + a.shape[0], dx:dx + a.shape[1]]
    return out


def to_ascii(ink: np.ndarray):
    h, w = ink.shape
    rows = int(round(COLS * (h / w) * (CW / LH)))
    k = 6
    hi = resize(ink, COLS * k, rows * k)
    lo = hi.reshape(rows, k, COLS, k).mean(axis=(1, 3))
    peak = hi.reshape(rows, k, COLS, k).max(axis=(1, 3))

    sx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float32)
    gx, gy = conv(hi, sx), conv(hi, sx.T)
    jxx = (gx * gx).reshape(rows, k, COLS, k).sum(axis=(1, 3))
    jyy = (gy * gy).reshape(rows, k, COLS, k).sum(axis=(1, 3))
    jxy = (gx * gy).reshape(rows, k, COLS, k).sum(axis=(1, 3))
    mag = np.sqrt(jxx + jyy)
    coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-6)
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy)       # direccion del gradiente
    edge_dir = (np.degrees(theta) + 90) % 180           # direccion del trazo

    mthr = np.percentile(mag[mag > 0], 82)
    grid, tone = [], []
    for r in range(rows):
        line, tl = [], []
        for c in range(COLS):
            v = lo[r, c]
            if peak[r, c] < 0.2 or v < 0.025:
                line.append(" ")
                tl.append(0)
                continue
            if mag[r, c] > mthr and coh[r, c] > 0.7 and 0.08 < v < 0.75:
                a = edge_dir[r, c]
                if a < 22.5 or a >= 157.5:
                    ch = "_" if v < 0.3 else "="
                elif a < 67.5:
                    ch = "\\"
                elif a < 112.5:
                    ch = "|"
                else:
                    ch = "/"
                b = max(v, 0.45)
            else:
                vv = v ** 0.65
                ch = RAMP[min(len(RAMP) - 1, max(1, int(vv * (len(RAMP) - 1) + 0.5)))]
                b = v
            line.append(ch)
            tl.append(1 + min(3, int((b ** 0.7) * 4.2)))
        grid.append("".join(line))
        tone.append(tl)
    return grid, tone, rows


def line_svg(chars: str, tones, y: float, width: float) -> str:
    parts, cur, buf = [], None, []

    def flush():
        if not buf:
            return
        s = html.escape("".join(buf))
        if cur:
            parts.append(f'<tspan class="t{cur}">{s}</tspan>')
        else:
            parts.append(s)

    for ch, t in zip(chars, tones):
        t = t if ch != " " else cur      # los espacios no cortan el tramo
        if t != cur:
            flush()
            buf, cur = [], t
        buf.append(ch)
    flush()
    body = "".join(parts).rstrip()
    if not body.strip():
        return ""
    return (f'<text y="{y:.2f}" textLength="{width:.1f}" lengthAdjust="spacing" '
            f'xml:space="preserve">{body}</text>')


def build() -> str:
    ink = load_ink()
    grid, tone, rows = to_ascii(ink)
    art_w, art_h = COLS * CW, rows * LH

    W = 900
    H = math.ceil(art_h + 80)
    ax = (W - art_w) / 2
    ay = 30

    # Rellena cada linea hasta el ancho completo para que textLength cuadre
    lines = []
    for r in range(rows):
        lines.append(line_svg(grid[r], tone[r], (r + 0.85) * LH, art_w))
    art = "\n".join(l for l in lines if l)

    # posicion de los ojos de los cuervos (coordenadas de la ilustracion)
    sx = art_w / (CROP[2] - CROP[0])
    sy = art_h / (CROP[3] - CROP[1])

    def pt(x, y):
        return ax + (x - CROP[0]) * sx, ay + (y - CROP[1]) * sy

    eyes = [pt(229, 548), pt(512, 508)]

    # el tajo: diagonal que cruza al samurai
    cut_a = (ax - 40, ay + art_h * 0.78)
    cut_b = (ax + art_w + 40, ay + art_h * 0.22)

    rnd = random.Random(7)
    embers = []
    for i in range(26):
        x = rnd.uniform(ax - 60, ax + art_w + 60)
        y0 = rnd.uniform(ay + art_h * 0.35, ay + art_h)
        d = rnd.uniform(7, 14)
        delay = -rnd.uniform(0, d)
        ch = rnd.choice(["'", ".", "`", ","])
        cls = "em r" if i % 3 == 0 else "em"
        embers.append(
            f'<text class="{cls}" x="{x:.1f}" y="{y0:.1f}" '
            f'style="animation-duration:{d:.1f}s;animation-delay:{delay:.1f}s">{ch}</text>'
        )

    # semiplanos para partir la figura por el tajo
    dx, dy = cut_b[0] - cut_a[0], cut_b[1] - cut_a[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * 2000, dx / L * 2000   # normal (hacia abajo-derecha)
    ext = 2000 / L
    p1 = (cut_a[0] - dx * ext, cut_a[1] - dy * ext)
    p2 = (cut_b[0] + dx * ext, cut_b[1] + dy * ext)
    upper = f"M{p1[0]:.0f},{p1[1]:.0f} L{p2[0]:.0f},{p2[1]:.0f} L{p2[0]-nx:.0f},{p2[1]-ny:.0f} L{p1[0]-nx:.0f},{p1[1]-ny:.0f}Z"
    lower = f"M{p1[0]:.0f},{p1[1]:.0f} L{p2[0]:.0f},{p2[1]:.0f} L{p2[0]+nx:.0f},{p2[1]+ny:.0f} L{p1[0]+nx:.0f},{p1[1]+ny:.0f}Z"
    ux, uy = dx / L, dy / L   # direccion del corte

    D = 12  # duracion del ciclo
    css = f"""
text{{font-family:'Courier New',Courier,'DejaVu Sans Mono','Liberation Mono',monospace;font-size:{FS}px;fill:{TONES[0]};white-space:pre}}
.t1{{fill:{TONES[0]}}}.t2{{fill:{TONES[1]}}}.t3{{fill:{TONES[2]}}}.t4{{fill:{TONES[3]}}}
.r{{fill:{SEAL}}}
/* revelado: la tinta baja como un pincel */
@keyframes wash{{0%{{transform:translateY(-110%)}}14%,100%{{transform:translateY(0)}}}}
.wash{{animation:wash {D}s cubic-bezier(.6,0,.2,1) infinite}}
/* respiracion de la tinta */
@keyframes breathe{{0%,100%{{opacity:1}}50%{{opacity:.86}}}}
.art{{animation:breathe 4s ease-in-out infinite}}
/* el tajo */
@keyframes cut{{0%,55%{{stroke-dashoffset:1400;opacity:0}}55.5%{{opacity:1}}58%{{stroke-dashoffset:0;opacity:1}}75%{{opacity:.9;stroke-width:1.2}}86%,100%{{stroke-dashoffset:0;opacity:0}}}}
.cut{{fill:none;stroke:{SEAL};stroke-width:2.4;stroke-linecap:round;stroke-dasharray:1400;animation:cut {D}s cubic-bezier(.2,.9,.3,1) infinite}}
@keyframes glow{{0%,55%{{opacity:0}}57%{{opacity:.5}}70%,100%{{opacity:0}}}}
.cutglow{{fill:none;stroke:{SEAL};stroke-width:14;opacity:0;filter:url(#blur);animation:glow {D}s ease-out infinite}}
/* las dos mitades se separan y vuelven a cerrarse */
@keyframes up{{0%,57%{{transform:translate(0,0)}}60%,80%{{transform:translate({-ux*10 - 3:.1f}px,{-uy*10 - 4:.1f}px)}}88%,100%{{transform:translate(0,0)}}}}
@keyframes lo{{0%,57%{{transform:translate(0,0)}}60%,80%{{transform:translate({ux*10 + 3:.1f}px,{uy*10 + 4:.1f}px)}}88%,100%{{transform:translate(0,0)}}}}
.hu{{animation:up {D}s cubic-bezier(.2,.9,.3,1) infinite}}
.hl{{animation:lo {D}s cubic-bezier(.2,.9,.3,1) infinite}}
/* destello */
@keyframes flash{{0%,55.5%{{opacity:0}}56%{{opacity:.22}}60%,100%{{opacity:0}}}}
.flash{{fill:#fff;opacity:0;animation:flash {D}s linear infinite}}
/* temblor */
@keyframes shake{{0%,55.5%,62%,100%{{transform:translate(0,0)}}56.5%{{transform:translate(-5px,2px)}}58%{{transform:translate(4px,-2px)}}59.5%{{transform:translate(-2px,1px)}}}}
.stage{{animation:shake {D}s linear infinite}}
/* ojos de Huginn y Muninn */
@keyframes eye{{0%,100%{{opacity:.95}}45%{{opacity:.35}}50%{{opacity:1}}}}
.eye{{fill:{SEAL};filter:url(#blur2);animation:eye 3.3s ease-in-out infinite}}
.eye2{{animation-duration:4.1s;animation-delay:-1.2s}}
/* ceniza */
@keyframes rise{{0%{{transform:translate(0,0);opacity:0}}12%{{opacity:.9}}100%{{transform:translate(-40px,-260px);opacity:0}}}}
.em{{font-size:11px;fill:{TONES[1]};animation:rise 10s linear infinite}}
.em.r{{fill:{SEAL}}}
/* sello */
.k{{font-family:'Yu Mincho','Hiragino Mincho ProN','Noto Serif CJK JP','MS Mincho',serif;font-size:30px;fill:{SEAL}}}
.cap{{font-size:11px;fill:{TONES[1]};letter-spacing:4px}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.cut,.cutglow,.flash{{opacity:0}}}}
"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Un samurai en arte ASCII con un sombrero de paja y dos cuervos, Huginn y Muninn, en los hombros. Un tajo rojo lo atraviesa.">
<defs>
<style>{css}</style>
<filter id="blur" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="4"/></filter>
<filter id="blur2" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="1.2"/></filter>
<clipPath id="cu"><path d="{upper}"/></clipPath>
<clipPath id="cl"><path d="{lower}"/></clipPath>
<linearGradient id="wg" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#fff"/><stop offset=".85" stop-color="#fff"/><stop offset="1" stop-color="#000"/>
</linearGradient>
<mask id="reveal" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">
<rect class="wash" x="0" y="0" width="{W}" height="{H * 1.15:.0f}" fill="url(#wg)"/>
</mask>
<g id="art" class="art" transform="translate({ax:.2f},{ay:.2f})">
{art}
</g>
</defs>
<rect width="{W}" height="{H}" fill="{BG}"/>
<g class="stage">
<g mask="url(#reveal)">
<g class="hu"><use xlink:href="#art" href="#art" clip-path="url(#cu)"/></g>
<g class="hl"><use xlink:href="#art" href="#art" clip-path="url(#cl)"/></g>
<circle class="eye" cx="{eyes[0][0]:.1f}" cy="{eyes[0][1]:.1f}" r="2.2"/>
<circle class="eye eye2" cx="{eyes[1][0]:.1f}" cy="{eyes[1][1]:.1f}" r="2.2"/>
</g>
{''.join(embers)}
<line class="cutglow" x1="{cut_a[0]:.0f}" y1="{cut_a[1]:.0f}" x2="{cut_b[0]:.0f}" y2="{cut_b[1]:.0f}"/>
<line class="cut" x1="{cut_a[0]:.0f}" y1="{cut_a[1]:.0f}" x2="{cut_b[0]:.0f}" y2="{cut_b[1]:.0f}"/>
</g>
<rect class="flash" width="{W}" height="{H}"/>
<text class="k" x="{W - 70}" y="80" text-anchor="middle">無</text>
<text class="k" x="{W - 70}" y="116" text-anchor="middle">心</text>
<text class="cap" x="70" y="{H - 30}">HUGINN · 思考</text>
<text class="cap" x="{W - 70}" y="{H - 30}" text-anchor="end">記憶 · MUNINN</text>
</svg>
"""


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    svg = build()
    OUT.write_text(svg, encoding="utf-8")
    print(f"{OUT}  ({len(svg) / 1024:.0f} KB)")
