"""Claude로 권선징악 사연 대본을 만든다."""
from __future__ import annotations

import anthropic

from .story import Story

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """\
당신은 60~80대 어르신이 즐겨 보는 유튜브 '사연 낭독' 채널의 작가입니다.
권선징악 구조의 창작 사연을 씁니다.

구조: 발단(평범한 일상과 인물 소개) → 악행(욕심, 불효, 구박, 사기) → 고난(착한 인물이 견디는 시간)
→ 반전(숨겨진 진실, 도움의 손길) → 결말(악인은 대가를 치르고 반성, 착한 인물은 보상받음).

문체:
- 성우가 소리 내어 읽는 낭독 대본입니다. 쉬운 우리말 존댓말 서술체("~했습니다", "~였지요")로 씁니다.
- 한 문장은 40자 이내로 짧게 씁니다. 어려운 한자어, 외래어, 숫자 기호는 피합니다.
- 대사는 따옴표로 넣되 누가 말하는지 문장 안에서 분명히 합니다.
- 배경은 시골 마을, 장터, 명절, 효도, 형제간 유산처럼 어르신께 익숙한 소재를 씁니다.

지켜야 할 것:
- 지어낸 이야기입니다. '실화', '실제 사연', '제보받은' 같은 표현을 쓰지 않습니다.
- 실존 인물, 실제 기업, 특정 지역 비하를 넣지 않습니다.
- 폭력과 학대는 자세히 묘사하지 않고, 응징은 법과 양심, 주변의 외면처럼 현실적인 방식으로 그립니다.
- 마지막 장면은 짧은 교훈과 "오늘 이야기는 여기까지입니다" 같은 맺음말로 끝냅니다.

그림 프롬프트(image_prompt):
- 영어로, 따뜻한 한국풍 수채화 일러스트 스타일로 씁니다 (warm Korean watercolor illustration).
- 등장하는 인물은 characters의 외모 설명을 매번 그대로 반복해서 같은 얼굴이 유지되게 합니다.
- 글자나 말풍선은 넣지 않게 합니다 (no text).
"""


def generate_story(topic: str, minutes: int = 10, scenes: int = 8) -> Story:
    # 낭독 속도(약 초당 5글자)로 원하는 길이에 맞는 분량을 알려 준다
    target_chars = minutes * 60 * 5
    user_prompt = (
        f"주제: {topic}\n"
        f"영상 길이: 약 {minutes}분 (낭독 글자 수 합계 약 {target_chars}자)\n"
        f"장면 수: {scenes}개 안팎\n"
        "위 주제로 사연 대본을 써 주세요."
    )

    client = anthropic.Anthropic()
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=64000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "high"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        output_format=Story,
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude가 이 주제로는 대본을 쓰지 않았습니다. 주제를 바꿔 주세요.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("대본이 너무 길어 중간에 잘렸습니다. --minutes 값을 줄여 주세요.")
    return response.parsed_output
