# Unified Resource Hub

Kubernetes와 Prometheus에서 클러스터·노드·Pod·워크로드·서비스·스토리지·GPU 상태를 조회하는 읽기 전용 모니터링 도구입니다. 자원 생성·변경·해지 API는 포함하지 않습니다.

| 구성 | 시작점 |
| --- | --- |
| 모니터링 API | [설정 및 실행](backend/USAGE.md) |
| NVIDIA GPU 수집기 (선택) | [빌드·실행](exporter/README.md) · [제3자 고지](exporter/NOTICE) |
| 클러스터 요약 화면 | [화면 사용법](ui/README.md) · 서버 시작 후 `/ui/` |

운영자가 제공한 읽기 전용 접근 권한과 메트릭 수집기가 필요합니다. API는 인증 계층을 내장하지 않으므로 로컬에서 실행하거나 인증된 게이트웨이 뒤에 두세요. 수집되지 않은 지표는 실제 사용량 0으로 단정할 수 없습니다.
