## Terraform Sidecar FastAPI

이 프로젝트는 Terraform 프로젝트들을 REST API로 관리하기 위한 FastAPI 기반 사이드카 컨테이너이다. 
Airflow 등 외부 워크플로우가 Terraform 작업을 직접 실행하는 대신 본 API에 apply/destroy를 요청해 노드를 생성/삭제하도록 설계되었다.

### 핵심 기능
- `/tfpjts` : Terraform 프로젝트 목록 및 상태 조회
- `/tfpjts/{id}` : 단일 프로젝트 상태 조회
- `/tfpjts/{id}` `POST` : `apply` 실행 (변수 전달 가능)
- `/tfpjts/{id}` `DELETE` : `destroy` 실행
- `/tfpjts/{id}/git` : Git 저장소를 프로젝트로 클론
- 파일 기반 락(`tf_lock_{id}.json`)으로 동시 실행 차단, TTL 기반 자동 정리 및 409 응답 시 메타데이터 반환
- 컨테이너 기동 시 1회 `terraform init` 실행 (`SIDECAR_STARTUP_INIT_ENABLED`로 제어)

### 설정 값
모든 설정은 `SIDECAR_` 프리픽스 환경변수로 재정의 가능하다.
- `SIDECAR_TERRAFORM_ROOT` (기본 `/tfpjts`)
- `SIDECAR_LOCK_DIR` (기본 `/tmp/tf_locks`)
- `SIDECAR_TERRAFORM_BIN` (기본 `terraform`)
- `SIDECAR_LOCK_TTL_SECONDS` (기본 `3600`)
- `SIDECAR_GIT_CLONE_DEPTH`
- `SIDECAR_STARTUP_INIT_ENABLED`

### 로컬 개발
```
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
`./tfpjts` 디렉터리를 만들어 Terraform 프로젝트를 넣어 두면 된다.

### Docker 빌드 & 실행
```
docker build -t terraform-sidecar:latest .
docker compose up --build
```
`docker-compose.yml`은 `./tfpjts`를 컨테이너 `/tfpjts`로 마운트한다. Terraform 프로젝트는 호스트 `tfpjts` 폴더에 배치한다.

### 기본 테스트 플로우
1. `GET /tfpjts` : 프로젝트 목록 확인
2. `POST /tfpjts/{project_id}/git` : Git 저장소 클론 → 자동 init
3. 필요 시 `POST /tfpjts/{project_id}`로 apply, `DELETE`로 destroy

현재 우선적으로 `GET /tfpjts`와 `POST /tfpjts/{project_id}/git`만 수동 테스트 중이며, 향후 자동화 테스트와 나머지 엔드포인트 검증이 필요하다.

### TODO & 향후 작업
- [ ] apply/destroy 엔드포인트 통합 테스트
- [ ] Airflow DAG에서 호출하는 예시 스크립트 작성
- [ ] 인증/권한(예: API Key) 추가 고려
- [ ] 로그/모니터링 연동

