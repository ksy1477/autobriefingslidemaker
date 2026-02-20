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


# ─── 학교 SSR 데이터 추출 ───

def fetch_school_basic_from_ssr(complex_id: str) -> List[Dict]:
    """
    fin.land.naver.com SSR에서 배정 학교 기본정보 추출.

    Returns:
        [{"code": "B100001411", "name": "서울상봉초등학교", "operationType": "공립",
          "distance": 106, "walkingMinute": 2, "coordinates": {...}, ...}, ...]
    """
    html = _fetch_ssr_html(complex_id)
    if not html:
        return []

    rsc_data = _parse_rsc_data(html)
    schools = rsc_data.get("schools")
    return schools if schools else []


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
        supply_area_m2 = None
        spc1 = article_data.get("spc1")  # 공급면적
        spc2 = article_data.get("spc2")  # 전용면적
        if spc2:
            try:
                area_m2 = float(spc2)
                area_pyeong = f"{round(area_m2 / 3.305785)}평"
            except (ValueError, TypeError):
                pass
        if spc1:
            try:
                supply_area_m2 = float(spc1)
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
            supply_area_m2=supply_area_m2,
        )

    print(f"  [WARN] 매물 상세 수집 실패 → 사용자 입력값 사용")
    return base_detail


# ─── 평면도 & 배치도 이미지 캡처 ───

def _extract_pyeong_list(html: str) -> List[Dict]:
    """
    SSR HTML에서 평형별 정보 추출 (floorPlanUrls 포함).

    Returns:
        [{"number": 1, "name": "100", "floorPlanUrls": {...},
          "exclusiveArea": 82.96, ...}, ...]
    """
    rsc_pattern = r'self\.__next_f\.push\(\[\d+,"((?:[^"\\]|\\.)*)"\]\)'
    for match in re.finditer(rsc_pattern, html, re.DOTALL):
        raw_chunk = match.group(1)
        if "floorPlanUrls" not in raw_chunk:
            continue

        try:
            chunk_clean = json.loads(f'"{raw_chunk}"')
        except (json.JSONDecodeError, ValueError):
            chunk_clean = raw_chunk.replace('\\"', '"').replace('\\\\', '\\')

        # result 배열에서 floorPlanUrls 포함된 것 추출
        for rm in re.finditer(r'"result":\[', chunk_clean):
            arr = _extract_json_array_at(chunk_clean, rm.end() - 1)
            if arr and len(arr) > 0 and "floorPlanUrls" in arr[0]:
                return arr

    return []


def _match_pyeong_type(pyeong_list: List[Dict], area_pyeong: str) -> Optional[Dict]:
    """area_pyeong ("25평")과 매칭되는 평형 타입 찾기"""
    if not area_pyeong:
        return None

    # "25평" → 25
    m = re.search(r"(\d+)", area_pyeong)
    if not m:
        return None
    target_pyeong = int(m.group(1))

    for pt in pyeong_list:
        exclusive = pt.get("exclusiveArea", 0)
        if exclusive > 0:
            calc_pyeong = round(exclusive / 3.305785)
            if calc_pyeong == target_pyeong:
                return pt

    return None


def _download_floor_plan_from_ssr(
    complex_id: str,
    area_pyeong: str,
    temp_dir: str,
) -> Optional[str]:
    """
    SSR HTML에서 평면도 이미지 URL 추출 → 다운로드.

    Args:
        complex_id: 단지 ID
        area_pyeong: "25평" 등 매칭할 평형
        temp_dir: 이미지 저장 폴더

    Returns:
        저장된 이미지 파일 경로 또는 None
    """
    save_path = os.path.join(temp_dir, complex_id, "floor_plan.jpg")

    # 캐시 확인
    if os.path.exists(save_path):
        print(f"  [CACHE] 평면도 캐시 사용")
        return save_path

    html = _fetch_ssr_html(complex_id)
    if not html:
        return None

    pyeong_list = _extract_pyeong_list(html)
    if not pyeong_list:
        print(f"  [WARN] 평형 정보에서 평면도 URL을 찾지 못함")
        return None

    # area_pyeong으로 매칭, 실패 시 첫 번째 평형
    target = _match_pyeong_type(pyeong_list, area_pyeong)
    if not target:
        target = pyeong_list[0]

    target_name = target.get("name", "?")
    exclusive = target.get("exclusiveArea", 0)
    print(f"  평면도 대상 평형: {target_name} (전용 {exclusive}㎡)")

    # floorPlanUrls에서 첫 번째 이미지 URL 추출
    floor_urls = target.get("floorPlanUrls", {})
    base = floor_urls.get("BASE", {})
    for key in sorted(base.keys()):
        image_urls = base[key]
        if image_urls:
            url = image_urls[0]
            if _download_image(url, save_path):
                print(f"  [OK] 평면도 다운로드 완료")
                return save_path
            break

    print(f"  [WARN] 평면도 다운로드 실패")
    return None


async def _capture_site_plan_async(
    complex_id: str,
    latitude: float,
    longitude: float,
    temp_dir: str,
    timeout: int = 30000,
) -> Optional[str]:
    """
    네이버지도 위성+건물지도에서 단지 위치 스크린샷 캡처.

    단지 좌표 중심으로 zoom 18 레벨의 지도를 캡처하여
    건물 배치/동 번호가 보이는 이미지를 생성.

    Returns:
        저장된 이미지 파일 경로 또는 None
    """
    from playwright.async_api import async_playwright

    save_path = os.path.join(temp_dir, complex_id, "site_plan.png")
    if os.path.exists(save_path):
        print(f"  [CACHE] 단지위치 캐시 사용")
        return save_path

    if not latitude or not longitude:
        print(f"  [SKIP] 좌표 없음 → 단지위치 캡처 생략")
        return None

    url = f"https://map.naver.com/p?c={longitude},{latitude},18,0,0,0,dh"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                viewport={"width": 1000, "height": 900},
                device_scale_factor=2,
                locale="ko-KR",
                user_agent=DESKTOP_UA,
            )
            page = await context.new_page()
            await page.add_init_script(
                'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
            )

            await page.goto(url, wait_until="networkidle", timeout=timeout)
            await page.wait_for_timeout(5000)

            # 좌측 패널 숨기기
            await page.evaluate("""() => {
                const panel = document.querySelector('.svc_panel');
                if (panel) panel.style.display = 'none';
                document.querySelectorAll('[class*="StyledPanelLayout"]')
                    .forEach(el => el.style.display = 'none');
            }""")
            await page.wait_for_timeout(500)

            # 중앙 영역만 클리핑 (UI 컨트롤 제외)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            clip = {"x": 100, "y": 100, "width": 600, "height": 600}
            await page.screenshot(path=save_path, clip=clip)

            await context.close()
            await browser.close()

        print(f"  [OK] 단지위치 지도 캡처 완료")
        return save_path

    except Exception as e:
        print(f"  [WARN] 단지위치 캡처 실패: {e}")
        return None


def capture_complex_images(
    complex_id: str,
    area_pyeong: str,
    temp_dir: str,
    latitude: float = 0.0,
    longitude: float = 0.0,
) -> dict:
    """
    단지 평면도 + 단지위치 이미지 캡처 (메인 진입점).

    1. 평면도: SSR HTML에서 URL 추출 → 직접 다운로드
    2. 단지위치: 네이버지도에서 건물배치 지도 스크린샷

    Args:
        complex_id: 단지 ID
        area_pyeong: "25평" 등 매칭할 평형
        temp_dir: 이미지 저장 폴더
        latitude: 단지 위도
        longitude: 단지 경도

    Returns:
        {"floor_plan_path": str|None, "site_plan_path": str|None}
    """
    from src.crawlers.browser_utils import is_playwright_available, run_async

    result = {"floor_plan_path": None, "site_plan_path": None}
    print(f"  평면도/단지위치 이미지 캡처 중...")

    # 1. 평면도 — SSR HTML에서 다운로드
    result["floor_plan_path"] = _download_floor_plan_from_ssr(
        complex_id, area_pyeong, temp_dir
    )

    # 2. 단지위치 — 네이버지도 스크린샷
    if is_playwright_available() and latitude and longitude:
        site_plan = run_async(
            _capture_site_plan_async(complex_id, latitude, longitude, temp_dir)
        )
        result["site_plan_path"] = site_plan
    elif not latitude or not longitude:
        print(f"  [SKIP] 좌표 없음 → 단지위치 캡처 생략")
    else:
        print(f"  [SKIP] Playwright 미설치 → 단지위치 캡처 생략")

    return result


# ─── 단지정보 상세 스크린샷 ───

async def _capture_complex_detail_async(
    complex_id: str,
    temp_dir: str,
    timeout: int = 30000,
) -> Optional[str]:
    """
    fin.land.naver.com 단지정보 페이지에서 기본 정보(세대수, 사용승인일 등)
    상세 리스트를 스크린샷 캡처.

    Returns:
        저장된 이미지 파일 경로 또는 None
    """
    from playwright.async_api import async_playwright

    save_path = os.path.join(temp_dir, complex_id, "complex_detail.png")
    if os.path.exists(save_path):
        print(f"  [CACHE] 단지정보 스크린샷 캐시 사용")
        return save_path

    url = f"https://fin.land.naver.com/complexes/{complex_id}?tab=complex-info"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                viewport={"width": 1400, "height": 900},
                device_scale_factor=2,
                locale="ko-KR",
                user_agent=DESKTOP_UA,
            )
            page = await context.new_page()
            await page.add_init_script(
                'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
            )

            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            await page.wait_for_timeout(5000)

            # 기본 정보 리스트 (위치, 사용승인일, 세대수, 난방, 주차, ...)
            detail_list = page.locator(
                '[class*="ComplexBaseInfoSummary"] ul'
            ).first
            if await detail_list.count() > 0:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                await detail_list.screenshot(path=save_path)
                await context.close()
                await browser.close()
                print(f"  [OK] 단지정보 스크린샷 캡처 완료")
                return save_path

            await context.close()
            await browser.close()

        print(f"  [WARN] 단지정보 상세 리스트를 찾지 못함")
        return None

    except Exception as e:
        print(f"  [WARN] 단지정보 스크린샷 캡처 실패: {e}")
        return None


def capture_complex_detail_screenshot(
    complex_id: str,
    temp_dir: str,
) -> Optional[str]:
    """단지정보 상세 스크린샷 캡처 (동기 래퍼)"""
    from src.crawlers.browser_utils import is_playwright_available, run_async

    if not is_playwright_available():
        print(f"  [SKIP] Playwright 미설치 → 단지정보 스크린샷 생략")
        return None

    return run_async(_capture_complex_detail_async(complex_id, temp_dir))


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
