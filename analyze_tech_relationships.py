"""
기술 스택 관계 분석 스크립트
tech_stacks_merged_final.csv를 읽어서 기술 간 관계를 분석하고 JSON으로 출력합니다.
"""
import csv
import json
import re
from typing import Dict, List, Set, Optional

# 기술 이름 정규화 매핑 (대소문자, 별칭 통합)
NAME_NORMALIZATION = {
    'Golang': 'Go',
    'Java 8': 'Java',
    'Java EE': 'Java',
    'C lang': 'C',
    'ES6': 'JavaScript',
    'AngularJS': 'Angular',
    'React.js': 'React',
    'React Native': 'React',
    'Vue.js': 'Vue',
    'Node.js': 'Node',
    'ASP.NET': '.NET',
    'ASP.NET Core': '.NET',
    'Microsoft SQL Server': 'SQL Server',
    'PostgreSQL': 'Postgres',
    'MySQL': 'MySQL',
    'MongoDB': 'MongoDB',
    'Redis': 'Redis',
    'Docker': 'Docker',
    'Kubernetes': 'Kubernetes',
    'AWS': 'Amazon Web Services',
    'GCP': 'Google Cloud Platform',
    'Azure': 'Microsoft Azure',
}

# 부모-자식 관계 매핑 (명확한 의존성)
PARENT_RELATIONSHIPS = {
    # 언어 기반 프레임워크
    'Django': 'Python',
    'Flask': 'Python',
    'FastAPI': 'Python',
    'Rails': 'Ruby',
    'Laravel': 'PHP',
    'Spring': 'Java',
    'Spring Boot': 'Java',
    'ExpressJS': 'Node',
    'NestJS': 'Node',
    'Koa': 'Node',
    'AdonisJS': 'Node',
    'React': 'JavaScript',
    'Vue': 'JavaScript',
    'Angular': 'TypeScript',
    'Next.js': 'React',
    'Nuxt.js': 'Vue',
    'Gatsby': 'React',
    'Svelte': 'JavaScript',
    'Ember.js': 'JavaScript',
    'Backbone.js': 'JavaScript',
    
    # 플랫폼 확장
    'Android Room': 'Android OS',
    'Android SDK': 'Android OS',
    'Android Studio': 'Android OS',
    'React Native': 'React',
    'Flutter': 'Dart',
    'Xamarin': '.NET',
    'Xamarin Forms': 'Xamarin',
    'Ionic': 'JavaScript',
    'NativeScript': 'JavaScript',
    
    # 데이터베이스 확장
    'PostGIS': 'Postgres',
    'pgvector': 'Postgres',
    'Hibernate': 'Java',
    'SQLAlchemy': 'Python',
    'Sequelize': 'Node',
    'TypeORM': 'TypeScript',
    'Prisma': 'TypeScript',
    'Mongoose': 'Node',
    
    # 클라우드 서비스 (AWS)
    'Amazon RDS': 'Amazon Web Services',
    'Amazon S3': 'Amazon Web Services',
    'Amazon EC2': 'Amazon Web Services',
    'Amazon EKS': 'Kubernetes',
    'Amazon ECR': 'Docker',
    'Amazon ElastiCache': 'Redis',
    'Amazon DynamoDB': 'Amazon Web Services',
    'Amazon Lambda': 'Amazon Web Services',
    'Amazon CloudFront': 'Amazon Web Services',
    'Amazon Route 53': 'Amazon Web Services',
    'Amazon CloudWatch': 'Amazon Web Services',
    'Amazon Cognito': 'Amazon Web Services',
    'Amazon SageMaker': 'Amazon Web Services',
    
    # 클라우드 서비스 (Azure)
    'Azure Functions': 'Microsoft Azure',
    'Azure App Service': 'Microsoft Azure',
    'Azure Cosmos DB': 'Microsoft Azure',
    'Azure SQL Database': 'Microsoft Azure',
    'Azure Storage': 'Microsoft Azure',
    'Azure Kubernetes Service': 'Kubernetes',
    'Azure DevOps': 'Microsoft Azure',
    
    # 클라우드 서비스 (GCP)
    'Google Cloud Functions': 'Google Cloud Platform',
    'Google Cloud Run': 'Google Cloud Platform',
    'Google Cloud SQL': 'Google Cloud Platform',
    'Google Cloud Storage': 'Google Cloud Platform',
    'Google Kubernetes Engine': 'Kubernetes',
    'Google Cloud Build': 'Google Cloud Platform',
    
    # 도구 및 라이브러리
    'Redux': 'React',
    'Vuex': 'Vue',
    'React Router': 'React',
    'Vue Router': 'Vue',
    'styled-components': 'React',
    'Tailwind CSS': 'CSS 3',
    'Bootstrap': 'CSS 3',
    'Sass': 'CSS 3',
    'Less': 'CSS 3',
    'Webpack': 'JavaScript',
    'Vite': 'JavaScript',
    'Babel': 'JavaScript',
    'ESLint': 'JavaScript',
    'Jest': 'JavaScript',
    'Mocha': 'JavaScript',
    'Cypress': 'JavaScript',
    'Selenium': 'JavaScript',
    'Puppeteer': 'JavaScript',
    
    # ML/AI 라이브러리
    'Keras': 'TensorFlow',
    'TensorFlow.js': 'TensorFlow',
    'PyTorch': 'Python',
    'scikit-learn': 'Python',
    'Pandas': 'Python',
    'NumPy': 'Python',
    'SciPy': 'Python',
    'Matplotlib': 'Python',
    'OpenCV': 'Python',
    
    # 인프라 도구
    'Docker Compose': 'Docker',
    'Docker Swarm': 'Docker',
    'Helm': 'Kubernetes',
    'Istio': 'Kubernetes',
    'Prometheus': 'Kubernetes',
    'Grafana': 'Prometheus',
    'Jenkins': 'Java',
    'GitLab CI': 'GitLab',
    'GitHub Actions': 'GitHub',
    'CircleCI': 'Docker',
    'Travis CI': 'Docker',
    'Ansible': 'Python',
    'Terraform': 'Go',
    'Vagrant': 'VirtualBox',
    
    # 메시징/큐
    'RabbitMQ': 'Erlang',
    'Kafka': 'Java',
    'ActiveMQ': 'Java',
    'Amazon SQS': 'Amazon Web Services',
    'Amazon SNS': 'Amazon Web Services',
    'Google Cloud Pub/Sub': 'Google Cloud Platform',
    'Azure Service Bus': 'Microsoft Azure',
    
    # 모니터링/로깅
    'ELK': 'Elasticsearch',
    'Logstash': 'Elasticsearch',
    'Kibana': 'Elasticsearch',
    'Datadog': 'Python',
    'New Relic': 'Ruby',
    'Sentry': 'Python',
    'Rollbar': 'Python',
    
    # 인증/보안
    'Passport': 'Node',
    'Devise': 'Rails',
    'Firebase Authentication': 'Firebase',
    'Auth0': 'Node',
    'Okta': 'Java',
    'Keycloak': 'Java',
    'OAuth2': 'Security',
    'JSON Web Token': 'Security',
    
    # 게임 엔진
    'Unity': 'C#',
    'Unreal Engine': 'C++',
    'Godot': 'GDScript',
    'Cocos2d-x': 'C++',
    'Phaser': 'JavaScript',
    'three.js': 'JavaScript',
    'Babylon.js': 'JavaScript',
}

# 시너지 관계 (함께 사용되는 기술)
SYNERGY_GROUPS = {
    # 프론트엔드 스택
    'React': ['Redux', 'React Router', 'Webpack', 'Babel', 'Jest', 'ESLint'],
    'Vue': ['Vuex', 'Vue Router', 'Webpack', 'Babel', 'Jest'],
    'Angular': ['TypeScript', 'RxJS', 'Angular Material'],
    'Next.js': ['React', 'Webpack', 'Babel'],
    'Nuxt.js': ['Vue', 'Webpack', 'Babel'],
    
    # 백엔드 스택
    'Django': ['Postgres', 'Redis', 'Celery', 'Gunicorn', 'Nginx'],
    'Flask': ['Postgres', 'Redis', 'Celery', 'Gunicorn', 'Nginx'],
    'Rails': ['Postgres', 'Redis', 'Sidekiq', 'Puma', 'Nginx'],
    'Laravel': ['MySQL', 'Redis', 'Queue', 'Nginx'],
    'Spring Boot': ['MySQL', 'Redis', 'Kafka', 'MongoDB'],
    'Node': ['ExpressJS', 'MongoDB', 'Redis', 'PM2', 'Nginx'],
    'NestJS': ['TypeScript', 'Postgres', 'Redis', 'Docker'],
    
    # 데이터 스택
    'Postgres': ['Redis', 'Elasticsearch', 'Kafka'],
    'MySQL': ['Redis', 'Elasticsearch'],
    'MongoDB': ['Redis', 'Elasticsearch', 'Kafka'],
    'Redis': ['Postgres', 'MySQL', 'MongoDB'],
    'Elasticsearch': ['Logstash', 'Kibana', 'Beats'],
    'Kafka': ['Zookeeper', 'Schema Registry', 'Kafka Connect'],
    
    # ML/AI 스택
    'Python': ['NumPy', 'Pandas', 'scikit-learn', 'TensorFlow', 'PyTorch', 'Jupyter'],
    'TensorFlow': ['Keras', 'NumPy', 'Pandas'],
    'PyTorch': ['NumPy', 'Pandas', 'scikit-learn'],
    'Jupyter': ['Python', 'NumPy', 'Pandas', 'Matplotlib'],
    
    # DevOps 스택
    'Docker': ['Docker Compose', 'Kubernetes', 'CI/CD'],
    'Kubernetes': ['Helm', 'Istio', 'Prometheus', 'Grafana'],
    'Terraform': ['AWS', 'Azure', 'GCP', 'Docker'],
    'Ansible': ['Docker', 'Kubernetes', 'AWS'],
    'Jenkins': ['Docker', 'Kubernetes', 'Git', 'Maven'],
    'GitLab CI': ['Docker', 'Kubernetes', 'GitLab'],
    'GitHub Actions': ['Docker', 'Kubernetes', 'GitHub'],
    
    # 모니터링 스택
    'Prometheus': ['Grafana', 'Alertmanager'],
    'Grafana': ['Prometheus', 'InfluxDB', 'Elasticsearch'],
    'ELK': ['Elasticsearch', 'Logstash', 'Kibana'],
    'Datadog': ['Docker', 'Kubernetes', 'AWS'],
    'New Relic': ['Docker', 'Kubernetes', 'AWS'],
    
    # 클라우드 스택
    'AWS': ['Docker', 'Kubernetes', 'Terraform', 'Ansible'],
    'Azure': ['Docker', 'Kubernetes', 'Terraform'],
    'GCP': ['Docker', 'Kubernetes', 'Terraform'],
}

# 대체 기술 그룹
ALTERNATIVE_GROUPS = {
    # 프론트엔드 프레임워크
    'React': ['Vue', 'Angular', 'Svelte', 'Ember.js'],
    'Vue': ['React', 'Angular', 'Svelte'],
    'Angular': ['React', 'Vue', 'Svelte'],
    'Svelte': ['React', 'Vue', 'Angular'],
    
    # 백엔드 프레임워크 (Python)
    'Django': ['Flask', 'FastAPI', 'Tornado'],
    'Flask': ['Django', 'FastAPI', 'Tornado'],
    'FastAPI': ['Django', 'Flask', 'Tornado'],
    
    # 백엔드 프레임워크 (Node)
    'ExpressJS': ['Koa', 'NestJS', 'Fastify', 'Hapi'],
    'Koa': ['ExpressJS', 'NestJS', 'Fastify'],
    'NestJS': ['ExpressJS', 'Koa', 'Fastify'],
    
    # 백엔드 프레임워크 (Java)
    'Spring Boot': ['Micronaut', 'Quarkus', 'Dropwizard'],
    'Micronaut': ['Spring Boot', 'Quarkus'],
    'Quarkus': ['Spring Boot', 'Micronaut'],
    
    # 데이터베이스 (관계형)
    'Postgres': ['MySQL', 'MariaDB', 'SQL Server', 'Oracle'],
    'MySQL': ['Postgres', 'MariaDB', 'SQL Server'],
    'MariaDB': ['MySQL', 'Postgres'],
    'SQL Server': ['Postgres', 'MySQL', 'Oracle'],
    
    # 데이터베이스 (NoSQL 문서)
    'MongoDB': ['CouchDB', 'Couchbase', 'DynamoDB'],
    'CouchDB': ['MongoDB', 'Couchbase'],
    'Couchbase': ['MongoDB', 'CouchDB'],
    'DynamoDB': ['MongoDB', 'CouchDB'],
    
    # 데이터베이스 (NoSQL 키-값)
    'Redis': ['Memcached', 'Hazelcast', 'ElastiCache'],
    'Memcached': ['Redis', 'Hazelcast'],
    'Hazelcast': ['Redis', 'Memcached'],
    
    # 데이터베이스 (그래프)
    'Neo4j': ['ArangoDB', 'Amazon Neptune'],
    'ArangoDB': ['Neo4j', 'Amazon Neptune'],
    
    # 메시징/큐
    'RabbitMQ': ['Kafka', 'ActiveMQ', 'Amazon SQS', 'Azure Service Bus'],
    'Kafka': ['RabbitMQ', 'ActiveMQ', 'Amazon Kinesis'],
    'ActiveMQ': ['RabbitMQ', 'Kafka'],
    'Amazon SQS': ['RabbitMQ', 'Kafka', 'Azure Service Bus'],
    
    # 컨테이너 오케스트레이션
    'Kubernetes': ['Docker Swarm', 'Nomad', 'Mesos'],
    'Docker Swarm': ['Kubernetes', 'Nomad'],
    'Nomad': ['Kubernetes', 'Docker Swarm'],
    
    # CI/CD
    'Jenkins': ['GitLab CI', 'GitHub Actions', 'CircleCI', 'Travis CI'],
    'GitLab CI': ['Jenkins', 'GitHub Actions', 'CircleCI'],
    'GitHub Actions': ['Jenkins', 'GitLab CI', 'CircleCI'],
    'CircleCI': ['Jenkins', 'GitLab CI', 'GitHub Actions'],
    'Travis CI': ['Jenkins', 'GitLab CI', 'CircleCI'],
    
    # 인프라 코드화
    'Terraform': ['CloudFormation', 'Pulumi', 'Ansible'],
    'CloudFormation': ['Terraform', 'Pulumi'],
    'Pulumi': ['Terraform', 'CloudFormation'],
    'Ansible': ['Terraform', 'Chef', 'Puppet'],
    
    # 모니터링
    'Prometheus': ['Datadog', 'New Relic', 'CloudWatch'],
    'Datadog': ['New Relic', 'Prometheus', 'CloudWatch'],
    'New Relic': ['Datadog', 'Prometheus', 'CloudWatch'],
    'CloudWatch': ['Prometheus', 'Datadog', 'New Relic'],
    
    # 로깅
    'ELK': ['Splunk', 'Datadog', 'New Relic'],
    'Splunk': ['ELK', 'Datadog', 'New Relic'],
    'Datadog': ['ELK', 'Splunk', 'New Relic'],
    
    # 인증
    'Auth0': ['Okta', 'Firebase Authentication', 'Amazon Cognito'],
    'Okta': ['Auth0', 'Firebase Authentication', 'Amazon Cognito'],
    'Firebase Authentication': ['Auth0', 'Okta', 'Amazon Cognito'],
    'Amazon Cognito': ['Auth0', 'Okta', 'Firebase Authentication'],
    
    # 클라우드 제공자
    'AWS': ['Azure', 'GCP', 'DigitalOcean'],
    'Azure': ['AWS', 'GCP', 'DigitalOcean'],
    'GCP': ['AWS', 'Azure', 'DigitalOcean'],
    
    # ML 프레임워크
    'TensorFlow': ['PyTorch', 'Keras', 'MXNet'],
    'PyTorch': ['TensorFlow', 'Keras', 'MXNet'],
    'Keras': ['TensorFlow', 'PyTorch'],
    
    # 웹 서버
    'Nginx': ['Apache HTTP Server', 'Caddy', 'Traefik'],
    'Apache HTTP Server': ['Nginx', 'Caddy'],
    'Caddy': ['Nginx', 'Apache HTTP Server'],
    'Traefik': ['Nginx', 'Caddy'],
    
    # 빌드 도구
    'Webpack': ['Vite', 'Rollup', 'Parcel'],
    'Vite': ['Webpack', 'Rollup', 'Parcel'],
    'Rollup': ['Webpack', 'Vite', 'Parcel'],
    'Parcel': ['Webpack', 'Vite', 'Rollup'],
    
    # 테스팅 프레임워크 (JavaScript)
    'Jest': ['Mocha', 'Jasmine', 'Vitest'],
    'Mocha': ['Jest', 'Jasmine', 'Vitest'],
    'Jasmine': ['Jest', 'Mocha'],
    'Vitest': ['Jest', 'Mocha'],
    
    # E2E 테스팅
    'Cypress': ['Selenium', 'Puppeteer', 'Playwright'],
    'Selenium': ['Cypress', 'Puppeteer', 'Playwright'],
    'Puppeteer': ['Cypress', 'Selenium', 'Playwright'],
    'Playwright': ['Cypress', 'Selenium', 'Puppeteer'],
    
    # CSS 프레임워크
    'Bootstrap': ['Tailwind CSS', 'Foundation', 'Bulma'],
    'Tailwind CSS': ['Bootstrap', 'Foundation', 'Bulma'],
    'Foundation': ['Bootstrap', 'Tailwind CSS'],
    'Bulma': ['Bootstrap', 'Tailwind CSS'],
    
    # 상태 관리 (React)
    'Redux': ['MobX', 'Zustand', 'Recoil'],
    'MobX': ['Redux', 'Zustand', 'Recoil'],
    'Zustand': ['Redux', 'MobX', 'Recoil'],
    'Recoil': ['Redux', 'MobX', 'Zustand'],
    
    # 상태 관리 (Vue)
    'Vuex': ['Pinia', 'Composition API'],
    'Pinia': ['Vuex', 'Composition API'],
    
    # 게임 엔진
    'Unity': ['Unreal Engine', 'Godot', 'Cocos2d-x'],
    'Unreal Engine': ['Unity', 'Godot'],
    'Godot': ['Unity', 'Unreal Engine'],
}

def normalize_name(name: str) -> str:
    """기술 이름을 정규화합니다."""
    name = name.strip()
    return NAME_NORMALIZATION.get(name, name)

def get_role_type(name: str, description: str) -> str:
    """기술의 역할 유형을 판단합니다."""
    name_lower = name.lower()
    desc_lower = description.lower()
    
    # 언어
    if any(keyword in desc_lower for keyword in ['프로그래밍 언어', 'language', '언어']):
        return 'Programming Language'
    
    # 프레임워크
    if any(keyword in desc_lower or keyword in name_lower for keyword in ['프레임워크', 'framework', '.js', 'js']):
        return 'Framework'
    
    # 라이브러리
    if any(keyword in desc_lower for keyword in ['라이브러리', 'library']):
        return 'Library'
    
    # 데이터베이스
    if any(keyword in desc_lower or keyword in name_lower for keyword in ['데이터베이스', 'database', 'db', 'nosql', 'sql']):
        return 'Database'
    
    # 클라우드 서비스
    if any(keyword in name_lower for keyword in ['amazon', 'aws', 'azure', 'google cloud', 'gcp']):
        return 'Cloud Service'
    
    # 도구
    if any(keyword in desc_lower for keyword in ['도구', 'tool', '플랫폼', 'platform']):
        return 'Tool'
    
    # 운영체제
    if any(keyword in desc_lower for keyword in ['운영체제', 'operating system', 'os']):
        return 'Operating System'
    
    # IDE
    if any(keyword in desc_lower for keyword in ['ide', '개발 환경', 'development environment']):
        return 'IDE'
    
    return 'Tool'

def get_architecture_layer(name: str, description: str, role_type: str) -> str:
    """아키텍처 계층을 판단합니다."""
    name_lower = name.lower()
    desc_lower = description.lower()
    
    if role_type == 'Database':
        return 'Persistence Layer'
    elif role_type == 'Cloud Service':
        if 'cdn' in desc_lower or 'cloudfront' in name_lower:
            return 'Edge Caching Layer'
        elif 'storage' in desc_lower or 's3' in name_lower:
            return 'Storage Layer'
        elif 'compute' in desc_lower or 'ec2' in name_lower or 'lambda' in name_lower:
            return 'Compute Layer'
        elif 'database' in desc_lower or 'rds' in name_lower:
            return 'Persistence Layer'
        else:
            return 'Application Layer'
    elif 'frontend' in desc_lower or 'ui' in desc_lower or 'client' in desc_lower:
        return 'Presentation Layer'
    elif 'backend' in desc_lower or 'server' in desc_lower or 'api' in desc_lower:
        return 'Application Layer'
    elif 'infrastructure' in desc_lower or 'devops' in desc_lower or 'ci/cd' in desc_lower:
        return 'Infrastructure Layer'
    elif 'monitoring' in desc_lower or 'logging' in desc_lower:
        return 'Observability Layer'
    elif 'security' in desc_lower or 'authentication' in desc_lower:
        return 'Security Layer'
    elif 'messaging' in desc_lower or 'queue' in desc_lower:
        return 'Messaging Layer'
    else:
        return 'Application Layer'

def analyze_tech_stack(name: str, description: str) -> Dict:
    """기술 스택을 분석하여 관계 정보를 추출합니다."""
    normalized_name = normalize_name(name)
    
    # 역할 유형
    role_type = get_role_type(name, description)
    
    # 계층 구조
    parent = PARENT_RELATIONSHIPS.get(normalized_name) or PARENT_RELATIONSHIPS.get(name)
    is_child = parent is not None
    
    # 필수 인프라
    required_infra = []
    if parent:
        required_infra.append(parent)
    if 'docker' in description.lower() and 'Docker' not in required_infra:
        required_infra.append('Docker')
    if 'kubernetes' in description.lower() and 'Kubernetes' not in required_infra:
        required_infra.append('Kubernetes')
    if 'aws' in description.lower() and 'Amazon Web Services' not in required_infra:
        required_infra.append('Amazon Web Services')
    if 'azure' in description.lower() and 'Microsoft Azure' not in required_infra:
        required_infra.append('Microsoft Azure')
    if 'gcp' in description.lower() or 'google cloud' in description.lower():
        if 'Google Cloud Platform' not in required_infra:
            required_infra.append('Google Cloud Platform')
    
    # 시너지 관계
    synergy_with = SYNERGY_GROUPS.get(normalized_name, []) or SYNERGY_GROUPS.get(name, [])
    
    # 대체 기술
    alternatives = ALTERNATIVE_GROUPS.get(normalized_name, []) or ALTERNATIVE_GROUPS.get(name, [])
    
    # 아키텍처 계층
    architecture_layer = get_architecture_layer(name, description, role_type)
    
    # 문제 해결
    problem_solved = description  # 기본적으로 설명을 사용
    
    # 상세 설명
    detailed_description = description
    
    return {
        "role_type": role_type,
        "hierarchy": {
            "is_child": str(is_child).lower(),
            "parent": parent if parent else None
        },
        "connections": {
            "required_infra": required_infra,
            "synergy_with": synergy_with
        },
        "alternatives": alternatives,
        "context": {
            "problem_solved": problem_solved,
            "architecture_layer": architecture_layer,
            "detailed_description": detailed_description
        }
    }

def main():
    """메인 함수"""
    input_file = 'tech_stacks_merged_final.csv'
    output_file = 'tech_stacks_relationships.json'
    
    results = {}
    
    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('name', '').strip()
            description = row.get('description', '').strip()
            
            if not name:
                continue
            
            print(f"Analyzing: {name}")
            results[name] = analyze_tech_stack(name, description)
    
    print(f"\nWriting results to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Done! Analyzed {len(results)} tech stacks.")
    print(f"Results saved to {output_file}")

if __name__ == '__main__':
    main()
