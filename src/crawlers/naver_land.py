"""
네이버부동산 크롤러 (v3 - SSR HTML 파싱 + m.land API)
단지정보, 매물상세, 이미지 다운로드

데이터 수집 전략:
  1차: fin.land.naver.com SSR HTML에서 React Server Components 데이터 추출
  2차: m.land.naver.com 모바일 API로 매물 목록 조회
  3차: Playwright 브라우저 fallback (API 모두 실패 시)
"""
import os
import time
import random
import json
import re
import httpx
from typing import Optional, Dict, Any, List, Tuple

from src.models import ComplexInfo, PropertyDetail
from src.utils.url_parser import parse_naver_land_url


# ─── 상수 ───

DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/16.6 Mobile/15E148 Safari/604.1"
)


def polite_delay(min_sec: float = 1.0, max_sec: float = 2.5):
    """서버 부하 방지를 위한 랜덤 딜레이"""
    time.sleep(random.uniform(min_sec, max_sec))


# ─── SSR HTML 파싱 (메인 방식) ───

def _fetch_ssr_html(complex_id: str) -> str:
    """fin.land.naver.com에서 SSR HTML 가져오기"""
    url = f"https://fin.land.naver.com/complexes/{complex_id}?tab=complex-info"
    headers = {
        "User-Agent": DESKTOP_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9",
    }
    try:
        with httpx.Client(headers=headers, timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.text
    except Exception as e:
        print(f"  [WARN] SSR HTML 가져오기 실패: {e}")
    return ""


def _parse_rsc_data(html: str) -> Dict[str, Any]:
    """
    SSR HTML에서 React Server Components 데이터 추출.
    self.__next_f.push([type, "data"]) 패턴에서 JSON 객체들을 파싱.

    Returns:
        {
            "complex_detail": {...},   # 단지 상세 (name, address, ...)
            "photos": [...],           # 사진 목록
            "price_range": {...},      # 매매/전세 가격 범위
            "schools": [...],          # 학교 목록
            "pyeong_types": [...],     # 평형 목록
        }
    """
    result = {
        "complex_detail": None,
        "photos": None,
        "price_range": None,
        "schools": None,
        "pyeong_types": None,
    }

    # 모든 __next_f 청크에서 데이터 추출
    # 이스케이프된 따옴표를 올바르게 처리하는 정규식
    rsc_pattern = r'self\.__next_f\.push\(\[\d+,"((?:[^"\\]|\\.)*)"\]\)'
    for match in re.finditer(rsc_pattern, html, re.DOTALL):
        raw_chunk = match.group(1)
        if len(raw_chunk) < 100:
            continue

        # JS 문자열 이스케이프 디코드 (\" → ", \\ → \, etc.)
        try:
            chunk_clean = json.loads(f'"{raw_chunk}"')
        except (json.JSONDecodeError, ValueError):
            # 디코드 실패 시 단순 치환 fallback
            chunk_clean = raw_chunk.replace('\\"', '"').replace('\\\\', '\\')

        # 1. 단지 상세 (totalHouseholdNumber 포함)
        if "totalHouseholdNumber" in chunk_clean and not result["complex_detail"]:
            obj = _extract_json_object(chunk_clean, '"totalHouseholdNumber":')
            if obj and "totalHouseholdNumber" in obj:
                result["complex_detail"] = obj

        # 2. 사진 + 단지명 (complexName 포함)
        if "complexName" in chunk_clean and not result["photos"]:
            for m in re.finditer(r'"isSuccess":true,"result":\{', chunk_clean):
                obj = _extract_json_at(chunk_clean, m.end() - 1)
                if obj and "complexName" in obj:
                    result["photos"] = obj.get("photos", [])
                    break

        # 3. 가격 범위 (dealMinPrice 포함)
        if "dealMinPrice" in chunk_clean and not result["price_range"]:
            for m in re.finditer(r'"isSuccess":true,"result":\{', chunk_clean):
                obj = _extract_json_at(chunk_clean, m.end() - 1)
                if obj and "dealMinPrice" in obj:
                    result["price_range"] = obj
                    break

        # 4. 학교 정보
        if "walkingMinute" in chunk_clean and not result["schools"]:
            for m in re.finditer(r'"isSuccess":true,"result":\[', chunk_clean):
                arr = _extract_json_array_at(chunk_clean, m.end() - 1)
                if arr and len(arr) > 0 and "walkingMinute" in arr[0]:
                    result["schools"] = arr
                    break

        # 5. 평형 목록 (pyeongTypeNumber 포함)
        if "pyeongTypeNumber" in chunk_clean and not result["pyeong_types"]:
            for m in re.finditer(r'"isSuccess":true,"result":\[', chunk_clean):
                arr = _extract_json_array_at(chunk_clean, m.end() - 1)
                if arr and len(arr) > 0 and "pyeongTypeNumber" in arr[0]:
                    result["pyeong_types"] = arr
                    break

    return result


def _extract_json_object(text: str, marker: str) -> Optional[Dict]:
    """텍스트에서 marker 위치의 JSON 객체 추출"""
    idx = text.find(marker)
    if idx < 0:
        return None

    # 이 marker를 포함하는 { 찾기
    brace = 0
    start = idx
    while start > 0:
        if text[start] == '}':
            brace += 1
        elif text[start] == '{':
            if brace == 0:
                break
            brace -= 1
        start -= 1

    return _extract_json_at(text, start)


def _extract_json_at(text: str, start: int) -> Optional[Dict]:
    """text[start]부터 시작하는 JSON 객체 추출"""
    if start >= len(text) or text[start] != '{':
        return None

    brace = 0
    i = start
    while i < len(text):
        if text[i] == '{':
            brace += 1
        elif text[i] == '}':
            brace -= 1
            if brace == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
        i += 1
    return None


def _extract_json_array_at(text: str, start: int) -> Optional[List]:
    """text[start]부터 시작하는 JSON 배열 추출"""
    if start >= len(text) or text[start] != '[':
        return None

    bracket = 0
    i = start
    while i < len(text):
        if text[i] == '[':
            bracket += 1
        elif text[i] == ']':
            bracket -= 1
            if bracket == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
        i += 1
    return None


# ─── m.land.naver.com 모바일 API ───

def _mland_api_get(path: str, params: Optional[Dict] = None) -> Optional[Any]:
    """m.land.naver.com 모바일 API 호출"""
    url = f"https://m.land.naver.com{path}"
    headers = {
        "User-Agent": MOBILE_UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Referer": "https://m.land.naver.com/",
    }
    try:
        with httpx.Client(headers=headers, timeout=10.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                ct = resp.headers.get("content-type", "")
                if "json" in ct:
                    return resp.json()
    except Exception as e:
        print(f"  [WARN] m.land API 실패: {path} - {e}")
    return None


def _fetch_article_list(
    complex_id: str,
    cortar_no: str = "0000000000",
    trade_type: str = "A1",
    page: int = 1,
) -> List[Dict]:
    """m.land.naver.com에서 매물 목록 조회"""
    data = _mland_api_get(
        "/complex/getComplexArticleList",
        params={
            "hscpNo": complex_id,
            "cortarNo": cortar_no,
            "tradTpCd": trade_type,
            "order": "point_",
            "showR0": "N",
            "page": str(page),
        },
    )
    if data:
        result = data.get("result", {})
        return result.get("list", [])
    return []


# ─── 이미지 다운로드 ───

def _download_image(url: str, save_path: str) -> bool:
    """이미지 다운로드"""
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        headers = {
            "User-Agent": DESKTOP_UA,
            "Referer": "https://fin.land.naver.com/",
        }
        with httpx.Client(headers=headers, timeout=30.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                f.write(response.content)
        return True
    except Exception as e:
        print(f"[ERROR] 이미지 다운로드 실패: {url[:80]} - {e}")
        return False


# ─── 공개 API ───

def fetch_complex_info(complex_id: str, temp_dir: str = "temp") -> Optional[ComplexInfo]:
    """
    단지 기본정보 조회

    1차: fin.land.naver.com SSR HTML에서 RSC 데이터 파싱
    2차: m.land.naver.com 매물 목록에서 기본정보 추출

    Args:
        complex_id: 단지 ID
        temp_dir: 이미지 저장 임시 폴더

    Returns:
        ComplexInfo 또는 None
    """
    print(f"  단지정보 수집 중 (ID: {complex_id})...")

    # 1. SSR HTML 파싱
    html = _fetch_ssr_html(complex_id)
    rsc_data = _parse_rsc_data(html) if html else {}

    detail = rsc_data.get("complex_detail")
    photos_data = rsc_data.get("photos", [])

    # 디버그 데이터 저장
    debug_dir = os.path.join(temp_dir, complex_id)
    os.makedirs(debug_dir, exist_ok=True)
    try:
        serializable = {}
        for k, v in rsc_data.items():
            if v is not None:
                serializable[k] = v
        with open(os.path.join(debug_dir, "rsc_data.json"), "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    if detail:
        print(f"  [OK] SSR 데이터에서 단지정보 추출 성공")

        # 주소 구성
        addr = detail.get("address", {})
        address_parts = [
            addr.get("city", ""),
            addr.get("division", ""),
            addr.get("sector", ""),
            addr.get("jibun", ""),
        ]
        address = " ".join(p for p in address_parts if p)
        road_address = addr.get("roadName", "")
        if road_address and address:
            address = f"{address} ({road_address})"

        # 좌표
        coords = detail.get("coordinates", {})
        longitude = coords.get("xCoordinate")
        latitude = coords.get("yCoordinate")

        # 기본정보
        name = detail.get("name", "")
        total_units = detail.get("totalHouseholdNumber", 0)
        dong_count = detail.get("dongCount", 0)
        construction_company = detail.get("constructionCompany", "")

        # 주차
        parking_info = detail.get("parkingInfo", {})
        parking_total = parking_info.get("totalParkingCount", 0)
        parking_per_unit = parking_info.get("parkingCountPerHousehold", 0)

        # 준공일
        use_approval = detail.get("useApprovalDate", "0000")
        try:
            built_year = int(str(use_approval)[:4])
        except (ValueError, TypeError):
            built_year = 0

        # 법정동코드 (매물 조회에 필요)
        legal_division = addr.get("legalDivisionNumber", "")

        # 해시태그
        hashtags = []
        if total_units >= 1000:
            hashtags.append("대단지")
        if built_year >= 2015:
            hashtags.append("신축")

        # 전경사진 다운로드
        aerial_photo_path = _download_complex_photo(
            complex_id, photos_data, temp_dir
        )

        info = ComplexInfo(
            complex_id=complex_id,
            name=name,
            address=address,
            total_units=total_units,
            parking_total=parking_total,
            parking_per_unit=parking_per_unit,
            built_year=built_year,
            hashtags=hashtags,
            latitude=latitude,
            longitude=longitude,
            aerial_photo_path=aerial_photo_path,
        )

        # 메타데이터 파일 저장 (법정동코드 등)
        meta = {
            "legal_division_number": legal_division,
            "dong_count": dong_count,
            "construction_company": construction_company,
            "road_address": road_address,
        }
        try:
            with open(os.path.join(debug_dir, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return info

    # 2. m.land API에서 매물 목록으로 기본정보 추출 (최소한의 fallback)
    print(f"  [FALLBACK] m.land 매물 목록에서 기본정보 추출 시도...")
    articles = _fetch_article_list(complex_id)
    if articles:
        first = articles[0]
        name = first.get("atclNm", f"단지_{complex_id}")
        print(f"  [OK] 매물 목록에서 단지명 확인: {name}")

        return ComplexInfo(
            complex_id=complex_id,
            name=name,
            address="",
            total_units=0,
            parking_total=0,
            parking_per_unit=0,
            built_year=0,
            hashtags=[],
        )

    # 3. 페이지 타이틀에서 최소한의 정보
    if html:
        title_match = re.search(r'<title>(.*?)</title>', html)
        if title_match:
            title = title_match.group(1).strip()
            if title and "네이버" not in title and "404" not in title:
                print(f"  [FALLBACK] 페이지 타이틀에서 단지명 확인: {title}")
                return ComplexInfo(
                    complex_id=complex_id,
                    name=title,
                    address="",
                    total_units=0,
                    parking_total=0,
                    parking_per_unit=0,
                    built_year=0,
                    hashtags=[],
                )

    print(f"  [FAIL] 단지정보 수집 실패 (complex_id={complex_id})")
    return None


def _download_complex_photo(
    complex_id: str, photos: List[Dict], temp_dir: str
) -> Optional[str]:
    """단지 전경사진 다운로드"""
    save_path = os.path.join(temp_dir, complex_id, "aerial.jpg")

    # 캐시 있으면 재사용
    if os.path.exists(save_path):
        print(f"  [CACHE] 전경사진 캐시 사용")
        return save_path

    if not photos:
        return None

    # 전경 사진 우선
    photo_url = None
    for photo in photos:
        url = photo.get("url", "")
        category = photo.get("category", "")
        if "전경" in category and url:
            photo_url = url
            break

    # 전경이 없으면 첫 번째 사진
    if not photo_url and photos:
        photo_url = photos[0].get("url", "")

    if photo_url:
        if _download_image(photo_url, save_path):
            return save_path

    return None


def _load_legal_division(complex_id: str, temp_dir: str) -> str:
    """저장된 메타데이터에서 법정동코드 로드"""
    meta_path = os.path.join(temp_dir, complex_id, "meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                return meta.get("legal_division_number", "0000000000")
        except Exception:
            pass
    return "0000000000"


def fetch_property_detail(
    complex_id: str,
    article_no: str,
    complex_name: str,
    user_input: Any,
    temp_dir: str = "temp"
) -> Optional[PropertyDetail]:
    """
    매물 상세정보 조회

    1차: m.land.naver.com 매물 목록에서 해당 매물 찾기
    2차: 사용자 입력값으로 기본 PropertyDetail 생성

    Args:
        complex_id: 단지 ID
        article_no: 매물 번호
        complex_name: 단지명
        user_input: PropertyInput 사용자 입력
        temp_dir: 이미지 저장 임시 폴더

    Returns:
        PropertyDetail 또는 None
    """
    # 기본값 (사용자 입력 기반)
    base_detail = PropertyDetail(
        complex_id=complex_id,
        complex_name=complex_name,
        dong=user_input.dong,
        floor=user_input.floor,
        price=user_input.price,
        direction=user_input.direction,
        structure=user_input.structure,
        memo=user_input.memo,
    )

    if not article_no:
        return base_detail

    # m.land API에서 매물 목록 조회 후 해당 매물 찾기
    cortar_no = _load_legal_division(complex_id, temp_dir)
    articles = _fetch_article_list(complex_id, cortar_no)

    article_data = None
    for art in articles:
        if str(art.get("atclNo")) == str(article_no):
            article_data = art
            break

    if not article_data:
        # 다른 거래유형으로도 시도
        polite_delay(0.5, 1.0)
        for trade_type in ["B1", "B2"]:  # 전세, 월세
            articles = _fetch_article_list(complex_id, cortar_no, trade_type)
            for art in articles:
                if str(art.get("atclNo")) == str(article_no):
                    article_data = art
                    break
            if article_data:
                break

    if article_data:
        print(f"  [OK] 매물 상세 정보 수집 성공 (atclNo={article_no})")

        # 면적
        area_m2 = None
        area_pyeong = None
        spc2 = article_data.get("spc2")
        if spc2:
            try:
                area_m2 = float(spc2)
                area_pyeong = f"{round(area_m2 / 3.305785)}평"
            except (ValueError, TypeError):
                pass

        # 방향
        direction = article_data.get("direction") or user_input.direction

        # 가격 (prcInfo 필드)
        price = article_data.get("prcInfo") or user_input.price

        # 층
        floor_info = article_data.get("flrInfo") or user_input.floor

        # 동
        dong = article_data.get("bildNm") or user_input.dong

        # 설명
        desc = article_data.get("atclFetrDesc", "")
        memo = user_input.memo or desc

        # 매물 이미지 다운로드
        rep_img = article_data.get("repImgUrl", "")
        article_img_path = None
        if rep_img:
            if not rep_img.startswith("http"):
                rep_img = f"https://landthumb-phinf.pstatic.net{rep_img}"
            img_save_path = os.path.join(temp_dir, complex_id, f"article_{article_no}.jpg")
            if os.path.exists(img_save_path):
                article_img_path = img_save_path
            elif _download_image(rep_img, img_save_path):
                article_img_path = img_save_path

        # 태그에서 방 정보 추출
        tags = article_data.get("tagList", [])
        rooms = None
        for tag in tags:
            if "방" in tag:
                m = re.search(r'(\d+)', tag.replace("세", "3").replace("두", "2").replace("한", "1").replace("네", "4"))
                if m:
                    rooms = int(m.group(1))
                    break
            # 한글 숫자 매핑
            if tag == "방세개":
                rooms = 3
                break
            elif tag == "방두개":
                rooms = 2
                break
            elif tag == "방네개":
                rooms = 4
                break
            elif tag == "방한개":
                rooms = 1
                break

        # 화장실 정보
        bathrooms = None
        for tag in tags:
            if "화장실" in tag:
                if "한개" in tag:
                    bathrooms = 1
                elif "두개" in tag or "2개" in tag:
                    bathrooms = 2
                break

        return PropertyDetail(
            complex_id=complex_id,
            complex_name=complex_name,
            dong=dong,
            floor=floor_info,
            price=price,
            direction=direction,
            structure=user_input.structure,
            memo=memo,
            rooms=rooms,
            bathrooms=bathrooms,
            area_pyeong=area_pyeong,
            area_m2=area_m2,
        )

    print(f"  [WARN] 매물 상세 수집 실패 → 사용자 입력값 사용")
    return base_detail


def fetch_all_for_complex(
    complex_id: str,
    property_inputs: list,
    temp_dir: str = "temp"
) -> dict:
    """
    한 단지에 대한 모든 데이터 수집

    Returns:
        {"complex_info": ComplexInfo, "properties": [PropertyDetail, ...]}
    """
    complex_info = fetch_complex_info(complex_id, temp_dir)
    if not complex_info:
        complex_info = ComplexInfo(
            complex_id=complex_id,
            name="정보 없음",
            address="",
            total_units=0,
            parking_total=0,
            parking_per_unit=0,
            built_year=0,
            hashtags=[],
        )

    properties = []
    for prop_input in property_inputs:
        _, article_no = parse_naver_land_url(prop_input.naver_land_url)
        if article_no:
            detail = fetch_property_detail(
                complex_id, article_no, complex_info.name, prop_input, temp_dir
            )
        else:
            detail = PropertyDetail(
                complex_id=complex_id,
                complex_name=complex_info.name,
                dong=prop_input.dong,
                floor=prop_input.floor,
                price=prop_input.price,
                direction=prop_input.direction,
                structure=prop_input.structure,
                memo=prop_input.memo,
            )
        if detail:
            properties.append(detail)

    return {
        "complex_info": complex_info,
        "properties": properties,
    }
