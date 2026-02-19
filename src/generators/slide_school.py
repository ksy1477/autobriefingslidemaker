"""
학군지도 슬라이드 생성
초등학교 학구도 (Slide C) + 중·고등학교 학군 지도 (Slide D)
"""
import os
from typing import Optional

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from src.models import SchoolInfo


def add_elementary_school_slide(
    prs: Presentation,
    complex_name: str,
    school_info: SchoolInfo,
    logo_path: Optional[str] = None,
):
    """
    학군지도(초등학교) 슬라이드 추가 (Slide C)

    Args:
        prs: Presentation 객체
        complex_name: 단지명
        school_info: 학군 정보
        logo_path: 회사 로고 경로
    """
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    # 헤더
    _add_slide_header(slide, "학구도(초등학교)", "학군지도")

    # ── 학구도 지도 이미지 ──
    if (school_info.elementary_map_path
            and os.path.exists(school_info.elementary_map_path)):
        slide.shapes.add_picture(
            school_info.elementary_map_path,
            Inches(0.5), Inches(1.2), Inches(6.5), Inches(4.8)
        )
    else:
        _add_placeholder_text(
            slide, Inches(0.5), Inches(1.2), Inches(6.5), Inches(4.8),
            "[초등학교 학구도 지도]"
        )

    # ── 배정 초등학교 정보 ──
    if school_info.elementary_name:
        txBox = slide.shapes.add_textbox(
            Inches(7.3), Inches(1.5), Inches(2.2), Inches(1.5)
        )
        tf = txBox.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = "배정 초등학교"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = RGBColor(0xC8, 0x10, 0x2E)
        p.space_after = Pt(8)

        p2 = tf.add_paragraph()
        p2.text = school_info.elementary_name
        p2.font.size = Pt(13)
        p2.font.bold = True
        p2.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # ── 출처 ──
    txBox3 = slide.shapes.add_textbox(
        Inches(0.5), Inches(6.5), Inches(5), Inches(0.3)
    )
    p3 = txBox3.text_frame.paragraphs[0]
    p3.text = "*학구도안내서비스 (https://schoolzone.emac.kr)  *네이버지도"
    p3.font.size = Pt(8)
    p3.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    # ── 로고 ──
    if logo_path and os.path.exists(logo_path):
        slide.shapes.add_picture(
            logo_path, Inches(7.5), Inches(6.2), Inches(2), Inches(0.6)
        )

    return slide


def add_middle_high_school_slide(
    prs: Presentation,
    complex_name: str,
    school_info: SchoolInfo,
    logo_path: Optional[str] = None,
):
    """
    학군지도(중·고등학교) 슬라이드 추가 (Slide D)

    Args:
        prs: Presentation 객체
        complex_name: 단지명
        school_info: 학군 정보
        logo_path: 회사 로고 경로
    """
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    # 헤더
    _add_slide_header(slide, "학군지도(중·고등학교)", "학군지도")

    # ── 학군 지도 이미지 ──
    if (school_info.middle_high_map_path
            and os.path.exists(school_info.middle_high_map_path)):
        slide.shapes.add_picture(
            school_info.middle_high_map_path,
            Inches(0.5), Inches(1.2), Inches(9.0), Inches(4.8)
        )
    else:
        _add_placeholder_text(
            slide, Inches(0.5), Inches(1.2), Inches(9.0), Inches(4.8),
            "[중·고등학교 학군 지도]"
        )

    # ── 출처 ──
    txBox3 = slide.shapes.add_textbox(
        Inches(0.5), Inches(6.5), Inches(5), Inches(0.3)
    )
    p3 = txBox3.text_frame.paragraphs[0]
    p3.text = "*아실 (https://asil.kr)"
    p3.font.size = Pt(8)
    p3.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    # ── 로고 ──
    if logo_path and os.path.exists(logo_path):
        slide.shapes.add_picture(
            logo_path, Inches(7.5), Inches(6.2), Inches(2), Inches(0.6)
        )

    return slide


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


def _add_slide_header(slide, title: str, subtitle: str):
    """슬라이드 공통 헤더 (제목 + 서브타이틀)"""
    # 좌측 빨간 마커
    marker = slide.shapes.add_shape(
        1, Inches(0.3), Inches(0.35), Pt(8), Inches(0.4)
    )
    marker.fill.solid()
    marker.fill.fore_color.rgb = RGBColor(0xC8, 0x10, 0x2E)
    marker.line.fill.background()

    # 제목
    txBox = slide.shapes.add_textbox(
        Inches(0.6), Inches(0.3), Inches(6), Inches(0.5)
    )
    p = txBox.text_frame.paragraphs[0]
    p.text = title
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # 우측 서브타이틀
    txBox2 = slide.shapes.add_textbox(
        Inches(7.5), Inches(0.3), Inches(2), Inches(0.5)
    )
    p2 = txBox2.text_frame.paragraphs[0]
    p2.text = subtitle
    p2.font.size = Pt(14)
    p2.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    p2.alignment = PP_ALIGN.RIGHT

    # 구분선
    line = slide.shapes.add_shape(
        1, Inches(0.3), Inches(0.85), Inches(9.4), Pt(1)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = RGBColor(0xE0, 0xE0, 0xE0)
    line.line.fill.background()
