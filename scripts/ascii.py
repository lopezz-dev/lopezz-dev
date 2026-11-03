"""Utilidades para convertir ilustraciones de tinta en arte ASCII dentro de un SVG."""
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

# ---- lienzo ---------------------------------------------------------------
W, H = 1200, 600
FS = 5.9                 # tamano de letra del ASCII
CW = FS * 0.6            # ancho de celda
LH = FS                  # alto de celda

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
    direct: bool = False              # True: la imagen ya es luz sobre negro

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
    if p.direct:
        return a / 255
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
