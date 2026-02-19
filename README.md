# RE Briefing Auto (부동산 브리핑 오토)

네이버부동산 매물 링크만 입력하면, 필요한 데이터를 자동 수집·가공하여 **고객 브리핑용 PPT를 자동 생성**하는 프로그램입니다.

## 주요 기능 (Phase 1 MVP)
- **데이터 자동 수집**: 네이버부동산 API를 통한 단지 정보 및 매물 상세 수집
- **이미지 자동화**: 전경 사진 및 평면도 이미지 자동 다운로드
- **실거래가 분석**: 최근 15개년 실거래가 추이 그래프 생성
- **PPT 엔진**: 총 6종의 전문적인 브리핑 슬라이드 자동 생성

## 설치 방법
```bash
# 레포지토리 클론
git clone https://github.com/ksy1477/autobriefingslidemaker.git
cd autobriefingslidemaker

# 의존성 설치
pip install -r requirements.txt
```

## 사용 방법
```bash
# 데모 모드로 실행 (Mock 데이터 사용)
python3 -m src.main --mock

# 실제 데이터로 실행
python3 -m src.main --customer "고객명" --urls "네이버부동산_링크"
```

## 기술 스택
- Python 3.9+
- python-pptx (PPT 생성)
- matplotlib (그래프 생성)
- httpx & BeautifulSoup4 (데이터 수집)
- Pydantic (데이터 모델링)

---
*개발 도구: Gemini 1.5 Pro & Antigravity*
