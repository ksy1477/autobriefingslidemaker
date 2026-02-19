"""
텍스트 헬퍼 유틸리티
가격 포맷팅, 면적 변환 등
"""
import math
from typing import Optional


def format_price(price_raw: int) -> str:
    """
    원 단위 가격을 읽기 쉬운 한글 형식으로 변환

    Examples:
        640000000 -> "6억 4000만원"
        59000000  -> "5900만원"
        1200000000 -> "12억"
    """
    if price_raw >= 100000000:  # 1억 이상
        eok = price_raw // 100000000
        remainder = price_raw % 100000000
        man = remainder // 10000

        if man > 0:
            return f"{eok}억 {man:,}만원"
        else:
            return f"{eok}억"
    elif price_raw >= 10000:  # 1만원 이상
        man = price_raw // 10000
        return f"{man:,}만원"
    else:
        return f"{price_raw:,}원"


def parse_price_to_raw(price_str: str) -> Optional[int]:
    """
    한글 가격 문자열을 원 단위 정수로 변환

    Examples:
        "6.4억"   -> 640000000
        "6억 4000만원" -> 640000000
        "5900만원" -> 59000000
    """
    import re
    price_str = price_str.replace(",", "").replace(" ", "").strip()

    # "6.4억" 패턴
    m = re.match(r'(\d+\.?\d*)억(?:(\d+)만)?', price_str)
    if m:
        eok = float(m.group(1))
        man = int(m.group(2)) if m.group(2) else 0
        return int(eok * 100000000) + man * 10000

    # "5900만원" 패턴
    m = re.match(r'(\d+)만', price_str)
    if m:
        return int(m.group(1)) * 10000

    return None


def m2_to_pyeong(m2: float) -> str:
    """평방미터를 평으로 변환 (소수점 반올림)"""
    pyeong = m2 / 3.305785
    return f"{round(pyeong)}평"


def pyeong_to_m2(pyeong: float) -> float:
    """평을 평방미터로 변환"""
    return round(pyeong * 3.305785, 2)


def format_floor(floor_str: str) -> str:
    """층수 포맷 정규화"""
    return floor_str.strip()


def truncate_text(text: str, max_len: int = 20) -> str:
    """긴 텍스트를 최대 길이로 잘라서 반환"""
    if len(text) <= max_len:
        return text
    return text[:max_len - 1] + "…"
