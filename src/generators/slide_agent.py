"""
중개사 소개 슬라이드 생성
"""
import os
from typing import Optional

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from src.models import AgentProfile


def add_agent_slide(
    prs: Presentation,
    agent: AgentProfile,
):
    """
    중개사 소개 슬라이드 추가

    Args:
        prs: Presentation 객체
        agent: 중개사 프로필
    """
    slide_layout = prs.slide_layouts[6]  # 빈 슬라이드
    slide = prs.slides.add_slide(slide_layout)

    # 슬로건
    txBox = slide.shapes.add_textbox(
        Inches(1), Inches(0.8), Inches(8), Inches(1)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = f'"{agent.slogan}"'
    p.font.size = Pt(20)
    p.font.italic = True
    p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    p.alignment = PP_ALIGN.CENTER

    # 구분선
    line = slide.shapes.add_shape(
        1,  # MSO_SHAPE.RECTANGLE
        Inches(1.5), Inches(2.0), Inches(7), Pt(2)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = RGBColor(0xC8, 0x10, 0x2E)
    line.line.fill.background()

    # 중개사 사진 (있으면)
    if agent.photo_path and os.path.exists(agent.photo_path):
        slide.shapes.add_picture(
            agent.photo_path, Inches(1.5), Inches(2.5), Inches(2.5), Inches(3)
        )

    # 정보 영역
    info_left = Inches(4.5)
    info_top = Inches(2.5)

    # 직함 + 이름
    txBox2 = slide.shapes.add_textbox(info_left, info_top, Inches(5), Inches(0.5))
    tf2 = txBox2.text_frame
    p2 = tf2.paragraphs[0]
    run = p2.add_run()
    run.text = "공인중개사  "
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    run2 = p2.add_run()
    run2.text = agent.name
    run2.font.size = Pt(22)
    run2.font.bold = True
    run2.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # 소속
    txBox3 = slide.shapes.add_textbox(
        info_left, Inches(3.1), Inches(5), Inches(0.4)
    )
    tf3 = txBox3.text_frame
    p3 = tf3.paragraphs[0]
    p3.text = agent.company
    p3.font.size = Pt(12)
    p3.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    # 자격증
    txBox4 = slide.shapes.add_textbox(
        info_left, Inches(3.6), Inches(5), Inches(1)
    )
    tf4 = txBox4.text_frame
    tf4.word_wrap = True
    for i, qual in enumerate(agent.qualifications):
        if i == 0:
            tf4.paragraphs[0].text = f"• {qual}"
            tf4.paragraphs[0].font.size = Pt(11)
            tf4.paragraphs[0].font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        else:
            p = tf4.add_paragraph()
            p.text = f"• {qual}"
            p.font.size = Pt(11)
            p.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    # 연락처
    txBox5 = slide.shapes.add_textbox(
        info_left, Inches(4.8), Inches(5), Inches(0.8)
    )
    tf5 = txBox5.text_frame
    p5 = tf5.paragraphs[0]
    p5.text = f"M: {agent.phone}"
    p5.font.size = Pt(12)
    p5.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    p5_2 = tf5.add_paragraph()
    p5_2.text = f"E: {agent.email}"
    p5_2.font.size = Pt(12)
    p5_2.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    # 로고
    if agent.logo_path and os.path.exists(agent.logo_path):
        slide.shapes.add_picture(
            agent.logo_path, Inches(7.5), Inches(6.2), Inches(2), Inches(0.6)
        )

    return slide
