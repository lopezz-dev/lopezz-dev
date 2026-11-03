"""Portada del perfil: una katana en horizontal sobre su katanakake, en ASCII.

    python3 scripts/hero.py

Dibuja la escena (assets/ref/katanakake.png) y la convierte en assets/hero.svg.
Requiere Pillow y numpy.
"""
from __future__ import annotations

import html
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ascii import (BG, CW, FS, KANJI, LH, REF, SEAL, SERIF, TONES, FONT,  # noqa: E402
                   Piece, piece_svg)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "hero.svg"
SCENE = REF / "katanakake.png"

IW, IH = 2400, 720      # tamano de la escena dibujada
SS = 2                  # sobremuestreo al dibujar

# ---- geometria de la katana (coordenadas de la escena) --------------------
KASHIRA, TSUKA_END = 300, 740
TSUBA_A, TSUBA_B = 740, 780
HABAKI_B = 830
TIP = 2160
YC = 322                # altura del eje sobre los soportes
SORI = 26               # curvatura: con el filo hacia arriba, la punta cae
POSTS = (640, 1640)


def axis(x: float) -> float:
    t = max(0.0, (x - HABAKI_B) / (TIP - HABAKI_B))
    return YC + SORI * t * t


def blade_width(x: float) -> float:
    t = max(0.0, (x - HABAKI_B) / (TIP - HABAKI_B))
    return 66 * (1 - 0.25 * t)


def noise(w: int, h: int, scale: float, seed: int) -> np.ndarray:
    rnd = np.random.default_rng(seed)
    g = rnd.random((max(2, int(h / scale) + 2), max(2, int(w / scale) + 2))).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im, dtype=np.float32) / 255


def draw_scene() -> np.ndarray:
    W, H = IW * SS, IH * SS
    img = np.zeros((H, W), np.float32)
    S = SS

    def layer():
        return Image.new("L", (W, H), 0)

    def paste(mask_im: Image.Image, value):
        m = np.asarray(mask_im, dtype=np.float32) / 255
        v = value if np.isscalar(value) else value
        img[:] = img * (1 - m) + m * v

    # --- soporte (katanakake) -------------------------------------------
    grain_v = noise(W, H, 3 * S, 1) * 0.5 + noise(W, H, 14 * S, 2) * 0.5
    grain_v = np.asarray(Image.fromarray((grain_v * 255).astype(np.uint8))
                         .resize((W // 40, H), Image.BILINEAR).resize((W, H), Image.BILINEAR),
                         dtype=np.float32) / 255           # vetas verticales
    grain_h = np.asarray(Image.fromarray((noise(W, H, 3 * S, 3) * 255).astype(np.uint8))
                         .resize((W, H // 60), Image.BILINEAR).resize((W, H), Image.BILINEAR),
                         dtype=np.float32) / 255           # vetas horizontales

    # base: cara superior y frente
    m = layer(); d = ImageDraw.Draw(m)
    d.polygon([(400 * S, 600 * S), (2000 * S, 600 * S), (1980 * S, 616 * S), (420 * S, 616 * S)], fill=255)
    paste(m, 0.62 * (0.75 + 0.35 * grain_h))
    m = layer(); d = ImageDraw.Draw(m)
    d.rectangle([420 * S, 616 * S, 1980 * S, 652 * S], fill=255)
    paste(m, 0.34 * (0.7 + 0.45 * grain_h))
    m = layer(); d = ImageDraw.Draw(m)
    for fx in (470, 1880):
        d.rectangle([fx * S, 652 * S, (fx + 60) * S, 668 * S], fill=255)
    paste(m, 0.22)

    # postes con su cuna en media luna
    for px in POSTS:
        top = axis(px) + 30
        m = layer(); d = ImageDraw.Draw(m)
        d.rectangle([(px - 30) * S, top * S, (px + 30) * S, 600 * S], fill=255)
        paste(m, 0.42 * (0.7 + 0.5 * grain_v))
        # luz en el canto
        m = layer(); d = ImageDraw.Draw(m)
        d.rectangle([(px - 30) * S, top * S, (px - 22) * S, 600 * S], fill=255)
        paste(m, 0.7)
        # cuna
        m = layer(); d = ImageDraw.Draw(m)
        cy = axis(px)
        d.ellipse([(px - 64) * S, (cy - 56) * S, (px + 64) * S, (cy + 60) * S], fill=255)
        d.ellipse([(px - 42) * S, (cy - 70) * S, (px + 42) * S, (cy + 38) * S], fill=0)
        d.rectangle([(px - 70) * S, (cy - 90) * S, (px + 70) * S, (cy - 36) * S], fill=0)
        paste(m, 0.5 * (0.75 + 0.4 * grain_h))
        # pequeno remate
        m = layer(); d = ImageDraw.Draw(m)
        d.rectangle([(px - 34) * S, 588 * S, (px + 34) * S, 600 * S], fill=255)
        paste(m, 0.55)

    # --- tsuka: trenzado ito con diamantes de samegawa ---------------------
    m = layer(); d = ImageDraw.Draw(m)
    d.rounded_rectangle([KASHIRA * S, (YC - 38) * S, TSUKA_END * S, (YC + 38) * S], radius=14 * S, fill=255)
    paste(m, 0.14)
    m = layer(); d = ImageDraw.Draw(m)
    step = 58
    x = KASHIRA + 34
    while x + step / 2 < TSUKA_END - 6:
        cx = x + step / 2
        d.polygon([(cx * S, (YC - 27) * S), ((cx + 22) * S, YC * S), (cx * S, (YC + 27) * S), ((cx - 22) * S, YC * S)], fill=255)
        x += step
    paste(m, 0.82)
    # cruces del ito: lineas que atan cada diamante
    m = layer(); d = ImageDraw.Draw(m)
    x = KASHIRA + 34
    while x < TSUKA_END - 6:
        d.line([(x * S, (YC - 38) * S), ((x + step / 2) * S, (YC + 38) * S)], fill=255, width=4 * S)
        d.line([(x * S, (YC + 38) * S), ((x + step / 2) * S, (YC - 38) * S)], fill=255, width=4 * S)
        x += step
    paste(m, 0.34)
    # menuki
    m = layer(); d = ImageDraw.Draw(m)
    d.ellipse([(500) * S, (YC - 14) * S, (568) * S, (YC + 14) * S], fill=255)
    paste(m, 0.9)
    # kashira y fuchi (metal)
    m = layer(); d = ImageDraw.Draw(m)
    d.rounded_rectangle([(KASHIRA - 24) * S, (YC - 40) * S, (KASHIRA + 24) * S, (YC + 40) * S], radius=16 * S, fill=255)
    d.rectangle([(TSUKA_END - 22) * S, (YC - 40) * S, TSUKA_END * S, (YC + 40) * S], fill=255)
    paste(m, 0.62)
    m = layer(); d = ImageDraw.Draw(m)
    d.line([((KASHIRA - 14) * S, (YC - 28) * S), ((KASHIRA + 16) * S, (YC - 28) * S)], fill=255, width=4 * S)
    paste(m, 1.0)

    # --- tsuba y seppa -----------------------------------------------------
    m = layer(); d = ImageDraw.Draw(m)
    d.rounded_rectangle([TSUBA_A * S, (YC - 96) * S, TSUBA_B * S, (YC + 96) * S], radius=12 * S, fill=255)
    paste(m, 0.46)
    m = layer(); d = ImageDraw.Draw(m)
    d.rounded_rectangle([(TSUBA_A + 4) * S, (YC - 92) * S, (TSUBA_A + 10) * S, (YC + 92) * S], radius=3 * S, fill=255)
    paste(m, 0.85)
    m = layer(); d = ImageDraw.Draw(m)
    for yy in (-70, 56):
        d.ellipse([(TSUBA_A + 12) * S, (YC + yy) * S, (TSUBA_A + 26) * S, (YC + yy + 14) * S], fill=255)
    paste(m, 0.1)

    # --- habaki ------------------------------------------------------------
    m = layer(); d = ImageDraw.Draw(m)
    d.polygon([(TSUBA_B * S, (YC - 38) * S), (HABAKI_B * S, (YC - 34) * S),
               (HABAKI_B * S, (YC + 34) * S), (TSUBA_B * S, (YC + 38) * S)], fill=255)
    paste(m, 0.78)
    m = layer(); d = ImageDraw.Draw(m)
    d.line([((TSUBA_B + 4) * S, (YC - 20) * S), ((HABAKI_B - 4) * S, (YC - 17) * S)], fill=255, width=3 * S)
    paste(m, 1.0)

    # --- hoja: filo arriba, hamon ondulado, shinogi y mune ------------------
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    xs /= S
    ys /= S
    xb = np.clip(xs, HABAKI_B, TIP)
    t = (xb - HABAKI_B) / (TIP - HABAKI_B)
    yc = YC + SORI * t * t
    w = 66 * (1 - 0.25 * t)
    top = yc - w / 2
    bot = yc + w / 2
    # kissaki: el filo baja en curva hasta la punta
    kiss = 120
    k = np.clip((xs - (TIP - kiss)) / kiss, 0, 1)
    top = top + (bot - 3 - top) * (k ** 1.8)
    inside = (xs >= HABAKI_B) & (xs <= TIP) & (ys >= top) & (ys <= bot)
    v = (ys - top) / np.maximum(bot - top, 1e-3)               # 0 filo, 1 mune
    hamon = 0.34 + 0.06 * np.sin(xs / 21) + 0.03 * np.sin(xs / 6.5 + 1) + 0.02 * np.sin(xs / 3.1)
    nie = noise(W, H, 1.5 * S, 9)
    lum = np.where(v < hamon, 0.9 + 0.1 * nie, 0.5 + 0.12 * (v - hamon))
    lum = np.where(np.abs(v - hamon) < 0.035, 1.0, lum)                 # linea del temple
    lum = np.where(np.abs(v - 0.7) < 0.03, 0.82, lum)                   # shinogi
    lum = np.where(v > 0.86, 0.36, lum)                                 # mune
    lum = np.where(v < 0.05, 1.0, lum)                                  # brillo del filo
    yokote = (np.abs(xs - (TIP - kiss)) < 2) & (v < 0.7)
    lum = np.where(yokote, 0.95, lum)
    img = np.where(inside, lum, img)

    # --- salpicaduras de tinta ---------------------------------------------
    pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(pil)
    rnd = random.Random(21)
    for _ in range(170):
        cx = rnd.gauss(1350, 380)
        cy = rnd.gauss(300, 110)
        if 200 < cy < 440 and 260 < cx < 2180:
            continue
        r = abs(rnd.gauss(0, 2.6)) + 0.8
        lv = rnd.randint(60, 150)
        d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=lv)
    pil = pil.filter(ImageFilter.GaussianBlur(0.6 * S)).resize((IW, IH), Image.LANCZOS)
    return np.asarray(pil, dtype=np.float32) / 255


def build() -> str:
    W, H = 1200, 470
    scene = draw_scene()
    Image.fromarray((scene * 255).astype(np.uint8)).save(SCENE)

    crop = (210, 180, 2230, 690)
    rows = int(1110 / ((crop[2] - crop[0]) / (crop[3] - crop[1])) / LH)
    piece = Piece(str(SCENE), crop, rows=rows, x=0, y=110, direct=True)
    aw, ah = piece.size
    piece.x = (W - aw) / 2
    art = piece_svg(piece)

    a = piece.to_canvas(HABAKI_B + 10, YC - 10)
    b = piece.to_canvas(TIP - 40, axis(TIP - 40) - 10)
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    blen = math.hypot(b[0] - a[0], b[1] - a[1])

    poem = [
        "Forjada en el fuego, plegada mil veces.",
        "Silenciosa en su vaina, espera.",
        "Solo el maestro la oye respirar.",
    ]
    poem_svg = "".join(f'<text class="poem" x="48" y="{H - 52 + i * 17}">{html.escape(t)}</text>'
                       for i, t in enumerate(poem))

    css = f"""
text{{font-family:{FONT};font-size:{FS}px;fill:{TONES[0]};white-space:pre}}
.t1{{fill:{TONES[0]}}}.t2{{fill:{TONES[1]}}}.t3{{fill:{TONES[2]}}}.t4{{fill:{TONES[3]}}}
.k{{font-family:{KANJI};font-size:40px;fill:{SEAL}}}
.poem{{font-family:{SERIF};font-style:italic;font-size:13px;fill:{TONES[1]}}}
.seal{{font-family:{KANJI};font-size:24px;fill:{BG}}}
/* un unico gesto: el brillo recorre la hoja de vez en cuando */
@keyframes shine{{0%,70%{{transform:translateX(0);opacity:0}}72%{{opacity:1}}86%{{transform:translateX({blen:.0f}px);opacity:1}}88%,100%{{transform:translateX({blen:.0f}px);opacity:0}}}}
.shine{{opacity:0;animation:shine 10s cubic-bezier(.5,0,.3,1) infinite}}
.g1{{fill:#fff;opacity:.5;filter:url(#soft)}}.g2{{fill:#fff}}
@media (prefers-reduced-motion:reduce){{.shine{{animation:none}}}}
"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Arte ASCII: una katana en horizontal, apoyada en su soporte de madera.">
<defs><style>{css}</style>
<filter id="soft" x="-50%" y="-300%" width="200%" height="700%"><feGaussianBlur stdDeviation="2"/></filter></defs>
<rect width="{W}" height="{H}" fill="{BG}"/>
{art}
<g transform="translate({a[0]:.1f},{a[1]:.1f}) rotate({ang:.2f})"><g class="shine">
<ellipse class="g1" rx="60" ry="3"/><ellipse class="g2" rx="22" ry="1"/></g></g>
<text class="k" x="{W - 64}" y="70" text-anchor="middle">無</text>
<text class="k" x="{W - 64}" y="114" text-anchor="middle">心</text>
{poem_svg}
<rect x="{W - 82}" y="{H - 82}" width="34" height="34" rx="3" fill="{SEAL}"/>
<text class="seal" x="{W - 65}" y="{H - 57}" text-anchor="middle">刀</text>
</svg>
"""


if __name__ == "__main__":
    svg = build()
    OUT.write_text(svg, encoding="utf-8")
    print(f"{OUT}  ({len(svg) / 1024:.0f} KB)")
