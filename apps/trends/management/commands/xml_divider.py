"""
Posts.xml에서 최근 N년 데이터만 추출하는 명령어
"""
from pathlib import Path
from xml.etree.ElementTree import iterparse
from datetime import datetime, timezone, timedelta

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Posts.xml에서 최근 N년 데이터만 추출하여 새 XML 파일로 저장합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            required=True,
            help='원본 Posts.xml 파일 경로'
        )
        parser.add_argument(
            '--output',
            type=str,
            required=True,
            help='출력 XML 파일 경로'
        )
        parser.add_argument(
            '--years',
            type=int,
            default=2,
            help='추출할 기간 (년). 기본값: 2년'
        )

    def handle(self, *args, **options):
        src_path = Path(options['source']).expanduser()
        dst_path = Path(options['output']).expanduser()
        years = options['years']

        if not src_path.exists():
            self.stdout.write(self.style.ERROR(f"❌ 파일을 찾을 수 없습니다: {src_path}"))
            return

        cutoff = datetime.now(timezone.utc) - timedelta(days=365 * years)

        self.stdout.write(f"📊 최근 {years}년 데이터 추출 시작...")
        self.stdout.write(f"📁 원본: {src_path}")
        self.stdout.write(f"📁 출력: {dst_path}")
        self.stdout.write(f"📅 기준 날짜: {cutoff.date()} 이후")

        count = 0
        total = 0

        with open(dst_path, "w", encoding="utf-8") as out:
            out.write('<?xml version="1.0" encoding="utf-8"?>\n')
            out.write('<posts>\n')

            for _, el in iterparse(src_path):
                total += 1
                if total % 10000 == 0:
                    self.stdout.write(f"  스캔: {total:,}개, 추출: {count:,}개...")

                d = el.attrib.get("CreationDate")
                if d:
                    # Z가 있으면 +00:00로 바꿔서 파싱
                    try:
                        dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
                        # tz 없는 값이면 UTC로 강제
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)

                        if dt >= cutoff:
                            # XML 요소를 문자열로 변환
                            import xml.etree.ElementTree as ET
                            xml_str = ET.tostring(el, encoding='unicode')
                            out.write(f"  {xml_str}\n")
                            count += 1
                    except (ValueError, AttributeError):
                        pass

                el.clear()

            out.write("</posts>\n")

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ 완료! 총 {total:,}개 중 {count:,}개 추출 → {dst_path}"
            )
        )