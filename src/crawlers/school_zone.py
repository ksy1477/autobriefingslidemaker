"""
학군 크롤러
초등학교: NEIS API로 상세정보 + 네이버지도 도보 경로 스크린샷
중·고등학교: 아실 학군지도 스크린샷

데이터 수집 전략:
  1. SSR에서 배정 학교 기본정보 (학교명, 거리, 도보시간) 획득
  2. NEIS 개방 API (open.neis.go.kr)로 학교 상세정보 (주소, 전화, 설립일, 홈페이지 등)
  3. Playwright로 네이버지도 도보 경로 / 학군지도 스크린샷 캡처
"""
import os
import re
import json
import httpx
from typing import Optional, Tuple, Dict, List
from urllib.parse import quote

from src.models import SchoolInfo
from src.processors.image_processor import create_placeholder_image


# ─── NEIS 개방 API ───

NEIS_API_URL = "https://open.neis.go.kr/hub/schoolInfo"


def _fetch_neis_school_info(school_name: str) -> Optional[Dict]:
    """
    NEIS 개방 API에서 학교 상세정보 조회 (인증키 불필요)

    Args:
        school_name: 학교명 (예: "서울상봉초등학교")

    Returns:
        학교 상세정보 dict 또는 None
    """
    params = {
        "Type": "json",
        "SCHUL_NM": school_name,
        "pSize": "5",
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(NEIS_API_URL, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()

            # 응답 파싱
            school_info = data.get("schoolInfo", [])
            if len(school_info) < 2:
                return None

            rows = school_info[1].get("row", [])
            if not rows:
                return None

            # 정확한 이름 매칭 우선
            for row in rows:
                if row.get("SCHUL_NM") == school_name:
                    return row

            # 정확한 매칭 없으면 첫 번째 결과
            return rows[0]

    except Exception as e:
        print(f"  [WARN] NEIS API 조회 실패 ({school_name}): {e}")
        return None


def _format_date(ymd: str) -> str:
    """YYYYMMDD → YYYY.MM.DD 형식"""
    if ymd and len(ymd) >= 8:
        return f"{ymd[:4]}.{ymd[4:6]}.{ymd[6:8]}"
    return ymd or ""


def _build_school_info_from_neis(
    neis_data: Dict,
    ssr_data: Optional[Dict] = None,
) -> Dict:
    """NEIS 데이터 + SSR 데이터를 조합하여 학교 상세정보 구성"""
    address = neis_data.get("ORG_RDNMA", "")
    address_detail = neis_data.get("ORG_RDNDA", "")
    if address_detail:
        address_detail = address_detail.strip().lstrip("/").strip()

    result = {
        "name": neis_data.get("SCHUL_NM", ""),
        "address": address.strip(),
        "phone": neis_data.get("ORG_TELNO", ""),
        "founding_date": _format_date(neis_data.get("FOND_YMD", "")),
        "type": neis_data.get("FOND_SC_NM", ""),
        "education_office": neis_data.get("ATPT_OFCDC_SC_NM", ""),
        "coedu": neis_data.get("COEDU_SC_NM", ""),
        "homepage": neis_data.get("HMPG_ADRES", ""),
    }

    if ssr_data:
        walk_min = ssr_data.get("walkingMinute", 0)
        distance = ssr_data.get("distance", 0)
        result["walk_distance"] = f"도보 {walk_min}분" if walk_min else ""
        result["distance_m"] = distance
    else:
        result["walk_distance"] = ""
        result["distance_m"] = 0

    return result


# ─── 학교 좌표 검색 (Nominatim HTTP) ───

def _geocode_school(school_name: str, address: str = "") -> Tuple[float, float]:
    """
    OpenStreetMap Nominatim으로 학교 좌표 검색 (HTTP, 브라우저 불필요)

    Returns:
        (lng, lat) 또는 (0.0, 0.0)
    """
    headers = {"User-Agent": "RealEstateBriefingBot/1.0"}
    queries = [school_name]
    # "서울" 접두사 제거한 검색어 추가
    short_name = re.sub(r"^서울", "", school_name)
    if short_name != school_name:
        queries.append(short_name + " 서울")
    # NEIS 주소
    if address:
        queries.append(address)

    for q in queries:
        try:
            resp = httpx.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "json", "limit": "1", "countrycodes": "kr"},
                headers=headers, timeout=10.0,
            )
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    lat = float(results[0]["lat"])
                    lon = float(results[0]["lon"])
                    if lat and lon:
                        return lon, lat
        except Exception:
            continue

    return 0.0, 0.0


# ─── 네이버지도 도보 경로 스크린샷 ───

async def _capture_walk_route_to_school(
    complex_lat: float, complex_lng: float, complex_name: str,
    school_lat: float, school_lng: float, school_name: str,
    save_path: str,
    timeout: int = 30000,
) -> Optional[str]:
    """
    네이버지도에서 단지→초등학교 도보 경로 스크린샷 캡처
    (좌측 패널 숨김, 지도+경로만 표시)
    """
    from src.crawlers.browser_utils import get_browser_page

    try:
        s_name = quote(complex_name)
        e_name = quote(school_name)
        url = (
            f"https://map.naver.com/p/directions/"
            f"{complex_lng},{complex_lat},{s_name},,,/"
            f"{school_lng},{school_lat},{e_name},,,/"
            f"-/walk"
        )

        async with get_browser_page() as page:
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            await page.wait_for_timeout(5000)

            # 좌측 패널 숨기기
            await page.evaluate("""() => {
                const panel = document.querySelector('.svc_panel');
                if (panel) panel.style.display = 'none';
                const styled = document.querySelector('[class*="StyledPanelLayout"]');
                if (styled) styled.style.display = 'none';
            }""")
            await page.wait_for_timeout(500)

            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            await page.screenshot(path=save_path, full_page=False)
            print(f"  [학군] 도보 경로 스크린샷 저장: {os.path.basename(save_path)}")
            return save_path

    except Exception as e:
        print(f"  [WARN] 도보 경로 스크린샷 실패: {e}")
        return None


# ─── Mock ───

def fetch_school_info_mock(
    complex_id: str,
    complex_name: str = "",
    temp_dir: str = "temp",
) -> SchoolInfo:
    """Mock 학군 정보 생성"""
    img_dir = os.path.join(temp_dir, complex_id)
    os.makedirs(img_dir, exist_ok=True)

    elem_img = os.path.join(img_dir, "elementary_zone.png")
    mh_img = os.path.join(img_dir, "middle_high_zone.png")

    create_placeholder_image(elem_img, 800, 600, text="[초등학교 도보 경로]")
    create_placeholder_image(mh_img, 800, 600, text="[중·고등학교 학군지도]")

    short_name = complex_name.replace("아파트", "").strip() if complex_name else "샘플"
    return SchoolInfo(
        complex_id=complex_id,
        elementary_name=f"서울{short_name}초등학교",
        elementary_map_path=elem_img,
        middle_high_map_path=mh_img,
    )


# ─── Playwright: 중·고등학교 학군 (asil.kr) ───

async def _capture_middle_high_school_zone(
    address: str,
    save_path: str,
    timeout: int = 30000,
) -> Optional[str]:
    """아실에서 중·고등학교 학군 지도 스크린샷 캡처"""
    from src.crawlers.browser_utils import get_browser_page

    try:
        async with get_browser_page() as page:
            url = "https://asil.kr/asil/svl/schoolZone"
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            await page.wait_for_timeout(3000)

            search_input = await page.query_selector(
                "input[type='text'], input[placeholder*='검색'], #search"
            )
            if search_input:
                await search_input.fill(address)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(5000)

            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            await page.screenshot(path=save_path, full_page=False)
            return save_path

    except Exception as e:
        print(f"[WARN] 중·고등학교 학군 캡처 실패: {e}")
        return None


# ─── 통합 수집 (async) ───

async def _fetch_school_info_async(
    complex_id: str,
    complex_name: str,
    address: str,
    complex_lat: float,
    complex_lng: float,
    elementary_name: str,
    neis_info: Dict,
    temp_dir: str = "temp",
) -> Optional[SchoolInfo]:
    """학군 데이터 수집 (네이버지도 도보 경로 + 아실 학군지도)"""
    img_dir = os.path.join(temp_dir, complex_id)

    # ── 1. 초등학교 도보 경로 스크린샷 ──
    elem_img = os.path.join(img_dir, "elementary_zone.png")

    if elementary_name and complex_lat and complex_lng:
        # Nominatim으로 학교 좌표 검색 (HTTP, 동기)
        school_address = neis_info.get("address", "")
        print(f"  [학군] {elementary_name} 좌표 검색 중...")
        school_lng, school_lat = _geocode_school(elementary_name, school_address)

        if school_lng and school_lat:
            print(f"  [학군] 좌표 확인: ({school_lat:.6f}, {school_lng:.6f})")
            await _capture_walk_route_to_school(
                complex_lat, complex_lng, complex_name,
                school_lat, school_lng, elementary_name,
                elem_img,
            )
        else:
            print(f"  [WARN] {elementary_name} 좌표를 찾을 수 없습니다")

    # ── 2. 중·고등학교 학군지도 ──
    mh_img = os.path.join(img_dir, "middle_high_zone.png")
    await _capture_middle_high_school_zone(address, mh_img)

    # placeholder 대체
    if not os.path.exists(elem_img):
        create_placeholder_image(elem_img, 800, 600, text="[초등학교 도보 경로]")
    if not os.path.exists(mh_img):
        create_placeholder_image(mh_img, 800, 600, text="[중·고등학교 학군지도]")

    return SchoolInfo(
        complex_id=complex_id,
        elementary_name=neis_info.get("name") or elementary_name,
        elementary_address=neis_info.get("address", ""),
        elementary_phone=neis_info.get("phone", ""),
        elementary_founding_date=neis_info.get("founding_date", ""),
        elementary_type=neis_info.get("type", ""),
        elementary_education_office=neis_info.get("education_office", ""),
        elementary_coedu=neis_info.get("coedu", ""),
        elementary_homepage=neis_info.get("homepage", ""),
        elementary_walk_distance=neis_info.get("walk_distance", ""),
        elementary_distance_m=neis_info.get("distance_m", 0),
        elementary_map_path=elem_img,
        middle_high_map_path=mh_img,
    )


# ─── Wrapper ───

def fetch_school_info(
    complex_id: str,
    complex_name: str = "",
    address: str = "",
    complex_lat: float = 0.0,
    complex_lng: float = 0.0,
    temp_dir: str = "temp",
    use_mock: bool = False,
    ssr_schools: Optional[List[Dict]] = None,
) -> SchoolInfo:
    """
    학군 정보 수집

    Args:
        complex_id: 단지 ID
        complex_name: 단지명
        address: 단지 주소 (검색용)
        complex_lat: 단지 위도
        complex_lng: 단지 경도
        temp_dir: 임시 파일 디렉토리
        use_mock: True이면 mock 데이터 사용
        ssr_schools: SSR에서 추출한 학교 기본정보 리스트

    Returns:
        SchoolInfo
    """
    if use_mock:
        return fetch_school_info_mock(complex_id, complex_name, temp_dir)

    # NEIS API로 학교 상세정보 수집
    neis_info = {}
    elementary_name = ""

    if ssr_schools:
        for school in ssr_schools:
            elementary_name = school.get("name", "")
            if elementary_name:
                print(f"  [NEIS] {elementary_name} 상세정보 조회...")
                neis_data = _fetch_neis_school_info(elementary_name)
                if neis_data:
                    neis_info = _build_school_info_from_neis(neis_data, school)
                    print(f"  [NEIS] 성공: {neis_info.get('address', '')}")
                else:
                    print(f"  [NEIS] 학교정보 없음")
            break

    if not elementary_name and complex_name:
        elementary_name = f"{complex_name} 배정 초등학교"

    # Playwright로 스크린샷 캡처 시도
    from src.crawlers.browser_utils import is_playwright_available, run_async

    img_dir = os.path.join(temp_dir, complex_id)
    elem_img = os.path.join(img_dir, "elementary_zone.png")
    mh_img = os.path.join(img_dir, "middle_high_zone.png")

    if is_playwright_available() and not use_mock:
        try:
            result = run_async(_fetch_school_info_async(
                complex_id=complex_id,
                complex_name=complex_name,
                address=address,
                complex_lat=complex_lat,
                complex_lng=complex_lng,
                elementary_name=elementary_name,
                neis_info=neis_info,
                temp_dir=temp_dir,
            ))
            if result:
                return result
        except Exception as e:
            print(f"  [WARN] Playwright 학군 스크린샷 실패: {e}")

    # Playwright 없거나 실패 시
    if not os.path.exists(elem_img):
        create_placeholder_image(elem_img, 800, 600, text="[초등학교 도보 경로]")
    if not os.path.exists(mh_img):
        create_placeholder_image(mh_img, 800, 600, text="[중·고등학교 학군지도]")

    return SchoolInfo(
        complex_id=complex_id,
        elementary_name=neis_info.get("name") or elementary_name,
        elementary_address=neis_info.get("address", ""),
        elementary_phone=neis_info.get("phone", ""),
        elementary_founding_date=neis_info.get("founding_date", ""),
        elementary_type=neis_info.get("type", ""),
        elementary_education_office=neis_info.get("education_office", ""),
        elementary_coedu=neis_info.get("coedu", ""),
        elementary_homepage=neis_info.get("homepage", ""),
        elementary_walk_distance=neis_info.get("walk_distance", ""),
        elementary_distance_m=neis_info.get("distance_m", 0),
        elementary_map_path=elem_img,
        middle_high_map_path=mh_img,
    )
