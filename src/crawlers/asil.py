"""
실거래가 크롤러
국토부 공공 API 또는 아실 웹 크롤링으로 실거래가 데이터 수집
+ 아실(asil.kr) 매매가 추이 그래프 캡처
"""
import os
import re
import time
import random
from datetime import date, datetime
from typing import Optional, List

import httpx
from bs4 import BeautifulSoup

from src.models import PriceInfo, Transaction
from src.utils.text_helpers import format_price
from src.crawlers.browser_utils import is_playwright_available, get_browser_page, run_async


# 국토부 실거래가 API
MOLIT_API_URL = (
    "http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/"
    "service/rest/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
)


def polite_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    """서버 부하 방지를 위한 랜덤 딜레이"""
    time.sleep(random.uniform(min_sec, max_sec))


def fetch_price_info_mock(complex_id: str, complex_name: str = "") -> PriceInfo:
    """
    Mock 실거래가 데이터 생성 (API 키 없을 때 사용)
    실제 크롤링 대신 샘플 데이터로 PPT 생성을 테스트할 수 있게 함
    """
    today = date.today()

    sample_transactions = [
        Transaction(
            date=date(today.year, max(1, today.month - 1), 15),
            area_pyeong="24평",
            area_m2=79.34,
            floor=8,
            price="5억 9000만원",
            price_raw=590000000,
        ),
        Transaction(
            date=date(today.year, max(1, today.month - 1), 3),
            area_pyeong="24평",
            area_m2=79.34,
            floor=5,
            price="5억 5300만원",
            price_raw=553000000,
        ),
        Transaction(
            date=date(today.year, max(1, today.month - 2), 20),
            area_pyeong="32평",
            area_m2=105.49,
            floor=12,
            price="7억 1000만원",
            price_raw=710000000,
        ),
    ]

    return PriceInfo(
        complex_id=complex_id,
        recent_transactions=sample_transactions,
        month1_count=2,
        month1_label=f"{today.year}년 {max(1, today.month - 1)}월",
        month2_count=1,
        month2_label=f"{today.year}년 {max(1, today.month - 2)}월",
        recent_3m_high="7억 1000만원",
        recent_3m_low="5억 5300만원",
        all_time_high="9억 2000만원",
        all_time_high_date="21년 9월",
    )


def fetch_price_info_from_api(
    complex_id: str,
    lawd_cd: str,
    api_key: str,
    complex_name: str = "",
    months: int = 6,
) -> Optional[PriceInfo]:
    """
    국토부 공공 API로 실거래가 데이터 조회

    Args:
        complex_id: 단지 ID
        lawd_cd: 법정동코드 5자리
        api_key: 공공데이터포털 API 키
        complex_name: 단지명 (필터링에 사용)
        months: 조회할 개월 수

    Returns:
        PriceInfo 또는 None
    """
    today = date.today()
    all_transactions: List[Transaction] = []

    for i in range(months):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1

        deal_ymd = f"{year}{month:02d}"

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(MOLIT_API_URL, params={
                    "LAWD_CD": lawd_cd,
                    "DEAL_YMD": deal_ymd,
                    "serviceKey": api_key,
                })
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml-xml")
            items = soup.find_all("item")

            for item in items:
                apt_name = item.find("아파트")
                if apt_name and complex_name and complex_name not in apt_name.text:
                    continue

                deal_amount = item.find("거래금액")
                deal_day = item.find("일")
                deal_floor = item.find("층")
                area = item.find("전용면적")

                if not all([deal_amount, deal_day, deal_floor, area]):
                    continue

                price_raw = int(deal_amount.text.strip().replace(",", "")) * 10000
                area_m2 = float(area.text.strip())
                floor_num = int(deal_floor.text.strip())
                day = int(deal_day.text.strip())

                txn = Transaction(
                    date=date(year, month, min(day, 28)),
                    area_pyeong=f"{round(area_m2 / 3.305785)}평",
                    area_m2=area_m2,
                    floor=floor_num,
                    price=format_price(price_raw),
                    price_raw=price_raw,
                )
                all_transactions.append(txn)

            polite_delay(0.5, 1.5)

        except Exception as e:
            print(f"[ERROR] 실거래가 API 호출 실패 ({deal_ymd}): {e}")
            continue

    if not all_transactions:
        return fetch_price_info_mock(complex_id, complex_name)

    # 최신순 정렬
    all_transactions.sort(key=lambda t: t.date, reverse=True)

    # 통계 계산
    month1_txns = [t for t in all_transactions if t.date.month == today.month and t.date.year == today.year]
    prev_month = today.month - 1 if today.month > 1 else 12
    prev_year = today.year if today.month > 1 else today.year - 1
    month2_txns = [t for t in all_transactions if t.date.month == prev_month and t.date.year == prev_year]

    # 최근 3개월 최고/최저
    recent_3m = all_transactions[:min(len(all_transactions), 20)]
    if recent_3m:
        high = max(recent_3m, key=lambda t: t.price_raw)
        low = min(recent_3m, key=lambda t: t.price_raw)
    else:
        high = low = all_transactions[0] if all_transactions else None

    # 역대 최고가
    all_time = max(all_transactions, key=lambda t: t.price_raw)

    return PriceInfo(
        complex_id=complex_id,
        recent_transactions=all_transactions,
        month1_count=len(month1_txns),
        month1_label=f"{today.year}년 {today.month}월",
        month2_count=len(month2_txns),
        month2_label=f"{prev_year}년 {prev_month}월",
        recent_3m_high=high.price if high else "",
        recent_3m_low=low.price if low else "",
        all_time_high=all_time.price if all_time else "",
        all_time_high_date=f"{all_time.date.strftime('%y년 %m월')}" if all_time else "",
    )


def fetch_price_info(
    complex_id: str,
    complex_name: str = "",
    lawd_cd: str = "",
    api_key: str = "",
) -> PriceInfo:
    """
    실거래가 데이터 수집 (API 키가 있으면 공공 API, 없으면 mock)
    """
    if api_key and lawd_cd:
        result = fetch_price_info_from_api(
            complex_id, lawd_cd, api_key, complex_name
        )
        if result:
            return result

    print(f"[INFO] Mock 실거래가 데이터 사용 (complex_id: {complex_id})")
    return fetch_price_info_mock(complex_id, complex_name)


# ─── 아실(asil.kr) 매매가 추이 그래프 캡처 ───

ASIL_PRICE_URL = "https://asil.kr/rts/v_aptprice.jsp"


def _parse_gu_dong(address: str) -> tuple:
    """
    주소에서 구/동 추출

    Args:
        address: "노원구 중계동" 또는 "서울특별시 송파구 거여동"

    Returns:
        (구, 동) 튜플 또는 (None, None)
    """
    m = re.search(r'(\S+구)\s+(\S+동)', address)
    if m:
        return m.group(1), m.group(2)
    return None, None


async def _find_and_select_option(page, selector: str, text: str) -> Optional[str]:
    """
    드롭다운에서 텍스트를 포함하는 옵션의 value를 찾아 선택

    Returns:
        선택된 옵션의 value 또는 None
    """
    value = await page.evaluate('''([sel, txt]) => {
        const options = document.querySelectorAll(sel + ' option');
        for (const opt of options) {
            if (opt.textContent.includes(txt) && opt.value) return opt.value;
        }
        return null;
    }''', [selector, text])
    if value:
        await page.select_option(selector, value)
    return value


async def _wait_for_options(page, selector: str, timeout: int = 10000) -> bool:
    """드롭다운에 옵션이 2개 이상 로드될 때까지 대기 (첫 번째는 placeholder)"""
    try:
        await page.wait_for_function(
            f'document.querySelectorAll("{selector} option").length > 1',
            timeout=timeout,
        )
        return True
    except Exception:
        return False


def _parse_asil_chart_data(raw_js: str, complex_id: str) -> Optional[PriceInfo]:
    """
    아실 차트 JSONP 응답을 파싱하여 PriceInfo 생성

    raw_js 예: chartData1[0] = {"date":"2006/1","M":36000,"M_CNT":1,"J_CNT":0};
    M = 매매 평균가(만원), M_CNT = 매매 건수
    """
    import json as _json
    entries = re.findall(r'chartData1\[\d+\]\s*=\s*(\{[^}]+\})', raw_js)
    if not entries:
        return None

    parsed = []
    for e in entries:
        try:
            parsed.append(_json.loads(e))
        except Exception:
            continue
    if not parsed:
        return None

    today = date.today()

    # 매매 거래가 있는 월만 필터
    sale_months = [e for e in parsed if e.get("M_CNT", 0) > 0 and "M" in e]

    # 이번 달 / 지난 달 거래건수
    cur_key = f"{today.year}/{today.month}"
    prev_m = today.month - 1
    prev_y = today.year
    if prev_m <= 0:
        prev_m += 12
        prev_y -= 1
    prev_key = f"{prev_y}/{prev_m}"

    month1_count = 0
    month2_count = 0
    for e in parsed:
        if e["date"] == cur_key:
            month1_count = e.get("M_CNT", 0)
        if e["date"] == prev_key:
            month2_count = e.get("M_CNT", 0)

    # 최근 6개월 매매 데이터 (거래 있는 월)
    recent_6m_entries = []
    for i in range(6):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        key = f"{y}/{m}"
        for e in sale_months:
            if e["date"] == key:
                recent_6m_entries.append(e)

    # 최근 3개월 최고/최저
    recent_3m_entries = []
    for i in range(3):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        key = f"{y}/{m}"
        for e in sale_months:
            if e["date"] == key:
                recent_3m_entries.append(e)

    if recent_3m_entries:
        high_3m = max(e["M"] for e in recent_3m_entries)
        low_3m = min(e["M"] for e in recent_3m_entries)
    elif recent_6m_entries:
        high_3m = max(e["M"] for e in recent_6m_entries)
        low_3m = min(e["M"] for e in recent_6m_entries)
    else:
        high_3m = low_3m = 0

    # 역대 최고가
    if sale_months:
        ath_entry = max(sale_months, key=lambda e: e["M"])
        ath_price = ath_entry["M"]
        ath_parts = ath_entry["date"].split("/")
        ath_date_str = f"{int(ath_parts[0]) % 100}년 {ath_parts[1]}월"
    else:
        ath_price = 0
        ath_date_str = ""

    # Transaction 리스트: 최근 6개월 월별 집계 → Transaction 객체
    transactions = []
    for e in sorted(recent_6m_entries, key=lambda x: x["date"], reverse=True):
        parts = e["date"].split("/")
        y, m = int(parts[0]), int(parts[1])
        price_raw = e["M"] * 10000  # 만원 → 원
        transactions.append(Transaction(
            date=date(y, m, 1),
            area_pyeong="전체",
            area_m2=0.0,
            floor=e["M_CNT"],  # 건수를 floor 필드에 임시 저장
            price=format_price(price_raw),
            price_raw=price_raw,
        ))

    return PriceInfo(
        complex_id=complex_id,
        recent_transactions=transactions,
        month1_count=month1_count,
        month1_label=f"{today.year}년 {today.month}월",
        month2_count=month2_count,
        month2_label=f"{prev_y}년 {prev_m}월",
        recent_3m_high=format_price(high_3m * 10000) if high_3m else "",
        recent_3m_low=format_price(low_3m * 10000) if low_3m else "",
        all_time_high=format_price(ath_price * 10000) if ath_price else "",
        all_time_high_date=ath_date_str,
    )


async def _capture_asil_price_chart_async(
    complex_name: str,
    complex_id: str,
    address: str,
    save_path: str,
    timeout: int = 45000,
) -> Optional[dict]:
    """
    아실(asil.kr) 매매가 추이 그래프 캡처 + 실거래 데이터 파싱 (async)

    Returns:
        {"chart_path": str, "price_info": PriceInfo or None} 또는 None
    """
    gu, dong = _parse_gu_dong(address)
    if not gu or not dong:
        print(f"  [WARN] 아실 차트: 주소에서 구/동 파싱 실패 ({address})")
        return None

    print(f"  아실 차트 캡처 시도: {complex_name} ({gu} {dong})")

    async with get_browser_page(viewport_width=1400, viewport_height=900) as page:
        # JSONP 차트 데이터 캡처용
        chart_data_raw = []

        async def _capture_chart_data(response):
            url = response.url
            if "data_price_js.jsp" in url and "apt=" in url and "apt=&" not in url:
                try:
                    body = await response.body()
                    chart_data_raw.append(body.decode("utf-8", errors="replace"))
                except Exception:
                    pass

        page.on("response", _capture_chart_data)

        # v_aptprice.jsp에 self.location.href 리다이렉트 스크립트가 있어 제거
        async def _strip_redirect(route):
            resp = await route.fetch()
            body = (await resp.body()).decode("utf-8", errors="replace")
            body = body.replace('self.location.href="http://asil.kr";', "")
            await route.fulfill(response=resp, body=body)

        await page.route("**/v_aptprice.jsp*", _strip_redirect)

        # 1. 아실 페이지 접속
        await page.goto(ASIL_PRICE_URL, wait_until="networkidle", timeout=timeout)

        # 2. 시 드롭다운 → 서울 (value="11", 기본 선택됨)
        await page.wait_for_selector("#area_si_1", state="attached", timeout=10000)
        await page.evaluate('setAreaSi1("11")')
        if not await _wait_for_options(page, "#area_gu_1"):
            print(f"  [WARN] 아실: 구 드롭다운 로드 실패")
            return None

        # 3. 구 드롭다운 → 해당 구 선택
        gu_value = await _find_and_select_option(page, "#area_gu_1", gu)
        if not gu_value:
            print(f"  [WARN] 아실: {gu} 옵션 없음")
            return None
        await page.evaluate(f'setAreaGu1("{gu_value}")')
        if not await _wait_for_options(page, "#area_dong_1"):
            print(f"  [WARN] 아실: 동 드롭다운 로드 실패")
            return None

        # 4. 동 드롭다운 → 해당 동 선택
        dong_value = await _find_and_select_option(page, "#area_dong_1", dong)
        if not dong_value:
            print(f"  [WARN] 아실: {dong} 옵션 없음")
            return None
        await page.evaluate(f'setAreaDong1("{dong_value}")')
        if not await _wait_for_options(page, "#area_apt_1", timeout=15000):
            print(f"  [WARN] 아실: 아파트 드롭다운 로드 실패")
            return None

        # 5. 아파트 드롭다운 → 단지명 포함 옵션 선택
        apt_value = await _find_and_select_option(page, "#area_apt_1", complex_name)
        if not apt_value:
            short_name = re.sub(r'\d+차$', '', complex_name)
            if short_name != complex_name:
                apt_value = await _find_and_select_option(page, "#area_apt_1", short_name)
            if not apt_value:
                print(f"  [WARN] 아실: 단지 '{complex_name}' 선택 실패")
                return None
        await page.evaluate(f'setAreaApt1("{apt_value}")')

        # 6. 차트 렌더링 대기
        try:
            await page.wait_for_function(
                'document.querySelector("#chartHolder1")?.children.length > 0',
                timeout=15000,
            )
            await page.wait_for_timeout(3000)
        except Exception:
            print(f"  [WARN] 아실: 차트 렌더링 대기 시간 초과")
            return None

        # 7. 최근 10년으로 재로드 (sY1 설정 후 setData1 호출)
        start_year = date.today().year - 10
        await page.evaluate(f'sY1 = "{start_year}"; sM1 = "1"; setData1();')
        await page.wait_for_timeout(3000)

        # 8. 로딩 스피너 숨기기 (rMateChartH5 Preloader)
        await page.evaluate(
            'document.querySelectorAll(".rMateH5__Preloader")'
            '.forEach(el => el.style.display = "none")'
        )

        # 9. 차트 영역 스크린샷
        chart_el = await page.query_selector("#chartHolder1")
        if not chart_el:
            print(f"  [WARN] 아실: #chartHolder1 요소 없음")
            return None

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        await chart_el.screenshot(path=save_path)
        print(f"  아실 차트 캡처 성공: {save_path}")

        # 10. JSONP 데이터에서 PriceInfo 파싱
        price_info = None
        if chart_data_raw:
            price_info = _parse_asil_chart_data(chart_data_raw[-1], complex_id)
            if price_info:
                print(f"  아실 실거래 데이터 파싱 완료 "
                      f"(이번달 {price_info.month1_count}건, "
                      f"지난달 {price_info.month2_count}건)")

        # 11. 거래내역 스크린샷 캡처 (같은 브라우저 세션 재사용)
        deals_path = os.path.join(os.path.dirname(save_path), "deals_table.png")
        deals_url = (
            f"https://asil.kr/app/price_detail_ver_3_9.jsp"
            f"?os=pc&user=null&building=apt&apt={apt_value}"
            f"&evt=0m2&year=9999&deal=1"
        )
        try:
            await page.set_viewport_size({"width": 480, "height": 900})
            await page.goto(deals_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            # 최근 6개월 거래만 보이도록: 범위 밖 행을 숨김 처리
            _today = date.today()
            cutoff_keys = []
            for i in range(6):
                m = _today.month - i
                y = _today.year
                while m <= 0:
                    m += 12
                    y -= 1
                cutoff_keys.append(f"{y % 100:02d}.{m:02d}")
            # 6개월 범위 밖 행을 display:none으로 숨기기
            await page.evaluate('''(keys) => {
                const rows = document.querySelectorAll('tr');
                let outOfRange = false;
                for (const row of rows) {
                    const cells = row.querySelectorAll('td');
                    if (cells.length === 0) continue;
                    const txt = cells[0]?.textContent?.trim() || '';
                    if (txt && /^\\d{2}\\.\\d{2}$/.test(txt)) {
                        if (!keys.includes(txt)) {
                            outOfRange = true;
                        }
                    }
                    if (outOfRange) {
                        row.style.display = 'none';
                    }
                }
            }''', cutoff_keys)
            await page.wait_for_timeout(500)
            # 뷰포트를 줄여서 body가 콘텐츠 높이에 맞게 되도록 함
            await page.set_viewport_size({"width": 480, "height": 100})
            await page.wait_for_timeout(300)
            await page.screenshot(path=deals_path, full_page=True)
            print(f"  아실 거래내역 캡처 성공: {deals_path}")
            if price_info:
                price_info.deals_image_path = deals_path
        except Exception as e:
            print(f"  [WARN] 아실 거래내역 캡처 실패: {e}")

        return {"chart_path": save_path, "price_info": price_info}


def capture_asil_price_chart(
    complex_name: str,
    complex_id: str,
    address: str,
    save_path: str,
) -> Optional[dict]:
    """
    아실 매매가 추이 그래프 캡처 + 실거래 데이터 파싱 (동기 래퍼)

    Returns:
        {"chart_path": str, "price_info": PriceInfo or None} 또는 None
    """
    if not is_playwright_available():
        print(f"  [INFO] Playwright 미설치, 아실 차트 캡처 건너뜀")
        return None

    try:
        return run_async(
            _capture_asil_price_chart_async(
                complex_name, complex_id, address, save_path
            )
        )
    except Exception as e:
        print(f"  [WARN] 아실 차트 캡처 실패: {e}")
        return None
