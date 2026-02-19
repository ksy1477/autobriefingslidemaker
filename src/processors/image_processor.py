"""
이미지 프로세서
크롭, 리사이즈, PPT 삽입 최적화
"""
import os
from typing import Optional, Tuple

from PIL import Image


def resize_image(
    input_path: str,
    output_path: str,
    max_width: int = 1200,
    max_height: int = 900,
    quality: int = 90,
) -> Optional[str]:
    """
    이미지를 PPT에 적합한 크기로 리사이즈

    Args:
        input_path: 원본 이미지 경로
        output_path: 저장 경로
        max_width: 최대 가로 픽셀
        max_height: 최대 세로 픽셀
        quality: JPEG 품질 (1-100)

    Returns:
        저장 경로 또는 None
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img = Image.open(input_path)

        # 원본 비율 유지하면서 리사이즈
        img.thumbnail((max_width, max_height), Image.LANCZOS)
        img.save(output_path, quality=quality)
        return output_path
    except Exception as e:
        print(f"[ERROR] 이미지 리사이즈 실패: {input_path} - {e}")
        return None


def crop_image(
    input_path: str,
    output_path: str,
    box: Tuple[int, int, int, int],
) -> Optional[str]:
    """
    이미지 특정 영역 크롭

    Args:
        input_path: 원본 이미지 경로
        output_path: 저장 경로
        box: (left, top, right, bottom)

    Returns:
        저장 경로 또는 None
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img = Image.open(input_path)
        cropped = img.crop(box)
        cropped.save(output_path)
        return output_path
    except Exception as e:
        print(f"[ERROR] 이미지 크롭 실패: {input_path} - {e}")
        return None


def create_placeholder_image(
    output_path: str,
    width: int = 400,
    height: int = 300,
    text: str = "",
    bg_color: str = "#E0E0E0",
) -> str:
    """
    대체 placeholder 이미지 생성 (실제 이미지가 없을 때)

    Args:
        output_path: 저장 경로
        width: 가로 픽셀
        height: 세로 픽셀
        text: 중앙 텍스트
        bg_color: 배경색

    Returns:
        저장 경로
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # PIL로 간단한 placeholder 이미지 생성
    from PIL import ImageDraw, ImageFont

    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    if text:
        try:
            import platform
            system = platform.system()
            if system == 'Windows':
                font_path = "C:/Windows/Fonts/malgun.ttf"
            elif system == 'Darwin':
                font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
            else:
                font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
            font = ImageFont.truetype(font_path, 20)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (width - text_w) // 2
        y = (height - text_h) // 2
        draw.text((x, y), text, fill="#888888", font=font)

    img.save(output_path)
    return output_path


def mark_location_on_map(
    map_image_path: str,
    output_path: str,
    center_x: int,
    center_y: int,
    marker_color: str = "#C8102E",
    marker_size: int = 20,
    label: str = "",
) -> Optional[str]:
    """
    지도 이미지에 위치 마커 표시 (동 위치 표시용)

    Args:
        map_image_path: 원본 지도 이미지 경로
        output_path: 저장 경로
        center_x: 마커 중심 x 좌표
        center_y: 마커 중심 y 좌표
        marker_color: 마커 색상
        marker_size: 마커 크기 (반지름)
        label: 마커 위 라벨 텍스트

    Returns:
        저장 경로 또는 None
    """
    try:
        from PIL import ImageDraw, ImageFont

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img = Image.open(map_image_path).copy()
        draw = ImageDraw.Draw(img)

        # 원형 마커
        bbox = [
            center_x - marker_size, center_y - marker_size,
            center_x + marker_size, center_y + marker_size,
        ]
        draw.ellipse(bbox, fill=marker_color, outline="#FFFFFF", width=3)

        # 라벨 텍스트
        if label:
            try:
                import platform
                system = platform.system()
                if system == 'Windows':
                    font_path = "C:/Windows/Fonts/malgun.ttf"
                elif system == 'Darwin':
                    font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
                else:
                    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
                font = ImageFont.truetype(font_path, 14)
            except Exception:
                font = ImageFont.load_default()

            text_bbox = draw.textbbox((0, 0), label, font=font)
            text_w = text_bbox[2] - text_bbox[0]
            text_x = center_x - text_w // 2
            text_y = center_y - marker_size - 20
            draw.text((text_x, text_y), label, fill=marker_color, font=font)

        img.save(output_path)
        return output_path
    except Exception as e:
        print(f"[ERROR] 지도 마킹 실패: {e}")
        return None


def mark_dong_on_siteplan(
    siteplan_path: str,
    dong_coordinates: Tuple[int, int, int, int],
    output_path: str,
    border_color: str = "#C8102E",
    border_width: int = 3,
) -> Optional[str]:
    """
    배치도 이미지에서 특정 동 위치에 빨간 박스 마킹

    Args:
        siteplan_path: 배치도 이미지 경로
        dong_coordinates: (x1, y1, x2, y2) 동 위치 좌표
        output_path: 저장 경로
        border_color: 박스 색상
        border_width: 박스 선 두께

    Returns:
        저장 경로 또는 None
    """
    try:
        from PIL import ImageDraw

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img = Image.open(siteplan_path).copy()
        draw = ImageDraw.Draw(img)
        draw.rectangle(dong_coordinates, outline=border_color, width=border_width)
        img.save(output_path)
        return output_path
    except Exception as e:
        print(f"[ERROR] 배치도 마킹 실패: {e}")
        return None
