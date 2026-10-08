"""유아 학습(숫자 세기, 단어 카드) 영상 만들기.

사용 예:
  python make_kids_video.py --lesson samples/kids_numbers_es.json           # 스페인어 숫자 1~10
  python make_kids_video.py --lesson samples/kids_numbers_es.json --silent  # 음성 없이 화면만 확인
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from storyfactory import kids_render, render, tts
from storyfactory.fonts import find_font
from storyfactory.lesson import Lesson, load_lesson

PAUSE_AFTER_COUNT = 0.35  # 하나, 둘 셀 때 사이 쉼(초)
PAUSE_AFTER_LINE = 0.7    # 문장 사이 쉼(초)
PAUSE_AFTER_CARD = 1.0    # 카드 사이 쉼(초)


class Builder:
    """화면 한 장 + 말 한 마디씩 영상 조각을 쌓는다."""

    def __init__(self, work: Path, *, voice: str, rate: str, silent: bool):
        self.work = work
        self.voice, self.rate, self.silent = voice, rate, silent
        self.segments: list[Path] = []

    def add(self, frame, text: str, pause: float) -> None:
        n = len(self.segments) + 1
        print(f"\r  [{n}] {text[:30]:<30}", end="", flush=True)
        frame_path = self.work / f"f{n:04d}.png"
        frame.save(frame_path)
        if self.silent:
            audio, length = None, tts.silent_duration(text) * 0.6
        else:
            # 같은 말(uno, dos...)은 여러 번 나오니 음성을 한 번만 만든다
            key = hashlib.sha1(f"{self.voice}|{self.rate}|{text}".encode()).hexdigest()[:16]
            audio = self.work / f"tts_{key}.mp3"
            length = tts.synthesize(text, audio, voice=self.voice, rate=self.rate)
        segment = self.work / f"f{n:04d}.mp4"
        render.make_segment(frame_path, audio, length + pause, segment)
        self.segments.append(segment)


def build_video(lesson: Lesson, out_dir: Path, *, font_path: str, voice: str, rate: str,
                silent: bool, bgm: Path | None) -> Path:
    work = out_dir / "work"
    work.mkdir(parents=True, exist_ok=True)
    b = Builder(work, voice=voice, rate=rate, silent=silent)
    emojis = [c.emoji for c in lesson.cards if c.emoji][:5]

    def say_lines(lines: list[str], make_frame, last_pause: float) -> None:
        for i, line in enumerate(lines):
            b.add(make_frame(line), line, last_pause if i == len(lines) - 1 else PAUSE_AFTER_LINE)

    say_lines(lesson.intro, lambda line: kids_render.title_frame(
        0, lesson.thumbnail_text, emojis, line, font_path), PAUSE_AFTER_CARD)

    for ci, card in enumerate(lesson.cards, 1):
        def frame(shown: int, big: str, word: str, caption: str, counting: bool = False):
            return kids_render.card_frame(
                ci, emoji=card.emoji, image=card.image, count=card.count, shown=shown,
                counting=counting, big=big, word=word, caption=caption, font_path=font_path)

        if card.question:
            # 셀 그림은 흐리게 두고 묻는다. 하나짜리는 무엇인지 보여 주며 묻는다
            shown = card.count if card.count == 1 else 0
            b.add(frame(shown, "", "", card.question), card.question, PAUSE_AFTER_LINE)
        # 하나씩 세기: 그림이 하나씩 켜지면서 숫자와 단어가 바뀐다
        if card.count > 1 and len(lesson.count_words) >= card.count:
            for k in range(1, card.count + 1):
                word = lesson.count_words[k - 1]
                b.add(frame(k, str(k), word, "", counting=True), word, PAUSE_AFTER_COUNT)
        say_lines(card.lines, lambda line: frame(card.count, card.big, card.word, line), PAUSE_AFTER_CARD)

    if lesson.review_title:
        b.add(kids_render.title_frame(len(lesson.cards) + 1, lesson.review_title, emojis, "", font_path),
              lesson.review_title, PAUSE_AFTER_LINE)
        for ci, card in enumerate(lesson.cards, 1):
            line = card.lines[0]
            b.add(kids_render.card_frame(
                ci, emoji=card.emoji, image=card.image, count=card.count, shown=card.count,
                counting=False, big=card.big, word=card.word, caption="", font_path=font_path),
                line, PAUSE_AFTER_COUNT)

    say_lines(lesson.outro, lambda line: kids_render.title_frame(
        0, lesson.thumbnail_text, emojis, line, font_path), PAUSE_AFTER_CARD)
    print()

    kids_render.thumbnail(lesson.thumbnail_text, emojis, font_path, out_dir / "thumbnail.jpg")
    video = out_dir / "video.mp4"
    render.concat_segments(b.segments, video, bgm=bgm)
    return video


def write_upload_info(lesson: Lesson, path: Path) -> None:
    lines = [
        "[제목]", lesson.title, "",
        "[설명]", lesson.description, "", lesson.disclosure, "",
        " ".join(lesson.hashtags), "",
        "[업로드할 때]",
        "- 시청자층은 반드시 '예, 아동용입니다'로 설정하세요 (아동용 콘텐츠는 법적으로 꼭 표시해야 합니다).",
        "- 이모지 그림 + 합성 음성 낭독은 실제 사람·사건처럼 보이는 합성이 아니라서 보통 "
        "'변경되거나 합성된 콘텐츠' 표시 대상이 아니지만, 사실적인 AI 그림을 넣었다면 '예'로 하세요.",
        "- 쇼츠용으로는 숫자 하나(약 20초)만 잘라 세로로 올리고 본편 링크를 연결하세요.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="유아 학습 영상 자동 제작")
    p.add_argument("--lesson", required=True, help="학습 대본 JSON 파일")
    p.add_argument("--out", default="output", help="결과 폴더, 기본 output/")
    p.add_argument("--voice", help="Edge TTS 목소리 (기본: 대본의 voice)")
    p.add_argument("--rate", help="말 빠르기 (기본: 대본의 rate)")
    p.add_argument("--bgm", help="배경음악 파일 (작게 깔립니다)")
    p.add_argument("--font", help="글자 폰트 파일 경로")
    p.add_argument("--silent", action="store_true", help="음성 없이 화면만 확인하는 테스트 모드")
    args = p.parse_args()

    lesson_path = Path(args.lesson)
    lesson = load_lesson(lesson_path)
    out_dir = Path(args.out) / lesson_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    write_upload_info(lesson, out_dir / "upload.txt")

    print("영상 만드는 중...")
    video = build_video(
        lesson, out_dir,
        font_path=find_font(args.font),
        voice=args.voice or lesson.voice, rate=args.rate or lesson.rate,
        silent=args.silent,
        bgm=Path(args.bgm) if args.bgm else None,
    )
    seconds = tts.audio_duration(video)
    print(f"완성: {video}  ({int(seconds // 60)}분 {int(seconds % 60)}초)")
    print(f"썸네일: {out_dir / 'thumbnail.jpg'}")
    print(f"업로드 정보: {out_dir / 'upload.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
