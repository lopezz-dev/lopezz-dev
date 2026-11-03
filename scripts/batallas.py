"""Dibuja el registro de batallas (contribuciones del ultimo ano) en ASCII.

    python3 scripts/batallas.py contrib.json batallas.svg

contrib.json es la respuesta de la API GraphQL de GitHub:
  user.contributionsCollection.contributionCalendar{totalContributions,weeks{contributionDays{date,contributionCount}}}
Sin argumentos genera datos inventados para previsualizar.
Solo usa la biblioteca estandar: lo ejecuta el workflow .github/workflows/batallas.yml.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import random
import sys
from pathlib import Path

BG = "#0b0b0b"
FAINT = "#262422"
DIM = "#55514b"
MID = "#9d968b"
LIGHT = "#d9d1c3"
BONE = "#fbf5ea"
SEAL = "#c8372d"
FONT = "'Courier New',Courier,'DejaVu Sans Mono','Liberation Mono',monospace"
KANJI = "'Yu Mincho','Hiragino Mincho ProN','Noto Serif CJK JP','MS Mincho',serif"

MONTHS = ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
DAYS = {1: "月", 3: "水", 5: "金"}   # filas lunes, miercoles, viernes (la fila 0 es domingo)


def load(path: str | None):
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        weeks = [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in cal["weeks"]]
        return cal["totalContributions"], weeks
    rnd = random.Random(4)
    end = dt.date.today()
    start = end - dt.timedelta(days=364 + (end.weekday() + 1) % 7)
    weeks, week, total = [], [], 0
    d = start
    while d <= end:
        burst = 1 if rnd.random() < .35 else 0
        c = rnd.choice([0, 0, 0, 1, 2, 3, 5, 8, 13]) * burst + (rnd.random() < .2) * rnd.randint(1, 4)
        week.append((d.isoformat(), c))
        total += c
        if len(week) == 7:
            weeks.append(week)
            week = []
        d += dt.timedelta(days=1)
    if week:
        weeks.append(week)
    return total, weeks


def streaks(days):
    longest = cur = 0
    for _, c in days:
        cur = cur + 1 if c else 0
        longest = max(longest, cur)
    # racha actual: si hoy aun no hay nada, cuenta desde ayer
    current = 0
    tail = days[:-1] if days and days[-1][1] == 0 else days
    for _, c in reversed(tail):
        if not c:
            break
        current += 1
    return longest, current


def render(total, weeks) -> str:
    days = [d for w in weeks for d in w]
    counts = sorted(c for _, c in days if c)
    if counts:
        q = [counts[int(len(counts) * f)] for f in (.25, .5, .75, .95)]
    else:
        q = [1, 2, 3, 4]
    longest, current = streaks(days)

    W, H = 1200, 290
    x0, y0 = 92, 104
    cell = (W - x0 - 40) / max(53, len(weeks))
    rowh = 20

    def level(c):
        if c == 0:
            return "·", "z"
        if c < q[0]:
            return ".", "a"
        if c < q[1]:
            return ":", "b"
        if c < q[2]:
            return "+", "c"
        if c < q[3]:
            return "#", "d"
        return "@", "e"

    cells, months = [], []
    last_month = None
    for wi, week in enumerate(weeks):
        x = x0 + wi * cell
        col = []
        for date, c in week:
            wd = (dt.date.fromisoformat(date).weekday() + 1) % 7   # 0 = domingo
            ch, cls = level(c)
            col.append(f'<text class="{cls}" x="{x:.1f}" y="{y0 + wd * rowh}">{ch}</text>')
        cells.append("".join(col))
        m = dt.date.fromisoformat(week[0][0]).month
        if m != last_month and wi < len(weeks) - 2:
            months.append(f'<text class="mo kj" x="{x:.1f}" y="{y0 + 7 * rowh + 14}">{MONTHS[m - 1]}</text>')
            last_month = m

    lw = len(weeks) - 1
    ld = (dt.date.fromisoformat(weeks[-1][-1][0]).weekday() + 1) % 7
    tx, ty = x0 + lw * cell + 4, y0 + ld * rowh - 5
    rows = "".join(f'<text class="dy kj" x="{x0 - 34}" y="{y0 + r * rowh}">{k}</text>' for r, k in DAYS.items())

    stats = [
        (f"{total}", "TAJOS EN EL ÚLTIMO AÑO"),
        (f"{longest}", "DÍAS · RACHA MÁS LARGA"),
        (f"{current}", "DÍAS · RACHA ACTUAL"),
    ]
    stat_svg = ""
    for i, (n, lbl) in enumerate(stats):
        sx = 40 + i * 380
        stat_svg += (f'<text class="sn" x="{sx}" y="58">{html.escape(n)}</text>'
                     f'<text class="sl" x="{sx + 18 + len(n) * 19}" y="56">{html.escape(lbl)}</text>')

    css = f"""
text{{font-family:{FONT};white-space:pre}}
.kj{{font-family:{KANJI}}}
.z,.a,.b,.c,.d,.e{{font-size:17px}}
.z{{fill:{FAINT}}}.a{{fill:{DIM}}}.b{{fill:{MID}}}.c{{fill:{LIGHT}}}.d{{fill:{BONE}}}.e{{fill:{SEAL};font-weight:bold}}
.mo{{font-size:12px;fill:{DIM}}}.dy{{font-size:13px;fill:{DIM}}}
.sn{{font-size:32px;fill:{BONE}}}.sl{{font-size:11px;fill:{MID};letter-spacing:4px}}
.td{{fill:none;stroke:{SEAL};stroke-width:1.3;opacity:.8}}
"""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
            f'aria-label="Registro de contribuciones: {total} en el último año, racha más larga de {longest} días, racha actual de {current}.">'
            f'<defs><style>{css}</style></defs><rect width="{W}" height="{H}" fill="{BG}"/>'
            f'{stat_svg}{rows}{"".join(cells)}{"".join(months)}'
            f'<circle class="td" cx="{tx:.1f}" cy="{ty:.1f}" r="8"/></svg>')


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "batallas.svg")
    total, weeks = load(src)
    out.write_text(render(total, weeks), encoding="utf-8")
    print(f"{out}  ({total} contribuciones)")
