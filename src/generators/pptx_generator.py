"""
PPT 생성 메인 엔진
전체 슬라이드 어셈블 및 .pptx 파일 출력
"""
import os
from datetime import date
from typing import List, Optional

from pptx import Presentation
from pptx.util import Inches

from src.models import AgentProfile, ComplexData
from src.generators.slide_cover import add_cover_slide
from src.generators.slide_agent import add_agent_slide
from src.generators.slide_list import add_list_slide
from src.generators.slide_overview import add_overview_slide
from src.generators.slide_price import add_price_slide
from src.generators.slide_property import add_property_slide
from src.processors.data_aggregator import (
    generate_complex_overview_text,
    generate_price_summary,
)


def generate_briefing_pptx(
    customer_name: str,
    agent: AgentProfile,
    complex_data_list: List[ComplexData],
    output_dir: str = "output",
    background_path: Optional[str] = None,
) -> str:
    """
    브리핑 PPT 생성 메인 함수

    슬라이드 순서:
    1. 표지
    2. 중개사 소개
    3. 물건 리스트
    4~N. 단지별 반복 (개요 → 실거래가 → 매물정보)

    Args:
        customer_name: 고객명
        agent: 중개사 프로필
        complex_data_list: 단지별 통합 데이터 리스트
        output_dir: 출력 디렉토리
        background_path: 표지 배경 이미지 경로

    Returns:
        생성된 PPT 파일 경로
    """
    # 16:9 와이드스크린 프레젠테이션
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    # 단지명 목록
    complex_names = [cd.complex_info.name for cd in complex_data_list]
    logo_path = agent.logo_path if os.path.exists(agent.logo_path) else None

    print(f"[INFO] PPT 생성 시작: {customer_name}님 브리핑자료")

    # ─── 1. 표지 ───
    print("  → 표지 슬라이드 생성")
    add_cover_slide(
        prs, customer_name, complex_names,
        logo_path=logo_path,
        background_path=background_path,
    )

    # ─── 2. 중개사 소개 ───
    print("  → 중개사 소개 슬라이드 생성")
    add_agent_slide(prs, agent)

    # ─── 3. 물건 리스트 ───
    print("  → 물건리스트 슬라이드 생성")
    add_list_slide(prs, complex_data_list, logo_path=logo_path)

    # ─── 4~N. 단지별 반복 ───
    for cd in complex_data_list:
        ci = cd.complex_info
        print(f"  → [{ci.name}] 단지 개요 슬라이드 생성")

        # 단지 개요
        overview_text = generate_complex_overview_text(ci)
        add_overview_slide(prs, ci, overview_text, logo_path=logo_path)

        # 실거래가 (Phase 1에서 제공)
        if cd.price_info:
            print(f"  → [{ci.name}] 실거래가 슬라이드 생성")
            price_summary = generate_price_summary(ci.name, cd.price_info)
            add_price_slide(
                prs, ci.name, cd.price_info, price_summary,
                logo_path=logo_path,
            )

        # 매물별 슬라이드
        for prop in cd.properties:
            print(f"  → [{ci.name}] {prop.dong} {prop.floor} 매물정보 슬라이드 생성")
            add_property_slide(prs, prop, logo_path=logo_path)

    # ─── 파일 저장 ───
    os.makedirs(output_dir, exist_ok=True)
    today_str = date.today().strftime("%Y%m%d")
    filename = f"{customer_name}_브리핑자료_{today_str}.pptx"
    output_path = os.path.join(output_dir, filename)
    prs.save(output_path)

    slide_count = len(prs.slides)
    print(f"\n[SUCCESS] PPT 생성 완료!")
    print(f"  파일: {output_path}")
    print(f"  슬라이드 수: {slide_count}장")

    return output_path
