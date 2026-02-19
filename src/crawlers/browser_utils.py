"""
브라우저 유틸리티 (Playwright 공유 모듈)
Headless 브라우저 초기화, 스크린샷 캡처 공통 로직
"""
import os
import asyncio
from typing import Optional
from contextlib import asynccontextmanager


_PLAYWRIGHT_AVAILABLE = None


def is_playwright_available() -> bool:
    """Playwright + Chromium 설치 여부 확인"""
    global _PLAYWRIGHT_AVAILABLE
    if _PLAYWRIGHT_AVAILABLE is None:
        try:
            from playwright.async_api import async_playwright  # noqa: F401
            _PLAYWRIGHT_AVAILABLE = True
        except ImportError:
            _PLAYWRIGHT_AVAILABLE = False
    return _PLAYWRIGHT_AVAILABLE


@asynccontextmanager
async def get_browser_page(
    headless: bool = True,
    device_scale_factor: int = 2,
    viewport_width: int = 1280,
    viewport_height: int = 900,
    locale: str = "ko-KR",
):
    """
    Playwright 브라우저 페이지를 yield하는 context manager

    Usage:
        async with get_browser_page() as page:
            await page.goto(url)
            await page.screenshot(path="out.png")
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            device_scale_factor=device_scale_factor,
            locale=locale,
        )
        page = await context.new_page()
        try:
            yield page
        finally:
            await context.close()
            await browser.close()


def run_async(coro):
    """동기 함수에서 async 코루틴을 실행하는 헬퍼"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)
