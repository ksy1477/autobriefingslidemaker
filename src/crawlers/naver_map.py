"""
네이버지도 크롤러
최근접 역 정보 + 강남역 대중교통 소요시간 수집
HTTP API 기반 (Playwright 불필요)
"""
import os
import re
import json
import math
from typing import Optional, Dict, Tuple
from urllib.parse import quote

import httpx

from src.models import LocationInfo
from src.processors.image_processor import create_placeholder_image
from src.data.subway_stations import SEOUL_STATIONS


DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# 강남역 좌표
GANGNAM_LAT = 37.497942
GANGNAM_LNG = 127.027621


# ─── 거리/시간 계산 유틸 ───

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 직선 거리 (km)"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _estimate_walk_minutes(distance_m: float) -> int:
    """도보 소요시간 추정 (평균 보행속도 4.5km/h)"""
    if distance_m <= 0:
        return 0
    return max(1, round(distance_m / 1000 * 60 / 4.5))


def _estimate_transit_minutes(distance_km: float) -> int:
    """대중교통 소요시간 추정 (평균 22km/h + 대기 10분)"""
    if distance_km <= 0:
        return 0
    return max(10, round(distance_km / 22 * 60 + 10))


# ─── SSR 기반 역 정보 추출 ───

def _fetch_station_from_land_ssr(complex_id: str) -> Dict:
    """
    fin.land.naver.com SSR HTML에서 교통/역 정보 추출

    Returns:
        {"station_name": "...", "line": "...", "walk_minutes": N, "distance_m": N}
        또는 빈 dict
    """
    from src.crawlers.naver_land import _fetch_ssr_html

    # 교통 정보 탭 시도
    for tab in ["complex-info", ""]:
        url = f"https://fin.land.naver.com/complexes/{complex_id}"
        if tab:
            url += f"?tab={tab}"

        headers = {
            "User-Agent": DESKTOP_UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ko-KR,ko;q=0.9",
        }
        try:
            with httpx.Client(headers=headers, timeout=15.0, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    result = _parse_transport_rsc(resp.text)
                    if result:
                        return result
        except Exception as e:
            print(f"  [WARN] SSR 교통 데이터 요청 실패: {e}")

    return {}


def _parse_transport_rsc(html: str) -> Dict:
    """RSC 청크에서 교통(지하철역) 관련 데이터 검색"""
    rsc_pattern = r'self\.__next_f\.push\(\[\d+,"((?:[^"\\]|\\.)*)"\]\)'

    for match in re.finditer(rsc_pattern, html, re.DOTALL):
        raw_chunk = match.group(1)
        if len(raw_chunk) < 50:
            continue

        try:
            chunk_clean = json.loads(f'"{raw_chunk}"')
        except (json.JSONDecodeError, ValueError):
            chunk_clean = raw_chunk.replace('\\"', '"').replace('\\\\', '\\')

        # 지하철역 관련 키워드 검색
        transport_keywords = [
            "stationName", "subwayLine", "nearestStation",
            "transportations", "subwayStations", "nearbySubway",
        ]
        if any(kw in chunk_clean for kw in transport_keywords):
            result = _extract_station_info(chunk_clean)
            if result:
                return result

    return {}


def _extract_station_info(text: str) -> Dict:
    """텍스트에서 지하철역 정보 JSON 추출"""
    # "stationName":"역이름" 패턴
    station_match = re.search(r'"stationName"\s*:\s*"([^"]+)"', text)
    line_match = re.search(r'"(?:subwayLine|lineName|lineNumber)"\s*:\s*"([^"]+)"', text)
    walk_match = re.search(r'"(?:walkTime|walkMinute|walkingMinute)"\s*:\s*(\d+)', text)
    dist_match = re.search(r'"(?:distance|distanceMeter)"\s*:\s*(\d+)', text)

    if station_match:
        return {
            "station_name": station_match.group(1),
            "line": line_match.group(1) if line_match else "",
            "walk_minutes": int(walk_match.group(1)) if walk_match else 0,
            "distance_m": int(dist_match.group(1)) if dist_match else 0,
        }
    return {}


# ─── 내장 지하철역 DB 검색 ───

# 사람들이 선호하는 주요 노선 (번호선 + 신분당/수인분당)
_PREFERRED_LINES = {
    "1호선", "2호선", "3호선", "4호선", "5호선",
    "6호선", "7호선", "8호선", "9호선",
    "신분당선", "수인분당선",
}

# 주요 노선 역이 이 거리(m) 이내이면 비주요 노선보다 우선
_PREFERRED_MAX_DISTANCE_M = 1500


def _find_nearest_station_db(lat: float, lng: float) -> Dict:
    """
    내장 서울 지하철역 DB에서 가장 가까운 역 검색

    주요 노선(1~9호선, 신분당선, 수인분당선) 역이 1.5km 이내에 있으면
    비주요 노선(경의중앙선, 경춘선 등)보다 우선 선택한다.

    Returns:
        {"station_name": "...", "line": "...", "distance_m": N, "walk_minutes": N}
    """
    if not lat or not lng:
        return {}

    nearest_any = None
    nearest_any_dist = float("inf")
    nearest_preferred = None
    nearest_preferred_dist = float("inf")

    for name, line, s_lat, s_lng in SEOUL_STATIONS:
        dist_m = _haversine_km(lat, lng, s_lat, s_lng) * 1000
        entry = {
            "station_name": name + "역" if not name.endswith("역") else name,
            "line": line,
            "lat": s_lat,
            "lng": s_lng,
            "distance_m": dist_m,
            "walk_minutes": _estimate_walk_minutes(dist_m),
        }

        # 전체 최근접
        if dist_m < nearest_any_dist:
            nearest_any_dist = dist_m
            nearest_any = entry

        # 주요 노선 최근접
        if line in _PREFERRED_LINES and dist_m < nearest_preferred_dist:
            nearest_preferred_dist = dist_m
            nearest_preferred = entry

    # 주요 노선 역이 1.5km 이내이면 우선 선택
    if nearest_preferred and nearest_preferred_dist <= _PREFERRED_MAX_DISTANCE_M:
        if nearest_any and nearest_any_dist < nearest_preferred_dist:
            print(f"  [교통] {nearest_any['station_name']}({nearest_any['line']}) "
                  f"{nearest_any_dist:.0f}m 대신 → "
                  f"{nearest_preferred['station_name']}({nearest_preferred['line']}) "
                  f"{nearest_preferred_dist:.0f}m 선택 (주요노선 우선)")
        return nearest_preferred

    return nearest_any or {}


# ─── Naver Map 검색 API ───

def _search_nearby_station_api(lat: float, lng: float) -> Dict:
    """
    Naver Map 검색 API로 가까운 지하철역 검색

    Returns:
        {"station_name": "...", "line": "...", "lat": N, "lng": N, "distance_m": N}
    """
    headers = {
        "User-Agent": DESKTOP_UA,
        "Referer": "https://map.naver.com/",
        "Accept": "application/json",
    }

    # Naver Map 장소 검색 API (내부 API)
    search_urls = [
        "https://map.naver.com/p/api/search/allSearch",
        "https://map.naver.com/v5/api/search/allSearch",
    ]

    for base_url in search_urls:
        try:
            params = {
                "query": "지하철역",
                "type": "all",
                "searchCoord": f"{lng};{lat}",
                "page": "1",
                "displayCount": "5",
            }
            with httpx.Client(headers=headers, timeout=10.0) as client:
                resp = client.get(base_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    result = _parse_station_search_result(data, lat, lng)
                    if result:
                        return result
        except Exception:
            continue

    return {}


def _parse_station_search_result(data: dict, origin_lat: float, origin_lng: float) -> Dict:
    """검색 결과에서 가장 가까운 지하철역 정보 추출"""
    # 다양한 응답 구조 시도
    places = []

    # 일반적인 구조
    if isinstance(data, dict):
        for key in ["place", "result", "places", "items"]:
            if key in data:
                items = data[key]
                if isinstance(items, dict) and "list" in items:
                    places = items["list"]
                elif isinstance(items, list):
                    places = items
                break

    if not places:
        return {}

    # 지하철역 필터링 + 거리순 정렬
    stations = []
    for place in places:
        name = place.get("name", "") or place.get("title", "")
        if "역" not in name:
            continue
        p_lat = float(place.get("y", 0) or place.get("lat", 0))
        p_lng = float(place.get("x", 0) or place.get("lng", 0))
        if p_lat and p_lng:
            dist = _haversine_km(origin_lat, origin_lng, p_lat, p_lng) * 1000
            stations.append({
                "station_name": name,
                "lat": p_lat,
                "lng": p_lng,
                "distance_m": dist,
            })

    if not stations:
        return {}

    stations.sort(key=lambda s: s["distance_m"])
    nearest = stations[0]

    # 노선 추출 시도 (역이름에서)
    line = ""
    line_match = re.search(r'(\d+호선|[가-힣]+선)', nearest["station_name"])
    if line_match:
        line = line_match.group(1)

    return {
        "station_name": nearest["station_name"],
        "line": line,
        "lat": nearest["lat"],
        "lng": nearest["lng"],
        "distance_m": nearest["distance_m"],
    }


# ─── 대중교통 소요시간 조회 ───

def _fetch_transit_time_api(
    start_lat: float, start_lng: float,
    end_lat: float, end_lng: float,
) -> int:
    """
    Naver Map 대중교통 경로 API로 소요시간 조회

    Returns:
        소요시간 (분), 실패 시 0
    """
    headers = {
        "User-Agent": DESKTOP_UA,
        "Referer": "https://map.naver.com/",
        "Accept": "application/json",
    }

    # 여러 API 엔드포인트 시도
    endpoints = [
        "https://map.naver.com/v5/api/transit/directions/point-to-point",
        "https://map.naver.com/p/api/transit/directions/point-to-point",
    ]

    for url in endpoints:
        try:
            params = {
                "start": f"{start_lng},{start_lat}",
                "goal": f"{end_lng},{end_lat}",
                "crs": "EPSG:4326",
                "mode": "TIME",
                "lang": "ko",
                "includeDetailOperation": "true",
            }
            with httpx.Client(headers=headers, timeout=15.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    minutes = _parse_transit_time(data)
                    if minutes > 0:
                        return minutes
        except Exception:
            continue

    return 0


def _parse_transit_time(data: dict) -> int:
    """대중교통 경로 응답에서 최단 소요시간 추출"""
    # 다양한 응답 구조 대응
    min_time = 0

    # paths 배열
    paths = data.get("paths", data.get("route", data.get("routes", [])))
    if isinstance(paths, list):
        for path in paths:
            duration = path.get("duration", path.get("totalTime", 0))
            if isinstance(duration, (int, float)):
                minutes = int(duration)
                # 초 단위인 경우 분으로 변환
                if minutes > 300:
                    minutes = minutes // 60
                if min_time == 0 or minutes < min_time:
                    min_time = minutes

    # 단일 결과
    if min_time == 0:
        duration = data.get("duration", data.get("totalTime", 0))
        if isinstance(duration, (int, float)) and duration > 0:
            min_time = int(duration)
            if min_time > 300:
                min_time = min_time // 60

    return min_time


# ─── Playwright 스크린샷 (fallback) ───

def _build_naver_map_directions_url(
    start_lat: float, start_lng: float, start_name: str,
    end_lat: float, end_lng: float, end_name: str,
    mode: str = "walk",
) -> str:
    """네이버지도 경로탐색 URL 생성 (/p/ 형식)"""
    s_name = quote(start_name)
    e_name = quote(end_name)
    return (
        f"https://map.naver.com/p/directions/"
        f"{start_lng},{start_lat},{s_name},,,/"
        f"{end_lng},{end_lat},{e_name},,,/"
        f"-/{mode}"
    )


# ─── Mock ───

def fetch_location_info_mock(
    complex_id: str,
    complex_name: str = "",
    temp_dir: str = "temp",
) -> LocationInfo:
    """Mock 입지 정보 생성"""
    img_dir = os.path.join(temp_dir, complex_id)
    os.makedirs(img_dir, exist_ok=True)

    walk_img = os.path.join(img_dir, "walk_route.png")
    transit_img = os.path.join(img_dir, "transit_route.png")

    create_placeholder_image(walk_img, 600, 450, text="[도보 경로 지도]")
    create_placeholder_image(transit_img, 600, 450, text="[대중교통 경로 지도]")

    return LocationInfo(
        complex_id=complex_id,
        nearest_station="샘플역",
        station_line="2호선",
        walk_minutes=5,
        gangnam_minutes=35,
        walk_route_image_path=walk_img,
        transit_route_image_path=transit_img,
    )


# ─── 메인 함수 ───

def fetch_location_info(
    complex_id: str,
    complex_name: str = "",
    complex_lat: float = 0.0,
    complex_lng: float = 0.0,
    temp_dir: str = "temp",
    config: dict = None,
    use_mock: bool = False,
) -> LocationInfo:
    """
    입지 정보 수집 (HTTP API 기반)

    수집 정보:
    1. 가장 가까운 지하철역 + 도보/대중교통 소요시간
    2. 강남역까지 최단 대중교통 소요시간
    """
    if use_mock:
        return fetch_location_info_mock(complex_id, complex_name, temp_dir)

    config = config or {}
    gangnam = config.get("gangnam_station", {})
    gangnam_lat = gangnam.get("lat", GANGNAM_LAT)
    gangnam_lng = gangnam.get("lng", GANGNAM_LNG)

    img_dir = os.path.join(temp_dir, complex_id)
    os.makedirs(img_dir, exist_ok=True)

    # ── 1. 가장 가까운 지하철역 찾기 ──
    station_info = {}

    # 1-1. SSR HTML에서 교통 정보 추출
    print(f"  [교통] SSR에서 역 정보 추출 시도...")
    station_info = _fetch_station_from_land_ssr(complex_id)

    # 1-2. Naver Map 검색 API
    if not station_info and complex_lat and complex_lng:
        print(f"  [교통] Naver Map API로 근처 역 검색...")
        station_info = _search_nearby_station_api(complex_lat, complex_lng)

    # 1-3. 내장 지하철역 DB 검색 (fallback)
    if not station_info and complex_lat and complex_lng:
        print(f"  [교통] 내장 DB에서 근처 역 검색...")
        station_info = _find_nearest_station_db(complex_lat, complex_lng)

    nearest_station = station_info.get("station_name", "")
    station_line = station_info.get("line", "")
    station_distance_m = station_info.get("distance_m", 0)
    walk_minutes = station_info.get("walk_minutes", 0)
    station_transit_minutes = 0

    # 도보 시간 추정 (SSR에 없을 경우)
    if not walk_minutes and station_distance_m > 0:
        walk_minutes = _estimate_walk_minutes(station_distance_m)

    # 역이 멀면 대중교통 소요시간도 계산
    if walk_minutes > 10 and station_distance_m > 0:
        station_transit_minutes = max(5, walk_minutes // 3)

    # ── 2. 강남역까지 대중교통 소요시간 ──
    gangnam_minutes = 0

    if complex_lat and complex_lng:
        # 2-1. Naver Map API로 대중교통 소요시간 조회
        print(f"  [교통] 강남역까지 대중교통 소요시간 조회...")
        gangnam_minutes = _fetch_transit_time_api(
            complex_lat, complex_lng, gangnam_lat, gangnam_lng,
        )

        # 2-2. API 실패 시 거리 기반 추정
        if gangnam_minutes == 0:
            dist_km = _haversine_km(complex_lat, complex_lng, gangnam_lat, gangnam_lng)
            gangnam_minutes = _estimate_transit_minutes(dist_km)
            print(f"  [교통] 강남역 거리 {dist_km:.1f}km → 추정 {gangnam_minutes}분")

    # ── 3. 이미지 (placeholder) ──
    walk_img = os.path.join(img_dir, "walk_route.png")
    transit_img = os.path.join(img_dir, "transit_route.png")

    # Playwright 사용 가능하면 스크린샷 시도
    _try_capture_screenshots(
        complex_lat, complex_lng, complex_name,
        station_info, gangnam_lat, gangnam_lng,
        walk_img, transit_img,
    )

    # placeholder 생성 (이미지 없을 때)
    if not os.path.exists(walk_img):
        label = f"[{nearest_station or complex_name} → 최근접역 경로]"
        create_placeholder_image(walk_img, 600, 450, text=label)
    if not os.path.exists(transit_img):
        create_placeholder_image(transit_img, 600, 450, text="[강남역 대중교통 경로]")

    # 역 이름 정리
    if not nearest_station:
        nearest_station = "정보 없음"

    print(f"  [교통] 결과: {nearest_station}({station_line}) "
          f"도보 {walk_minutes}분, 강남역 {gangnam_minutes}분")

    return LocationInfo(
        complex_id=complex_id,
        nearest_station=nearest_station,
        station_line=station_line,
        walk_minutes=walk_minutes,
        station_transit_minutes=station_transit_minutes,
        gangnam_minutes=gangnam_minutes,
        walk_route_image_path=walk_img,
        transit_route_image_path=transit_img,
    )


def _try_capture_screenshots(
    complex_lat: float, complex_lng: float, complex_name: str,
    station_info: dict,
    gangnam_lat: float, gangnam_lng: float,
    walk_img_path: str, transit_img_path: str,
):
    """Playwright 가용 시 경로 스크린샷 캡처 시도"""
    from src.crawlers.browser_utils import is_playwright_available, run_async

    if not is_playwright_available():
        return
    if not complex_lat or not complex_lng:
        return

    # 도보 경로 (단지 → 최근접역)
    station_lat = station_info.get("lat", 0)
    station_lng = station_info.get("lng", 0)
    station_name = station_info.get("station_name", "")

    if station_lat and station_lng and not os.path.exists(walk_img_path):
        try:
            run_async(_capture_route_screenshot(
                complex_lat, complex_lng, complex_name,
                station_lat, station_lng, station_name,
                mode="walk", save_path=walk_img_path,
            ))
        except Exception as e:
            print(f"  [WARN] 도보 경로 스크린샷 실패: {e}")

    # 대중교통 경로 (단지 → 강남역)
    if not os.path.exists(transit_img_path):
        try:
            run_async(_capture_route_screenshot(
                complex_lat, complex_lng, complex_name,
                gangnam_lat, gangnam_lng, "강남역",
                mode="transit", save_path=transit_img_path,
            ))
        except Exception as e:
            print(f"  [WARN] 대중교통 경로 스크린샷 실패: {e}")


async def _capture_route_screenshot(
    start_lat: float, start_lng: float, start_name: str,
    end_lat: float, end_lng: float, end_name: str,
    mode: str, save_path: str,
    timeout: int = 30000,
) -> Optional[str]:
    """Playwright로 네이버지도 경로 스크린샷 캡처 (좌측 패널 숨김)"""
    from src.crawlers.browser_utils import get_browser_page

    try:
        url = _build_naver_map_directions_url(
            start_lat, start_lng, start_name,
            end_lat, end_lng, end_name,
            mode=mode,
        )
        async with get_browser_page() as page:
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            await page.wait_for_timeout(5000)

            # 좌측 검색결과 패널 숨기기 → 지도+경로만 표시
            await page.evaluate("""() => {
                const panel = document.querySelector('.svc_panel');
                if (panel) panel.style.display = 'none';
                const styled = document.querySelector('[class*="StyledPanelLayout"]');
                if (styled) styled.style.display = 'none';
            }""")
            await page.wait_for_timeout(500)

            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            await page.screenshot(path=save_path, full_page=False)
            return save_path
    except Exception as e:
        print(f"  [WARN] 경로 스크린샷 실패 ({mode}): {e}")
        return None
