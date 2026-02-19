"""
학군 크롤러
학구도안내서비스(초등) + 아실(중·고등) 학군 지도 스크린샷 캡처
"""
import os
from typing import Optional, Tuple
from urllib.parse import quote

from src.models import SchoolInfo
from src.processors.image_processor import create_placeholder_image


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

    create_placeholder_image(elem_img, 800, 600, text="[초등학교 학구도]")
    create_placeholder_image(mh_img, 800, 600, text="[중·고등학교 학군지도]")

    short_name = complex_name.replace("아파트", "").strip() if complex_name else "샘플"
    return SchoolInfo(
        complex_id=complex_id,
        elementary_name=f"서울{short_name}초등학교",
        elementary_map_path=elem_img,
        middle_high_map_path=mh_img,
    )


# ─── Playwright: 초등학교 학구도 (schoolzone.emac.kr) ───

async def _capture_elementary_school_zone(
    address: str,
    save_path: str,
    timeout: int = 30000,
) -> Tuple[Optional[str], str]:
    """
    학구도안내서비스에서 초등학교 학구도 스크린샷 캡처

    Returns:
        (image_path, elementary_school_name)
    """
    from src.crawlers.browser_utils import get_browser_page
    import re

    elementary_name = ""

    try:
        async with get_browser_page() as page:
            await page.goto(
                "https://schoolzone.emac.kr/",
                wait_until="networkidle",
                timeout=timeout,
            )
            await page.wait_for_timeout(2000)

            # 주소 검색
            search_input = await page.query_selector(
                "input[type='text'], input[placeholder*='주소'], #searchInput"
            )
            if search_input:
                await search_input.fill(address)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(5000)

                # 배정 학교명 추출 시도
                for selector in [
                    ".school-name", ".result-name",
                    "[class*='school']", "td:has-text('초등학교')",
                ]:
                    try:
                        name_el = await page.query_selector(selector)
                        if name_el:
                            text = await name_el.inner_text()
                            match = re.search(r'(\S+초등학교)', text)
                            if match:
                                elementary_name = match.group(1)
                                break
                    except Exception:
                        continue

            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            await page.screenshot(path=save_path, full_page=False)
            return save_path, elementary_name

    except Exception as e:
        print(f"[WARN] 초등학교 학구도 캡처 실패: {e}")
        return None, ""


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
            # 아실 학군 페이지
            url = f"https://asil.kr/asil/svl/schoolZone"
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            await page.wait_for_timeout(3000)

            # 주소 검색 시도
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


# ─── API 기반 수집 ───

async def _fetch_school_info_async(
    complex_id: str,
    complex_name: str,
    address: str,
    temp_dir: str = "temp",
) -> Optional[SchoolInfo]:
    """실제 학군 데이터 수집"""
    img_dir = os.path.join(temp_dir, complex_id)

    # 초등학교 학구도
    elem_img = os.path.join(img_dir, "elementary_zone.png")
    elem_result, elementary_name = await _capture_elementary_school_zone(
        address, elem_img
    )

    # 중·고등학교 학군지도
    mh_img = os.path.join(img_dir, "middle_high_zone.png")
    mh_result = await _capture_middle_high_school_zone(address, mh_img)

    # 실패한 이미지는 placeholder로 대체
    if not elem_result or not os.path.exists(elem_img):
        create_placeholder_image(elem_img, 800, 600, text="[초등학교 학구도]")
    if not mh_result or not os.path.exists(mh_img):
        create_placeholder_image(mh_img, 800, 600, text="[중·고등학교 학군지도]")

    if not elementary_name:
        short_name = complex_name.replace("아파트", "").strip() if complex_name else "정보 없음"
        elementary_name = f"{short_name} 배정 초등학교"

    return SchoolInfo(
        complex_id=complex_id,
        elementary_name=elementary_name,
        elementary_map_path=elem_img,
        middle_high_map_path=mh_img,
    )


# ─── Wrapper ───

def fetch_school_info(
    complex_id: str,
    complex_name: str = "",
    address: str = "",
    temp_dir: str = "temp",
    use_mock: bool = False,
) -> SchoolInfo:
    """
    학군 정보 수집 (Playwright 사용 가능하면 실제, 아니면 mock)

    Args:
        complex_id: 단지 ID
        complex_name: 단지명
        address: 단지 주소 (검색용)
        temp_dir: 임시 파일 디렉토리
        use_mock: True이면 mock 데이터 사용

    Returns:
        SchoolInfo
    """
    if use_mock:
        return fetch_school_info_mock(complex_id, complex_name, temp_dir)

    from src.crawlers.browser_utils import is_playwright_available, run_async

    if not is_playwright_available():
        print("[WARN] Playwright 미설치 - 학군정보 mock 데이터 사용")
        return fetch_school_info_mock(complex_id, complex_name, temp_dir)

    try:
        result = run_async(_fetch_school_info_async(
            complex_id=complex_id,
            complex_name=complex_name,
            address=address,
            temp_dir=temp_dir,
        ))
        if result:
            return result
    except Exception as e:
        print(f"[WARN] 학군정보 수집 실패, mock 사용: {e}")

    return fetch_school_info_mock(complex_id, complex_name, temp_dir)
