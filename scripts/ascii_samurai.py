"""Genera la portada del perfil: un SVG apaisado en dos columnas de arte ASCII.

    python3 scripts/ascii_samurai.py

Izquierda: el samurai con Huginn y Muninn  (assets/ref/samurai.webp)
Derecha:   la katana entre salpicaduras    (assets/ref/katana-tinta.jpg)
Escribe:   assets/samurai.svg
Requiere Pillow y numpy.
"""
from __future__ import annotations

import html
import math
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "assets" / "ref"
OUT = ROOT / "assets" / "samurai.svg"

# ---- lienzo ---------------------------------------------------------------
W, H = 1200, 600
FS = 5.9                 # tamano de letra del ASCII
CW = FS * 0.6            # ancho de celda
LH = FS                  # alto de celda
D = 12                   # segundos por ciclo de animacion

# ---- paleta (la de la web: tinta, papel, sello) ---------------------------
BG = "#0b0b0b"
TONES = ["#55514b", "#9d968b", "#d9d1c3", "#fbf5ea"]   # de tenue a brillante
SEAL = "#c8372d"
FONT = "'Courier New',Courier,'DejaVu Sans Mono','Liberation Mono',monospace"
SERIF = "'Cormorant Garamond',Garamond,'Times New Roman',serif"
KANJI = "'Yu Mincho','Hiragino Mincho ProN','Noto Serif CJK JP','MS Mincho',serif"

RAMP = " .:-=+*#%@"


@dataclass
class Piece:
    src: str
    crop: tuple[int, int, int, int]   # x0, y0, x1, y1 sobre la ilustracion
    rows: int                         # alto en lineas de texto
    x: float                          # esquina superior izquierda en el lienzo
    y: float
    grow: int = 9                     # cuanto se engorda la tinta para la silueta
    splatter: float = 0.55            # brillo de las salpicaduras fuera de la figura
    invert: bool = False              # True: la tinta se pinta como luz

    @property
    def cols(self) -> int:
        w = self.crop[2] - self.crop[0]
        h = self.crop[3] - self.crop[1]
        return int(round(self.rows * LH * (w / h) / CW))

    @property
    def size(self) -> tuple[float, float]:
        return self.cols * CW, self.rows * LH

    def to_canvas(self, px: float, py: float) -> tuple[float, float]:
        """Pasa un punto de la ilustracion original al lienzo del SVG."""
        w, h = self.size
        sx = w / (self.crop[2] - self.crop[0])
        sy = h / (self.crop[3] - self.crop[1])
        return self.x + (px - self.crop[0]) * sx, self.y + (py - self.crop[1]) * sy


# ---- de ilustracion a luz -------------------------------------------------
def light_map(p: Piece) -> np.ndarray:
    """0 = negro, 1 = papel. La figura conserva sus luces; fuera de ella, solo
    las salpicaduras de tinta, en tenue."""
    im = Image.open(REF / p.src).convert("L").crop(p.crop)
    a = np.asarray(im, dtype=np.float32)
    paper = np.percentile(a, 85)
    dark = np.percentile(a, 0.5)
    ink = np.clip((paper - a) / (paper - dark), 0, 1)
    ink[ink < 0.10] = 0                       # fuera el grano del papel
    if p.invert:
        ink[ink < 0.28] = 0                   # aqui el papel tiene mas grano
        li = Image.fromarray((ink * 255).astype(np.uint8))
        blur = np.asarray(li.filter(ImageFilter.GaussianBlur(6)), dtype=np.float32) / 255
        return np.clip(ink + 1.2 * (ink - blur), 0, 1) ** 0.9

    # silueta: engorda la tinta, rellena desde el borde y lo que no se alcanza es figura
    solid = Image.fromarray(((ink > 0.18) * 255).astype(np.uint8))
    solid = solid.filter(ImageFilter.MaxFilter(p.grow))
    w, h = solid.size
    canvas = Image.new("L", (w + 2, h + 2), 0)
    canvas.paste(solid, (1, 1))
    ImageDraw.floodfill(canvas, (0, 0), 128)
    fig = np.asarray(canvas, dtype=np.uint8)[1:-1, 1:-1] != 128
    # las motas sueltas no son figura
    fig_im = Image.fromarray((fig * 255).astype(np.uint8))
    fig_im = fig_im.filter(ImageFilter.MinFilter(max(3, p.grow - 4)))
    fig_im = fig_im.filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MaxFilter(9))
    fig = np.asarray(fig_im.filter(ImageFilter.GaussianBlur(2)), dtype=np.float32) / 255

    light = (1 - ink) * fig
    light = np.asarray(Image.fromarray((light * 255).astype(np.uint8))
                       .filter(ImageFilter.MedianFilter(3))
                       .filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255
    li = Image.fromarray((light * 255).astype(np.uint8))
    blur = np.asarray(li.filter(ImageFilter.GaussianBlur(7)), dtype=np.float32) / 255
    light = np.clip(light + 1.6 * (light - blur), 0, 1) * (fig > 0.05)

    # salpicaduras: la tinta fuera de la figura se pinta tenue
    light = np.maximum(light, ink * (fig < 0.05) * p.splatter)
    return light


def resize(a: np.ndarray, w: int, h: int) -> np.ndarray:
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.resize((w, h), Image.LANCZOS), dtype=np.float32) / 255


def conv(a, k):
    p = np.pad(a, 1, mode="edge")
    out = np.zeros_like(a)
    for dy in range(3):
        for dx in range(3):
            out += k[dy, dx] * p[dy:dy + a.shape[0], dx:dx + a.shape[1]]
    return out


def to_ascii(p: Piece):
    light = light_map(p)
    rows, cols, k = p.rows, p.cols, 6
    hi = resize(light, cols * k, rows * k)
    lo = hi.reshape(rows, k, cols, k).mean(axis=(1, 3))
    peak = hi.reshape(rows, k, cols, k).max(axis=(1, 3))

    sx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float32)
    gx, gy = conv(hi, sx), conv(hi, sx.T)
    jxx = (gx * gx).reshape(rows, k, cols, k).sum(axis=(1, 3))
    jyy = (gy * gy).reshape(rows, k, cols, k).sum(axis=(1, 3))
    jxy = (gx * gy).reshape(rows, k, cols, k).sum(axis=(1, 3))
    mag = np.sqrt(jxx + jyy)
    coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-6)
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy)        # direccion del gradiente
    edge_dir = (np.degrees(theta) + 90) % 180            # direccion del trazo
    mthr = np.percentile(mag[mag > 0], 82)

    grid, tone = [], []
    for r in range(rows):
        line, tl = [], []
        for c in range(cols):
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
    return grid, tone


def line_svg(chars: str, tones, y: float, width: float, colored=True) -> str:
    if not chars.strip():
        return ""
    if not colored:
        body = html.escape(chars)
    else:
        parts, cur, buf = [], None, []

        def flush():
            if buf:
                s = html.escape("".join(buf))
                parts.append(f'<tspan class="t{cur}">{s}</tspan>' if cur else s)

        for ch, t in zip(chars, tones):
            t = t if ch != " " else cur      # los espacios no cortan el tramo
            if t != cur:
                flush()
                buf, cur = [], t
            buf.append(ch)
        flush()
        body = "".join(parts)
    return (f'<text y="{y:.2f}" textLength="{width:.1f}" lengthAdjust="spacing" '
            f'xml:space="preserve">{body}</text>')


def piece_svg(p: Piece, colored=True) -> str:
    grid, tone = to_ascii(p)
    w, _ = p.size
    lines = (line_svg(g, t, (r + 0.85) * LH, w, colored) for r, (g, t) in enumerate(zip(grid, tone)))
    return f'<g transform="translate({p.x:.2f},{p.y:.2f})">' + "".join(l for l in lines if l) + "</g>"


# ---- composicion ----------------------------------------------------------
def build() -> str:
    samurai = Piece("samurai.webp", (150, 470, 690, 1140), rows=94, x=0, y=32)
    katana = Piece("katana-tinta.jpg", (150, 220, 880, 1024), rows=94, x=0, y=32,
                   invert=True)
    sw, _ = samurai.size
    kw, _ = katana.size
    samurai.x = 70
    katana.x = 640
    # se recalculan con la x definitiva
    sam_svg = piece_svg(samurai)
    kat_svg = piece_svg(katana)

    eyes = [samurai.to_canvas(229, 548), samurai.to_canvas(512, 508)]
    blade_a = katana.to_canvas(470, 590)        # nacimiento de la hoja (habaki)
    blade_b = katana.to_canvas(720, 1024)       # hoja saliendo del encuadre

    # el tajo: diagonal que cruza las dos columnas
    cut_a = (30, H - 70)
    cut_b = (W - 30, 70)
    dx, dy = cut_b[0] - cut_a[0], cut_b[1] - cut_a[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy * 3000, ux * 3000
    p1 = (cut_a[0] - ux * 3000, cut_a[1] - uy * 3000)
    p2 = (cut_b[0] + ux * 3000, cut_b[1] + uy * 3000)

    def half(sign):
        return (f"M{p1[0]:.0f},{p1[1]:.0f} L{p2[0]:.0f},{p2[1]:.0f} "
                f"L{p2[0] + sign * nx:.0f},{p2[1] + sign * ny:.0f} "
                f"L{p1[0] + sign * nx:.0f},{p1[1] + sign * ny:.0f}Z")

    # ceniza
    rnd = random.Random(7)
    embers = []
    for i in range(34):
        x = rnd.uniform(20, W - 20)
        y0 = rnd.uniform(H * 0.4, H)
        d = rnd.uniform(8, 15)
        delay = -rnd.uniform(0, d)
        ch = rnd.choice(["'", ".", "`", ","])
        cls = "em r" if i % 3 == 0 else "em"
        embers.append(f'<text class="{cls}" x="{x:.1f}" y="{y0:.1f}" '
                      f'style="animation-duration:{d:.1f}s;animation-delay:{delay:.1f}s">{ch}</text>')

    # el reflejo recorre la hoja a lo largo de su eje
    bx, by = blade_b[0] - blade_a[0], blade_b[1] - blade_a[1]
    bang = math.degrees(math.atan2(by, bx))
    blen = math.hypot(bx, by)

    poem = [
        "Forjada en el fuego, plegada mil veces.",
        "Silenciosa en su vaina, espera.",
        "Solo el maestro la oye respirar.",
    ]
    poem_svg = "".join(
        f'<text class="poem" x="660" y="{H - 92 + i * 17}">{html.escape(t)}</text>'
        for i, t in enumerate(poem)
    )

    col_div = 600
    seal_x, seal_y = W - 86, H - 112

    css = f"""
text{{font-family:{FONT};font-size:{FS}px;fill:{TONES[0]};white-space:pre}}
.t1{{fill:{TONES[0]}}}.t2{{fill:{TONES[1]}}}.t3{{fill:{TONES[2]}}}.t4{{fill:{TONES[3]}}}
.r{{fill:{SEAL}}}
@keyframes wash{{0%{{transform:translateY(-110%)}}14%,100%{{transform:translateY(0)}}}}
.wash{{animation:wash {D}s cubic-bezier(.6,0,.2,1) infinite}}
@keyframes washx{{0%,4%{{transform:translateX(-110%)}}20%,100%{{transform:translateX(0)}}}}
.washx{{animation:washx {D}s cubic-bezier(.6,0,.2,1) infinite}}
@keyframes breathe{{0%,100%{{opacity:1}}50%{{opacity:.86}}}}
.art{{animation:breathe 4s ease-in-out infinite}}
/* reflejo en la hoja */
@keyframes shine{{0%,31%{{transform:translateX(-40px)}}43%,100%{{transform:translateX({blen:.0f}px)}}}}
.shine{{animation:shine {D}s cubic-bezier(.5,0,.3,1) infinite,shinefade {D}s linear infinite}}
.glint{{fill:#fff;opacity:.55;filter:url(#blur2)}}.glint.core{{opacity:.95;filter:none}}
@keyframes shinefade{{0%,30%{{opacity:0}}32%,42%{{opacity:1}}44%,100%{{opacity:0}}}}
.shine{{opacity:0}}
/* el tajo */
@keyframes cut{{0%,55%{{stroke-dashoffset:1700;opacity:0}}55.5%{{opacity:1}}58%{{stroke-dashoffset:0;opacity:1}}75%{{opacity:.9;stroke-width:1.2}}86%,100%{{stroke-dashoffset:0;opacity:0}}}}
.cut{{fill:none;stroke:{SEAL};stroke-width:2.4;stroke-linecap:round;stroke-dasharray:1700;animation:cut {D}s cubic-bezier(.2,.9,.3,1) infinite}}
@keyframes glow{{0%,55%{{opacity:0}}57%{{opacity:.5}}70%,100%{{opacity:0}}}}
.cutglow{{fill:none;stroke:{SEAL};stroke-width:14;opacity:0;filter:url(#blur);animation:glow {D}s ease-out infinite}}
@keyframes up{{0%,57%{{transform:translate(0,0)}}60%,80%{{transform:translate({-ux * 12 - 4:.1f}px,{-uy * 12 - 6:.1f}px)}}88%,100%{{transform:translate(0,0)}}}}
@keyframes lo{{0%,57%{{transform:translate(0,0)}}60%,80%{{transform:translate({ux * 12 + 4:.1f}px,{uy * 12 + 6:.1f}px)}}88%,100%{{transform:translate(0,0)}}}}
.hu{{animation:up {D}s cubic-bezier(.2,.9,.3,1) infinite}}
.hl{{animation:lo {D}s cubic-bezier(.2,.9,.3,1) infinite}}
@keyframes flash{{0%,55.5%{{opacity:0}}56%{{opacity:.2}}60%,100%{{opacity:0}}}}
.flash{{fill:#fff;opacity:0;animation:flash {D}s linear infinite}}
@keyframes shake{{0%,55.5%,62%,100%{{transform:translate(0,0)}}56.5%{{transform:translate(-5px,2px)}}58%{{transform:translate(4px,-2px)}}59.5%{{transform:translate(-2px,1px)}}}}
.stage{{animation:shake {D}s linear infinite}}
/* ojos de Huginn y Muninn */
@keyframes eye{{0%,100%{{opacity:.95}}45%{{opacity:.35}}50%{{opacity:1}}}}
.eye{{fill:{SEAL};filter:url(#blur2);animation:eye 3.3s ease-in-out infinite}}
.eye2{{animation-duration:4.1s;animation-delay:-1.2s}}
/* ceniza */
@keyframes rise{{0%{{transform:translate(0,0);opacity:0}}12%{{opacity:.9}}100%{{transform:translate(-40px,-280px);opacity:0}}}}
.em{{font-size:11px;fill:{TONES[1]};animation:rise 10s linear infinite}}
.em.r{{fill:{SEAL}}}
/* textos */
@keyframes appear{{0%,14%{{opacity:0}}24%,100%{{opacity:1}}}}
.late{{opacity:0;animation:appear {D}s ease-out infinite}}
.k{{font-family:{KANJI};font-size:46px;fill:{SEAL}}}
.cap{{font-size:10px;fill:{TONES[1]};letter-spacing:4px}}
.poem{{font-family:{SERIF};font-style:italic;font-size:13px;fill:{TONES[1]};letter-spacing:.5px}}
.seal{{font-family:{KANJI};font-size:26px;fill:{BG}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.cut,.cutglow,.flash,.shine{{opacity:0}}.late{{opacity:1}}}}
"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Dos columnas en arte ASCII: a la izquierda un samurai con sombrero de paja y los cuervos Huginn y Muninn en los hombros; a la derecha una katana entre salpicaduras de tinta. Un tajo rojo lo atraviesa todo.">
<defs>
<style>{css}</style>
<filter id="blur" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="4"/></filter>
<filter id="blur2" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="1.2"/></filter>
<clipPath id="cu"><path d="{half(-1)}"/></clipPath>
<clipPath id="cl"><path d="{half(1)}"/></clipPath>
<linearGradient id="wg" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#fff"/><stop offset=".85" stop-color="#fff"/><stop offset="1" stop-color="#000"/>
</linearGradient>
<linearGradient id="wgx" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="#fff"/><stop offset=".85" stop-color="#fff"/><stop offset="1" stop-color="#000"/>
</linearGradient>
<linearGradient id="sg" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="#000"/><stop offset=".5" stop-color="#fff"/><stop offset="1" stop-color="#000"/>
</linearGradient>
<mask id="reveal" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">
<rect class="wash" x="0" y="0" width="{col_div}" height="{H * 1.15:.0f}" fill="url(#wg)"/>
<rect class="washx" x="{col_div}" y="0" width="{(W - col_div) * 1.15:.0f}" height="{H}" fill="url(#wgx)"/>
</mask>
<g id="art" class="art">
{sam_svg}
{kat_svg}
</g>
</defs>
<rect width="{W}" height="{H}" fill="{BG}"/>
<g class="stage">
<g mask="url(#reveal)">
<g class="hu"><use xlink:href="#art" href="#art" clip-path="url(#cu)"/></g>
<g class="hl"><use xlink:href="#art" href="#art" clip-path="url(#cl)"/></g>
<g transform="translate({blade_a[0]:.1f},{blade_a[1]:.1f}) rotate({bang:.2f})">
<g class="shine"><ellipse class="glint" cx="0" cy="0" rx="46" ry="3.2"/><ellipse class="glint core" cx="0" cy="0" rx="18" ry="1.2"/></g>
</g>
<circle class="eye" cx="{eyes[0][0]:.1f}" cy="{eyes[0][1]:.1f}" r="2"/>
<circle class="eye eye2" cx="{eyes[1][0]:.1f}" cy="{eyes[1][1]:.1f}" r="2"/>
</g>
{''.join(embers)}
<line class="cutglow" x1="{cut_a[0]}" y1="{cut_a[1]}" x2="{cut_b[0]}" y2="{cut_b[1]}"/>
<line class="cut" x1="{cut_a[0]}" y1="{cut_a[1]}" x2="{cut_b[0]}" y2="{cut_b[1]}"/>
</g>
<rect class="flash" width="{W}" height="{H}"/>
<line x1="{col_div}" y1="60" x2="{col_div}" y2="{H - 60}" stroke="{TONES[0]}" stroke-width="1" stroke-dasharray="1 7"/>
<g class="late">
<text class="cap" x="40" y="44">HUGINN · 思考</text>
<text class="cap" x="{col_div - 40}" y="44" text-anchor="end">記憶 · MUNINN</text>
<text class="k" x="{W - 70}" y="96" text-anchor="middle">無</text>
<text class="k" x="{W - 70}" y="150" text-anchor="middle">心</text>
<line x1="{W - 70}" y1="172" x2="{W - 70}" y2="300" stroke="{SEAL}" stroke-width="1" opacity=".6"/>
{poem_svg}
<rect x="{seal_x}" y="{seal_y}" width="34" height="34" rx="3" fill="{SEAL}"/>
<text class="seal" x="{seal_x + 17}" y="{seal_y + 27}" text-anchor="middle">刀</text>
</g>
</svg>
"""


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    svg = build()
    OUT.write_text(svg, encoding="utf-8")
    print(f"{OUT}  ({len(svg) / 1024:.0f} KB)")
