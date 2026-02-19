"""
데이터 취합기
크롤링 결과 + 사용자 입력 → 슬라이드별 데이터 구조로 정규화
"""
from collections import OrderedDict
from typing import List, Dict

from src.models import (
    BriefingInput,
    ComplexData,
    ComplexInfo,
    PropertyDetail,
    PriceInfo,
)
from src.utils.url_parser import parse_naver_land_url


def group_properties_by_complex(briefing_input: BriefingInput) -> OrderedDict:
    """
    매물을 단지별로 그룹핑 (입력 순서 유지)

    Args:
        briefing_input: 전체 브리핑 입력

    Returns:
        OrderedDict[complex_id, List[PropertyInput]]
    """
    groups = OrderedDict()
    for prop in briefing_input.properties:
        complex_id, _ = parse_naver_land_url(prop.naver_land_url)
        if complex_id is None:
            complex_id = "unknown"
        if complex_id not in groups:
            groups[complex_id] = []
        groups[complex_id].append(prop)
    return groups


def generate_hashtags(complex_info: ComplexInfo, walk_minutes: int = 0) -> List[str]:
    """
    단지 정보에서 해시태그 자동 생성

    Args:
        complex_info: 단지 정보
        walk_minutes: 최근접 역까지 도보 시간

    Returns:
        해시태그 리스트
    """
    tags = []
    if walk_minutes > 0 and walk_minutes <= 5:
        tags.append("역세권")
    if complex_info.total_units >= 1000:
        tags.append("대단지")
    if complex_info.parking_per_unit >= 1.0:
        tags.append("주차여유")
    if complex_info.built_year >= 2015:
        tags.append("신축")
    elif complex_info.built_year >= 2000:
        tags.append("준신축")
    return tags


def generate_price_summary(complex_name: str, price_info: PriceInfo) -> str:
    """
    실거래가 요약 텍스트 자동 생성

    Args:
        complex_name: 단지명
        price_info: 실거래가 정보

    Returns:
        요약 텍스트 문자열
    """
    lines = []
    lines.append(
        f"{complex_name}은(는) {price_info.month1_label} "
        f"[{price_info.month1_count}]건, "
        f"{price_info.month2_label} [{price_info.month2_count}]건 "
        f"거래되었습니다."
    )
    if price_info.recent_3m_high and price_info.recent_3m_low:
        lines.append(
            f"최근 3개월 최고 [{price_info.recent_3m_high}], "
            f"최저 [{price_info.recent_3m_low}]에 거래되었습니다."
        )
    if price_info.all_time_high:
        lines.append(
            f"최고가 [{price_info.all_time_high}] "
            f"{price_info.all_time_high_date}에 거래되었습니다."
        )
    return "\n".join(lines)


def generate_complex_overview_text(complex_info: ComplexInfo) -> str:
    """
    단지 개요 텍스트 자동 생성

    Args:
        complex_info: 단지 정보

    Returns:
        단지 개요 텍스트
    """
    text = (
        f"{complex_info.name}은(는)\n"
        f"{complex_info.address}에 위치해있으며\n"
        f"세대수 {complex_info.total_units:,}세대, "
        f"주차대수 {complex_info.parking_total:,}대 "
        f"(세대당 {complex_info.parking_per_unit}대)\n"
        f"{complex_info.built_year}년 준공된 아파트입니다."
    )
    return text
