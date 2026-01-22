import csv
import requests
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from apps.trends.models import TechStack

class Command(BaseCommand):
    help = 'tech_stacks_merged_final.csv로부터 기술 스택을 읽어 이미지를 S3에 저장하고 DB를 동기화합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            'source_csv',
            type=str,
            nargs='?',
            default='tech_stacks_merged_final.csv'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        source_csv_path = options['source_csv']
        self.stdout.write(self.style.SUCCESS(f'--- Syncing TechStacks from {source_csv_path} ---'))

        if not os.path.exists(source_csv_path):
            self.stdout.write(self.style.ERROR(f'파일을 찾을 수 없습니다: {source_csv_path}'))
            return

        try:
            with open(source_csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                created_count = 0
                updated_count = 0
                
                for row in reader:
                    # CSV 헤더가 'Name' (대문자)이므로 대소문자 구분 없이 찾기
                    stack_name = (row.get('Name') or row.get('name') or '').strip()
                    description = (row.get('description') or '').strip()
                    image_url = (row.get('image') or '').strip()
                    link_url = (row.get('link') or '').strip()

                    if not stack_name:
                        self.stdout.write(self.style.WARNING(f'  > 빈 이름 건너뛰기: {row}'))
                        continue

                    self.stdout.write(f"처리 중: {stack_name}...")

                    # 1. 이미지 다운로드 및 S3 업로드 로직
                    final_logo_path = image_url # 기본값은 기존 URL
                    
                    if image_url and image_url.startswith('http'):
                        try:
                            # 이미지 스트림 가져오기
                            response = requests.get(image_url, timeout=10)
                            if response.status_code == 200:
                                # 확장자 추출 (없으면 png로 기본 설정)
                                ext = image_url.split('.')[-1].split('?')[0]
                                if len(ext) > 4 or not ext: ext = 'png'
                                
                                # S3 저장 경로 설정 (예: logos/Python.png)
                                s3_file_name = f"logos/{stack_name.replace(' ', '_')}.{ext}"
                                
                                # S3에 파일이 없을 때만 업로드 (이미 있으면 기존 파일 경로 사용)
                                if not default_storage.exists(s3_file_name):
                                    saved_file = default_storage.save(s3_file_name, ContentFile(response.content))
                                    final_logo_path = default_storage.url(saved_file)
                                else:
                                    final_logo_path = default_storage.url(s3_file_name)
                                    
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"  > {stack_name} 이미지 업로드 실패: {e}"))

                    # 2. 데이터베이스 업데이트 (update_or_create 활용)
                    obj, created = TechStack.objects.update_or_create(
                        name=stack_name,
                        defaults={
                            'description': description if description else None,
                            'logo': final_logo_path,
                            'docs_url': link_url if link_url and link_url != 'replace_here' else None,
                            'is_deleted': False
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

            self.stdout.write(self.style.SUCCESS(f'작업 완료. 신규 등록: {created_count}, 업데이트: {updated_count}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'에러 발생: {str(e)}'))
            raise