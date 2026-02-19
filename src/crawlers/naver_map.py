"""
네이버지도 크롤러
도보/대중교통 경로 스크린샷 및 입지 정보 수집
"""
import os
from typing import Optional
from urllib.parse import quote

from src.models import LocationInfo
from src.processors.image_processor import create_placeholder_image


# ─── Mock ───

def fetch_location_info_mock(
    complex_id: str,
    complex_name: str = "",
    temp_dir: str = "temp",
) -> LocationInfo:
    """Mock 입지 정보 생성 (Playwright/API 없을 때 사용)"""
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


# ─── Playwright 스크린샷 ───

def _build_naver_map_directions_url(
    start_lat: float, start_lng: float, start_name: str,
    end_lat: float, end_lng: float, end_name: str,
    mode: str = "walk",
) -> str:
    """네이버지도 경로탐색 URL 생성"""
    s_name = quote(start_name)
    e_name = quote(end_name)
    return (
        f"https://map.naver.com/v5/directions/"
        f"{start_lng},{start_lat},{s_name},false,false/"
        f"{end_lng},{end_lat},{e_name},false,false/"
        f"-/{mode}"
    )


async def _capture_route_screenshot(
    start_lat: float, start_lng: float, start_name: str,
    end_lat: float, end_lng: float, end_name: str,
    mode: str,
    save_path: str,
    timeout: int = 30000,
) -> Optional[str]:
    """Playwright로 네이버지도 경로 스크린샷 캡처"""
    from src.crawlers.browser_utils import get_browser_page

    try:
        url = _build_naver_map_directions_url(
            start_lat, start_lng, start_name,
            end_lat, end_lng, end_name,
            mode=mode,
        )
        async with get_browser_page() as page:
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            await page.wait_for_timeout(5000)  # 지도 타일 로딩 대기

            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            await page.screenshot(path=save_path, full_page=False)
            return save_path
    except Exception as e:
        print(f"[WARN] 경로 스크린샷 실패 ({mode}): {e}")
        return None


async def _extract_route_info(page) -> dict:
    """경로 탐색 결과에서 소요시간 추출 시도"""
    info = {"minutes": 0}
    try:
        # 네이버지도 경로 결과에서 소요시간 텍스트 추출
        time_el = await page.query_selector(".summary_time, .route_time, [class*='time']")
        if time_el:
            text = await time_el.inner_text()
            # "약 5분", "50분" 등에서 숫자 추출
            import re
            match = re.search(r'(\d+)\s*분', text)
            if match:
                info["minutes"] = int(match.group(1))
    except Exception:
        pass
    return info


# ─── API 기반 수집 ───

async def _fetch_location_info_async(
    complex_id: str,
    complex_name: str,
    complex_lat: float,
    complex_lng: float,
    temp_dir: str = "temp",
    gangnam_lat: float = 37.497942,
    gangnam_lng: float = 127.027621,
) -> Optional[LocationInfo]:
    """실제 네이버지도 데이터 수집"""
    from src.crawlers.browser_utils import get_browser_page

    img_dir = os.path.join(temp_dir, complex_id)

    # 최근접 역 정보 추출 시도 (네이버지도 장소 페이지에서)
    nearest_station = ""
    station_line = ""
    walk_minutes = 0

    try:
        async with get_browser_page() as page:
            place_url = f"https://map.naver.com/v5/search/{quote(complex_name)}"
            await page.goto(place_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            # 주변 지하철 정보 추출 시도
            subway_el = await page.query_selector(
                "[class*='subway'], [class*='station'], [class*='transit']"
            )
            if subway_el:
                text = await subway_el.inner_text()
                import re
                # "중계역(7호선) 도보 2분" 패턴 매칭
                match = re.search(r'(\S+역)\s*\((\S+선)\)\s*도보\s*(\d+)분', text)
                if match:
                    nearest_station = match.group(1)
                    station_line = match.group(2)
                    walk_minutes = int(match.group(3))
    except Exception as e:
        print(f"[WARN] 역 정보 추출 실패: {e}")

    if not nearest_station:
        nearest_station = "정보 없음"
        station_line = ""
        walk_minutes = 0

    # 도보 경로 스크린샷 (단지 → 최근접역)
    walk_img = os.path.join(img_dir, "walk_route.png")
    walk_result = await _capture_route_screenshot(
        complex_lat, complex_lng, complex_name,
        complex_lat, complex_lng, nearest_station,  # 역 좌표를 모를 때 같은 위치 사용
        mode="walk",
        save_path=walk_img,
    )

    # 대중교통 경로 스크린샷 (단지 → 강남역)
    transit_img = os.path.join(img_dir, "transit_route.png")
    transit_result = await _capture_route_screenshot(
        complex_lat, complex_lng, complex_name,
        gangnam_lat, gangnam_lng, "강남역",
        mode="transit",
        save_path=transit_img,
    )

    # 대중교통 소요시간 추출 시도
    gangnam_minutes = 0
    if transit_result:
        try:
            async with get_browser_page() as page:
                url = _build_naver_map_directions_url(
                    complex_lat, complex_lng, complex_name,
                    gangnam_lat, gangnam_lng, "강남역",
                    mode="transit",
                )
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(5000)
                info = await _extract_route_info(page)
                gangnam_minutes = info.get("minutes", 0)
        except Exception:
            pass

    # 이미지 없으면 placeholder 생성
    if not walk_result or not os.path.exists(walk_img):
        create_placeholder_image(walk_img, 600, 450, text="[도보 경로 지도]")
    if not transit_result or not os.path.exists(transit_img):
        create_placeholder_image(transit_img, 600, 450, text="[대중교통 경로 지도]")

    return LocationInfo(
        complex_id=complex_id,
        nearest_station=nearest_station,
        station_line=station_line,
        walk_minutes=walk_minutes,
        gangnam_minutes=gangnam_minutes,
        walk_route_image_path=walk_img,
        transit_route_image_path=transit_img,
    )


# ─── Wrapper ───

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
    입지 정보 수집 (Playwright 사용 가능하면 실제, 아니면 mock)

    Args:
        complex_id: 단지 ID
        complex_name: 단지명
        complex_lat: 단지 위도
        complex_lng: 단지 경도
        temp_dir: 임시 파일 디렉토리
        config: 설정 딕셔너리
        use_mock: True이면 mock 데이터 사용

    Returns:
        LocationInfo
    """
    if use_mock:
        return fetch_location_info_mock(complex_id, complex_name, temp_dir)

    from src.crawlers.browser_utils import is_playwright_available, run_async

    if not is_playwright_available():
        print("[WARN] Playwright 미설치 - 입지정보 mock 데이터 사용")
        return fetch_location_info_mock(complex_id, complex_name, temp_dir)

    config = config or {}
    gangnam = config.get("gangnam_station", {})
    gangnam_lat = gangnam.get("lat", 37.497942)
    gangnam_lng = gangnam.get("lng", 127.027621)

    try:
        result = run_async(_fetch_location_info_async(
            complex_id=complex_id,
            complex_name=complex_name,
            complex_lat=complex_lat,
            complex_lng=complex_lng,
            temp_dir=temp_dir,
            gangnam_lat=gangnam_lat,
            gangnam_lng=gangnam_lng,
        ))
        if result:
            return result
    except Exception as e:
        print(f"[WARN] 입지정보 수집 실패, mock 사용: {e}")

    return fetch_location_info_mock(complex_id, complex_name, temp_dir)
