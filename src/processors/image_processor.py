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
            # 시스템 폰트 시도
            font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 20)
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
