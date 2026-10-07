"""사연 대본의 형식(스키마)과 JSON 읽기/쓰기."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class Character(BaseModel):
    name: str = Field(description="등장인물 이름 또는 호칭 (예: 순자 할머니)")
    description: str = Field(description="나이, 외모, 옷차림. 그림을 그릴 때 매 장면 똑같이 쓰인다")


class Scene(BaseModel):
    heading: str = Field(description="장면 제목 (예: 장터에서 생긴 일)")
    image_prompt: str = Field(description="이 장면 그림을 그리기 위한 영어 프롬프트")
    narration: list[str] = Field(description="낭독할 문장들. 한 문장은 자막 한 화면 분량(40자 이내)")


class Story(BaseModel):
    title: str = Field(description="유튜브 영상 제목")
    thumbnail_text: str = Field(description="썸네일 큰 글씨. 줄바꿈은 \\n, 2줄 이내, 한 줄 10자 이내")
    description: str = Field(description="유튜브 설명란 본문")
    hashtags: list[str] = Field(description="#으로 시작하는 해시태그 5~8개")
    characters: list[Character]
    scenes: list[Scene]


def load_story(path: str | Path) -> Story:
    return Story.model_validate_json(Path(path).read_text(encoding="utf-8"))


def save_story(story: Story, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(story.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
