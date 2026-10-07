"""권선징악 사연 영상 만들기.

사용 예:
  python make_video.py --story samples/sample_story.json        # 예시 대본으로 (API 키 불필요)
  python make_video.py --topic "시어머니 구박한 며느리의 최후"     # Claude로 대본부터 생성
  python make_video.py --topic "..." --script-only              # 대본만 먼저 뽑아서 다듬기
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from storyfactory import render, tts
from storyfactory.fonts import find_font
from storyfactory.story import Story, load_story, save_story

PAUSE_AFTER_SENTENCE = 0.45  # 문장 사이 쉼(초)
PAUSE_AFTER_SCENE = 1.2      # 장면 사이 쉼(초)

DISCLOSURE = (
    "※ 이 영상은 AI의 도움을 받아 만든 창작 사연입니다. "
    "등장인물과 사건은 실제와 관계없습니다."
)


def slugify(text: str) -> str:
    text = re.sub(r"[^\w가-힣]+", "_", text).strip("_")
    return text[:40] or "story"


def write_upload_info(story: Story, path: Path) -> None:
    lines = [
        "[제목]", story.title, "",
        "[설명]", story.description, "", DISCLOSURE, "",
        " ".join(story.hashtags), "",
        "[업로드할 때]",
        "- 그림이나 목소리를 AI로 만들었다면 '변경되거나 합성된 콘텐츠' 항목을 '예'로 선택하세요.",
        "- 시청자층은 '아동용 아님'으로 설정하세요.", "",
        "[장면별 그림 프롬프트] images/scene_01.png 처럼 저장하면 다음 실행 때 배경으로 들어갑니다.",
    ]
    for i, scene in enumerate(story.scenes, 1):
        lines.append(f"scene_{i:02d} ({scene.heading}): {scene.image_prompt}")
    lines += ["", "[등장인물]"]
    lines += [f"- {c.name}: {c.description}" for c in story.characters]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_video(story: Story, out_dir: Path, *, images_dir: Path, font_path: str,
                voice: str, rate: str, silent: bool, bgm: Path | None) -> Path:
    work = out_dir / "work"
    work.mkdir(parents=True, exist_ok=True)

    segments: list[Path] = []
    first_background = None
    total = sum(len(s.narration) for s in story.scenes)
    done = 0

    for si, scene in enumerate(story.scenes, 1):
        image = next((images_dir / f"scene_{si:02d}{ext}" for ext in (".png", ".jpg", ".jpeg", ".webp")
                      if (images_dir / f"scene_{si:02d}{ext}").exists()), None)
        background = render.scene_background(si - 1, scene.heading, image, font_path)
        if first_background is None:  # 썸네일 배경 (장면 제목 글씨 없이)
            first_background = render.scene_background(0, "", image, font_path)

        for li, sentence in enumerate(scene.narration, 1):
            done += 1
            print(f"\r  [{done}/{total}] {scene.heading}", end="", flush=True)
            key = f"s{si:02d}_{li:03d}"

            frame = work / f"{key}.png"
            render.draw_frame(background, sentence, font_path).save(frame)

            if silent:
                audio, length = None, tts.silent_duration(sentence)
            else:
                audio = work / f"{key}.mp3"
                length = tts.synthesize(sentence, audio, voice=voice, rate=rate)

            pause = PAUSE_AFTER_SCENE if li == len(scene.narration) else PAUSE_AFTER_SENTENCE
            segment = work / f"{key}.mp4"
            render.make_segment(frame, audio, length + pause, segment)
            segments.append(segment)
    print()

    render.make_thumbnail(story.thumbnail_text, first_background, font_path, out_dir / "thumbnail.jpg")
    video = out_dir / "video.mp4"
    render.concat_segments(segments, video, bgm=bgm)
    return video


def main() -> int:
    p = argparse.ArgumentParser(description="권선징악 사연 영상 자동 제작")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--topic", help="이 주제로 Claude가 대본을 씁니다 (ANTHROPIC_API_KEY 필요)")
    src.add_argument("--story", help="이미 있는 대본 JSON 파일로 영상을 만듭니다")
    p.add_argument("--minutes", type=int, default=10, help="목표 영상 길이(분), 기본 10")
    p.add_argument("--script-only", action="store_true", help="대본(story.json)만 만들고 멈춥니다")
    p.add_argument("--out", default="output", help="결과 폴더, 기본 output/")
    p.add_argument("--images", help="장면 그림 폴더 (scene_01.png ...). 기본: 결과 폴더의 images/")
    p.add_argument("--voice", default=tts.DEFAULT_VOICE, help="Edge TTS 목소리 (남성: ko-KR-InJoonNeural)")
    p.add_argument("--rate", default=tts.DEFAULT_RATE, help="말 빠르기, 기본 -10%%")
    p.add_argument("--bgm", help="배경음악 파일 (작게 깔립니다)")
    p.add_argument("--font", help="자막 폰트 파일 경로")
    p.add_argument("--silent", action="store_true", help="음성 없이 화면만 확인하는 테스트 모드")
    args = p.parse_args()

    if args.story:
        story_path = Path(args.story)
        story = load_story(story_path)
        # --script-only로 만든 폴더의 story.json이면 그 폴더에 그대로 이어서 만든다
        if story_path.name == "story.json":
            out_dir = story_path.parent
        else:
            out_dir = Path(args.out) / story_path.stem
    else:
        from storyfactory.script import generate_story

        print(f"대본 생성 중: {args.topic} (1~3분 걸립니다)")
        story = generate_story(args.topic, minutes=args.minutes)
        out_dir = Path(args.out) / f"{datetime.now():%Y%m%d_%H%M}_{slugify(story.title)}"

    out_dir.mkdir(parents=True, exist_ok=True)
    save_story(story, out_dir / "story.json")
    write_upload_info(story, out_dir / "upload.txt")
    print(f"대본: {out_dir / 'story.json'}  ({len(story.scenes)}장면, "
          f"{sum(len(s.narration) for s in story.scenes)}문장)")

    if args.script_only:
        print("대본을 고친 뒤 이렇게 영상을 만드세요:")
        print(f"  python make_video.py --story \"{out_dir / 'story.json'}\"")
        return 0

    images_dir = Path(args.images) if args.images else out_dir / "images"
    print("영상 만드는 중...")
    video = build_video(
        story, out_dir,
        images_dir=images_dir,
        font_path=find_font(args.font),
        voice=args.voice, rate=args.rate,
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
