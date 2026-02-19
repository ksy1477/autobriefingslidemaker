"""
네이버부동산 URL 파서
URL에서 complexId와 articleNo를 추출
"""
import re
from urllib.parse import urlparse, parse_qs
from typing import Tuple, Optional


def parse_naver_land_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    네이버부동산 URL에서 complex_id와 article_no 추출

    지원 URL 패턴:
    - https://new.land.naver.com/complexes/12345?articleNo=67890
    - https://fin.land.naver.com/complexes/12345?articleNo=67890
    - https://land.naver.com/article/info.naver?article_id=67890

    Returns:
        (complex_id, article_no) 튜플
    """
    parsed = urlparse(url)

    # /complexes/{complexId} 패턴
    path_match = re.search(r'/complexes/(\d+)', parsed.path)
    complex_id = path_match.group(1) if path_match else None

    # querystring에서 articleNo 추출
    params = parse_qs(parsed.query)
    article_no = params.get('articleNo', [None])[0]

    # article_id 패턴 (구 네이버부동산)
    if article_no is None:
        article_no = params.get('article_id', [None])[0]

    return complex_id, article_no


def extract_complex_ids(urls: list) -> list:
    """
    여러 URL에서 고유한 complex_id 목록 추출 (순서 유지)
    """
    seen = set()
    result = []
    for url in urls:
        cid, _ = parse_naver_land_url(url)
        if cid and cid not in seen:
            seen.add(cid)
            result.append(cid)
    return result
