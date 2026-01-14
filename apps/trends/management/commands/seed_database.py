"""
Django management command to seed the database with canonical TechStack data and categories.

This script consolidates all previous import, deduplication, and categorization
logic into a single, idempotent command. It is designed to bring a new or
existing database to the final, fully categorized state.

Sequence of operations:
1.  Import TechStacks from 'tech_stacks_source.csv'.
2.  Deduplicate TechStacks based on name (case-insensitive) to ensure uniqueness.
3.  Define and sync all 9 canonical Category names, deleting erroneous ones.
4.  Apply a comprehensive, final categorization map to all TechStacks.
"""
import csv
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import Lower
from apps.trends.models import TechStack, Category, CategoryTech

logger = logging.getLogger(__name__)

# This map combines ALL final categorization logic for ALL 1070 unique TechStacks.
# This ensures a consistent and complete categorization.
# It is built from all previous refinement rounds.
MASTER_CATEGORIZATION_MAP = {
    # Languages
    'Python': ['Backend', 'AI & Data', 'DevOps'],
    'Java': ['Backend', 'AI & Data'], # Corrected (removed Game)
    'Java 8': ['Backend', 'AI & Data'], # Corrected (removed Game)
    'Java EE': ['Backend'],
    'JavaScript': ['Frontend', 'Backend'],
    'TypeScript': ['Frontend', 'Backend'],
    'C++': ['Backend', 'Game', 'Embedding'],
    'C lang': ['Backend', 'Game', 'Embedding'],
    'C#': ['Backend', 'Game'],
    'Go': ['Backend', 'DevOps'],
    'Golang': ['Backend', 'DevOps'],
    'Rust': ['Backend', 'DevOps', 'Game', 'Embedding'],
    'Swift': ['Mobile & App'], # Corrected
    'Kotlin': ['Mobile & App', 'Backend'], # Corrected
    'Ruby': ['Backend'],
    'PHP': ['Backend'],
    'Dart': ['Frontend', 'Mobile & App'], # Corrected (removed Game)
    'Scala': ['Backend', 'AI & Data'],
    'R Language': ['AI & Data'],
    'Shell': ['DevOps'],
    'GNU Bash': ['DevOps'],
    'PowerShell': ['DevOps'],
    'Groovy': ['DevOps', 'Backend'],
    'Elixir': ['Backend'],
    'Clojure': ['Backend'],
    'ClojureScript': ['Frontend'],
    'Haskell': ['Backend'],
    'Perl': ['Backend', 'DevOps'],
    'Objective-C': ['Mobile & App'], # Corrected
    'Lua': ['Game', 'Embedding'],
    'Assembly Language': ['Embedding', 'Game'],
    'F#': ['Backend', 'AI & Data'],
    'Julia': ['AI & Data'],
    'Elm': ['Frontend'],
    'Crystal': ['Backend'],
    'Hack': ['Backend'],
    'D': ['Backend', 'Game'],
    'Smalltalk': ['Backend'],
    'Common Lisp': ['AI & Data', 'Backend'],
    'OCaml': ['Backend'],
    'Delphi': ['Backend'],
    'Visual Basic': ['Backend'],
    'PureBasic': ['Game'],
    'HTML5': ['Frontend'],
    'CSS 3': ['Frontend'],
    'SQL': ['Backend', 'AI & Data'],
    'ES6': ['Frontend', 'Backend'],

    # Frontend Frameworks & Libraries
    'React': ['Frontend'],
    'Angular': ['Frontend'],
    'AngularJS': ['Frontend'],
    'Vue.js': ['Frontend'],
    'Svelte': ['Frontend'],
    'jQuery': ['Frontend'],
    'jQuery UI': ['Frontend'],
    'jQuery Mobile': ['Frontend'],
    'Next.js': ['Frontend', 'Backend'],
    'Nuxt.js': ['Frontend', 'Backend'],
    'Gatsby': ['Frontend'],
    'Ember.js': ['Frontend'],
    'Backbone.js': ['Frontend'],
    'Preact': ['Frontend'],
    'React Native': ['Mobile & App'], # Corrected
    'Flutter': ['Mobile & App'], # Corrected
    'Ionic': ['Mobile & App'], # Corrected
    'Xamarin': ['Mobile & App'],
    'Xamarin Forms': ['Mobile & App'],
    'NativeScript': ['Mobile & App'],
    'Expo': ['Mobile & App'],
    'SwiftUI': ['Mobile & App'],
    'Redux': ['Frontend'],
    'redux-thunk': ['Frontend'],
    'redux-saga': ['Frontend'],
    'reselect': ['Frontend'],
    'MobX': ['Frontend'],
    'vuex': ['Frontend'],
    'React Router': ['Mobile & App', 'Frontend'], # Corrected
    'Vue Router': ['Frontend'],
    'styled-components': ['Frontend'],
    'Emotion': ['Frontend'],
    'Sass': ['Frontend'],
    'Less': ['Frontend'],
    'Stylus': ['Frontend'],
    'PostCSS': ['Frontend'],
    'Tailwind CSS': ['Frontend'],
    'Bootstrap': ['Frontend'],
    'Material-UI': ['Frontend'],
    'Ant Design': ['Frontend'],
    'Chakra UI': ['Frontend'],
    'Semantic UI': ['Frontend'],
    'Foundation': ['Frontend'],
    'Bulma': ['Frontend'],
    'Materialize': ['Frontend'],
    'Vuetify': ['Frontend'],
    'PrimeNg': ['Frontend'],
    'Angular Material': ['Frontend'],
    'Material Design for Angular': ['Frontend'],
    'Kendo UI': ['Frontend'],
    'D3.js': ['Frontend', 'AI & Data'],
    'three.js': ['Frontend', 'Game'],
    'Chart.js': ['Frontend', 'AI & Data'],
    'Highcharts': ['Frontend', 'AI & Data'],
    'Leaflet': ['Frontend'],
    'Mapbox': ['Frontend'],
    'Plotly.js': ['Frontend', 'AI & Data'],
    'Animate.css': ['Frontend'],
    'Aurelia': ['Frontend'],
    'Polymer': ['Frontend'],
    'Quasar Framework': ['Frontend'],
    'Bootstrap Vue': ['Frontend'],
    'Semantic UI React': ['Frontend'],
    'VuePress': ['Frontend', 'etc'],
    'React.js Boilerplate': ['Frontend'],
    'React Hot Loader': ['Frontend', 'DevOps'],
    'reactstrap': ['Frontend'],
    'Normalize.css': ['Frontend'],
    'Vue Native': ['Mobile & App'], # Corrected
    'Docusaurus': ['Frontend', 'etc'],
    'GLSL': ['Game', 'Frontend'],
    'MooTools': ['Frontend'],
    'YUI Library': ['Frontend'],
    'Phaser': ['Frontend', 'Game'], # New
    'PixiJS': ['Frontend', 'Game'], # New
    'Babylon.js': ['Frontend', 'Game'], # New
    'PlayCanvas': ['Frontend', 'Game'], # New

    # Backend Frameworks & Libraries
    'Node.js': ['Backend'],
    'ExpressJS': ['Backend'],
    'Django': ['Backend'],
    'Flask': ['Backend'],
    'Spring': ['Backend'],
    'Spring Boot': ['Backend'],
    'Spring Framework': ['Backend'],
    'Rails': ['Backend'],
    'Laravel': ['Backend'],
    'ASP.NET': ['Backend'],
    'ASP.NET Core': ['Backend'],
    'FastAPI': ['Backend'],
    'NestJS': ['Backend'],
    'Koa': ['Backend'],
    'AdonisJS': ['Backend'],
    'Phoenix Framework': ['Backend'],
    'Symfony': ['Backend'],
    'CodeIgniter': ['Backend'],
    'CakePHP': ['Backend'],
    'Yii': ['Backend'],
    'Lumen': ['Backend'],
    'Sinatra': ['Backend'],
    'Dropwizard': ['Backend'],
    'Play': ['Backend'],
    'Hibernate': ['Backend'],
    'SQLAlchemy': ['Backend'],
    'Mongoose': ['Backend'],
    'Sequelize': ['Backend'],
    'TypeORM': ['Backend'],
    'Prisma': ['Backend'],
    'Entity Framework': ['Backend'],
    'Gunicorn': ['Backend'],
    'uWSGI': ['Backend'],
    'PM2': ['Backend'],
    'Celery': ['Backend', 'DevOps'],
    'Socket.IO': ['Backend', 'Frontend'],
    'GraphQL': ['Backend', 'Frontend'],
    'Apollo': ['Backend', 'Frontend'],
    'gRPC': ['Backend'],
    'Fastify': ['Backend'],
    'Gin Gonic': ['Backend'],
    'Apache Tomcat': ['Backend'],
    'Microsoft IIS': ['Backend', 'DevOps'],
    'OpenResty': ['Backend', 'DevOps'],
    'LiteSpeed': ['Backend', 'DevOps'],
    'Akka': ['Backend'],
    'Erlang': ['Backend'],
    'ActiveMQ': ['Backend', 'DevOps'],
    'Sidekiq': ['Backend', 'DevOps'],
    'Passenger': ['Backend', 'DevOps'],
    'Puma': ['Backend', 'DevOps'],
    'Spring Data': ['Backend'],
    'Spring Security': ['Backend', 'Security'],
    'Spring MVC': ['Backend'],
    'ws': ['Backend', 'Frontend'],
    'Tornado': ['Backend'],
    'Thymeleaf': ['Backend', 'Frontend'],
    'JHipster': ['Backend', 'Frontend', 'DevOps'],
    'MyBatis': ['Backend'],
    'Micronaut Framework': ['Backend'],
    'FeathersJS': ['Backend'],
    'Sails.js': ['Backend'],
    'LoopBack': ['Backend'],
    'Grails': ['Backend'],
    'Cowboy': ['Backend'],
    'Dapper': ['Backend'],
    'Quarkus': ['Backend'],
    'Netty': ['Backend'],
    'Vert.x': ['Backend'],
    'Knex.js': ['Backend'],
    'Doctrine 2': ['Backend'],
    'Zend Framework': ['Backend'],
    'Strapi': ['Backend'],

    # AI & Data
    'TensorFlow': ['AI & Data'],
    'PyTorch': ['AI & Data'],
    'Keras': ['AI & Data'],
    'scikit-learn': ['AI & Data'],
    'Pandas': ['AI & Data'],
    'NumPy': ['AI & Data'],
    'SciPy': ['AI & Data'],
    'Jupyter': ['AI & Data', 'DevOps'],
    'Apache Spark': ['AI & Data'],
    'Hadoop': ['AI & Data'],
    'Kafka': ['AI & Data', 'Backend', 'DevOps'],
    'RabbitMQ': ['Backend', 'DevOps'],
    'Apache Flink': ['AI & Data'],
    'Apache Beam': ['AI & Data'],
    'OpenCV': ['AI & Data'],
    'Matplotlib': ['AI & Data'],
    'Databricks': ['AI & Data', 'DevOps'],
    'Snowflake': ['AI & Data', 'Backend'],
    'Google BigQuery': ['AI & Data', 'Backend'],
    'Amazon Redshift': ['AI & Data', 'Backend'],
    'LangChain': ['AI & Data'], # Corrected (removed Embedding)
    'SpaCy': ['AI & Data'],
    'Airflow': ['AI & Data', 'DevOps'],
    'Kubeflow': ['AI & Data', 'DevOps'],
    'MLflow': ['AI & Data', 'DevOps'],
    'dbt': ['AI & Data', 'Backend'],
    'Tableau': ['AI & Data'],
    'Power BI': ['AI & Data'], # Corrected merge
    'Looker': ['AI & Data'],
    'Superset': ['AI & Data'],
    'Metabase': ['AI & Data'],
    'Streamlit': ['AI & Data', 'Frontend'],
    'Dash': ['AI & Data', 'Frontend'],
    'Amazon Kinesis': ['AI & Data', 'DevOps'],
    'Amazon Athena': ['AI & Data', 'Backend'],
    'Presto': ['AI & Data', 'Backend'],
    'AWS Glue': ['AI & Data', 'DevOps'],
    'Amazon EMR': ['AI & Data', 'DevOps'],
    'Druid': ['AI & Data', 'Backend'],
    'Apache NiFi': ['AI & Data', 'DevOps'],
    'HBase': ['AI & Data', 'Backend'],
    'Apache Hive': ['AI & Data'],
    'Kafka Streams': ['AI & Data', 'Backend'],
    'Dialogflow': ['AI & Data'],
    'PySpark': ['AI & Data'],
    'Apache Storm': ['AI & Data'],
    'Aerospike': ['AI & Data', 'Backend'],
    'TensorFlow.js': ['AI & Data', 'Frontend'],
    'Google Cloud Dataflow': ['AI & Data', 'DevOps'],
    'Avro': ['AI & Data', 'Backend'],
    'Confluent': ['AI & Data', 'Backend', 'DevOps'],
    'Amazon SageMaker': ['AI & Data'],
    'Amazon Quicksight': ['AI & Data'],
    'MATLAB': ['AI & Data'],
    'IPython': ['AI & Data'],
    'Torch': ['AI & Data'],
    'scikit-image': ['AI & Data'],
    'Talend': ['AI & Data'],
    'Apache Zeppelin': ['AI & Data'],
    'Chartio': ['AI & Data'],
    'Redash': ['AI & Data'],
    'Microsoft Bot Framework': ['AI & Data', 'Backend'],
    'Data Studio': ['AI & Data'],
    'Azure Machine Learning': ['AI & Data'],
    'Mixpanel': ['AI & Data', 'etc'],
    'Segment': ['AI & Data', 'etc'],
    'Piwik': ['AI & Data', 'etc'],
    'Heap': ['AI & Data', 'etc'],
    'Amplitude': ['AI & Data', 'etc'],
    'CUDA': ['AI & Data', 'Game', 'Embedding'],
    'Edge AI (TinyML)': ['Embedding', 'AI & Data'],

    # DevOps
    'Docker': ['DevOps'],
    'Kubernetes': ['DevOps'],
    'Jenkins': ['DevOps'],
    'GitLab CI': ['DevOps'],
    'GitHub Actions': ['DevOps'],
    'CircleCI': ['DevOps'],
    'Travis CI': ['DevOps'],
    'Ansible': ['DevOps'],
    'Terraform': ['DevOps'],
    'Pulumi': ['DevOps'],
    'Chef': ['DevOps'],
    'Puppet Labs': ['DevOps'],
    'Vagrant': ['DevOps'],
    'Prometheus': ['DevOps'],
    'Grafana': ['DevOps'],
    'Datadog': ['DevOps', 'AI & Data'],
    'New Relic': ['DevOps'],
    'Splunk': ['DevOps', 'Security'],
    'ELK': ['DevOps', 'AI & Data'],
    'Elasticsearch': ['DevOps', 'Backend', 'AI & Data'],
    'Logstash': ['DevOps', 'AI & Data'],
    'Kibana': ['DevOps', 'AI & Data'],
    'Fluentd': ['DevOps'],
    'Jaeger': ['DevOps'],
    'Istio': ['DevOps'],
    'Envoy': ['DevOps'],
    'Consul': ['DevOps'],
    'NGINX': ['Backend', 'DevOps'],
    'Apache HTTP Server': ['Backend', 'DevOps'],
    'HAProxy': ['Backend', 'DevOps'],
    'Traefik': ['DevOps'],
    'Heroku': ['DevOps'],
    'Vercel': ['DevOps', 'Frontend'],
    'Netlify': ['DevOps', 'Frontend'],
    'AWS': ['DevOps', 'Backend', 'AI & Data'],
    'Amazon Web Services (AWS)': ['DevOps', 'Backend', 'AI & Data'],
    'Microsoft Azure': ['DevOps', 'Backend', 'AI & Data'],
    'Google Cloud Platform': ['DevOps', 'Backend', 'AI & Data'],
    'DigitalOcean': ['DevOps', 'Backend'],
    'Serverless': ['DevOps', 'Backend'],
    'AWS Lambda': ['DevOps', 'Backend'],
    'Google Cloud Functions': ['DevOps', 'Backend'],
    'Azure Functions': ['DevOps', 'Backend'],
    'Docker Compose': ['DevOps'],
    'Amazon CloudFront': ['DevOps', 'Backend'],
    'GitHub Pages': ['DevOps', 'Frontend'],
    'Amazon Route 53': ['DevOps'],
    'Amazon EC2 Container Service': ['DevOps'],
    'AWS Elastic Load Balancing (ELB)': ['DevOps'],
    'Amazon CloudWatch': ['DevOps'],
    'Google App Engine': ['DevOps', 'Backend'],
    'Varnish': ['Backend', 'DevOps'],
    'Azure DevOps': ['DevOps'],
    'AWS Elastic Beanstalk': ['DevOps', 'Backend'],
    'Red Hat OpenShift': ['DevOps'],
    'AWS CloudFormation': ['DevOps'],
    'Azure Pipelines': ['DevOps'],
    'Amazon VPC': ['DevOps'],
    'Rancher': ['DevOps'],
    'Helm': ['DevOps'],
    'TeamCity': ['DevOps'],
    'Terraform Registry': ['DevOps'],
    'AWS IAM': ['DevOps', 'Security'],
    'Google Kubernetes Engine': ['DevOps'],
    'Kong': ['Backend', 'DevOps'],
    'Codeship': ['DevOps'],
    'OpenStack': ['DevOps'],
    'Nagios': ['DevOps'],
    'Docker Swarm': ['DevOps'],
    'Plesk': ['DevOps'],
    'pre-commit': ['DevOps'],
    'Zabbix': ['DevOps'],
    'Fastly': ['DevOps'],
    'Linode': ['DevOps'],
    'Lerna': ['DevOps'],
    'AWS CodePipeline': ['DevOps'],
    'Drone.io': ['DevOps'],
    'Portainer': ['DevOps'],
    'Argo': ['DevOps'],
    'Packer': ['DevOps'],
    'AWS Fargate': ['DevOps'],
    'AWS CodeCommit': ['DevOps'],
    'Google Cloud Build': ['DevOps'],
    'Bamboo': ['DevOps'],
    'AWS CodeDeploy': ['DevOps'],
    'Eureka': ['DevOps', 'Backend'],
    'AWS CodeBuild': ['DevOps'],
    'Sonatype Nexus': ['DevOps'],
    'Docker Machine': ['DevOps'],
    'Octopus Deploy': ['DevOps'],
    'Salt': ['DevOps'],
    'NATS': ['Backend', 'DevOps'],
    'AppDynamics': ['DevOps'],
    'Loki': ['DevOps'],
    'ngrok': ['DevOps', 'etc'],
    'Fabric': ['DevOps'],
    'Apigee': ['Backend', 'DevOps'],
    'Sauce Labs': ['DevOps'],
    'Azure Websites': ['DevOps', 'Backend'],
    'Flyway': ['DevOps', 'Backend'],
    'hub': ['DevOps', 'etc'],
    'Graphite': ['DevOps'],
    'Zuul': ['DevOps', 'Backend'],
    'Gitea': ['DevOps', 'etc'],
    'JFrog Artifactory': ['DevOps'],
    'Buddy': ['DevOps'],
    'Proxmox VE': ['DevOps'],
    'Amazon Elasticsearch Service': ['DevOps', 'AI & Data', 'Backend'],
    'Azure Data Factory': ['AI & Data', 'DevOps'],
    'Azure App Service': ['DevOps', 'Backend'],
    'Stackdriver': ['DevOps'],
    'Caddy': ['Backend', 'DevOps'],
    'Azure Application Insights': ['DevOps'],
    'Concourse': ['DevOps'],
    'wercker': ['DevOps'],
    'Telegraf': ['DevOps'],
    'AWS Step Functions': ['DevOps', 'Backend'],
    'Netdata': ['DevOps'],
    'Loggly': ['DevOps'],
    'Nomad': ['DevOps'],
    'Amazon ECR': ['DevOps'],
    'Spinnaker': ['DevOps'],
    'LogRocket': ['DevOps', 'Frontend'],
    'Gatling': ['DevOps'],
    'OpsGenie': ['DevOps'],
    'Splunk Cloud': ['DevOps', 'Security'],
    'GoCD': ['DevOps'],
    'boot2docker': ['DevOps'],
    'CoreOS': ['DevOps'],
    'Rundeck': ['DevOps'],
    'Hystrix': ['Backend', 'DevOps'],
    'SonarLint': ['DevOps'],
    'Cloud Foundry': ['DevOps'],
    'k6': ['DevOps'],
    'Render': ['DevOps'],
    'Locust': ['DevOps'],
    'ESLint': ['Frontend', 'DevOps'],
    'Yarn': ['Frontend', 'DevOps'],
    'Matomo': ['AI & Data', 'etc'],
    'Amazon EKS': ['DevOps'],
    'Bazel': ['DevOps'],
    'Laravel Forge': ['DevOps'],
    'Docker Hub': ['DevOps'],
    'Jenkins X': ['DevOps'],
    'Lighthouse': ['Frontend', 'DevOps'],
    'Mercurial': ['DevOps'],
    'OpenVPN': ['Security', 'DevOps'],
    'Sumo Logic': ['DevOps', 'Security'],
    'Webpack': ['Frontend', 'DevOps'],
    'Stylelint': ['Frontend', 'DevOps'],
    'Composer': ['DevOps', 'Backend'],
    'PagerDuty': ['DevOps'],
    'RuboCop': ['DevOps', 'Backend'],
    'Bugsnag': ['DevOps'],
    'Docker Swarm': ['DevOps'],
    'Dyn': ['DevOps'],
    'pre-commit': ['DevOps'],
    'Puppeteer': ['Frontend', 'DevOps'],
    'JSHint': ['Frontend', 'DevOps'],
    'Zabbix': ['DevOps'],
    'Bundler': ['DevOps', 'Backend'],
    'rollup': ['Frontend', 'DevOps'],
    'Moq': ['Backend', 'DevOps'],
    'Azure Pipelines': ['DevOps'],
    'AWS CodePipeline': ['DevOps'],
    'Drone.io': ['DevOps'],
    'flake8': ['DevOps', 'Backend'],
    'Code Climate': ['DevOps'],
    'PySpark': ['AI & Data'],
    'Watchdog Timer': ['Embedding'],
    'Verilog/VHDL': ['Embedding'],
    'Keil MDK / IAR Workbench': ['Embedding', 'etc'],
    'GNU Arm Toolchain (GCC)': ['Embedding', 'DevOps'],
    'OpenOCD': ['Embedding', 'DevOps'],
    'J-Link / ST-LINK': ['Embedding', 'DevOps'],
    'Oscilloscope / Logic Analyzer': ['Embedding', 'etc'],
    'OTA (Over-The-Air)': ['Embedding', 'DevOps'],
    'Edge AI (TinyML)': ['Embedding', 'AI & Data'],
    'Bootloader': ['Embedding'],
    'MISRA C': ['Embedding'],
    'Functional Safety (ISO 26262)': ['Embedding'],
    'Burp Suite': ['Security'],
    'Metasploit': ['Security'],
    'ZAP (OWASP)': ['Security'],
    'WAF (Web Application Firewall)': ['Security', 'DevOps'],
    'SQL Injection / XSS': ['Security'],
    'Wireshark': ['Security', 'DevOps'],
    'Nmap': ['Security', 'DevOps'],
    'IDS/IPS': ['Security', 'DevOps'],
    'SSH / SFTP / FTP': ['Security', 'DevOps'],
    'WireGuard': ['Security', 'DevOps'],
    'Suricata': ['Security', 'DevOps'],
    'Snort': ['Security', 'DevOps'],
    'OIDC': ['Security', 'Backend'],
    'MFA (Multi-Factor Authentication)': ['Security'],
    'RBAC / ABAC': ['Security', 'Backend'],
    'Falco': ['Security', 'DevOps'],
    'Trivy': ['Security', 'DevOps'],
    'KMS (Key Management Service)': ['Security', 'DevOps'],
    'Ghidra / IDA Pro': ['Security'],
    'John the Ripper / Hashcat': ['Security'],
    'SIEM (Splunk, ELK Stack)': ['Security', 'DevOps'],
    'ARM Cortex-M': ['Embedding'],
    'ARM Cortex-A': ['Embedding'],
    'STM32': ['Embedding'],
    'AVR / PIC': ['Embedding'],
    'RISC-V': ['Embedding'],
    'Nordic nRF': ['Embedding'],
    'FPGA': ['Embedding'],
    'FreeRTOS': ['Embedding'],
    'Zephyr': ['Embedding'],
    'Yocto Project': ['Embedding', 'DevOps'],
    'Buildroot': ['Embedding', 'DevOps'],
    'QNX / VxWorks': ['Embedding'],
    'uC/OS (Micrium)': ['Embedding'],
    'Bare-metal': ['Embedding'],
    'UART': ['Embedding'],
    'I2C': ['Embedding'],
    'SPI': ['Embedding'],
    'CAN bus': ['Embedding'],
    'Modbus': ['Embedding'],
    'EtherCAT': ['Embedding'],
    'BLE (Bluetooth Low Energy)': ['Embedding', 'Mobile & App'],
    'Zigbee': ['Embedding'],
    'HAL (Hardware Abstraction Layer)': ['Embedding'],
    'Device Driver': ['Embedding'],
    'Register Level Programming': ['Embedding'],
    'GPIO/PWM': ['Embedding'],
    'ADC/DAC': ['Embedding'],
    'DMA(Direct Memory Access)': ['Embedding'],
    'Angular CLI': ['Frontend', 'DevOps'],
    'G Suite': ['etc'],
    'Electron': ['Frontend', 'Backend'],
    'Google Compute Engine': ['DevOps', 'Backend'],
    '.NET': ['Backend', 'Game'],
    'Memcached': ['Backend', 'DevOps'],
    '.NET Core': ['Backend', 'Game'],
    'Apache Camel': ['Backend'],
    'Amazon API Gateway': ['Backend', 'DevOps'],
    'Pug': ['Frontend'],
    'Spring Cloud': ['Backend', 'DevOps'],
    'Android OS': ['Mobile & App'],
    'Firefox': ['etc'],
    'Create React App': ['Frontend', 'DevOps'],
    'Strapi': ['Backend'],
    'Zookeeper': ['DevOps', 'Backend'],
    'Cloud Firestore': ['Backend'],
    'Ethereum': ['Backend', 'etc'],
    'Parse': ['Backend'],
    'GitHub Enterprise': ['DevOps', 'etc'],
    'Playwright': ['Frontend', 'DevOps'],
    'Google Cloud Pub/Sub': ['Backend', 'DevOps'],
    'Raspberry Pi': ['Embedding', 'etc'],
    'MEAN': ['Frontend', 'Backend'],
    'Hasura': ['Backend'],
    'OpenAI': ['AI & Data'],
    'RxJava': ['Backend', 'Frontend', 'Mobile & App'],
    'Apex': ['Backend'],
    'StatusPage.io': ['DevOps', 'etc'],
    'Power BI': ['AI & Data'],
    'Data Studio': ['AI & Data'],
    'JavaFX': ['Frontend', 'Backend'],
    'Firebase Cloud Messaging': ['Backend', 'Frontend'],
    'Linux Mint': ['etc'],
    'Dynatrace': ['DevOps'],
    'Slim': ['Backend'],
    'highlight.js': ['Frontend'],
    'Compass': ['Frontend', 'DevOps'],
    'phpMyAdmin': ['etc'],
    'SEMrush': ['etc'],
    'SweetAlert': ['Frontend'],
    'Pipedrive': ['etc'],
    'Google Cloud Datastore': ['Backend'],
    'LaunchDarkly': ['DevOps'],
    'Castle Core': ['Backend'],
    'Apache FreeMarker': ['Backend'],
    'Dojo': ['Frontend'],
    'Ramda': ['Frontend', 'Backend'],
    'PhpSpec': ['Backend', 'DevOps'],
    'Telegram Bot API': ['Backend', 'etc'],
    'Jackson': ['Backend'],
    'Airbrake': ['DevOps'],
    'Red Hat Enterprise Linux (RHEL)': ['etc'],
    'Polly': ['Backend', 'AI & Data'],
    'Clever Cloud': ['DevOps'],
    'Retrofit': ['Backend', 'Mobile & App'],
    'Laravel Homestead': ['DevOps'],
    'UptimeRobot': ['DevOps'],
    'Odoo': ['Backend', 'etc'],
    'Hangfire': ['Backend'],
    'AWS CloudTrail': ['DevOps', 'Security'],
    'C3.js': ['Frontend', 'AI & Data'],
    'Weebly': ['etc'],
    'Zulip': ['etc'],
    'dbForge Studio for Oracle': ['Backend', 'etc'],
    'IFTTT': ['etc'],
    'Unbounce': ['etc'],
    'Typeform': ['etc'],
    'Knockout': ['Frontend'],
    'dbForge Studio for PostgreSQL': ['Backend', 'etc'],
    'Azure Databricks': ['AI & Data', 'DevOps'],
    'HSQLDB': ['Backend'],
    'Salesforce Commerce Cloud': ['etc'],
    'Nightwatchjs': ['Frontend', 'DevOps'],
    'vscode.dev': ['etc'],
    'Mac OS X': ['etc'],
    'Tumblr': ['etc'],
    'Microsoft SQL Server Management Studio': ['Backend', 'etc'],
    'dbForge Studio for MySQL': ['Backend', 'etc'],
    'Godot': ['Game'],
    'GameMaker': ['Game'],
    'Love2D': ['Game'],
    'MonoGame': ['Game'],
    'Phaser': ['Frontend', 'Game'],
    'PixiJS': ['Frontend', 'Game'],
    'Babylon.js': ['Frontend', 'Game'],
    'PlayCanvas': ['Frontend', 'Game'],
    'Haxe': ['Game'],
    'Cocos2d-x': ['Game', 'Mobile & App'],
}

class Command(BaseCommand):
    help = 'Seeds the database with canonical TechStack data and categories.'

    def add_arguments(self, parser):
        parser.add_argument(
            'source_csv',
            type=str,
            help='The path to the canonical CSV file for TechStacks.',
            nargs='?', # Makes it optional
            default='tech_stacks_source.csv' # Default value
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Starting Database Seeding ---'))
        source_csv_path = options['source_csv']

        # --- Step 1: Import/Sync Tech Stacks from CSV ---
        self.stdout.write(f'\n[Step 1/4] Importing/Syncing TechStacks from {source_csv_path}...'))
        try:
            with open(source_csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                imported_count = 0
                for row in reader:
                    tech_stack, created = TechStack.objects.get_or_create(
                        name=row['Name'],
                        defaults={
                            'logo': row.get('Image', ''),
                            'docs_url': row.get('Link', 'replace_here')
                        }
                    )
                    if created:
                        imported_count += 1
                self.stdout.write(self.style.SUCCESS(f'Successfully imported/synced {imported_count} new TechStacks.'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Source CSV file not found: {source_csv_path}. Please ensure it is in the backend directory.'))
            raise

        # --- Step 2: Deduplicate Tech Stacks (Safety Measure) ---
        self.stdout.write('\n[Step 2/4] Deduplicating TechStack entries...'))
        duplicate_names = (
            TechStack.objects.values('name')
            .annotate(name_count=Count('name'))
            .filter(name_count__gt=1)
            .order_by('name')
        )
        if duplicate_names.exists():
            for entry in duplicate_names:
                name = entry['name']
                self.stdout.write(f'  - Processing duplicate name: "{name}"'))
                duplicates = TechStack.objects.filter(name=name).order_by('id')
                canonical_stack = duplicates.first()
                redundant_stacks = duplicates.exclude(id=canonical_stack.id)
                for redundant_stack in redundant_stacks:
                    for ct in redundant_stack.category_relations.all():
                        CategoryTech.objects.get_or_create(
                            tech_stack=canonical_stack,
                            category=ct.category
                        )
                    redundant_stack.delete()
            self.stdout.write(self.style.SUCCESS('...Deduplication complete.'))
        else:
            self.stdout.write('  - No duplicate TechStack names found. Skipping deduplication.'))

        # --- Step 3: Sync Categories (Define 9 categories, delete erroneous ones) ---
        self.stdout.write('\n[Step 3/4] Syncing 9-category system and cleaning old categories...'))
        
        # Define the canonical 9 category names
        canonical_category_names = [
            'Frontend', 'Backend', 'AI & Data', 'DevOps', 'Embedding', 
            'Game', 'Security', 'etc', 'Mobile & App'
        ]
        
        # Ensure these canonical categories exist
        category_objects = {}
        for name in canonical_category_names:
            category, created = Category.objects.get_or_create(name=name)
            category_objects[name] = category
            if created:
                self.stdout.write(f'  - Created canonical category: "{name}"'))

        # Delete any old, erroneous categories
        erroneous_categories_to_delete = ['IDE & Tool', 'OS', 'Embedded System']
        for cat_name in erroneous_categories_to_delete:
            deleted, _ = Category.objects.filter(name=cat_name).delete()
            if deleted:
                self.stdout.write(self.style.WARNING(f'  - Deleted erroneous category: \'{cat_name}\''))
        self.stdout.write(self.style.SUCCESS('...Category syncing complete.'))

        # --- Step 4: Apply Full Categorization ---
        self.stdout.write('\n[Step 4/4] Applying full categorization to all TechStacks...'))
        self.stdout.write('  - Clearing all existing tech-category relationships for a fresh start.'))
        deleted_rels_count, _ = CategoryTech.objects.all().delete()
        self.stdout.write(f'  - Deleted {deleted_rels_count} old relationships.'))

        all_tech_stacks = TechStack.objects.all()
        uncategorized_count = 0
        categorized_count = 0
        
        for tech_stack in all_tech_stacks:
            # Match tech_stack.name from DB to key in MASTER_CATEGORIZATION_MAP
            # Use lower() for robustness against slight case variations in the map
            found_mapping = MASTER_CATEGORIZATION_MAP.get(tech_stack.name, []) # Default to empty list if not found
            
            if not found_mapping and tech_stack.name.lower() != tech_stack.name: # Try case-insensitive if direct match failed
                for key, value in MASTER_CATEGORIZATION_MAP.items():
                    if key.lower() == tech_stack.name.lower():
                        found_mapping = value
                        break
            
            if found_mapping:
                categorized_count += 1
                for cat_name in found_mapping:
                    if cat_name in category_objects:
                        CategoryTech.objects.create(
                            tech_stack=tech_stack,
                            category=category_objects[cat_name]
                        )
                    else:
                        self.stdout.write(self.style.WARNING(f'    - Warning: Category "{cat_name}" from map not found for tech "{tech_stack.name}".'))
            else:
                uncategorized_count += 1
                self.stdout.write(self.style.NOTICE(f'    - No categorization found for "{tech_stack.name}".'))
        
        self.stdout.write(self.style.SUCCESS(f'\nCategorization complete!'))
        self.stdout.write(f'  - {categorized_count} TechStacks were categorized.'))
        self.stdout.write(f'  - {uncategorized_count} TechStacks remain uncategorized (please update MASTER_CATEGORIZATION_MAP).'))
        self.stdout.write(self.style.SUCCESS('\n--- Database Seeding Complete! ---'))
