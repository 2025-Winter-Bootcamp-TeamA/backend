"""
기술 스택 관계 데이터를 JSON 파일에서 DB로 import하는 명령어
tech_stacks_relationships.json 파일을 읽어서 TechStackRelationship 모델에 저장합니다.
"""
import json
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.trends.models import TechStack, TechStackRelationship


class Command(BaseCommand):
    help = 'tech_stacks_relationships.json 파일에서 기술 스택 관계를 읽어 DB에 저장합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            'source_json',
            type=str,
            nargs='?',
            default='tech_stacks_relationships.json'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        source_json_path = options['source_json']
        self.stdout.write(self.style.SUCCESS(f'--- Importing Tech Stack Relationships from {source_json_path} ---'))

        if not os.path.exists(source_json_path):
            self.stdout.write(self.style.ERROR(f'파일을 찾을 수 없습니다: {source_json_path}'))
            return

        try:
            with open(source_json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            # 기존 관계 데이터 삭제 (선택적)
            self.stdout.write('Clearing existing relationships...')
            deleted_count, _ = TechStackRelationship.objects.all().delete()
            self.stdout.write(f'  - Deleted {deleted_count} old relationships.')

            # TechStack 이름으로 ID 매핑 생성 (대소문자 무시, 공백 정규화)
            tech_stacks = {ts.name: ts for ts in TechStack.objects.all()}
            # 이름 매칭을 위한 정규화된 딕셔너리 (대소문자 무시, 공백 제거)
            tech_stacks_normalized = {}
            for ts in TechStack.objects.all():
                normalized = ts.name.lower().strip()
                tech_stacks_normalized[normalized] = ts
                # 원본 이름도 유지
                if normalized not in tech_stacks:
                    tech_stacks[normalized] = ts
            
            created_count = 0
            skipped_count = 0
            not_found_techs = set()

            def find_tech_stack(name):
                """기술 이름으로 TechStack 찾기 (유연한 매칭)"""
                # 1. 정확한 이름으로 찾기
                if name in tech_stacks:
                    return tech_stacks[name]
                # 2. 정규화된 이름으로 찾기
                normalized = name.lower().strip()
                if normalized in tech_stacks_normalized:
                    return tech_stacks_normalized[normalized]
                # 3. 부분 일치로 찾기 (예: "Amazon Web Services" -> "AWS")
                for ts_name, ts_obj in tech_stacks.items():
                    if normalized in ts_name.lower() or ts_name.lower() in normalized:
                        return ts_obj
                return None

            for tech_name, tech_data in data.items():
                from_tech = find_tech_stack(tech_name)
                if not from_tech:
                    not_found_techs.add(tech_name)
                    skipped_count += 1
                    continue

                # hierarchy.parent 관계 처리 (양방향: parent와 child)
                hierarchy = tech_data.get('hierarchy', {})
                if hierarchy.get('is_child') == 'true':
                    parent_name = hierarchy.get('parent')
                    if parent_name:
                        parent_tech = find_tech_stack(parent_name)
                        if parent_tech:
                            # 자식 → 부모 (parent 관계)
                            TechStackRelationship.objects.update_or_create(
                                from_tech_stack=from_tech,
                                to_tech_stack=parent_tech,
                                relationship_type='parent',
                                defaults={'weight': 1.0, 'is_deleted': False}
                            )
                            created_count += 1
                            # 부모 → 자식 (child 관계)
                            TechStackRelationship.objects.update_or_create(
                                from_tech_stack=parent_tech,
                                to_tech_stack=from_tech,
                                relationship_type='child',
                                defaults={'weight': 1.0, 'is_deleted': False}
                            )
                            created_count += 1

                # connections.required_infra 관계 처리
                connections = tech_data.get('connections', {})
                required_infra = connections.get('required_infra', [])
                for infra_name in required_infra:
                    infra_tech = find_tech_stack(infra_name)
                    if infra_tech:
                        TechStackRelationship.objects.update_or_create(
                            from_tech_stack=from_tech,
                            to_tech_stack=infra_tech,
                            relationship_type='required_infra',
                            defaults={'weight': 0.9, 'is_deleted': False}
                        )
                        created_count += 1

                # connections.synergy_with 관계 처리 (양방향)
                synergy_with = connections.get('synergy_with', [])
                for synergy_name in synergy_with:
                    synergy_tech = find_tech_stack(synergy_name)
                    if synergy_tech:
                        # A → B
                        TechStackRelationship.objects.update_or_create(
                            from_tech_stack=from_tech,
                            to_tech_stack=synergy_tech,
                            relationship_type='synergy_with',
                            defaults={'weight': 0.8, 'is_deleted': False}
                        )
                        created_count += 1
                        # B → A (양방향)
                        TechStackRelationship.objects.update_or_create(
                            from_tech_stack=synergy_tech,
                            to_tech_stack=from_tech,
                            relationship_type='synergy_with',
                            defaults={'weight': 0.8, 'is_deleted': False}
                        )
                        created_count += 1

                # alternatives 관계 처리 (양방향)
                alternatives = tech_data.get('alternatives', [])
                for alt_name in alternatives:
                    alt_tech = find_tech_stack(alt_name)
                    if alt_tech:
                        # A → B
                        TechStackRelationship.objects.update_or_create(
                            from_tech_stack=from_tech,
                            to_tech_stack=alt_tech,
                            relationship_type='alternative',
                            defaults={'weight': 0.7, 'is_deleted': False}
                        )
                        created_count += 1
                        # B → A (양방향)
                        TechStackRelationship.objects.update_or_create(
                            from_tech_stack=alt_tech,
                            to_tech_stack=from_tech,
                            relationship_type='alternative',
                            defaults={'weight': 0.7, 'is_deleted': False}
                        )
                        created_count += 1

                if created_count % 100 == 0:
                    self.stdout.write(f'  Processed {created_count} relationships...')

            self.stdout.write(self.style.SUCCESS(
                f'\n작업 완료!\n'
                f'  - 생성된 관계: {created_count}\n'
                f'  - 건너뛴 기술: {skipped_count}'
            ))

            if not_found_techs:
                self.stdout.write(self.style.WARNING(
                    f'\nDB에 없는 기술 스택 ({len(not_found_techs)}개):\n'
                    f'  {", ".join(list(not_found_techs)[:10])}'
                    f'{"..." if len(not_found_techs) > 10 else ""}'
                ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'에러 발생: {str(e)}'))
            raise
