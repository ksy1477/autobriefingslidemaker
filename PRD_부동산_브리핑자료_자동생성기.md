# PRD: 부동산 임장 브리핑자료 자동생성기

> **Product Name:** 부동산 브리핑 오토 (RE Briefing Auto)
> **Version:** 1.0
> **Last Updated:** 2025-02-19
> **개발 도구:** Claude Code
> **작성 근거:** 실제 운영 중인 브리핑자료 PPT 템플릿 역분석

---

## 1. 제품 개요

### 1.1 문제 정의

부동산 중개사가 고객 임장 브리핑자료를 제작할 때, 네이버부동산·네이버지도·아실 등 여러 사이트에서 수작업으로 정보를 수집하고, 스크린샷을 찍어 PPT에 배치하는 과정에 **건당 1~2시간 이상** 소요된다. 물건이 많아질수록 반복 작업이 기하급수적으로 증가한다.

### 1.2 솔루션

네이버부동산 매물 링크만 입력하면, 필요한 데이터를 자동 수집·가공하여 **고객 브리핑용 PPT를 자동 생성**하는 프로그램을 개발한다.

### 1.3 핵심 가치

| 항목 | AS-IS | TO-BE |
|------|-------|-------|
| 자료 제작 시간 | 물건당 1~2시간 | **5분 이내 (입력 → 생성)** |
| 데이터 정확성 | 수동 입력 실수 가능 | 실시간 크롤링으로 최신 데이터 반영 |
| 디자인 일관성 | 사람마다 편차 | 템플릿 기반 균일한 품질 |

---

## 2. 사용자 흐름 (User Flow)

```
[사용자]
  │
  ├─ 1. 프로그램 실행
  │
  ├─ 2. 입력 정보 기입
  │    ├─ 고객명 (예: "유니냥님")
  │    ├─ 중개사 정보 (최초 1회 설정 후 저장)
  │    └─ 매물 리스트 입력 (반복)
  │         ├─ 네이버부동산 매물 링크 (필수)
  │         ├─ 매매가격 (필수)
  │         ├─ 동/호수 (필수)
  │         ├─ 층수 (필수)
  │         ├─ 향 (선택)
  │         └─ 특이사항 메모 (선택, 예: "올수리", "네고여지 있음")
  │
  ├─ 3. [생성] 버튼 클릭
  │
  ├─ 4. 시스템 자동 처리 (백그라운드)
  │    ├─ 네이버부동산 데이터 크롤링
  │    ├─ 네이버지도 데이터 크롤링
  │    ├─ 아실 데이터 크롤링
  │    └─ PPT 생성
  │
  └─ 5. 완성된 PPT 다운로드
```

---

## 3. 슬라이드 구조 정의

분석된 기존 PPT(25슬라이드)를 기반으로, 슬라이드는 아래와 같은 **모듈 구조**로 생성된다.

### 3.1 고정 슬라이드 (매 브리핑마다 1회)

| 순번 | 슬라이드 타입 | 내용 | 데이터 소스 |
|------|-------------|------|------------|
| 1 | **표지** | 고객명, "내집마련을 위한 브리핑자료", 임장 단지명 목록, 회사 로고 | 사용자 입력 |
| 2 | **중개사 소개** | 중개사 사진, 이름, 자격증, 소속, 연락처 | 사전 설정값 |
| 3 | **물건 리스트 & 투어일정** | 전체 매물 요약 테이블 (지역, 단지명, 동/호수, 평형, 매매가, 향/구조, 특이사항) | 사용자 입력 + 크롤링 |

### 3.2 단지별 반복 슬라이드 (단지 N개 × 아래 세트)

| 순번 | 슬라이드 타입 | 내용 | 데이터 소스 |
|------|-------------|------|------------|
| A | **단지 개요** | 단지 전경사진, 단지명, 위치, 세대수, 주차대수(세대당), 준공년도, 해시태그 | 네이버부동산 |
| B | **입지정보** | 최근접 지하철역까지 도보시간, 강남역까지 대중교통 소요시간, 경로 지도 캡처 | 네이버지도 |
| C | **학군지도 (초등)** | 학구도 지도 캡처, 배정 초등학교명 | 학구도안내서비스 + 네이버지도 |
| D | **학군지도 (중·고등)** | 중·고등학교 학군 지도 캡처 | 아실 |
| E | **실거래가** | 최근 거래건수, 최근 3개월 최고/최저가, 역대 최고가, 최근 실거래 테이블, 15년 매매가 그래프 | 아실 |

### 3.3 매물별 반복 슬라이드 (매물 M개 × 아래 1장)

| 순번 | 슬라이드 타입 | 내용 | 데이터 소스 |
|------|-------------|------|------------|
| F | **매물정보** | 단지 배치도에서 해당 동 위치 표시, 해당 평형 평면도, 매물 상세정보 (방/화장실 수, 향, 구조 등) | 네이버부동산 + 네이버지도 |

### 3.4 슬라이드 생성 순서 로직

```
표지 → 중개사 소개 → 물건 리스트

→ [단지 1] 개요 → 입지 → 학군(초) → 학군(중고) → 실거래가
    → [매물 1-1] 매물정보
    → [매물 1-2] 매물정보
    → ...

→ [단지 2] 개요 → 입지 → 학군(초) → 학군(중고) → 실거래가
    → [매물 2-1] 매물정보
    → ...

→ (단지 N까지 반복)
```

---

## 4. 데이터 수집 명세

### 4.1 네이버부동산 (land.naver.com)

#### 4.1.1 입력값
- **매물 링크** (예: `https://new.land.naver.com/complexes/XXXXX?...articleNo=YYYYYY`)
- 링크에서 `complexId`와 `articleNo`를 파싱

#### 4.1.2 수집 대상 데이터

| 데이터 항목 | 용도 슬라이드 | 추출 방식 |
|------------|-------------|----------|
| 단지명 | 개요, 표지 | API/HTML 파싱 |
| 주소 (구/동) | 개요, 물건리스트 | API/HTML 파싱 |
| 세대수 | 개요 | API/HTML 파싱 |
| 주차대수 / 세대당 주차 | 개요 | API/HTML 파싱 |
| 준공년도 | 개요 | API/HTML 파싱 |
| 단지 전경 사진 | 개요 | 이미지 URL 추출 → 다운로드 |
| 전용면적 / 평형 | 물건리스트, 매물정보 | API/HTML 파싱 |
| 방수 / 화장실수 | 매물정보 | API/HTML 파싱 |
| 해당 평형 평면도 이미지 | 매물정보 | 이미지 URL 추출 → 다운로드 |
| 단지 배치도 이미지 | 매물정보 | 이미지 URL 추출 → 다운로드 |

#### 4.1.3 기술 참고사항

네이버부동산은 내부 API를 통해 데이터를 제공한다. 주요 엔드포인트 패턴:

```
# 단지 기본정보
GET https://new.land.naver.com/api/complexes/{complexId}

# 단지 상세정보 (세대수, 주차 등)
GET https://new.land.naver.com/api/complexes/{complexId}?sameAddressGroup=false

# 매물 상세
GET https://new.land.naver.com/api/articles/{articleNo}

# 단지 사진 목록
GET https://new.land.naver.com/api/complexes/{complexId}/photos

# 평면도
GET https://new.land.naver.com/api/complexes/{complexId}/ground-plans
```

> **⚠️ 주의:** 네이버 API는 User-Agent, Referer 헤더를 검증한다. 적절한 헤더 설정 필요.
> ```
> headers = {
>     "User-Agent": "Mozilla/5.0 ...",
>     "Referer": "https://new.land.naver.com/"
> }
> ```

---

### 4.2 네이버지도 (map.naver.com)

#### 4.2.1 수집 대상 데이터

| 데이터 항목 | 용도 슬라이드 | 추출 방식 |
|------------|-------------|----------|
| 단지 → 최근접 지하철역 도보 소요시간 | 입지정보 | 네이버지도 도보 경로 API / 스크린샷 |
| 단지 → 강남역 대중교통 소요시간 | 입지정보 | 네이버지도 대중교통 경로 API / 스크린샷 |
| 경로 지도 이미지 (도보) | 입지정보 | 스크린샷 캡처 |
| 경로 지도 이미지 (대중교통) | 입지정보 | 스크린샷 캡처 |
| 단지 위치 지도 (위성/일반) | 개요 | 스크린샷 캡처 |
| 단지 배치도 내 동 위치 | 매물정보 | 스크린샷 + 마킹 처리 |

#### 4.2.2 기술 접근 방식

**방식 A: 네이버 지도 API 활용 (권장)**

```
# 도보 경로
GET https://map.naver.com/v5/api/dir/findwalk?...

# 대중교통 경로
GET https://map.naver.com/v5/api/dir/findtransit?...

# Static Map 이미지
GET https://naveropenapi.apigw.ntruss.com/map-static/v2/raster?...
```

> 네이버 클라우드 플랫폼에서 Maps API 키 발급 필요 (월 무료 한도 있음)

**방식 B: Headless 브라우저 스크린샷 (대안)**

Puppeteer/Playwright로 네이버지도를 열고, 경로를 설정한 뒤 해당 영역을 스크린샷으로 캡처.

```javascript
// Puppeteer 예시 의사코드
await page.goto(`https://map.naver.com/v5/directions/...`);
await page.waitForSelector('.route_result');
await page.screenshot({ clip: { x, y, width, height } });
```

#### 4.2.3 최근접 역 판별 로직

1. 네이버부동산에서 단지 좌표(위도/경도) 추출
2. 반경 1km 내 지하철역 목록 조회 (공공데이터포털 지하철역 좌표 DB 활용 또는 하드코딩)
3. 가장 가까운 역을 선택하고, 해당 역까지 도보 경로 조회
4. 역 이름 + 호선 정보 함께 표시 (예: "중계역(7호선)")

#### 4.2.4 강남역 고정 목적지

강남역 좌표: `37.497942, 127.027621` (고정값)

---

### 4.3 아실 (asil.kr)

#### 4.3.1 수집 대상 데이터

| 데이터 항목 | 용도 슬라이드 | 추출 방식 |
|------------|-------------|----------|
| 최근 실거래 내역 (날짜, 평형, 층, 가격) | 실거래가 | API/HTML 파싱 |
| 최근 N개월 거래건수 | 실거래가 | 위 데이터에서 집계 |
| 최근 3개월 최고가 / 최저가 | 실거래가 | 위 데이터에서 집계 |
| 역대 최고가 (금액 + 시기) | 실거래가 | API/HTML 파싱 |
| 15년 매매가 추이 그래프 이미지 | 실거래가 | 스크린샷 캡처 또는 차트 자체 생성 |
| 중·고등학교 학군 지도 이미지 | 학군지도 | 스크린샷 캡처 |

#### 4.3.2 기술 접근 방식

**실거래가 데이터:**

아실 내부 API 또는 **국토교통부 실거래가 공공데이터 API** 활용 가능:

```
# 국토부 아파트 매매 실거래가 API (공공데이터포털)
GET http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev
  ?LAWD_CD={법정동코드5자리}
  &DEAL_YMD={거래년월YYYYMM}
  &serviceKey={API_KEY}
```

> 공공데이터포털(data.go.kr) API 키 발급 필요 (무료)

**15년 매매가 그래프:**

- **방식 A (권장):** 실거래가 데이터를 직접 수집 → Python matplotlib 또는 JS Chart.js로 그래프 자체 생성
- **방식 B:** 아실 웹페이지의 그래프 영역을 Headless 브라우저로 스크린샷

**학군 지도:**

아실의 학군 지도는 Headless 브라우저 스크린샷으로 캡처.

---

### 4.4 학구도안내서비스 (schoolzone.emac.kr)

#### 4.4.1 수집 대상

| 데이터 항목 | 용도 슬라이드 | 추출 방식 |
|------------|-------------|----------|
| 초등학교 학구도 지도 이미지 | 학군지도(초등) | 스크린샷 캡처 |
| 배정 초등학교명 | 학군지도(초등) | HTML 파싱 |

---

## 5. PPT 생성 명세

### 5.1 디자인 사양

기존 PPT 분석 결과 기반 디자인 시스템:

| 항목 | 값 |
|------|---|
| 슬라이드 비율 | 16:9 (와이드스크린) |
| 기본 배경색 | `#FFFFFF` (화이트) |
| 표지 배경 | 다크 톤 + 단지 항공사진 오버레이 |
| 주요 컬러 | `#C8102E` (레드 계열 - 월급쟁이부자들 브랜드) |
| 보조 컬러 | `#333333` (다크 그레이), `#F5F5F5` (라이트 그레이) |
| 본문 폰트 | Pretendard 또는 Noto Sans KR (없으면 맑은 고딕) |
| 제목 폰트 크기 | 28~36pt Bold |
| 본문 폰트 크기 | 12~16pt |
| 출처 표기 폰트 | 9~10pt, 회색 |

### 5.2 슬라이드별 레이아웃 상세

#### 슬라이드 1: 표지

```
┌─────────────────────────────────────────────┐
│  (배경: 아파트 단지 야경/항공 이미지)           │
│                                             │
│         {고객명}님                            │
│    내집마련을 위한 브리핑자료                    │
│                                             │
│    임장브리핑 : {단지1} / {단지2} / ...         │
│                                             │
│              [회사 로고]                       │
└─────────────────────────────────────────────┘
```

#### 슬라이드 2: 중개사 소개

```
┌─────────────────────────────────────────────┐
│                                             │
│  "전문가로서 분석하고,                         │
│   고객의 편에서 중개하겠습니다"                  │
│                                             │
│  [중개사 사진]     공인중개사 [ {이름} ]         │
│                  {소속}                       │
│                  {자격증 목록}                  │
│                  M: {전화번호}                 │
│                  E: {이메일}                   │
│                                [회사 로고]     │
└─────────────────────────────────────────────┘
```

#### 슬라이드 3: 물건리스트 & 투어일정

```
┌─────────────────────────────────────────────┐
│  물건리스트 및 투어일정                         │
│                                             │
│  ┌────┬──────┬──────┬────┬────┬────┬─────┐  │
│  │지역│단지명 │동/호수│평형 │매매가│향   │특이사항│  │
│  ├────┼──────┼──────┼────┼────┼────┼─────┤  │
│  │    │      │      │    │    │    │     │  │
│  │    │      │      │    │    │    │     │  │
│  └────┴──────┴──────┴────┴────┴────┴─────┘  │
│                                [회사 로고]     │
└─────────────────────────────────────────────┘
```

#### 슬라이드 A: 단지 개요

```
┌─────────────────────────────────────────────┐
│ ■ {단지명}                          개요      │
│─────────────────────────────────────────────│
│                                             │
│  {단지명}은(는)                               │
│  {구} {동}에 위치해있으며                       │
│  세대수 {N}세대, 주차대수 {M}대 (세대당 {X}대)   │
│  {YYYY}년 준공된 아파트입니다.                   │
│                                             │
│  #역세권 #대단지 ...       [단지 전경사진]       │
│                           [위성지도 이미지]     │
│                                             │
│  *네이버지도 (https://map.naver.com)           │
│                                [회사 로고]     │
└─────────────────────────────────────────────┘
```

#### 슬라이드 B: 입지정보

```
┌─────────────────────────────────────────────┐
│ ■ {단지명}                       입지정보      │
│─────────────────────────────────────────────│
│                                             │
│  [{역명}({호선}) - 도보 {N}분]                  │
│  [강남역 - 대중교통 {M}분]                     │
│                                             │
│  [도보 경로 지도]        [대중교통 경로 지도]     │
│                                             │
│  *네이버지도 (https://map.naver.com)           │
│                                [회사 로고]     │
└─────────────────────────────────────────────┘
```

#### 슬라이드 C: 학군지도 (초등학교)

```
┌─────────────────────────────────────────────┐
│ ■ 학구도(초등학교)                  학군지도     │
│─────────────────────────────────────────────│
│                                             │
│       [학구도 지도 캡처 이미지]                  │
│                          배정 초등학교:        │
│                          - {학교명}           │
│                                             │
│  *학구도안내서비스 / *네이버지도                  │
│                                [회사 로고]     │
└─────────────────────────────────────────────┘
```

#### 슬라이드 D: 학군지도 (중·고등학교)

```
┌─────────────────────────────────────────────┐
│ ■ 학군지도(중·고등학교)             학군지도     │
│─────────────────────────────────────────────│
│                                             │
│       [아실 학군 지도 캡처 이미지]               │
│                                             │
│  *아실 (https://asil.kr)                     │
│                                [회사 로고]     │
└─────────────────────────────────────────────┘
```

#### 슬라이드 E: 실거래가

```
┌─────────────────────────────────────────────┐
│ ■ {단지명}                       실거래가      │
│─────────────────────────────────────────────│
│                                             │
│  {단지명}은(는) {YYYY}년 {M}월 [{N}]건,        │
│  {YYYY}년 {M}월 [{N}]건 거래되었습니다.         │
│  최근 3개월 최고 [{가격}], 최저 [{가격}]         │
│  최고가 [{가격}] {YY}년 {M}월에 거래             │
│                                             │
│  ┌ 최근 실거래 ┐   ┌ 최근 매매거래 ─────────┐   │
│  │ (테이블)    │   │ (15년 그래프 이미지)    │   │
│  └────────────┘   └─────────────────────┘   │
│  *아실 (https://asil.kr)                     │
│                                [회사 로고]     │
└─────────────────────────────────────────────┘
```

#### 슬라이드 F: 매물정보

```
┌─────────────────────────────────────────────┐
│ ■ {단지명} - {동} {층}층              매물정보   │
│─────────────────────────────────────────────│
│                                             │
│  [단지내 위치]                                 │
│  [배치도에서 해당 동     [해당 평형 평면도]       │
│   빨간 박스 마킹]       [매물 상세정보 텍스트]    │
│                                             │
│                                [회사 로고]     │
└─────────────────────────────────────────────┘
```

---

## 6. 기술 아키텍처

### 6.1 시스템 구성도

```
┌──────────────────────────────────────────────────────┐
│                    사용자 인터페이스                      │
│              (CLI 또는 간단한 Web GUI)                   │
└────────────────────┬─────────────────────────────────┘
                     │ 입력: 고객명, 매물링크[], 중개사정보
                     ▼
┌──────────────────────────────────────────────────────┐
│                   메인 오케스트레이터                     │
│              (main.py / main.ts)                      │
│                                                      │
│  1. 입력값 파싱 (URL에서 complexId, articleNo 추출)      │
│  2. 동일 단지 매물 그룹핑                                │
│  3. 데이터 수집 파이프라인 실행                            │
│  4. PPT 생성 엔진 호출                                  │
└───┬──────────┬──────────┬──────────┬─────────────────┘
    │          │          │          │
    ▼          ▼          ▼          ▼
┌────────┐┌────────┐┌────────┐┌──────────┐
│ 네이버   ││ 네이버   ││ 아실     ││ 학구도    │
│ 부동산   ││ 지도    ││ 크롤러   ││ 크롤러    │
│ 크롤러   ││ 크롤러   ││         ││          │
└────┬───┘└────┬───┘└────┬───┘└─────┬────┘
     │         │         │          │
     ▼         ▼         ▼          ▼
┌──────────────────────────────────────────────────────┐
│              데이터 정규화 & 이미지 저장                   │
│           (temp/ 폴더에 구조화된 JSON + 이미지)           │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│                PPT 생성 엔진                            │
│         (python-pptx 또는 pptxgenjs)                   │
│                                                      │
│  - 슬라이드 템플릿 로드                                  │
│  - 데이터 바인딩                                        │
│  - 이미지 삽입                                          │
│  - 차트/그래프 생성                                      │
│  - .pptx 파일 출력                                      │
└──────────────────────────────────────────────────────┘
```

### 6.2 기술 스택 (권장)

| 레이어 | 기술 | 선택 이유 |
|--------|------|----------|
| 언어 | **Python 3.11+** | 크롤링 생태계 풍부, Claude Code 호환성 |
| HTTP 클라이언트 | **httpx** 또는 **requests** | API 호출 및 HTML 다운로드 |
| HTML 파싱 | **BeautifulSoup4** + **lxml** | 네이버부동산/아실 HTML 파싱 |
| 브라우저 자동화 | **Playwright** (Python) | 지도/학군 스크린샷 캡처 (Headless Chrome) |
| PPT 생성 | **python-pptx** | Python에서 가장 성숙한 PPTX 생성 라이브러리 |
| 차트 생성 | **matplotlib** | 실거래가 15년 추이 그래프 생성 |
| 이미지 처리 | **Pillow** | 스크린샷 크롭, 리사이즈, 동 위치 마킹 |
| CLI | **typer** 또는 **argparse** | 명령줄 인터페이스 |
| Web GUI (선택) | **Streamlit** | 빠른 프로토타이핑 (선택사항) |
| 설정 관리 | **YAML** 또는 **JSON** | 중개사 정보, API 키 등 설정 저장 |

### 6.3 디렉토리 구조

```
re-briefing-auto/
├── README.md
├── requirements.txt
├── config/
│   ├── config.yaml              # API 키, 기본 설정
│   └── agent_profile.yaml       # 중개사 정보 (이름, 자격증, 연락처 등)
├── assets/
│   ├── logo.png                 # 회사 로고
│   ├── agent_photo.png          # 중개사 사진
│   └── cover_background.png     # 표지 배경 이미지
├── src/
│   ├── __init__.py
│   ├── main.py                  # 메인 오케스트레이터
│   ├── models.py                # 데이터 모델 (Pydantic)
│   ├── crawlers/
│   │   ├── __init__.py
│   │   ├── naver_land.py        # 네이버부동산 크롤러
│   │   ├── naver_map.py         # 네이버지도 크롤러
│   │   ├── asil.py              # 아실 크롤러
│   │   └── school_zone.py       # 학구도 크롤러
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── data_aggregator.py   # 데이터 취합 및 정규화
│   │   ├── image_processor.py   # 이미지 크롭/마킹/리사이즈
│   │   └── chart_generator.py   # 실거래가 그래프 생성
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── pptx_generator.py    # PPT 생성 메인 로직
│   │   ├── slide_cover.py       # 표지 슬라이드
│   │   ├── slide_agent.py       # 중개사 소개
│   │   ├── slide_list.py        # 물건리스트
│   │   ├── slide_overview.py    # 단지 개요
│   │   ├── slide_location.py    # 입지정보
│   │   ├── slide_school.py      # 학군지도
│   │   ├── slide_price.py       # 실거래가
│   │   └── slide_property.py    # 매물정보
│   └── utils/
│       ├── __init__.py
│       ├── url_parser.py        # 네이버부동산 URL 파싱
│       └── text_helpers.py      # 가격 포맷팅 등 유틸
├── templates/
│   └── base_template.pptx       # 기본 PPT 템플릿 (마스터 슬라이드 포함)
├── output/                      # 생성된 PPT 출력 폴더
└── tests/
    ├── test_crawlers.py
    ├── test_generators.py
    └── fixtures/                # 테스트용 목업 데이터
```

---

## 7. 데이터 모델

```python
from pydantic import BaseModel
from typing import Optional
from datetime import date

class AgentProfile(BaseModel):
    """중개사 프로필 (사전 설정)"""
    name: str                          # "김경빈"
    photo_path: str                    # 중개사 사진 경로
    company: str                       # "월급쟁이부자들부동산법인중개주식회사"
    qualifications: list[str]          # ["31회 공인중개사", "43회 투자자산운용사", ...]
    phone: str                         # "010-4537-3513"
    email: str                         # "kb@weolbu.com"
    slogan: str                        # "전문가로서 분석하고, 고객의 편에서 중개하겠습니다"
    logo_path: str                     # 회사 로고 이미지 경로

class PropertyInput(BaseModel):
    """사용자가 입력하는 매물 정보"""
    naver_land_url: str                # 네이버부동산 매물 링크
    price: str                         # "6.4억"
    dong: str                          # "124동"
    ho: Optional[str] = None           # "7호" (선택)
    floor: str                         # "7/15층"
    direction: Optional[str] = None    # "동향"
    structure: Optional[str] = None    # "복도식 방2화1"
    memo: Optional[str] = None         # "샷시교체, 욕실수리"

class BriefingInput(BaseModel):
    """전체 브리핑 입력"""
    customer_name: str                 # "유니냥님"
    properties: list[PropertyInput]    # 매물 리스트

# ── 크롤링 후 정규화된 데이터 모델 ──

class ComplexInfo(BaseModel):
    """단지 정보 (크롤링 결과)"""
    complex_id: str
    name: str                          # "중계그린"
    address: str                       # "노원구 중계동"
    total_units: int                   # 3481
    parking_total: int                 # 1311
    parking_per_unit: float            # 0.37
    built_year: int                    # 1990
    hashtags: list[str]                # ["역세권", "대단지"]
    aerial_photo_path: str             # 다운로드된 전경사진 경로
    site_plan_path: Optional[str]      # 배치도 이미지 경로
    satellite_map_path: str            # 위성지도 캡처 경로

class LocationInfo(BaseModel):
    """입지 정보 (크롤링 결과)"""
    complex_id: str
    nearest_station: str               # "중계역"
    station_line: str                  # "7호선"
    walk_minutes: int                  # 2
    gangnam_minutes: int               # 50
    walk_route_image_path: str         # 도보 경로 지도 캡처
    transit_route_image_path: str      # 대중교통 경로 지도 캡처

class SchoolInfo(BaseModel):
    """학군 정보 (크롤링 결과)"""
    complex_id: str
    elementary_name: str               # "서울중계초등학교"
    elementary_map_path: str           # 학구도 캡처 이미지
    middle_high_map_path: str          # 중·고등학교 학군 지도 캡처

class Transaction(BaseModel):
    """개별 실거래 기록"""
    date: date
    area_pyeong: str                   # "21평"
    area_m2: float                     # 49.0
    floor: int
    price: str                         # "5억 9000만원"
    price_raw: int                     # 590000000

class PriceInfo(BaseModel):
    """실거래가 정보 (크롤링 결과)"""
    complex_id: str
    recent_transactions: list[Transaction]
    month1_count: int                  # 이번 달 거래건수
    month1_label: str                  # "2026년 1월"
    month2_count: int                  # 지난 달 거래건수
    month2_label: str                  # "2025년 12월"
    recent_3m_high: str                # "5억 9000만원"
    recent_3m_low: str                 # "5억 5300만원"
    all_time_high: str                 # "7억 2000만원"
    all_time_high_date: str            # "21년 10월"
    price_graph_image_path: str        # 15년 추이 그래프 이미지

class PropertyDetail(BaseModel):
    """매물 상세 (크롤링 + 입력 결합)"""
    complex_id: str
    complex_name: str
    dong: str
    floor: str
    price: str
    direction: Optional[str]
    structure: Optional[str]
    memo: Optional[str]
    floor_plan_image_path: str         # 평면도 이미지
    dong_location_image_path: str      # 배치도에서 동 위치 마킹된 이미지
    rooms: Optional[int] = None        # 방 수
    bathrooms: Optional[int] = None    # 화장실 수
    area_pyeong: Optional[str] = None  # "21평"
    area_m2: Optional[float] = None    # 49.0
```

---

## 8. 핵심 로직 상세

### 8.1 URL 파싱

```python
import re
from urllib.parse import urlparse, parse_qs

def parse_naver_land_url(url: str) -> tuple[str, str]:
    """
    네이버부동산 URL에서 complex_id와 article_no 추출

    지원 URL 패턴:
    - https://new.land.naver.com/complexes/12345?articleNo=67890
    - https://fin.land.naver.com/complexes/12345?articleNo=67890
    - https://land.naver.com/article/info.naver?article_id=67890
    """
    parsed = urlparse(url)
    path_match = re.search(r'/complexes/(\d+)', parsed.path)
    complex_id = path_match.group(1) if path_match else None

    params = parse_qs(parsed.query)
    article_no = params.get('articleNo', [None])[0]

    return complex_id, article_no
```

### 8.2 동일 단지 그룹핑

```python
from collections import OrderedDict

def group_by_complex(properties: list[PropertyInput]) -> OrderedDict:
    """
    매물을 단지별로 그룹핑 (입력 순서 유지)
    같은 complex_id를 가진 매물들을 묶음
    """
    groups = OrderedDict()
    for prop in properties:
        complex_id, _ = parse_naver_land_url(prop.naver_land_url)
        if complex_id not in groups:
            groups[complex_id] = []
        groups[complex_id].append(prop)
    return groups
```

### 8.3 해시태그 자동 생성 로직

```python
def generate_hashtags(complex_info: ComplexInfo, location_info: LocationInfo) -> list[str]:
    tags = []
    if location_info.walk_minutes <= 5:
        tags.append("역세권")
    if complex_info.total_units >= 1000:
        tags.append("대단지")
    if complex_info.parking_per_unit >= 1.0:
        tags.append("주차여유")
    if complex_info.built_year >= 2015:
        tags.append("신축")
    # 추가 조건은 확장 가능
    return tags
```

### 8.4 동 위치 마킹 처리

```python
from PIL import Image, ImageDraw

def mark_dong_on_siteplan(
    siteplan_path: str,
    dong_coordinates: tuple[int, int, int, int],  # (x1, y1, x2, y2)
    output_path: str,
    border_color: str = "red",
    border_width: int = 3
):
    """배치도 이미지에서 특정 동 위치에 빨간 박스 마킹"""
    img = Image.open(siteplan_path)
    draw = ImageDraw.Draw(img)
    draw.rectangle(dong_coordinates, outline=border_color, width=border_width)
    img.save(output_path)
```

> **동 좌표 매핑 과제:** 배치도 이미지에서 특정 동의 좌표를 자동 판별하는 것은 난이도가 높은 과제. 아래 접근 방식 중 선택:
> - **방식 A:** 네이버지도에서 건물별 폴리곤 좌표를 추출하여 이미지 좌표로 변환
> - **방식 B:** OCR로 배치도 내 동 번호 텍스트를 인식하여 위치 특정
> - **방식 C (MVP):** 네이버지도 위성뷰에서 해당 동 중심으로 줌인한 스크린샷 + 마커 핀 배치

### 8.5 실거래가 텍스트 자동 생성

```python
def generate_price_summary(complex_name: str, price_info: PriceInfo) -> str:
    return (
        f"{complex_name}은(는) {price_info.month1_label} "
        f"[{price_info.month1_count}]건, "
        f"{price_info.month2_label} [{price_info.month2_count}]건 "
        f"거래되었습니다.\n"
        f"최근 3개월 최고 [{price_info.recent_3m_high}], "
        f"최저 [{price_info.recent_3m_low}]에 거래되었습니다.\n"
        f"최고가 [{price_info.all_time_high}] "
        f"{price_info.all_time_high_date}에 거래되었습니다."
    )
```

---

## 9. 실행 인터페이스

### 9.1 CLI 인터페이스

```bash
# 기본 실행
python -m src.main \
  --customer "유니냥님" \
  --urls "https://new.land.naver.com/complexes/12345?articleNo=111" \
         "https://new.land.naver.com/complexes/12345?articleNo=222" \
         "https://new.land.naver.com/complexes/67890?articleNo=333"

# 또는 JSON 입력 파일 사용
python -m src.main --input briefing_request.json
```

### 9.2 JSON 입력 파일 예시

```json
{
  "customer_name": "유니냥님",
  "properties": [
    {
      "naver_land_url": "https://new.land.naver.com/complexes/12345?articleNo=111",
      "price": "6.4억",
      "dong": "124동",
      "floor": "7/15층",
      "direction": "동향",
      "structure": "복도식 방2화1",
      "memo": "샷시교체, 욕실수리"
    },
    {
      "naver_land_url": "https://new.land.naver.com/complexes/12345?articleNo=222",
      "price": "6.6억",
      "dong": "115동",
      "floor": "7/15층",
      "direction": "남향",
      "structure": "복도식 방2화1",
      "memo": ""
    }
  ]
}
```

### 9.3 Web GUI (선택 - Streamlit)

```
┌─────────────────────────────────────────────────┐
│  🏠 부동산 브리핑자료 자동생성기                      │
│                                                 │
│  고객명: [_______________]                        │
│                                                 │
│  매물 추가 ──────────────────────────             │
│  │ 네이버부동산 링크: [___________________________] │
│  │ 매매가격: [________]  동: [______]              │
│  │ 층수: [________]  향: [______]                 │
│  │ 특이사항: [___________________________]        │
│  │                          [+ 매물 추가]         │
│  ────────────────────────────────────            │
│                                                 │
│  추가된 매물: 7건 (3개 단지)                        │
│                                                 │
│  [🔄 브리핑자료 생성]                               │
│                                                 │
│  ✅ 생성 완료! [📥 다운로드]                        │
└─────────────────────────────────────────────────┘
```

---

## 10. API 키 및 외부 서비스 요구사항

| 서비스 | 필요 여부 | 용도 | 발급 방법 |
|--------|----------|------|----------|
| 공공데이터포털 API | 권장 | 실거래가 데이터 (국토부) | data.go.kr 회원가입 → API 키 발급 (무료) |
| 네이버 클라우드 Maps API | 선택 | Static Map 이미지, 경로 API | ncloud.com → Maps API 키 발급 (월 무료한도) |
| Playwright/Chrome | 필수 | 스크린샷 캡처 (지도, 학군, 그래프) | `pip install playwright && playwright install chromium` |

---

## 11. 개발 단계 (Milestone)

### Phase 1: MVP (핵심 기능) — 2~3주

| 태스크 | 설명 | 우선순위 |
|--------|------|---------|
| URL 파서 | 네이버부동산 URL → complexId, articleNo 추출 | P0 |
| 네이버부동산 크롤러 | 단지정보(이름, 세대수, 준공 등) + 전경사진 + 평면도 수집 | P0 |
| 아실 크롤러 | 실거래가 데이터 수집 + 그래프 스크린샷 | P0 |
| PPT 기본 생성 | python-pptx로 기본 레이아웃 슬라이드 생성 | P0 |
| 실거래가 그래프 | matplotlib로 15년 추이 차트 자체 생성 | P0 |
| CLI 인터페이스 | 커맨드라인 입력 → PPT 출력 | P0 |

### Phase 2: 지도/학군 연동 — 1~2주

| 태스크 | 설명 | 우선순위 |
|--------|------|---------|
| 네이버지도 크롤러 | 도보 경로/대중교통 경로 스크린샷 캡처 | P1 |
| 학구도 크롤러 | 초등학교 학구도 스크린샷 캡처 | P1 |
| 아실 학군 지도 | 중·고등학교 학군 지도 스크린샷 | P1 |
| 동 위치 마킹 | 배치도에서 해당 동 표시 | P1 |

### Phase 3: 품질 개선 — 1주

| 태스크 | 설명 | 우선순위 |
|--------|------|---------|
| PPT 디자인 고도화 | 기존 PPT 템플릿 수준의 디자인 매칭 | P2 |
| 에러 핸들링 | 크롤링 실패 시 대체 처리 (빈 슬라이드 + 경고) | P2 |
| Streamlit GUI | 웹 인터페이스 추가 | P2 |
| 캐싱 | 동일 단지 재조회 시 캐시 활용 | P2 |

### Phase 4: 확장 (선택) — 이후

| 태스크 | 설명 | 우선순위 |
|--------|------|---------|
| 전세/월세 지원 | 매매 외 전세/월세 실거래가 표시 | P3 |
| 커스텀 슬라이드 | 사용자가 슬라이드 순서/포함 여부 선택 | P3 |
| 멀티 에이전트 | 여러 중개사 프로필 관리 | P3 |
| 자동 업데이트 | 실거래가 변동 시 기존 PPT 자동 갱신 | P3 |

---

## 12. 리스크 및 대응 방안

| 리스크 | 영향도 | 발생 가능성 | 대응 방안 |
|--------|--------|-----------|----------|
| **네이버부동산 API 차단/변경** | 높음 | 중간 | User-Agent 로테이션, 요청 간격 조절(1~3초), Selenium/Playwright 대안 경로 준비 |
| **아실 크롤링 차단** | 높음 | 중간 | 국토부 공공 API를 1차 데이터 소스로 사용, 아실은 그래프 스크린샷 전용 |
| **네이버지도 스크린샷 품질** | 중간 | 낮음 | 해상도 설정(deviceScaleFactor: 2), 로딩 대기 시간 충분히 확보 |
| **동 위치 자동 마킹 실패** | 중간 | 높음 | MVP에서는 전체 배치도만 포함, 동 위치 마킹은 Phase 2에서 반자동화 |
| **네이버부동산 URL 형식 변경** | 중간 | 낮음 | 여러 URL 패턴을 파서에 등록, 정규식 기반 유연한 파싱 |
| **한글 폰트 PPT 호환성** | 낮음 | 중간 | python-pptx에서 맑은 고딕(시스템 기본 폰트) 사용, 폰트 임베딩 불필요 |

---

## 13. 크롤링 시 유의사항

### 13.1 요청 제한 및 예의

```python
import time
import random

# 요청 간 딜레이 (서버 부하 방지)
REQUEST_DELAY_MIN = 1.0  # 초
REQUEST_DELAY_MAX = 3.0  # 초

def polite_delay():
    time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))
```

### 13.2 필수 헤더

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://new.land.naver.com/",
}
```

### 13.3 법적 고려

- 수집 데이터는 **내부 업무용 브리핑자료 제작 목적**으로만 사용
- 출처 표기 필수 (슬라이드에 이미 포함됨: "*네이버지도", "*아실" 등)
- 대량 자동 수집이 아닌 **건별 소량 조회**이므로 합리적 사용 범위

---

## 14. 테스트 전략

### 14.1 단위 테스트

```python
# tests/test_url_parser.py
def test_parse_standard_url():
    url = "https://new.land.naver.com/complexes/12345?articleNo=67890"
    complex_id, article_no = parse_naver_land_url(url)
    assert complex_id == "12345"
    assert article_no == "67890"

# tests/test_price_summary.py
def test_generate_price_summary():
    result = generate_price_summary("중계그린", mock_price_info)
    assert "중계그린" in result
    assert "거래되었습니다" in result
```

### 14.2 통합 테스트

- 실제 네이버부동산 URL로 전체 파이프라인 실행
- 생성된 PPT 파일 열어서 슬라이드 수, 내용 검증
- 스크린샷 이미지 해상도/크기 확인

### 14.3 품질 검증 체크리스트

- [ ] 모든 슬라이드에 회사 로고 포함
- [ ] 출처 표기 정확 (네이버지도, 아실 등)
- [ ] 가격 포맷 일관성 (예: "6억 4000만원" 형식)
- [ ] 이미지 해상도 최소 150dpi
- [ ] 단지별 슬라이드 순서 정확
- [ ] 폰트 깨짐 없음
- [ ] 데이터 누락 시 빈 필드 대신 "정보 없음" 표시

---

## 15. Claude Code 개발 가이드

Claude Code로 개발 시 아래 순서로 진행을 권장합니다.

### 15.1 개발 순서 프롬프트 예시

```
# Step 1: 프로젝트 셋업
"requirements.txt와 기본 디렉토리 구조를 만들어줘. 
Python 3.11+, python-pptx, playwright, httpx, beautifulsoup4, 
matplotlib, Pillow, pydantic, typer를 포함해줘."

# Step 2: 데이터 모델 정의
"PRD의 Section 7 데이터 모델을 models.py에 구현해줘."

# Step 3: URL 파서
"네이버부동산 URL을 파싱하는 url_parser.py를 만들어줘."

# Step 4: 네이버부동산 크롤러
"naver_land.py를 만들어서 complexId로 단지정보를 가져오고, 
전경사진과 평면도 이미지를 다운로드하는 기능을 구현해줘."

# Step 5: 아실 크롤러 + 실거래가 그래프
"asil.py와 chart_generator.py를 만들어서 실거래가 데이터를 
수집하고 matplotlib으로 15년 추이 그래프를 생성해줘."

# Step 6: PPT 생성 엔진
"pptx_generator.py를 만들어서 모든 슬라이드를 생성하는 
메인 엔진을 구현해줘. PRD Section 5.2 레이아웃을 따라줘."

# Step 7: 통합 + CLI
"main.py에서 전체 파이프라인을 연결하고, 
CLI에서 실행할 수 있게 해줘."
```

### 15.2 Claude Code 활용 팁

- 각 크롤러 모듈은 **독립적으로 테스트 가능**하게 작성 (mock 데이터로 PPT 생성 테스트 가능)
- 크롤링 결과를 중간 JSON 파일로 저장하면 디버깅이 쉬움
- python-pptx의 Inches, Pt, Emu 단위 변환에 주의
- Playwright 스크린샷은 `page.screenshot(full_page=False, clip={...})` 으로 특정 영역만 캡처

---

## 16. 성공 지표

| 지표 | 목표 |
|------|------|
| 1건 매물 기준 PPT 생성 시간 | < 60초 |
| 7건 매물 (3단지) 기준 전체 생성 시간 | < 5분 |
| 크롤링 성공률 | > 95% |
| 생성된 PPT 슬라이드 수 정확도 | 100% (입력 기반 예측 가능) |
| 사용자 수동 수정 필요 빈도 | < 10% (대부분 그대로 사용 가능) |

---

*이 PRD는 실제 운영 중인 브리핑자료 PPT 25슬라이드를 역분석하여 작성되었습니다.*
*네이버부동산 매물 링크를 입력하면 표지 → 중개사 소개 → 물건리스트 → (단지별: 개요/입지/학군/실거래가) → (매물별: 매물정보) 순으로 자동 생성됩니다.*
