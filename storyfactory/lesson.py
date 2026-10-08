"""유아 학습(숫자, 단어 카드) 영상 대본의 형식과 JSON 읽기."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class Card(BaseModel):
    big: str = Field("", description="크게 보여 줄 숫자나 글자 (예: 3, A). 없으면 단어만 크게")
    word: str = Field(description="화면에 쓰는 단어 (예: tres)")
    emoji: str = Field("", description="화면에 늘어놓을 그림 이모지 (예: 🍓)")
    image: str = Field("", description="이모지 대신 쓸 그림 파일 경로 (선택)")
    count: int = Field(1, ge=1, le=10, description="그림을 몇 개 보여 줄지")
    question: str = Field("", description="그림을 보여 주기 전에 묻는 말 (예: ¿Cuántas fresas hay?)")
    lines: list[str] = Field(description="다 센 뒤에 읽는 문장들 (예: ¡Tres!, Tres fresas.)")


class Lesson(BaseModel):
    title: str
    thumbnail_text: str = Field(description="썸네일 큰 글씨. 줄바꿈은 \\n")
    description: str
    hashtags: list[str]
    disclosure: str = Field("", description="설명란 끝에 붙는 AI 사용 안내 (영상 언어로)")
    voice: str = Field("es-MX-DaliaNeural", description="Edge TTS 목소리")
    rate: str = Field("-15%", description="말 빠르기. 아이용으로 조금 느리게")
    count_words: list[str] = Field(
        default_factory=list,
        description="하나씩 셀 때 읽는 말 (uno, dos, ...). 비워 두면 세기 단계를 건너뜀")
    intro: list[str]
    review_title: str = Field("", description="마지막 복습 시작 말. 비워 두면 복습 없음")
    outro: list[str]
    cards: list[Card]


def load_lesson(path: str | Path) -> Lesson:
    return Lesson.model_validate_json(Path(path).read_text(encoding="utf-8"))
