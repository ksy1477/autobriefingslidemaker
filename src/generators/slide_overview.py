"""
단지 개요 슬라이드 생성 — 레퍼런스 PPT 양식
"""
import os
from typing import Optional

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

from src.models import ComplexInfo
from src.generators.slide_utils import add_slide_header, add_logo, add_source_text


def add_overview_slide(
    prs: Presentation,
    complex_info: ComplexInfo,
    overview_text: str,
    logo_path: Optional[str] = None,
):
    """
    단지 개요 슬라이드 추가 (레퍼런스 레이아웃)

    - 공통 헤더 (Group 마커)
    - 개요 텍스트: (0.490", 0.903", 12pt)
    - 해시태그: 노란배경(EEFF41) 텍스트박스 (5.085", 1.192"), 색상 404040, 18pt bold
    - 좌측 이미지: 전경사진 (0.428", 1.948", 4.415"×3.509")
    - 우측 이미지: 배치도/위성지도 (5.0", 1.948", 4.439"×3.246")
    """
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    # 공통 헤더
    add_slide_header(slide, complex_info.name, "개요")

    # 개요 텍스트 (0.490", 0.903", 12pt)
    txBox = slide.shapes.add_textbox(
        Inches(0.490), Inches(0.903),
        Inches(4.5), Inches(0.9),
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, line in enumerate(overview_text.split("\n")):
        if i == 0:
            tf.paragraphs[0].text = line
            tf.paragraphs[0].font.size = Pt(12)
            tf.paragraphs[0].font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            tf.paragraphs[0].space_after = Pt(4)
        else:
            p = tf.add_paragraph()
            p.text = line
            p.font.size = Pt(12)
            p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            p.space_after = Pt(4)

    # 해시태그: 노란배경(EEFF41) (5.085", 1.192"), 색상 404040, 18pt bold
    if complex_info.hashtags:
        hashtag_text = "  ".join([f"#{tag}" for tag in complex_info.hashtags])
        txBox2 = slide.shapes.add_textbox(
            Inches(5.085), Inches(1.192),
            Inches(4.5), Inches(0.5),
        )
        tf2 = txBox2.text_frame
        p2 = tf2.paragraphs[0]
        p2.text = hashtag_text
        p2.font.size = Pt(18)
        p2.font.bold = True
        p2.font.color.rgb = RGBColor(0x40, 0x40, 0x40)

        # 노란 배경
        txBox2.fill.solid()
        txBox2.fill.fore_color.rgb = RGBColor(0xEE, 0xFF, 0x41)

    # 좌측 이미지: 전경사진 (0.428", 1.948", 4.415"×3.509")
    if complex_info.aerial_photo_path and os.path.exists(complex_info.aerial_photo_path):
        slide.shapes.add_picture(
            complex_info.aerial_photo_path,
            Inches(0.428), Inches(1.948),
            Inches(4.415), Inches(3.509),
        )

    # 우측 이미지: 배치도/위성지도 (5.0", 1.948", 4.439"×3.246")
    if complex_info.satellite_map_path and os.path.exists(complex_info.satellite_map_path):
        slide.shapes.add_picture(
            complex_info.satellite_map_path,
            Inches(5.0), Inches(1.948),
            Inches(4.439), Inches(3.246),
        )
    elif complex_info.site_plan_path and os.path.exists(complex_info.site_plan_path):
        slide.shapes.add_picture(
            complex_info.site_plan_path,
            Inches(5.0), Inches(1.948),
            Inches(4.439), Inches(3.246),
        )

    # 출처
    add_source_text(slide, "*네이버부동산  *네이버지도")

    # 로고
    add_logo(slide, logo_path)

    return slide
