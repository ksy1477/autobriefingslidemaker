"""
부동산 브리핑자료 자동생성기 - 데이터 모델
PRD Section 7 기반 Pydantic 모델 정의
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class AgentProfile(BaseModel):
    """중개사 프로필 (사전 설정)"""
    name: str                          # "홍길동"
    photo_path: str                    # 중개사 사진 경로
    company: str                       # "부동산중개법인"
    qualifications: List[str]          # ["공인중개사", ...]
    phone: str                         # "010-0000-0000"
    email: str                         # "agent@example.com"
    slogan: str                        # 인사말
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
    properties: List[PropertyInput]    # 매물 리스트


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
    hashtags: List[str]                # ["역세권", "대단지"]
    aerial_photo_path: Optional[str] = None   # 다운로드된 전경사진 경로
    site_plan_path: Optional[str] = None      # 배치도 이미지 경로
    satellite_map_path: Optional[str] = None  # 위성지도 캡처 경로


class LocationInfo(BaseModel):
    """입지 정보 (크롤링 결과) — Phase 2"""
    complex_id: str
    nearest_station: str = ""          # "중계역"
    station_line: str = ""             # "7호선"
    walk_minutes: int = 0              # 2
    gangnam_minutes: int = 0           # 50
    walk_route_image_path: Optional[str] = None
    transit_route_image_path: Optional[str] = None


class SchoolInfo(BaseModel):
    """학군 정보 (크롤링 결과) — Phase 2"""
    complex_id: str
    elementary_name: str = ""
    elementary_map_path: Optional[str] = None
    middle_high_map_path: Optional[str] = None


class Transaction(BaseModel):
    """개별 실거래 기록"""
    date: date
    area_pyeong: str                   # "21평"
    area_m2: float                     # 49.0
    floor: int
    price: str                         # "5억 9000만원"
    price_raw: int                     # 590000000 (원 단위)


class PriceInfo(BaseModel):
    """실거래가 정보 (크롤링 결과)"""
    complex_id: str
    recent_transactions: List[Transaction] = []
    month1_count: int = 0              # 이번 달 거래건수
    month1_label: str = ""             # "2026년 1월"
    month2_count: int = 0              # 지난 달 거래건수
    month2_label: str = ""             # "2025년 12월"
    recent_3m_high: str = ""           # "5억 9000만원"
    recent_3m_low: str = ""            # "5억 5300만원"
    all_time_high: str = ""            # "7억 2000만원"
    all_time_high_date: str = ""       # "21년 10월"
    price_graph_image_path: Optional[str] = None  # 15년 추이 그래프 이미지


class PropertyDetail(BaseModel):
    """매물 상세 (크롤링 + 입력 결합)"""
    complex_id: str
    complex_name: str
    dong: str
    floor: str
    price: str
    direction: Optional[str] = None
    structure: Optional[str] = None
    memo: Optional[str] = None
    floor_plan_image_path: Optional[str] = None   # 평면도 이미지
    dong_location_image_path: Optional[str] = None  # 배치도에서 동 위치
    rooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area_pyeong: Optional[str] = None  # "21평"
    area_m2: Optional[float] = None    # 49.0


class ComplexData(BaseModel):
    """단지별 통합 데이터 (슬라이드 생성에 사용)"""
    complex_info: ComplexInfo
    location_info: Optional[LocationInfo] = None
    school_info: Optional[SchoolInfo] = None
    price_info: Optional[PriceInfo] = None
    properties: List[PropertyDetail] = []
