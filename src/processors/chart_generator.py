"""
실거래가 추이 그래프 생성
matplotlib으로 15년 매매가 추이 차트 생성
"""
import os
from typing import List, Optional

import matplotlib
matplotlib.use('Agg')  # GUI 없는 환경에서 사용
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
from datetime import date

from src.models import Transaction


def _get_korean_font_paths():
    """OS별 한글 폰트 경로 목록 반환"""
    import platform
    system = platform.system()

    if system == 'Windows':
        return [
            "C:/Windows/Fonts/malgun.ttf",      # 맑은 고딕
            "C:/Windows/Fonts/NanumGothic.ttf",
            "C:/Windows/Fonts/gulim.ttc",        # 굴림
        ]
    elif system == 'Darwin':  # macOS
        return [
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/Library/Fonts/NanumGothic.ttf",
        ]
    else:  # Linux
        return [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/nhn-nanum/NanumGothic.ttf",
        ]


def _setup_korean_font():
    """한글 폰트 설정 (OS 자동 감지)"""
    font_paths = _get_korean_font_paths()
    for fp in font_paths:
        if os.path.exists(fp):
            font_manager.fontManager.addfont(fp)
            prop = font_manager.FontProperties(fname=fp)
            plt.rcParams['font.family'] = prop.get_name()
            break
    else:
        plt.rcParams['font.family'] = 'sans-serif'

    plt.rcParams['axes.unicode_minus'] = False


def generate_price_chart(
    transactions: List[Transaction],
    complex_name: str,
    output_path: str,
    figsize: tuple = (8, 4),
) -> Optional[str]:
    """
    실거래가 추이 차트 생성

    Args:
        transactions: 거래 내역 리스트
        complex_name: 단지명 (차트 제목용)
        output_path: 저장 경로
        figsize: 차트 크기

    Returns:
        저장된 이미지 경로 또는 None
    """
    if not transactions:
        return None

    _setup_korean_font()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 데이터 준비
    dates = [t.date for t in transactions]
    prices = [t.price_raw / 100000000 for t in transactions]  # 억 단위

    fig, ax = plt.subplots(figsize=figsize, dpi=150)

    # 스타일링
    ax.scatter(dates, prices, color='#C8102E', s=30, zorder=5, alpha=0.7)
    ax.plot(dates, prices, color='#C8102E', alpha=0.3, linewidth=1)

    # 축 설정
    ax.set_ylabel('매매가 (억원)', fontsize=11)
    ax.set_title(f'{complex_name} 매매가 추이', fontsize=14, fontweight='bold', pad=15)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_major_locator(mdates.YearLocator(3))
    plt.xticks(rotation=0, fontsize=9)
    plt.yticks(fontsize=9)

    # 그리드
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    # 배경
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#FAFAFA')

    # 여백
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    return output_path
