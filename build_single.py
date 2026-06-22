#!/usr/bin/env python3
"""꼬미의 부엌 — 단일 파일 빌드기.
index.html + assets/*.png 를 합쳐서 에셋이 전부 인라인된 portable HTML 하나를 만든다.
결과 파일은 assets/ 폴더 없이 어디서든(파일 더블클릭·이메일·USB·정적호스팅) 열린다.
"""
import base64, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(ROOT, "index.html")
OUT  = os.path.join(ROOT, "꼬미의-부엌.html")

def main():
    with open(SRC, encoding="utf-8") as f:
        html = f.read()

    # 1) build {filename.png: dataURI} for every png in assets/
    ap = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "assets", "*.png"))):
        name = os.path.basename(path)
        with open(path, "rb") as fp:
            b64 = base64.b64encode(fp.read()).decode("ascii")
        ap[name] = "data:image/png;base64," + b64

    if not ap:
        print("⚠️  assets/ 에 png가 없어요. 먼저 에셋을 받아주세요.", file=sys.stderr)
        sys.exit(1)

    # 2) inject window.AP just before the main script (which defines asset()).
    inject = "<script>window.AP=" + json.dumps(ap) + ";</script>\n"
    marker = '<script>\n"use strict";'
    if marker not in html:
        print("⚠️  메인 스크립트 마커를 못 찾았어요.", file=sys.stderr)
        sys.exit(1)
    html = html.replace(marker, inject + marker, 1)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)

    kb = os.path.getsize(OUT) / 1024
    print(f"✅ {os.path.basename(OUT)} 생성 완료 — 에셋 {len(ap)}개 인라인, {kb:.0f}KB")

if __name__ == "__main__":
    main()
