"""한글 폰트 찾기."""
from __future__ import annotations

from pathlib import Path

BUNDLED = Path(__file__).resolve().parent.parent / "fonts" / "Pretendard-ExtraBold.otf"

SYSTEM_CANDIDATES = [
    "C:/Windows/Fonts/malgunbd.ttf",                          # Windows 맑은 고딕 Bold
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",             # Mac
    "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
]


def find_font(override: str | None = None) -> str:
    if override:
        if not Path(override).exists():
            raise FileNotFoundError(f"폰트 파일이 없습니다: {override}")
        return override
    for p in [BUNDLED, *map(Path, SYSTEM_CANDIDATES)]:
        if p.exists():
            return str(p)
    raise FileNotFoundError("한글 폰트를 찾지 못했습니다. --font 로 폰트 파일 경로를 지정해 주세요.")
