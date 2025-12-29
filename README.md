# AnswerSelector (민원답변검색기) v1.0.0

**AnswerSelector**는 반복적인 민원 답변 업무의 효율성을 극대화하기 위해 개발된 **AI 기반 유사 답변 검색 및 관리 솔루션**입니다.
단순 키워드 매칭을 넘어, 문장의 의미를 이해하는 **Semantic Search** 기술을 통해 사용자의 질문과 가장 유사한 과거 답변을 찾아줍니다.

---

## 🚀 주요 기능 (Key Features)

### 1. 체계적인 카테고리 필터링
-   `대분류` > `중분류` > `소분류`로 이어지는 3단계 계층 구조를 지원합니다.
-   데이터베이스 기반으로 카테고리가 동적으로 로드되어, 데이터 변경 시 유연하게 대응합니다.

### 2. AI 의미 기반 검색 (Semantic Search)
-   **ONNX 포맷**의 임베딩 모델을 활용하여, 질문의 의도와 맥락이 유사한 답변을 검색합니다.
-   단어가 정확히 일치하지 않아도 의미상 유사하면 검색됩니다. (※ 언어모델을 별도로 다운로드해야 합니다)

### 3. 강력한 템플릿 관리
-   자주 사용하는 서문/본문/결문을 조합해 개인 템플릿으로 저장하고, 즉시 불러올 수 있습니다.

### 4. 데이터 빌더 (Data Builder) 도구 제공
-   엑셀(Excel)로 정리된 데이터를 앱에서 사용하는 고성능 DB(SQLite + FAISS/Numpy) 형식으로 자동 변환해주는 전용 툴을 제공합니다.

---

## 🛠 기술 스택 (Tech Stack)

-   **Language**: Python 3.12
-   **GUI Framework**: wxPython (Native Look & Feel)
-   **AI Engine**: ONNX Runtime (w/ Quantized Models)
-   **Database**: SQLite
-   **Build Tool**: PyInstaller

---

## 📦 설치 및 실행 (Installation & Usage)

### 실행 파일 사용 시
1.  배포된 `AnswerSelector` 폴더를 다운로드합니다.
2.  `AnswerSelector.exe`를 실행합니다.

### 개발 환경 설정 (For Developers)

```bash
# 1. 저장소 클론
git clone https://github.com/duruhrene/answerselector.git

# 2. 필수 패키지 설치
pip install -r requirements.txt

# 3. 앱 실행
python main.py
```

---

## 📜 라이선스 (License)

**Copyright (c) 2025-2026 Duruhrene. All rights reserved.**
