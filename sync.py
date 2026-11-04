#!/usr/bin/env python3
"""ซิงก์ Simulation จากโฟลเดอร์แผนของแต่ละรายวิชามาเป็นฉบับเว็บ แล้วสร้างหน้ารวม index.html

ใช้: python3 sync.py   (รันจากที่ใดก็ได้)
รายการ Simulation อยู่ใน sims.json ต้นฉบับอยู่ในโฟลเดอร์แผนเสมอ ห้ามแก้ไฟล์ในโฟลเดอร์นี้โดยตรง
"""
import html
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
WORKSPACE = REPO.parent  # โฟลเดอร์ "ครูฟิสิกส์ ม4" ที่เก็บโปรเจกต์ทุกรายวิชา

# ฟอนต์ในเครื่องใช้พาธ ../../../_assets/font/ ซึ่งใช้บนเว็บไม่ได้ ฉบับเว็บจึงใช้ Sarabun จาก Google Fonts
LOCAL_FONT = re.compile(r'^[ \t]*@font-face\s*\{[^}]*_assets/font/[^}]*\}[ \t]*\n', re.M)
GOOGLE_FONT = "fonts.googleapis.com/css2?family=Sarabun"
# ข้อความแนะนำในแถบ #jsWarn เขียนไว้สำหรับไฟล์ในเครื่อง ฉบับเว็บใช้ข้อความนี้แทน
WARN_MSG = re.compile(r'(<span id="jsMsg">).*?(</span>)', re.S)
WEB_WARN = r"\1เบราว์เซอร์นี้ไม่รันโปรแกรม ให้เปิดลิงก์ด้วย Safari หรือ Chrome หรือดูจากจอที่ครูฉาย\2"
UNIT = re.compile(r"หน่วยที่ (\d+) ([^/]+)")
PLAN = re.compile(r"แผนที่ (\d+) ([^/]+)")


def fail(msg):
    sys.exit("ผิดพลาด: " + msg)


def to_web(src_text, name):
    text, n = LOCAL_FONT.subn("", src_text)
    if GOOGLE_FONT not in text:
        fail(f"{name} ไม่ได้โหลด Sarabun จาก Google Fonts (ต้องมี <link> ไปที่ {GOOGLE_FONT})")
    text, w = WARN_MSG.subn(WEB_WARN, text, count=1)
    if w == 0:
        print(f"  เตือน: {name} ไม่มี <span id=\"jsMsg\"> ข้อความแจ้งเตือนจึงไม่ได้ปรับเป็นฉบับเว็บ")
    left = re.findall(r'(?:src|href|url)\(?\s*=?\s*["\']?(\.\./[^"\')]+)', text)
    if left:
        fail(f"{name} ยังอ้างไฟล์ในเครื่อง {left[:3]} ซึ่งใช้บนเว็บไม่ได้")
    return text


def main():
    cfg = json.loads((REPO / "sims.json").read_text(encoding="utf-8"))
    courses = {c["id"]: c for c in cfg["courses"]}
    slugs, entries = set(), []
    for s in cfg["sims"]:
        course = courses.get(s["course"]) or fail(f"ไม่พบรายวิชา {s['course']} ใน courses")
        if not re.fullmatch(r"[a-z0-9-]+", s["slug"]):
            fail(f"slug '{s['slug']}' ต้องเป็นอักษรอังกฤษพิมพ์เล็ก ตัวเลข หรือ - เท่านั้น")
        key = (s["course"], s["slug"])
        if key in slugs:
            fail(f"slug ซ้ำ: {s['course']}/{s['slug']}")
        slugs.add(key)
        src = WORKSPACE / course["project"] / s["source"]
        if not src.is_file():
            fail(f"ไม่พบต้นฉบับ {src}")
        text = to_web(src.read_text(encoding="utf-8"), src.name)
        out = REPO / s["course"] / (s["slug"] + ".html")
        out.parent.mkdir(exist_ok=True)
        changed = not out.exists() or out.read_text(encoding="utf-8") != text
        out.write_text(text, encoding="utf-8")
        title = re.search(r"<title>(.*?)</title>", text, re.S)
        unit, plan = UNIT.search(s["source"]), PLAN.search(s["source"])
        entries.append({
            "course": s["course"], "href": f"{s['course']}/{s['slug']}.html",
            "title": title.group(1).strip() if title else s["slug"],
            "unit": f"หน่วยที่ {unit.group(1)} {unit.group(2)}" if unit else "",
            "unit_no": int(unit.group(1)) if unit else 0,
            "plan": f"แผนที่ {plan.group(1)}" if plan else "",
            "plan_no": int(plan.group(1)) if plan else 0,
        })
        print(("  อัปเดต " if changed else "  ไม่เปลี่ยน ") + f"{s['course']}/{s['slug']}.html ← {src.name}")

    # ไฟล์ที่ไม่อยู่ใน sims.json แล้ว แจ้งให้ลบเองเพื่อไม่ให้ลิงก์เดิมหายโดยไม่ตั้งใจ
    for d in courses:
        for f in (REPO / d).glob("*.html") if (REPO / d).is_dir() else []:
            if (d, f.stem) not in slugs:
                print(f"  เตือน: {d}/{f.name} ไม่อยู่ใน sims.json แล้ว ถ้าไม่ใช้ให้ลบไฟล์เอง")

    (REPO / "index.html").write_text(render_index(cfg["courses"], entries), encoding="utf-8")
    print(f"สร้าง index.html แล้ว ({len(entries)} Simulation)")


def render_index(courses, entries):
    e = html.escape
    parts = []
    for c in courses:
        items = sorted((x for x in entries if x["course"] == c["id"]), key=lambda x: x["plan_no"])  # ในแผนเดียวกันเรียงตามลำดับใน sims.json
        if not items:
            continue
        parts.append(f'<section><h2>{e(c["title"])}</h2>')
        unit = None
        for x in items:
            if x["unit"] != unit:
                if unit is not None:
                    parts.append("</ul>")
                unit = x["unit"]
                parts.append(f"<h3>{e(unit)}</h3><ul>")
            parts.append(f'<li><a href="{e(x["href"])}"><span class="t">{e(x["title"])}</span>'
                         f'<span class="m">{e(x["plan"])}</span></a></li>')
        parts.append("</ul></section>")
    return INDEX.replace("{{BODY}}", "\n".join(parts))


INDEX = """<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Simulation ฟิสิกส์</title>
<!-- ไฟล์นี้สร้างโดย sync.py ห้ามแก้เอง -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root { --primary: #4A2033; --secondary: #1E6670; --accent: #E2772E; --ink: #2B2427; --muted: #7a6d72;
  --paper: #FCF8F3; --card: #ffffff; --line: #e6dcd3; }
@media (prefers-color-scheme: dark) {
  :root { --primary: #f0c6d6; --secondary: #6cc3cc; --accent: #f29a5c; --ink: #eee6e9; --muted: #b3a5ab;
    --paper: #1d181a; --card: #2a2326; --line: #3d3337; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink); font-family: "Sarabun", sans-serif;
  font-size: 18px; line-height: 1.5; }
main { max-width: 760px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { margin: 0 0 4px; font-size: 30px; color: var(--primary); }
.sub { margin: 0 0 24px; color: var(--muted); }
h2 { margin: 28px 0 4px; font-size: 24px; color: var(--secondary); }
h3 { margin: 16px 0 8px; font-size: 18px; font-weight: 600; color: var(--muted); }
ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
a { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 14px 18px;
  background: var(--card); border: 1px solid var(--line); border-left: 5px solid var(--accent);
  border-radius: 10px; color: var(--ink); text-decoration: none; }
a:active, a:hover { border-color: var(--accent); }
.t { font-size: 20px; font-weight: 600; }
.m { color: var(--muted); white-space: nowrap; }
</style>
</head>
<body>
<main>
<h1>Simulation ฟิสิกส์</h1>
<p class="sub">โรงเรียนมัธยมสาธิตมหาวิทยาลัยนเรศวร · แตะชื่อเพื่อเปิด ใช้ได้ทั้ง iPad โทรศัพท์ และคอมพิวเตอร์</p>
{{BODY}}
</main>
</body>
</html>
"""

if __name__ == "__main__":
    main()
