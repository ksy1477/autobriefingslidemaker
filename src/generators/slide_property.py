"""
매물정보 슬라이드 생성
"""
import os
from typing import Optional

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from src.models import PropertyDetail


def add_property_slide(
    prs: Presentation,
    prop: PropertyDetail,
    logo_path: Optional[str] = None,
):
    """
    매물정보 슬라이드 추가

    Args:
        prs: Presentation 객체
        prop: 매물 상세 정보
        logo_path: 회사 로고 경로
    """
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    # 헤더
    title = f"{prop.complex_name} - {prop.dong} {prop.floor}"
    _add_slide_header(slide, title, "매물정보")

    # 좌측: 배치도/동 위치 이미지
    if prop.dong_location_image_path and os.path.exists(prop.dong_location_image_path):
        slide.shapes.add_picture(
            prop.dong_location_image_path,
            Inches(0.3), Inches(1.3), Inches(4.5), Inches(3.5)
        )
    else:
        # placeholder
        txBox = slide.shapes.add_textbox(
            Inches(0.3), Inches(1.3), Inches(4.5), Inches(3.5)
        )
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = "[단지 내 위치]"
        p.font.size = Pt(16)
        p.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
        p.alignment = PP_ALIGN.CENTER

    # 우측 상단: 평면도
    if prop.floor_plan_image_path and os.path.exists(prop.floor_plan_image_path):
        slide.shapes.add_picture(
            prop.floor_plan_image_path,
            Inches(5.0), Inches(1.3), Inches(4.5), Inches(2.5)
        )
    else:
        txBox2 = slide.shapes.add_textbox(
            Inches(5.0), Inches(1.3), Inches(4.5), Inches(2.5)
        )
        tf2 = txBox2.text_frame
        p2 = tf2.paragraphs[0]
        p2.text = "[평면도]"
        p2.font.size = Pt(16)
        p2.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
        p2.alignment = PP_ALIGN.CENTER

    # 매물 상세 정보 텍스트
    info_lines = []
    info_lines.append(f"매매가: {prop.price}")
    info_lines.append(f"동/층: {prop.dong} / {prop.floor}")
    if prop.area_pyeong:
        info_lines.append(f"전용면적: {prop.area_pyeong} ({prop.area_m2}㎡)" if prop.area_m2 else f"전용면적: {prop.area_pyeong}")
    if prop.direction:
        info_lines.append(f"향: {prop.direction}")
    if prop.structure:
        info_lines.append(f"구조: {prop.structure}")
    if prop.rooms is not None:
        bath_text = f" / 화장실 {prop.bathrooms}개" if prop.bathrooms else ""
        info_lines.append(f"방 {prop.rooms}개{bath_text}")
    if prop.memo:
        info_lines.append(f"특이사항: {prop.memo}")

    txBox3 = slide.shapes.add_textbox(
        Inches(5.0), Inches(4.0), Inches(4.5), Inches(2.5)
    )
    tf3 = txBox3.text_frame
    tf3.word_wrap = True
    for i, line in enumerate(info_lines):
        if i == 0:
            tf3.paragraphs[0].text = line
            tf3.paragraphs[0].font.size = Pt(12)
            tf3.paragraphs[0].font.bold = True
            tf3.paragraphs[0].font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            tf3.paragraphs[0].space_after = Pt(4)
        else:
            p = tf3.add_paragraph()
            p.text = line
            p.font.size = Pt(11)
            p.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            p.space_after = Pt(4)

    # 로고
    if logo_path and os.path.exists(logo_path):
        slide.shapes.add_picture(
            logo_path, Inches(7.5), Inches(6.2), Inches(2), Inches(0.6)
        )

    return slide


def _add_slide_header(slide, title: str, subtitle: str):
    """슬라이드 공통 헤더"""
    marker = slide.shapes.add_shape(
        1, Inches(0.3), Inches(0.35), Pt(8), Inches(0.4)
    )
    marker.fill.solid()
    marker.fill.fore_color.rgb = RGBColor(0xC8, 0x10, 0x2E)
    marker.line.fill.background()

    txBox = slide.shapes.add_textbox(
        Inches(0.6), Inches(0.3), Inches(6), Inches(0.5)
    )
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    txBox2 = slide.shapes.add_textbox(
        Inches(7.5), Inches(0.3), Inches(2), Inches(0.5)
    )
    tf2 = txBox2.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = subtitle
    p2.font.size = Pt(14)
    p2.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    p2.alignment = PP_ALIGN.RIGHT

    line = slide.shapes.add_shape(
        1, Inches(0.3), Inches(0.85), Inches(9.4), Pt(1)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = RGBColor(0xE0, 0xE0, 0xE0)
    line.line.fill.background()
