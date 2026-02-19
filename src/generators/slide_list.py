"""
물건리스트 & 투어일정 슬라이드 생성
"""
import os
from typing import List, Optional

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from src.models import PropertyDetail, ComplexData


def add_list_slide(
    prs: Presentation,
    complex_data_list: List[ComplexData],
    logo_path: Optional[str] = None,
):
    """
    물건리스트 & 투어일정 슬라이드 추가

    Args:
        prs: Presentation 객체
        complex_data_list: 단지별 통합 데이터 리스트
        logo_path: 회사 로고 경로
    """
    slide_layout = prs.slide_layouts[6]  # 빈 슬라이드
    slide = prs.slides.add_slide(slide_layout)

    # 제목
    txBox = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.3), Inches(9), Inches(0.6)
    )
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = "물건리스트 및 투어일정"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # 제목 아래 빨간 라인
    line = slide.shapes.add_shape(
        1, Inches(0.5), Inches(0.9), Inches(2), Pt(3)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = RGBColor(0xC8, 0x10, 0x2E)
    line.line.fill.background()

    # 전체 매물 목록 플랫화
    all_properties = []
    for cdata in complex_data_list:
        for prop in cdata.properties:
            all_properties.append(prop)

    # 테이블 생성
    cols = 7  # 지역, 단지명, 동/호수, 평형, 매매가, 향/구조, 특이사항
    rows = len(all_properties) + 1  # 헤더 + 데이터

    if rows < 2:
        rows = 2  # 최소 1행

    table_shape = slide.shapes.add_table(
        rows, cols,
        Inches(0.3), Inches(1.2),
        Inches(9.4), Inches(min(4.5, rows * 0.4))
    )
    table = table_shape.table

    # 열 너비 설정
    col_widths = [Inches(1.0), Inches(1.5), Inches(1.1), Inches(0.9),
                  Inches(1.1), Inches(1.3), Inches(2.5)]
    for i, w in enumerate(col_widths):
        table.columns[i].width = w

    # 헤더
    headers = ["지역", "단지명", "동/호수", "평형", "매매가", "향/구조", "특이사항"]
    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = header
        for paragraph in cell.text_frame.paragraphs:
            paragraph.font.size = Pt(10)
            paragraph.font.bold = True
            paragraph.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            paragraph.alignment = PP_ALIGN.CENTER
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(0xC8, 0x10, 0x2E)

    # 데이터 행
    for row_idx, prop in enumerate(all_properties, start=1):
        # 지역 (주소에서 추출)
        address = ""
        for cdata in complex_data_list:
            if cdata.complex_info.complex_id == prop.complex_id:
                address = cdata.complex_info.address
                break
        # 구/동만 추출
        addr_short = address.split()[:2] if address else [""]
        addr_text = " ".join(addr_short)

        dong_ho = prop.dong
        if hasattr(prop, 'ho') and getattr(prop, 'ho', None):
            dong_ho += f" {prop.ho}"

        area_text = prop.area_pyeong or ""
        direction_structure = " ".join(
            filter(None, [prop.direction, prop.structure])
        )

        row_data = [
            addr_text,
            prop.complex_name,
            dong_ho,
            area_text,
            prop.price,
            direction_structure,
            prop.memo or "",
        ]

        for col_idx, value in enumerate(row_data):
            cell = table.cell(row_idx, col_idx)
            cell.text = str(value)
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = Pt(9)
                paragraph.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
                paragraph.alignment = PP_ALIGN.CENTER

            # 짝/홀수 행 배경색
            if row_idx % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(0xF5, 0xF5, 0xF5)

    # 로고
    if logo_path and os.path.exists(logo_path):
        slide.shapes.add_picture(
            logo_path, Inches(7.5), Inches(6.2), Inches(2), Inches(0.6)
        )

    return slide
