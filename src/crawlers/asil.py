"""
실거래가 크롤러
국토부 공공 API 또는 아실 웹 크롤링으로 실거래가 데이터 수집
"""
import os
import time
import random
from datetime import date, datetime
from typing import Optional, List

import httpx
from bs4 import BeautifulSoup

from src.models import PriceInfo, Transaction
from src.utils.text_helpers import format_price


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
        recent_transactions=all_transactions[:10],  # 최근 10건
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
