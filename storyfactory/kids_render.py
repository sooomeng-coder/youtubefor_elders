"""유아 학습 영상 화면: 밝은 배경, 그림(이모지) 늘어놓기, 큰 숫자와 단어."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .render import H, W, wrap_korean

# 아이용 밝은 파스텔 배경 (카드마다 돌아가며)
PALETTE = [
    ((255, 214, 224), (255, 183, 200)),
    ((210, 236, 255), (170, 212, 250)),
    ((255, 240, 190), (255, 220, 140)),
    ((214, 245, 214), (170, 228, 175)),
    ((232, 220, 255), (205, 185, 250)),
    ((255, 225, 200), (255, 195, 160)),
]
INK = (40, 40, 70)

# 색 이모지 폰트 (Windows, Mac, 리눅스). 비트맵 폰트는 정해진 크기로만 열린다
EMOJI_FONTS = [
    "C:/Windows/Fonts/seguiemj.ttf",
    "/System/Library/Fonts/Apple Color Emoji.ttc",
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
]
EMOJI_SIZES = [160, 137, 109, 96, 64]

ITEMS_TOP, ITEMS_BOTTOM = 40, 620  # 그림을 늘어놓는 영역
BIG_Y = 770                         # 큰 숫자와 단어의 세로 중심
CAPTION_Y = 970                     # 아래 자막의 세로 중심


def _gradient(top: tuple, bottom: tuple) -> Image.Image:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        draw.line([(0, y), (W, y)], fill=tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3)))
    return img


def background(index: int) -> Image.Image:
    return _gradient(*PALETTE[index % len(PALETTE)])


@lru_cache(maxsize=1)
def _emoji_font() -> ImageFont.FreeTypeFont:
    for path in EMOJI_FONTS:
        if not Path(path).exists():
            continue
        for size in EMOJI_SIZES:
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    raise FileNotFoundError("색 이모지 폰트를 찾지 못했습니다. 카드에 image 그림 파일을 지정해 주세요.")


@lru_cache(maxsize=64)
def item_tile(emoji: str, image: str, size: int) -> Image.Image:
    """그림 한 개를 size×size 투명 타일로 만든다."""
    if image:
        src = Image.open(image).convert("RGBA")
    else:
        font = _emoji_font()
        canvas = Image.new("RGBA", (font.size * 2, font.size * 2), (0, 0, 0, 0))
        ImageDraw.Draw(canvas).text((font.size // 2, font.size // 2), emoji, font=font, embedded_color=True)
        src = canvas.crop(canvas.getbbox() or (0, 0, 1, 1))
    scale = size / max(src.width, src.height)
    src = src.resize((max(1, round(src.width * scale)), max(1, round(src.height * scale))), Image.LANCZOS)
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tile.paste(src, ((size - src.width) // 2, (size - src.height) // 2))
    return tile


def _item_positions(count: int) -> tuple[int, list[tuple[int, int]]]:
    """그림 count개를 최대 5개씩 줄 맞춰 놓을 때의 크기와 왼쪽 위 좌표들."""
    cols = min(count, 5)
    rows = (count + 4) // 5
    gap = 50
    size = min(260 if rows == 1 else 220, (W - 200 - gap * (cols - 1)) // cols)
    area_h = ITEMS_BOTTOM - ITEMS_TOP
    top = ITEMS_TOP + (area_h - (rows * size + (rows - 1) * gap)) // 2
    positions = []
    for i in range(count):
        r, c = divmod(i, 5)
        in_row = min(5, count - r * 5)
        left = (W - (in_row * size + (in_row - 1) * gap)) // 2
        positions.append((left + c * (size + gap), top + r * (size + gap)))
    return size, positions


def _big_text(draw: ImageDraw.ImageDraw, big: str, word: str, font_path: str) -> None:
    if not big and not word:
        return
    big_font = ImageFont.truetype(font_path, 280)
    word_font = ImageFont.truetype(font_path, 150 if big else 200)
    style = dict(fill=(255, 255, 255), stroke_width=14, stroke_fill=INK)
    if not big:
        draw.text((W / 2, BIG_Y), word, font=word_font, anchor="mm", **style)
        return
    gap = 70
    big_w = draw.textlength(big, font=big_font)
    word_w = draw.textlength(word, font=word_font)
    left = (W - (big_w + gap + word_w)) / 2
    draw.text((left, BIG_Y), big, font=big_font, anchor="lm", **style)
    draw.text((left + big_w + gap, BIG_Y + 10), word, font=word_font, anchor="lm", **style)


def _caption(draw: ImageDraw.ImageDraw, text: str, font_path: str) -> None:
    if not text:
        return
    font = ImageFont.truetype(font_path, 60)
    line = " ".join(wrap_korean(text, max_chars=40)[:1])
    w = draw.textlength(line, font=font)
    draw.rounded_rectangle((W / 2 - w / 2 - 50, CAPTION_Y - 55, W / 2 + w / 2 + 50, CAPTION_Y + 55),
                           radius=55, fill=(255, 255, 255))
    draw.text((W / 2, CAPTION_Y), line, font=font, fill=INK, anchor="mm")


def card_frame(index: int, *, emoji: str, image: str, count: int, shown: int, counting: bool,
               big: str, word: str, caption: str, font_path: str) -> Image.Image:
    """shown개까지는 또렷하게, 나머지는 흐릿하게 그린다. 세는 중이면 방금 센 그림에 노란 동그라미."""
    img = background(index).convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    if emoji or image:
        size, positions = _item_positions(count)
        tile = item_tile(emoji, image, size)
        faded = tile.copy()
        faded.putalpha(faded.getchannel("A").point(lambda a: a * 30 // 100))
        for i, (x, y) in enumerate(positions):
            if i < shown:
                pad = size // 8
                fill = (255, 230, 90) if counting and i == shown - 1 else (255, 255, 255, 170)
                draw.ellipse((x - pad, y - pad, x + size + pad, y + size + pad), fill=fill)
        img = Image.alpha_composite(img, layer)
        for i, (x, y) in enumerate(positions):
            img.alpha_composite(tile if i < shown else faded, (x, y))
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
    _big_text(draw, big, word, font_path)
    _caption(draw, caption, font_path)
    return Image.alpha_composite(img, layer).convert("RGB")


def title_frame(index: int, title: str, emojis: list[str], caption: str, font_path: str) -> Image.Image:
    """시작과 끝 화면: 위에 그림 한 줄, 가운데 큰 제목."""
    img = background(index).convert("RGBA")
    if emojis:
        size, gap = 170, 40
        left = (W - (len(emojis) * size + (len(emojis) - 1) * gap)) // 2
        for i, e in enumerate(emojis):
            img.alpha_composite(item_tile(e, "", size), (left + i * (size + gap), 150))
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    lines = title.replace("\\n", "\n").split("\n")
    font = ImageFont.truetype(font_path, 150)
    for i, line in enumerate(lines):
        draw.text((W / 2, 560 + (i - (len(lines) - 1) / 2) * 175), line, font=font, anchor="mm",
                  fill=(255, 255, 255), stroke_width=14, stroke_fill=INK)
    _caption(draw, caption, font_path)
    return Image.alpha_composite(img, layer).convert("RGB")


def thumbnail(text: str, emojis: list[str], font_path: str, out: Path) -> None:
    img = background(2).convert("RGBA")
    size = 300
    corners = [(60, 60), (W - size - 60, 60), (60, H - size - 60), (W - size - 60, H - size - 60)]
    for (x, y), e in zip(corners, emojis):
        img.alpha_composite(item_tile(e, "", size), (x, y))
    draw = ImageDraw.Draw(img)
    lines = text.replace("\\n", "\n").split("\n")[:3]
    font = ImageFont.truetype(font_path, 190)
    line_h = 220
    top = (H - line_h * len(lines)) / 2
    for i, line in enumerate(lines):
        draw.text((W / 2, top + line_h * i + line_h / 2), line, font=font, anchor="mm",
                  fill=(255, 221, 0), stroke_width=18, stroke_fill=INK)
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(out, quality=92)
