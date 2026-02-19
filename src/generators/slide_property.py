"""
매물정보 슬라이드 생성 — 레퍼런스 PPT 양식
"""
import os
from typing import Optional

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from src.models import PropertyDetail
from src.generators.slide_utils import add_slide_header, add_logo, add_source_text


def add_property_slide(
    prs: Presentation,
    prop: PropertyDetail,
    logo_path: Optional[str] = None,
):
    """
    매물정보 슬라이드 추가 (레퍼런스 레이아웃)

    - 공통 헤더
    - 빨간 세로 마커 + "단지내 위치" 라벨 at (0.127", 1.255")
    - 배치도 이미지: (0.084", 1.688", 2.712"×3.673")
    - 평면도: (2.864", 1.688", 4.607"×3.673")
    """
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    # 공통 헤더
    title = f"{prop.complex_name} - {prop.dong} {prop.floor}"
    add_slide_header(slide, title, "매물정보")

    # ── 빨간 세로 마커 + "단지내 위치" 라벨 ──
    _add_red_marker(slide, Inches(0.127), Inches(1.255))
    label_box = slide.shapes.add_textbox(
        Inches(0.22), Inches(1.225),
        Inches(2), Inches(0.3),
    )
    lp = label_box.text_frame.paragraphs[0]
    lp.text = "단지내 위치"
    lp.font.size = Pt(12)
    lp.font.bold = True
    lp.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # ── 빨간 세로 마커 + "평면도" 라벨 ──
    _add_red_marker(slide, Inches(2.864), Inches(1.255))
    label_box2 = slide.shapes.add_textbox(
        Inches(2.96), Inches(1.225),
        Inches(2), Inches(0.3),
    )
    lp2 = label_box2.text_frame.paragraphs[0]
    lp2.text = "평면도"
    lp2.font.size = Pt(12)
    lp2.font.bold = True
    lp2.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # ── 좌측: 배치도/동 위치 이미지 (0.084", 1.688", 2.712"×3.673") ──
    if prop.dong_location_image_path and os.path.exists(prop.dong_location_image_path):
        slide.shapes.add_picture(
            prop.dong_location_image_path,
            Inches(0.084), Inches(1.688),
            Inches(2.712), Inches(3.673),
        )
    else:
        _add_placeholder_text(
            slide,
            Inches(0.084), Inches(1.688),
            Inches(2.712), Inches(3.673),
            "[단지 내 위치]",
        )

    # ── 우측: 평면도 (2.864", 1.688", 4.607"×3.673") ──
    if prop.floor_plan_image_path and os.path.exists(prop.floor_plan_image_path):
        slide.shapes.add_picture(
            prop.floor_plan_image_path,
            Inches(2.864), Inches(1.688),
            Inches(4.607), Inches(3.673),
        )
    else:
        _add_placeholder_text(
            slide,
            Inches(2.864), Inches(1.688),
            Inches(4.607), Inches(3.673),
            "[평면도]",
        )

    # 매물 상세 정보 텍스트 (우측 하단)
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
        Inches(7.6), Inches(1.688), Inches(2.2), Inches(3.5)
    )
    tf3 = txBox3.text_frame
    tf3.word_wrap = True
    for i, line in enumerate(info_lines):
        if i == 0:
            tf3.paragraphs[0].text = line
            tf3.paragraphs[0].font.size = Pt(11)
            tf3.paragraphs[0].font.bold = True
            tf3.paragraphs[0].font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            tf3.paragraphs[0].space_after = Pt(4)
        else:
            p = tf3.add_paragraph()
            p.text = line
            p.font.size = Pt(10)
            p.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            p.space_after = Pt(4)

    # 로고
    add_logo(slide, logo_path)

    return slide


def _add_red_marker(slide, left, top):
    """빨간 세로 마커 (0.052"×0.197")"""
    marker = slide.shapes.add_shape(
        1,  # RECTANGLE
        left, top,
        Inches(0.052), Inches(0.197),
    )
    marker.fill.solid()
    marker.fill.fore_color.rgb = RGBColor(0xC8, 0x10, 0x2E)
    marker.line.fill.background()


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
