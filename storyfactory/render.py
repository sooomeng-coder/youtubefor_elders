"""화면(배경+자막) 그리기, 썸네일, ffmpeg로 영상 합치기."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
FPS = 30

# 그림이 없는 장면에 쓰는 차분한 배경색 (장면마다 돌아가며)
PALETTE = [
    ((58, 82, 64), (24, 36, 28)),
    ((96, 70, 48), (40, 28, 20)),
    ((52, 70, 98), (20, 28, 44)),
    ((104, 62, 62), (44, 24, 24)),
    ((76, 64, 96), (30, 24, 42)),
    ((70, 90, 90), (26, 36, 36)),
]

SUB_FONT_SIZE = 72
SUB_MAX_CHARS = 20  # 한 줄 최대 글자 수


def wrap_korean(text: str, max_chars: int = SUB_MAX_CHARS) -> list[str]:
    """띄어쓰기 기준으로 줄을 나눈다. 너무 긴 단어는 글자 단위로 자른다."""
    lines: list[str] = []
    cur = ""
    for word in text.split():
        while len(word) > max_chars:
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(word[:max_chars])
            word = word[max_chars:]
        candidate = f"{cur} {word}" if cur else word
        if len(candidate) <= max_chars:
            cur = candidate
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _gradient(top: tuple, bottom: tuple) -> Image.Image:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        draw.line([(0, y), (W, y)], fill=color)
    return img


def _cover(img: Image.Image) -> Image.Image:
    """그림을 화면에 꽉 차게 자른다."""
    img = img.convert("RGB")
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left = (img.width - W) // 2
    top = (img.height - H) // 2
    return img.crop((left, top, left + W, top + H))


def scene_background(index: int, heading: str, image_path: Path | None, font_path: str) -> Image.Image:
    if image_path and image_path.exists():
        return _cover(Image.open(image_path))
    img = _gradient(*PALETTE[index % len(PALETTE)])
    if not heading:
        return img
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, 96)
    draw.text((W // 2, H // 2 - 140), heading, font=font, fill=(255, 255, 255, 230),
              anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
    return img


def draw_frame(background: Image.Image, subtitle: str, font_path: str,
               label: str = "AI 창작 사연") -> Image.Image:
    img = background.copy().convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 왼쪽 위 안내 표시
    small = ImageFont.truetype(font_path, 34)
    draw.rounded_rectangle((32, 28, 32 + 28 + draw.textlength(label, font=small) + 28, 90),
                           radius=14, fill=(0, 0, 0, 150))
    draw.text((60, 59), label, font=small, fill=(255, 255, 255), anchor="lm")

    # 아래쪽 자막: 검은 반투명 박스 위에 흰 글씨
    if subtitle:
        font = ImageFont.truetype(font_path, SUB_FONT_SIZE)
        lines = wrap_korean(subtitle)
        line_h = int(SUB_FONT_SIZE * 1.35)
        box_h = line_h * len(lines) + 60
        widest = max(draw.textlength(line, font=font) for line in lines)
        box_w = widest + 120
        x0 = (W - box_w) / 2
        y0 = H - box_h - 60
        draw.rounded_rectangle((x0, y0, x0 + box_w, y0 + box_h), radius=24, fill=(0, 0, 0, 185))
        for i, line in enumerate(lines):
            draw.text((W / 2, y0 + 30 + line_h * i + line_h / 2), line, font=font,
                      fill=(255, 255, 255), anchor="mm",
                      stroke_width=3, stroke_fill=(0, 0, 0))

    return Image.alpha_composite(img, overlay).convert("RGB")


def make_thumbnail(text: str, background: Image.Image, font_path: str, out: Path) -> None:
    img = background.copy().filter(ImageFilter.GaussianBlur(2)).convert("RGBA")
    shade = Image.new("RGBA", img.size, (0, 0, 0, 90))
    img = Image.alpha_composite(img, shade)
    draw = ImageDraw.Draw(img)
    lines = text.replace("\\n", "\n").split("\n")[:3]
    size = 170 if max(len(l) for l in lines) <= 8 else 140
    font = ImageFont.truetype(font_path, size)
    line_h = int(size * 1.2)
    top = (H - line_h * len(lines)) / 2
    for i, line in enumerate(lines):
        draw.text((W / 2, top + line_h * i + line_h / 2), line, font=font,
                  fill=(255, 221, 0), anchor="mm", stroke_width=14, stroke_fill=(0, 0, 0))
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(out, quality=92)


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("ffmpeg 오류:\n" + result.stderr[-2000:])


def make_segment(frame: Path, audio: Path | None, duration: float, out: Path) -> None:
    """정지 화면 한 장 + 음성(없으면 무음)으로 짧은 영상 조각을 만든다."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(frame)]
    if audio:
        cmd += ["-i", str(audio)]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    cmd += [
        "-af", "apad", "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
        str(out),
    ]
    _run(cmd)


def concat_segments(segments: list[Path], out: Path, bgm: Path | None = None,
                    bgm_volume: float = 0.08) -> None:
    list_file = out.with_suffix(".txt")
    list_file.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in segments), encoding="utf-8")
    if not bgm:
        _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
              "-i", str(list_file), "-c", "copy", "-movflags", "+faststart", str(out)])
        return
    _run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-stream_loop", "-1", "-i", str(bgm),
        "-filter_complex",
        f"[1:a]volume={bgm_volume}[b];[0:a][b]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", str(out),
    ])
