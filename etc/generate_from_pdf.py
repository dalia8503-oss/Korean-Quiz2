"""
초급 1-2_문법 및 단어.pdf 기반 카테고리별 퀴즈 생성 스크립트
Gemini File API를 사용하여 이미지 기반 PDF를 직접 읽어 문제를 생성합니다.
"""
import re, json, pathlib, shutil, tempfile
from google import genai

# ── API 키 읽기 (config.js는 상위 폴더에 위치) ──────────────────────────────
config_path = pathlib.Path(__file__).parent.parent / "config.js"
with open(config_path, encoding="utf-8") as f:
    m = re.search(r'GEMINI_API_KEY:\s*["\']([^"\']+)["\']', f.read())
    if not m:
        raise RuntimeError("config.js에서 GEMINI_API_KEY를 찾을 수 없습니다.")
    API_KEY = m.group(1)

client = genai.Client(api_key=API_KEY)

# ── PDF 업로드 (Gemini File API — 이미지 기반 PDF도 인식 가능) ──────────────
PDF_PATH = pathlib.Path(__file__).parent / "초급 1-2_문법 및 단어.pdf"

# 파일명에 한글이 있으면 HTTP 헤더 인코딩 오류가 발생하므로 ASCII 임시 파일로 복사 후 업로드
print("PDF 파일을 Gemini에 업로드하는 중...", flush=True)
_tmp = pathlib.Path(tempfile.mktemp(suffix=".pdf"))
shutil.copy2(PDF_PATH, _tmp)
try:
    uploaded_pdf = client.files.upload(
        file=_tmp,
        config={"mime_type": "application/pdf", "display_name": "korean_textbook"},
    )
finally:
    _tmp.unlink(missing_ok=True)
print(f"업로드 완료: {uploaded_pdf.name}", flush=True)

# ── 시스템 메시지 ─────────────────────────────────────────────────────────
SYSTEM_MSG = (
    "당신은 삼성중공업 외국인 근로자를 위한 한국어 교육 전문가입니다. "
    "반드시 순수 JSON만 출력하세요. 마크다운(```)을 절대 쓰지 마세요."
)

# ── 빈칸 어휘 넣기 세부 카테고리 (명사·대명사·동사·형용사·부사·의문사) ─────
VOCAB_SUBCATEGORIES = [
    (
        "명사",
        "빈칸에 현장·직장 명사(회사, 공장, 안전모, 작업복, 식당 등)를 넣는 문제",
        "예: 오늘 ___ 에서 용접 작업을 합니다. → 정답: 공장",
    ),
    (
        "대명사",
        "빈칸에 지시 대명사(이것/그것/저것, 여기/거기/저기, 이분/그분 등)를 넣는 문제",
        "예: ___ 가 제 안전모입니다. → 정답: 이것",
    ),
    (
        "동사",
        "빈칸에 현장 동사(착용하다, 확인하다, 출근하다, 용접하다 등)를 기본형 또는 활용형으로 넣는 문제",
        "예: 작업 전에 반드시 안전 장비를 ___ 해야 합니다. → 정답: 착용",
    ),
    (
        "형용사",
        "빈칸에 현장 형용사(뜨겁다, 위험하다, 무겁다, 피곤하다 등)를 활용형으로 넣는 문제",
        "예: 쇠를 불로 달구면 매우 ___ 니다. → 정답: 뜨겁습",
    ),
    (
        "부사",
        "빈칸에 현장 부사(반드시, 조심히, 빨리, 함께, 천천히 등)를 넣는 문제",
        "예: 계단에서는 ___ 내려오세요. → 정답: 천천히",
    ),
    (
        "의문사",
        "빈칸에 의문사(언제, 어디, 누가, 무엇, 어떻게, 왜 등)를 넣는 문제",
        "예: ___ 퇴근합니까? → 정답: 언제",
    ),
]

CATEGORIES = [
    {
        "name": "빈칸에 알맞은 어휘 넣기",
        "key": "vocab_fill",
        "color": "#2e6da4",
        "instruction": "문장에서 ___ 부분에 들어갈 알맞은 어휘를 고르는 4지선다 문제. 선택지는 어휘 4개.",
    },
    {
        "name": "잘못 사용한 어휘 찾기",
        "key": "wrong_word",
        "color": "#dc3545",
        "instruction": "문장에서 틀리게 쓰인 단어를 **단어** 형식으로 표시하고, 올바른 단어를 선택지 4개 중 고르는 문제.",
        "example": {
            "question": "오늘 점심에 밥을 **마셨습니다**.",
            "choices": ["먹었습니다", "입었습니다", "잤습니다", "걸었습니다"],
            "answer": "먹었습니다",
            "explanation": "밥은 '마시다'가 아니라 '먹다'를 사용합니다."
        },
    },
    {
        "name": "비슷한 의미의 문장 고르기",
        "key": "similar_meaning",
        "color": "#6f42c1",
        "instruction": "주어진 문장과 가장 비슷한 의미의 문장을 4지선다에서 고르는 문제.",
        "example": {
            "question": "저는 지금 배가 고픕니다.",
            "choices": [
                "저는 지금 먹고 싶습니다.",
                "저는 지금 피곤합니다.",
                "저는 지금 목이 마릅니다.",
                "저는 지금 기분이 좋습니다."
            ],
            "answer": "저는 지금 먹고 싶습니다.",
            "explanation": "'배가 고프다'는 음식을 먹고 싶은 상태로, '먹고 싶다'와 의미가 비슷합니다."
        },
    },
    {
        "name": "적절한 문법 표현 넣기",
        "key": "grammar_fill",
        "color": "#28a745",
        "instruction": "문장에서 ___ 부분에 들어갈 알맞은 문법 표현(조사·어미·표현)을 고르는 4지선다 문제.",
        "example": {
            "question": "저는 공장___ 일합니다.",
            "choices": ["에서", "에", "으로", "한테"],
            "answer": "에서",
            "explanation": "행동이 일어나는 장소에는 조사 '에서'를 사용합니다."
        },
    },
    {
        "name": "문장 연결하기",
        "key": "sentence_connect",
        "color": "#fd7e14",
        "instruction": "두 문장 사이의 ___ 에 들어갈 알맞은 연결 표현(접속사·연결어미)을 4지선다에서 고르는 문제.",
        "example": {
            "question": "오늘 몸이 아팠습니다. ___ 병원에 갔습니다.",
            "choices": ["그래서", "그런데", "하지만", "그리고"],
            "answer": "그래서",
            "explanation": "'그래서'는 앞 문장의 원인·이유에 따른 결과를 나타냅니다."
        },
    },
]


def generate_vocab_fill(n_per_sub: int = 2) -> list:
    """빈칸 어휘 넣기: 6개 세부 카테고리별 n_per_sub개씩 = 총 12문제"""
    sub_lines = []
    for sub, desc, ex in VOCAB_SUBCATEGORIES:
        sub_lines.append(
            f"  [{sub}] {desc} — {n_per_sub}문제\n  예시: {ex}"
        )
    sub_block = "\n".join(sub_lines)
    total = len(VOCAB_SUBCATEGORIES) * n_per_sub

    prompt = f"""첨부된 PDF 교재(초급 1-2 한국어 문법 및 단어)를 꼼꼼히 읽고,
아래 세부 카테고리별로 [빈칸에 알맞은 어휘 넣기] 문제를 정확히 {total}개 생성하세요.

[세부 카테고리별 요구 사항]
{sub_block}

공통 조건:
- 대상: 삼성중공업 외국인 근로자 (한국어 초급 1-2 수준)
- 직장·현장·일상 맥락의 문장 사용
- 4지선다, 정답 1개, 중복 없음
- 출력 JSON에 반드시 "subcategory" 필드 포함

출력 형식 (총 {total}개):
{{"quizzes": [
  {{"subcategory": "명사", "question": "...", "choices": [...], "answer": "...", "explanation": "..."}},
  {{"subcategory": "대명사", ...}},
  ...
]}}"""

    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[uploaded_pdf, prompt],
        config={"system_instruction": SYSTEM_MSG},
    )
    raw = re.sub(r"```json\s*|\s*```", "", resp.text.strip()).strip()
    return json.loads(raw)["quizzes"]


def generate_for_category(cat: dict, n: int = 12) -> list:
    """vocab_fill 외 카테고리 공통 생성 함수"""
    example_json = json.dumps(cat["example"], ensure_ascii=False, indent=2)
    prompt = f"""첨부된 PDF 교재(초급 1-2 한국어 문법 및 단어)를 꼼꼼히 읽고,
[{cat['name']}] 유형의 한국어 문제 {n}개를 만드세요.

[유형 설명]
{cat['instruction']}

[문제 형식 예시]
{example_json}

조건:
- 대상: 삼성중공업 외국인 근로자 (한국어 초급 1-2 수준)
- 직장·일상생활·안전 관련 어휘 중심
- 각 문제: 선택지 4개, 정답 1개
- 다양하고 중복 없는 문제 {n}개

다음 JSON 형식으로만 출력:
{{"quizzes": [ ... {n}개 ... ]}}"""

    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[uploaded_pdf, prompt],
        config={"system_instruction": SYSTEM_MSG},
    )
    raw = re.sub(r"```json\s*|\s*```", "", resp.text.strip()).strip()
    return json.loads(raw)["quizzes"]


def main():
    all_q = []
    qid = 1
    for cat in CATEGORIES:
        print(f"[{cat['name']}] 생성 중...", flush=True)
        try:
            if cat["key"] == "vocab_fill":
                qs = generate_vocab_fill(n_per_sub=2)
            else:
                qs = generate_for_category(cat, n=12)

            for q in qs:
                entry = {
                    "id": f"{cat['key']}_{qid:03d}",
                    "category": cat["name"],
                    "category_key": cat["key"],
                    "color": cat["color"],
                    "question": q.get("question", ""),
                    "choices": q.get("choices", []),
                    "answer": q.get("answer", ""),
                    "explanation": q.get("explanation", ""),
                }
                if "subcategory" in q:
                    entry["subcategory"] = q["subcategory"]
                all_q.append(entry)
                qid += 1
            print(f"  → {len(qs)}개 완료", flush=True)
        except Exception as e:
            print(f"  → 오류: {e}", flush=True)

    # quiz_category.json은 etc/ 폴더 안에 저장
    out = pathlib.Path(__file__).parent / "quiz_category.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_q, f, ensure_ascii=False, indent=2)
    print(f"\n총 {len(all_q)}개 저장 → {out}")


if __name__ == "__main__":
    main()
