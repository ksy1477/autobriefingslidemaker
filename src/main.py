"""
부동산 브리핑자료 자동생성기 - 메인 오케스트레이터
CLI 인터페이스 + 전체 파이프라인
"""
import os
import sys
import json
import yaml
from collections import OrderedDict
from typing import Optional

from src.models import (
    AgentProfile,
    BriefingInput,
    PropertyInput,
    ComplexData,
    ComplexInfo,
    PriceInfo,
    PropertyDetail,
)
from src.utils.url_parser import parse_naver_land_url
from src.crawlers.naver_land import fetch_complex_info, fetch_property_detail, fetch_school_basic_from_ssr, capture_complex_images, capture_complex_detail_screenshot
from src.crawlers.asil import fetch_price_info, fetch_price_info_mock, capture_asil_price_chart
from src.crawlers.naver_map import fetch_location_info
from src.crawlers.school_zone import fetch_school_info
from src.processors.data_aggregator import (
    group_properties_by_complex,
    generate_hashtags,
)
from src.processors.chart_generator import generate_price_chart
from src.generators.pptx_generator import generate_briefing_pptx


# ─── 설정 로드 ───

def load_config(config_path: str = "config/config.yaml") -> dict:
    """설정 파일 로드"""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def load_agent_profile(
    profile_path: str = "config/agent_profile.yaml",
    logo_path: str = "assets/logo.png"
) -> AgentProfile:
    """중개사 프로필 로드"""
    if os.path.exists(profile_path):
        with open(profile_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    return AgentProfile(
        name=data.get("name", "홍길동"),
        photo_path=data.get("photo_path", "assets/agent_photo.png"),
        company=data.get("company", "부동산중개법인"),
        qualifications=data.get("qualifications", ["공인중개사"]),
        phone=data.get("phone", "010-0000-0000"),
        email=data.get("email", "agent@example.com"),
        slogan=data.get("slogan", "전문가로서 분석하고, 고객의 편에서 중개하겠습니다"),
        logo_path=data.get("logo_path", logo_path),
    )


def load_input_from_json(json_path: str) -> BriefingInput:
    """JSON 파일에서 입력 데이터 로드"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return BriefingInput(**data)


# ─── 파이프라인 ───

def run_pipeline(
    briefing_input: BriefingInput,
    config: dict,
    agent: AgentProfile,
    use_mock: bool = False,
) -> str:
    """
    전체 파이프라인 실행

    Args:
        briefing_input: 브리핑 입력 데이터
        config: 설정
        agent: 중개사 프로필
        use_mock: True이면 크롤링 없이 mock 데이터 사용

    Returns:
        생성된 PPT 파일 경로
    """
    temp_dir = "temp"
    output_dir = config.get("output", {}).get("directory", "output")
    api_key = config.get("public_data_api_key", "")

    print("=" * 60)
    print(f"  부동산 브리핑자료 자동생성기")
    print(f"  고객: {briefing_input.customer_name}")
    print(f"  매물 수: {len(briefing_input.properties)}건")
    print("=" * 60)

    # 1. 매물을 단지별로 그룹핑
    print("\n[1/4] 매물 그룹핑...")
    groups = group_properties_by_complex(briefing_input)
    print(f"  {len(groups)}개 단지로 그룹핑 완료")

    # 2. 단지별 데이터 수집
    print("\n[2/4] 데이터 수집...")
    complex_data_list = []

    for complex_id, prop_inputs in groups.items():
        print(f"\n  ── 단지 [{complex_id}] 처리 중 ──")

        # 단지 기본정보
        if use_mock:
            complex_info = _create_mock_complex_info(complex_id, prop_inputs)
        else:
            complex_info = fetch_complex_info(complex_id, temp_dir)
            if not complex_info:
                print(f"  [WARN] 단지정보 조회 실패, mock 데이터 사용")
                complex_info = _create_mock_complex_info(complex_id, prop_inputs)

        # 단지정보 상세 스크린샷 캡처 (4페이지 우측)
        if not use_mock:
            detail_screenshot = capture_complex_detail_screenshot(complex_id, temp_dir)
            if detail_screenshot:
                complex_info.satellite_map_path = detail_screenshot

        # 해시태그 업데이트
        complex_info.hashtags = generate_hashtags(complex_info)
        print(f"  단지명: {complex_info.name}")

        # 실거래가
        if use_mock or not api_key:
            price_info = fetch_price_info_mock(complex_id, complex_info.name)
        else:
            price_info = fetch_price_info(
                complex_id, complex_info.name, api_key=api_key
            )

        # 실거래가 그래프 생성 (아실 캡처 → matplotlib fallback)
        chart_path = os.path.join(temp_dir, complex_id, "price_chart.png")
        asil_result = None
        if not use_mock:
            asil_result = capture_asil_price_chart(
                complex_info.name, complex_id, complex_info.address, chart_path
            )
        if asil_result:
            # 아실 데이터로 price_info 대체
            if asil_result.get("price_info"):
                price_info = asil_result["price_info"]
            if price_info:
                price_info.price_graph_image_path = asil_result["chart_path"]
        elif price_info and price_info.recent_transactions:
            generate_price_chart(
                price_info.recent_transactions,
                complex_info.name,
                chart_path,
            )
            price_info.price_graph_image_path = chart_path
            print(f"  실거래가 그래프 생성 완료 (matplotlib)")

        # 입지정보 (Phase 2)
        print(f"  입지정보 수집...")
        location_info = fetch_location_info(
            complex_id=complex_id,
            complex_name=complex_info.name,
            complex_lat=complex_info.latitude or 0.0,
            complex_lng=complex_info.longitude or 0.0,
            temp_dir=temp_dir,
            config=config,
            use_mock=use_mock,
        )
        if location_info:
            print(f"  입지정보: {location_info.nearest_station}({location_info.station_line}) 도보 {location_info.walk_minutes}분")
            # 역세권 등 해시태그 업데이트 (walk_minutes 반영)
            complex_info.hashtags = generate_hashtags(complex_info, location_info.walk_minutes)

        # 학군정보 (Phase 2)
        print(f"  학군정보 수집...")
        ssr_schools = None
        if not use_mock:
            ssr_schools = fetch_school_basic_from_ssr(complex_id)
        school_info = fetch_school_info(
            complex_id=complex_id,
            complex_name=complex_info.name,
            address=complex_info.address,
            complex_lat=complex_info.latitude or 0.0,
            complex_lng=complex_info.longitude or 0.0,
            temp_dir=temp_dir,
            use_mock=use_mock,
            ssr_schools=ssr_schools,
        )
        if school_info:
            print(f"  학군정보: {school_info.elementary_name}")

        # 매물 상세
        properties = []
        for prop_input in prop_inputs:
            _, article_no = parse_naver_land_url(prop_input.naver_land_url)
            if not use_mock and article_no:
                detail = fetch_property_detail(
                    complex_id, article_no, complex_info.name,
                    prop_input, temp_dir
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
            properties.append(detail)
            print(f"  매물: {prop_input.dong} {prop_input.floor} - {prop_input.price}")

        # 단지 이미지 캡처 (평면도 + 단지위치)
        if not use_mock:
            for prop in properties:
                images = capture_complex_images(
                    complex_id,
                    prop.area_pyeong or "",
                    temp_dir,
                    latitude=complex_info.latitude or 0.0,
                    longitude=complex_info.longitude or 0.0,
                )
                prop.floor_plan_image_path = images.get("floor_plan_path")
                prop.dong_location_image_path = images.get("site_plan_path")

        complex_data = ComplexData(
            complex_info=complex_info,
            location_info=location_info,
            school_info=school_info,
            price_info=price_info,
            properties=properties,
        )
        complex_data_list.append(complex_data)

    # 3. PPT 생성
    print("\n[3/4] PPT 생성...")
    output_path = generate_briefing_pptx(
        customer_name=briefing_input.customer_name,
        agent=agent,
        complex_data_list=complex_data_list,
        output_dir=output_dir,
    )

    # 4. 완료
    print("\n[4/4] 완료!")
    print(f"\n{'=' * 60}")
    print(f"  생성된 파일: {output_path}")
    print(f"{'=' * 60}")

    return output_path


def _create_mock_complex_info(complex_id: str, prop_inputs: list) -> ComplexInfo:
    """Mock 단지 정보 생성"""
    return ComplexInfo(
        complex_id=complex_id,
        name=f"샘플단지_{complex_id[-4:]}",
        address="서울시 강남구",
        total_units=1500,
        parking_total=1200,
        parking_per_unit=0.8,
        built_year=2005,
        hashtags=["대단지"],
    )


# ─── CLI 엔트리포인트 ───

def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description="부동산 브리핑자료 자동생성기 (RE Briefing Auto)"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="입력 JSON 파일 경로",
    )
    parser.add_argument(
        "--customer", "-c",
        type=str,
        help="고객명",
    )
    parser.add_argument(
        "--urls", "-u",
        nargs="+",
        help="네이버부동산 매물 URL 목록",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="크롤링 없이 mock 데이터로 테스트",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="설정 파일 경로 (기본: config/config.yaml)",
    )

    args = parser.parse_args()

    # 설정 로드
    config = load_config(args.config)
    agent = load_agent_profile()

    # 입력 데이터 구성
    if args.input:
        briefing_input = load_input_from_json(args.input)
    elif args.customer and args.urls:
        # URL만 있는 경우 최소 입력으로 PropertyInput 구성
        properties = []
        for url in args.urls:
            properties.append(PropertyInput(
                naver_land_url=url,
                price="미입력",
                dong="미입력",
                floor="미입력",
            ))
        briefing_input = BriefingInput(
            customer_name=args.customer,
            properties=properties,
        )
    else:
        # demo 모드
        print("\n[INFO] 입력이 없으므로 데모 모드로 실행합니다.")
        briefing_input = BriefingInput(
            customer_name="테스트고객",
            properties=[
                PropertyInput(
                    naver_land_url="https://new.land.naver.com/complexes/12345?articleNo=67890",
                    price="6.4억",
                    dong="124동",
                    floor="7/15층",
                    direction="동향",
                    structure="복도식 방2화1",
                    memo="샷시교체, 욕실수리",
                ),
                PropertyInput(
                    naver_land_url="https://new.land.naver.com/complexes/12345?articleNo=11111",
                    price="6.6억",
                    dong="115동",
                    floor="12/15층",
                    direction="남향",
                    structure="복도식 방3화2",
                    memo="",
                ),
                PropertyInput(
                    naver_land_url="https://new.land.naver.com/complexes/99999?articleNo=22222",
                    price="8.2억",
                    dong="201동",
                    floor="3/20층",
                    direction="남서향",
                    structure="타워식 방3화2",
                    memo="올수리, 네고 가능",
                ),
            ],
        )
        args.mock = True

    # 파이프라인 실행
    try:
        output_path = run_pipeline(
            briefing_input, config, agent,
            use_mock=args.mock,
        )
        return output_path
    except Exception as e:
        print(f"\n[ERROR] PPT 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
