"""문장별 음성 만들기 (Edge TTS, 무료)."""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

DEFAULT_VOICE = "ko-KR-SunHiNeural"  # 차분한 여성 목소리. 남성: ko-KR-InJoonNeural
DEFAULT_RATE = "-10%"                # 어르신용으로 기본보다 조금 느리게

# 무음 모드에서 쓰는 예상 낭독 속도 (초당 글자 수)
SILENT_CHARS_PER_SEC = 5.0


def audio_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


async def _synthesize(text: str, out: Path, voice: str, rate: str) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


def synthesize(text: str, out: Path, voice: str = DEFAULT_VOICE,
               rate: str = DEFAULT_RATE, retries: int = 3) -> float:
    """text를 읽은 mp3를 out에 저장하고 길이(초)를 돌려준다."""
    if out.exists() and out.stat().st_size > 0:
        return audio_duration(out)
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            asyncio.run(_synthesize(text, out, voice, rate))
            return audio_duration(out)
        except Exception as e:  # 네트워크 오류는 몇 번 다시 시도
            last_error = e
    raise RuntimeError(f"음성 생성 실패: {text[:20]}... ({last_error})")


def silent_duration(text: str) -> float:
    return max(1.5, len(text) / SILENT_CHARS_PER_SEC)
