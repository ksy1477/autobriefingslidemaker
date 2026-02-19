"""
표지 슬라이드 생성
"""
import os
from typing import List, Optional

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN


def add_cover_slide(
    prs: Presentation,
    customer_name: str,
    complex_names: List[str],
    logo_path: Optional[str] = None,
    background_path: Optional[str] = None,
):
    """
    표지 슬라이드 추가

    Args:
        prs: Presentation 객체
        customer_name: 고객명
        complex_names: 단지명 리스트
        logo_path: 회사 로고 경로
        background_path: 배경 이미지 경로
    """
    slide_layout = prs.slide_layouts[6]  # 빈 슬라이드
    slide = prs.slides.add_slide(slide_layout)

    slide_width = prs.slide_width
    slide_height = prs.slide_height

    # 배경색 (다크 블루/블랙)
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

    # 배경 이미지 (있으면)
    if background_path and os.path.exists(background_path):
        slide.shapes.add_picture(
            background_path, 0, 0, slide_width, slide_height
        )

    # 고객명
    txBox = slide.shapes.add_textbox(
        Inches(1), Inches(1.5), Inches(8), Inches(1)
    )
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = f"{customer_name}님"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    p.alignment = PP_ALIGN.CENTER

    # 부제목
    txBox2 = slide.shapes.add_textbox(
        Inches(1), Inches(2.5), Inches(8), Inches(0.8)
    )
    tf2 = txBox2.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = "내집마련을 위한 브리핑자료"
    p2.font.size = Pt(24)
    p2.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    p2.alignment = PP_ALIGN.CENTER

    # 단지 목록
    complex_text = " / ".join(complex_names)
    txBox3 = slide.shapes.add_textbox(
        Inches(1), Inches(3.8), Inches(8), Inches(0.6)
    )
    tf3 = txBox3.text_frame
    p3 = tf3.paragraphs[0]
    p3.text = f"임장브리핑 : {complex_text}"
    p3.font.size = Pt(14)
    p3.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
    p3.alignment = PP_ALIGN.CENTER

    # 로고 (있으면)
    if logo_path and os.path.exists(logo_path):
        slide.shapes.add_picture(
            logo_path, Inches(3.75), Inches(5.5), Inches(2.5), Inches(0.8)
        )

    return slide
