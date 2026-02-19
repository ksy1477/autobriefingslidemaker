"""
입지정보 슬라이드 생성 — 레퍼런스 PPT 양식
"""
import os
from typing import Optional

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from src.models import LocationInfo
from src.generators.slide_utils import add_slide_header, add_logo, add_source_text


def add_location_slide(
    prs: Presentation,
    complex_name: str,
    location_info: LocationInfo,
    logo_path: Optional[str] = None,
):
    """
    입지정보 슬라이드 추가 (레퍼런스 레이아웃)

    좌측: 최근접 역까지 경로 (도보 or 대중교통)
    우측: 강남역까지 대중교통 경로
    """
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    # 공통 헤더
    add_slide_header(slide, complex_name, "입지정보")

    # ── 좌측 라벨: 최근접 역 소요시간 ──
    station_label = _build_station_label(location_info)
    if station_label:
        label_left = slide.shapes.add_textbox(
            Inches(0.678), Inches(0.987),
            Inches(4.0), Inches(0.35),
        )
        tf = label_left.text_frame
        p = tf.paragraphs[0]
        p.text = station_label
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # ── 우측 라벨: 강남역 대중교통 ──
    gangnam_text = f"[강남역 - 대중교통 {location_info.gangnam_minutes}분]"
    label_right = slide.shapes.add_textbox(
        Inches(4.998), Inches(0.987),
        Inches(4.5), Inches(0.35),
    )
    tf2 = label_right.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = gangnam_text
    p2.font.size = Pt(12)
    p2.font.bold = True
    p2.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # ── 좌측 지도 이미지 ──
    if (location_info.walk_route_image_path
            and os.path.exists(location_info.walk_route_image_path)):
        slide.shapes.add_picture(
            location_info.walk_route_image_path,
            Inches(0.678), Inches(1.384),
            Inches(3.956), Inches(3.935),
        )
    else:
        _add_placeholder_text(
            slide,
            Inches(0.678), Inches(1.384),
            Inches(3.956), Inches(3.935),
            "[최근접역 경로 지도]",
        )

    # ── 우측 지도 이미지 ──
    if (location_info.transit_route_image_path
            and os.path.exists(location_info.transit_route_image_path)):
        slide.shapes.add_picture(
            location_info.transit_route_image_path,
            Inches(4.998), Inches(1.387),
            Inches(3.905), Inches(3.935),
        )
    else:
        _add_placeholder_text(
            slide,
            Inches(4.998), Inches(1.387),
            Inches(3.905), Inches(3.935),
            "[강남역 대중교통 경로]",
        )

    # 출처
    add_source_text(slide, "*네이버지도")

    # 로고
    add_logo(slide, logo_path)

    return slide


def _build_station_label(location_info: LocationInfo) -> str:
    """
    최근접 역 라벨 생성

    - 역과 가까우면(도보 10분 이내): "[역명(노선) - 도보 N분]"
    - 역이 멀면: "[역명(노선) - 대중교통 N분]"
    """
    station = location_info.nearest_station
    if not station or station == "정보 없음":
        return ""

    line_text = f"({location_info.station_line})" if location_info.station_line else ""

    if location_info.walk_minutes <= 10:
        # 도보권 — 도보 시간만 표시
        return f"[{station}{line_text} - 도보 {location_info.walk_minutes}분]"
    else:
        # 역이 멀다 — 대중교통 시간 표시
        transit_min = location_info.station_transit_minutes or location_info.walk_minutes
        return f"[{station}{line_text} - 대중교통 {transit_min}분]"


def _add_placeholder_text(slide, left, top, width, height, text):
    """이미지 없을 때 텍스트 placeholder"""
    shape = slide.shapes.add_shape(1, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(0xF0, 0xF0, 0xF0)
    shape.line.fill.background()

    tf = shape.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(14)
    p.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    p.alignment = PP_ALIGN.CENTER
