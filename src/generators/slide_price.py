"""
실거래가 슬라이드 생성 — 레퍼런스 PPT 양식
"""
import os
from typing import Optional, List

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from src.models import PriceInfo
from src.generators.slide_utils import add_slide_header, add_logo, add_source_text


def add_price_slide(
    prs: Presentation,
    complex_name: str,
    price_info: PriceInfo,
    price_summary_text: str,
    logo_path: Optional[str] = None,
):
    """
    실거래가 슬라이드 추가 (레퍼런스 레이아웃)

    - 공통 헤더
    - 빨간 세로 마커 (0.052"x0.197") + 라벨 "최근 실거래" at (0.661", 1.882")
    - 빨간 세로 마커 + 라벨 "매매거래" at (4.049", 1.882")
    - 실거래 테이블 이미지: (0.713", 2.102")
    - 매매거래 그래프: (4.139", 2.102")
    """
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    # 공통 헤더
    add_slide_header(slide, complex_name, "실거래가")

    # 요약 텍스트 (헤더 아래)
    txBox = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.9), Inches(9), Inches(0.8)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, line in enumerate(price_summary_text.split("\n")):
        if i == 0:
            tf.paragraphs[0].text = line
            tf.paragraphs[0].font.size = Pt(11)
            tf.paragraphs[0].font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            tf.paragraphs[0].space_after = Pt(3)
        else:
            p = tf.add_paragraph()
            p.text = line
            p.font.size = Pt(11)
            p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            p.space_after = Pt(3)

    # ── 좌측: 빨간 세로 마커 + "최근 실거래" 라벨 ──
    _add_red_marker(slide, Inches(0.661), Inches(1.882))
    label_left = slide.shapes.add_textbox(
        Inches(0.75), Inches(1.852),
        Inches(2), Inches(0.3),
    )
    lp = label_left.text_frame.paragraphs[0]
    lp.text = "최근 실거래"
    lp.font.size = Pt(12)
    lp.font.bold = True
    lp.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # ── 우측: 빨간 세로 마커 + "매매거래" 라벨 ──
    _add_red_marker(slide, Inches(4.049), Inches(1.882))
    label_right = slide.shapes.add_textbox(
        Inches(4.139), Inches(1.852),
        Inches(2), Inches(0.3),
    )
    rp = label_right.text_frame.paragraphs[0]
    rp.text = "매매거래"
    rp.font.size = Pt(12)
    rp.font.bold = True
    rp.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # ── 좌측: 최근 실거래 테이블 (0.713", 2.102") ──
    transactions = price_info.recent_transactions[:6]
    if transactions:
        cols = 4
        rows = len(transactions) + 1
        table_shape = slide.shapes.add_table(
            rows, cols,
            Inches(0.713), Inches(2.102),
            Inches(3.2), Inches(min(3.0, rows * 0.35))
        )
        table = table_shape.table

        col_widths = [Inches(0.9), Inches(0.7), Inches(0.5), Inches(1.1)]
        for i, w in enumerate(col_widths):
            table.columns[i].width = w

        headers = ["거래일", "평형", "층", "거래가"]
        for i, h in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = h
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9)
                p.font.bold = True
                p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
                p.alignment = PP_ALIGN.CENTER
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(0xEF, 0xEF, 0xEF)

        for row_idx, txn in enumerate(transactions, start=1):
            data = [
                txn.date.strftime("%Y.%m.%d"),
                txn.area_pyeong,
                f"{txn.floor}층",
                txn.price,
            ]
            for col_idx, val in enumerate(data):
                cell = table.cell(row_idx, col_idx)
                cell.text = val
                for p in cell.text_frame.paragraphs:
                    p.font.size = Pt(9)
                    p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
                    p.alignment = PP_ALIGN.CENTER
                if row_idx % 2 == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor(0xF5, 0xF5, 0xF5)

    # ── 우측: 매매거래 그래프 (4.139", 2.102") ──
    if price_info.price_graph_image_path and os.path.exists(price_info.price_graph_image_path):
        slide.shapes.add_picture(
            price_info.price_graph_image_path,
            Inches(4.139), Inches(2.102),
            Inches(5.3), Inches(3.2),
        )

    # 출처
    add_source_text(slide, "*아실  *국토교통부 실거래가 공개시스템")

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
