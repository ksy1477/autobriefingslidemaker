"""
네이버부동산 크롤러
단지정보, 매물상세, 이미지 다운로드
"""
import os
import time
import random
import httpx
from typing import Optional, Dict, Any, List

from src.models import ComplexInfo, PropertyDetail
from src.utils.url_parser import parse_naver_land_url


# 네이버부동산 API 헤더
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://new.land.naver.com/",
    "Accept": "*/*",
}

BASE_URL = "https://new.land.naver.com/api"


def polite_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    """서버 부하 방지를 위한 랜덤 딜레이"""
    time.sleep(random.uniform(min_sec, max_sec))


def _api_get(endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """네이버부동산 API GET 요청"""
    url = f"{BASE_URL}{endpoint}"
    try:
        with httpx.Client(headers=HEADERS, timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"[ERROR] API 호출 실패: {url} - {e}")
        return None


def _download_image(url: str, save_path: str) -> bool:
    """이미지 다운로드"""
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with httpx.Client(headers=HEADERS, timeout=30.0) as client:
            response = client.get(url)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                f.write(response.content)
        return True
    except Exception as e:
        print(f"[ERROR] 이미지 다운로드 실패: {url} - {e}")
        return False


def fetch_complex_info(complex_id: str, temp_dir: str = "temp") -> Optional[ComplexInfo]:
    """
    단지 기본정보 조회

    Args:
        complex_id: 단지 ID
        temp_dir: 이미지 저장 임시 폴더

    Returns:
        ComplexInfo 또는 None
    """
    data = _api_get(f"/complexes/{complex_id}", params={"sameAddressGroup": "false"})
    if not data:
        return None

    polite_delay()

    # 단지 기본정보 추출
    complex_detail = data.get("complexDetail", data)
    name = complex_detail.get("complexName", "")
    address_parts = []
    if complex_detail.get("cortarAddress"):
        address_parts.append(complex_detail["cortarAddress"])
    elif complex_detail.get("address"):
        address_parts.append(complex_detail["address"])
    address = " ".join(address_parts) if address_parts else ""

    total_units = complex_detail.get("totalHouseholdCount", 0)
    parking_total = complex_detail.get("parkingCount", 0)
    parking_per_unit = round(parking_total / total_units, 2) if total_units > 0 else 0
    built_year = complex_detail.get("useApproveYmd", "0000")[:4]

    try:
        built_year = int(built_year)
    except (ValueError, TypeError):
        built_year = 0

    # 전경사진 다운로드
    aerial_photo_path = None
    photos_data = _api_get(f"/complexes/{complex_id}/photos")
    if photos_data and isinstance(photos_data, list) and len(photos_data) > 0:
        first_photo = photos_data[0]
        photo_url = first_photo.get("photoUrl", "")
        if photo_url:
            aerial_photo_path = os.path.join(temp_dir, complex_id, "aerial.jpg")
            if not _download_image(photo_url, aerial_photo_path):
                aerial_photo_path = None
        polite_delay()

    # 해시태그 (기본값, 실제로는 generate_hashtags에서 재계산)
    hashtags = []
    if total_units >= 1000:
        hashtags.append("대단지")
    if built_year >= 2015:
        hashtags.append("신축")

    return ComplexInfo(
        complex_id=complex_id,
        name=name,
        address=address,
        total_units=total_units,
        parking_total=parking_total,
        parking_per_unit=parking_per_unit,
        built_year=built_year,
        hashtags=hashtags,
        aerial_photo_path=aerial_photo_path,
    )


def fetch_property_detail(
    complex_id: str,
    article_no: str,
    complex_name: str,
    user_input: Any,
    temp_dir: str = "temp"
) -> Optional[PropertyDetail]:
    """
    매물 상세정보 조회

    Args:
        complex_id: 단지 ID
        article_no: 매물 번호
        complex_name: 단지명
        user_input: PropertyInput 사용자 입력
        temp_dir: 이미지 저장 임시 폴더

    Returns:
        PropertyDetail 또는 None
    """
    data = _api_get(f"/articles/{article_no}")
    if not data:
        # API 실패 시 사용자 입력 기반으로 기본 정보 생성
        return PropertyDetail(
            complex_id=complex_id,
            complex_name=complex_name,
            dong=user_input.dong,
            floor=user_input.floor,
            price=user_input.price,
            direction=user_input.direction,
            structure=user_input.structure,
            memo=user_input.memo,
        )

    polite_delay()

    article_detail = data.get("articleDetail", data)
    rooms = article_detail.get("roomCount")
    bathrooms = article_detail.get("bathroomCount")
    area_m2 = article_detail.get("exclusiveArea") or article_detail.get("area2")
    area_pyeong = None
    if area_m2:
        try:
            area_m2 = float(area_m2)
            area_pyeong = f"{round(area_m2 / 3.305785)}평"
        except (ValueError, TypeError):
            area_m2 = None

    # 평면도 다운로드
    floor_plan_path = None
    ground_plans = _api_get(f"/complexes/{complex_id}/ground-plans")
    if ground_plans and isinstance(ground_plans, list) and len(ground_plans) > 0:
        plan_url = ground_plans[0].get("imageUrl", "")
        if plan_url:
            floor_plan_path = os.path.join(
                temp_dir, complex_id, f"floor_plan_{article_no}.jpg"
            )
            if not _download_image(plan_url, floor_plan_path):
                floor_plan_path = None
        polite_delay()

    return PropertyDetail(
        complex_id=complex_id,
        complex_name=complex_name,
        dong=user_input.dong,
        floor=user_input.floor,
        price=user_input.price,
        direction=user_input.direction,
        structure=user_input.structure,
        memo=user_input.memo,
        floor_plan_image_path=floor_plan_path,
        rooms=rooms,
        bathrooms=bathrooms,
        area_pyeong=area_pyeong,
        area_m2=area_m2,
    )


def fetch_all_for_complex(
    complex_id: str,
    property_inputs: list,
    temp_dir: str = "temp"
) -> dict:
    """
    한 단지에 대한 모든 데이터 수집

    Returns:
        {"complex_info": ComplexInfo, "properties": [PropertyDetail, ...]}
    """
    complex_info = fetch_complex_info(complex_id, temp_dir)
    if not complex_info:
        complex_info = ComplexInfo(
            complex_id=complex_id,
            name="정보 없음",
            address="",
            total_units=0,
            parking_total=0,
            parking_per_unit=0,
            built_year=0,
            hashtags=[],
        )

    properties = []
    for prop_input in property_inputs:
        _, article_no = parse_naver_land_url(prop_input.naver_land_url)
        if article_no:
            detail = fetch_property_detail(
                complex_id, article_no, complex_info.name, prop_input, temp_dir
            )
        else:
            detail = PropertyDetail(
                complex_id=complex_id,
                complex_name=complex_info.name,
                dong=prop_input.dong,
                floor=prop_input.floor,
                price=prop_input.price,
                direction=prop_input.direction,
                structure=prop_input.structure,
                memo=prop_input.memo,
            )
        if detail:
            properties.append(detail)

    return {
        "complex_info": complex_info,
        "properties": properties,
    }
