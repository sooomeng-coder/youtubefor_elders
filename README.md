# 권선징악 사연 영상 자동 제작

어르신 시청자를 위한 권선징악 사연 영상을 만드는 파이프라인입니다.

```
주제 → 대본(Claude) → 문장별 음성(Edge TTS) → 화면+큰 자막 → 영상(mp4) + 썸네일 + 업로드 정보
```

## 준비

1. [Python](https://www.python.org/downloads/) 3.10 이상과 [ffmpeg](https://ffmpeg.org/download.html)를 설치합니다.
   (Windows: `winget install Gyan.FFmpeg`, Mac: `brew install ffmpeg`)
2. 필요한 패키지를 설치합니다.
   ```
   pip install -r requirements.txt
   ```
3. 대본 자동 생성까지 쓰려면 [Claude API 키](https://console.anthropic.com/)를 `ANTHROPIC_API_KEY` 환경변수로 넣습니다.
   (Windows: `setx ANTHROPIC_API_KEY "sk-ant-..."` 후 새 터미널 열기)

## 사용법

```
# 1) 예시 대본으로 영상 만들기 (API 키 없어도 됨)
python make_video.py --story samples/sample_story.json

# 2) 주제만 주고 대본부터 자동으로
python make_video.py --topic "시어머니 구박한 며느리의 최후"

# 3) 추천: 대본만 먼저 뽑아서 고친 다음 영상 만들기
python make_video.py --topic "유산 욕심낸 형제" --script-only
python make_video.py --story "output/20261007_1200_.../story.json"
```

결과는 `output/<이름>/` 폴더에 생깁니다.

| 파일 | 내용 |
|---|---|
| `video.mp4` | 1920×1080 영상 |
| `thumbnail.jpg` | 1280×720 썸네일 (노란 큰 글씨) |
| `upload.txt` | 제목, 설명, 해시태그, AI 창작 안내문, 장면별 그림 프롬프트 |
| `story.json` | 대본. 고친 뒤 `--story`로 다시 만들 수 있음 |

### 옵션

| 옵션 | 설명 |
|---|---|
| `--minutes 15` | 목표 영상 길이(분). 기본 10 |
| `--voice ko-KR-InJoonNeural` | 남성 목소리. 기본은 차분한 여성 목소리 `ko-KR-SunHiNeural` |
| `--rate -15%` | 말 빠르기. 기본 `-10%` (보통보다 조금 느리게) |
| `--bgm 음악.mp3` | 배경음악을 작게 깝니다 |
| `--images 폴더` | 장면 그림 폴더. 기본은 결과 폴더의 `images/` |
| `--silent` | 음성 없이 화면만 빠르게 확인하는 테스트 모드 |
| `--font 폰트파일` | 자막 폰트. 기본은 함께 들어 있는 Pretendard |

### 장면 그림 넣기

`upload.txt`의 장면별 그림 프롬프트로 그림을 만들어 `images/scene_01.png`, `scene_02.png` …로 저장하고
같은 명령을 다시 실행하면 해당 장면 배경으로 들어갑니다. 그림이 없는 장면은 단색 배경에 장면 제목이 나옵니다.
음성 파일은 `work/` 폴더에 남아 있어서 다시 만들 때는 빠르게 끝납니다.

## 유튜브에 올릴 때 지킬 것

- **AI 표시**: 그림이나 목소리를 AI로 만들었다면 업로드 화면에서 "변경되거나 합성된 콘텐츠"를 **예**로 선택하세요.
- **실화라고 하지 않기**: 지어낸 이야기를 실화처럼 소개하면 정책 위반이 될 수 있습니다. 영상 왼쪽 위에 "AI 창작 사연" 표시가 들어가고, 설명란 안내문도 `upload.txt`에 들어 있습니다.
- **수익화**: 똑같은 틀로 찍어낸 영상은 "반복적인 콘텐츠"로 수익화가 거절되기 쉽습니다. 대본을 직접 다듬고, 그림과 연출에 손을 대 주세요.

## 폰트

`fonts/Pretendard-ExtraBold.otf` — [Pretendard](https://github.com/orioncactus/pretendard), SIL Open Font License 1.1 (`fonts/Pretendard-LICENSE.txt`).

## 유아 학습 영상 (숫자 세기, 단어 카드)

이모지 그림이 하나씩 켜지면서 숫자를 세고, 큰 숫자와 단어를 또박또박 읽어 주는 아이용 영상입니다.
API 키 없이 학습 대본 JSON만으로 만듭니다.

```
# 스페인어 숫자 1~10 (과일 세기) 샘플
python make_kids_video.py --lesson samples/kids_numbers_es.json

# 음성 없이 화면만 빠르게 확인
python make_kids_video.py --lesson samples/kids_numbers_es.json --silent
```

결과는 `output/<대본 파일 이름>/`에 `video.mp4`, `thumbnail.jpg`, `upload.txt`로 생깁니다.

- 다른 언어로 만들려면 JSON을 복사해서 문장(`intro`, `count_words`, `question`, `lines`, `outro`)과
  `voice`만 바꾸면 됩니다. 예: 일본어 `ja-JP-NanamiNeural`, 포르투갈어 `pt-BR-FranciscaNeural`.
- 카드마다 `emoji` 대신 `image`에 그림 파일 경로를 넣으면 직접 만든 그림이 들어갑니다.
- `count_words`를 비우고 `count`를 1로 두면 동물, 색깔 같은 단어 카드 영상이 됩니다.
- 업로드할 때 시청자층은 반드시 '아동용'으로 설정하세요.
