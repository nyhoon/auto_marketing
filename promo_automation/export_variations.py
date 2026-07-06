"""NeoFall 배리에이션을 generated/ 폴더로보내기."""

from __future__ import annotations

import argparse

from common import create_output_bundle, load_config, write_json
from variation_loader import export_variations_to_dir, get_angle_for_today, list_angles


def main() -> None:
    parser = argparse.ArgumentParser(description="NeoFall 홍보 배리에이션보내기")
    parser.add_argument("--angle", default="", help="각도 코드 (미지정 시 오늘 요일 로테이션)")
    parser.add_argument("--list-angles", action="store_true", help="사용 가능한 각도 목록")
    args = parser.parse_args()

    if args.list_angles:
        for code, label in list_angles().items():
            print(f"  {code}: {label}")
        return

    config = load_config()
    angle = args.angle or None
    bundle = create_output_bundle(config)
    exported = export_variations_to_dir(bundle.directory, angle=angle)

    write_json(
        bundle.directory / "summary.json",
        {
            "timestamp": bundle.timestamp,
            "mode": "variation_export",
            "angle": angle or get_angle_for_today(),
            "platforms": exported,
        },
    )

    print(f"[INFO] 각도: {angle or get_angle_for_today()}")
    print(f"[INFO]보낸 플랫폼: {', '.join(exported)}")
    print(f"[INFO] 출력: {bundle.directory.resolve()}")


if __name__ == "__main__":
    main()
