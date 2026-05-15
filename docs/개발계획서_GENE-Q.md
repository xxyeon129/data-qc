# GENE-Q 멀티오믹스 데이터 품질 관리 시스템 — 개발 계획서

| 항목 | 내용 |
|------|------|
| 시스템 명칭 | GENE-Q |
| 문서 유형 | 개발 계획서 |
| 버전 | 1.5 |
| 기준 코드베이스 | `frontend/`, `backend/` (본 저장소) |
| 관련 문서 | `docs/기능설계서_GENE-Q.md`, `docs/GENE-QC_지표설계_명세서_v2.md` |
| 작성 기준일 | 2026-04-17 |

---

## 목차

1. [문서 목적 및 적용 범위](#1-문서-목적-및-적용-범위)
2. [용어 정의](#2-용어-정의)
3. [개발 배경 및 목표](#3-개발-배경-및-목표)
4. [개발 범위](#4-개발-범위)
5. [시스템 구조](#5-시스템-구조)
6. [데이터베이스 모델](#6-데이터베이스-모델)
7. [개발 환경 및 전제 조건](#7-개발-환경-및-전제-조건)
8. [개발 단계 및 절차](#8-개발-단계-및-절차)
9. [단계별 주요 산출물](#9-단계별-주요-산출물)
10. [품질 및 위험 관리](#10-품질-및-위험-관리)
11. [기술 스택](#11-기술-스택)
12. [관련 문서](#12-관련-문서)
13. [부록 — 백엔드 HTTP API 일람](#13-부록--백엔드-http-api-일람)
14. [변경 이력](#14-변경-이력)

---

## 1. 문서 목적 및 적용 범위

### 1.1 목적

본 문서는 **GENE-Q**의 개발을 **단계·범위·산출물·품질 관점**에서 정리한 **개발 계획서**입니다. 멀티오믹스 파일에 대한 **결측 분석**, **규칙·지표 기반 품질 검증**, **통계·AI 기반 결측 보간**을 하나의 웹 플랫폼에서 구현하기 위한 **기술적 개발 절차**와 **모듈 단위의 개발 순서**를 기술하였습니다. 구현 내용과 대응되는 형태로 서술하였습니다.

### 1.2 적용 범위

- **포함**: 본 저장소에 반영된 백엔드(FastAPI)·프론트엔드(React)·비동기 작업·DB 모델·원격 ML 연동에 대한 개발 범위 및 단계적 구성입니다.
- **제외**: 타 시스템의 상세 설계, 상업적 일정·인력 산정·단가, 인프라·네트워크 보안 감사 전문 영역입니다.

### 1.3 문서와 구현의 관계

아래 **개발 단계(제8장)**는 실제 코드베이스의 모듈 구조·API·서비스 계층과 **대응**되도록 구성하였습니다. 본 문서는 계획서 형식의 기술 정리이며, **현재 저장소 상태를 완료된 개발 산출물로 간주**할 때 각 단계의 목표가 달성된 것으로 읽을 수 있습니다.

---

## 2. 용어 정의

| 용어 | 설명 |
|------|------|
| 오믹스(Omics) | 유전체(Genomics)·전사체(Transcriptomics)·메틸화(Methylation)·단백질체(Proteomics) 등 고차원 생물학 데이터 |
| 결측치(Missing Value) | 수집되지 않거나 측정 실패로 빈 값(NaN)으로 남겨진 데이터 셀 |
| 보간(Imputation) | 결측값을 통계·머신러닝으로 추정해 채우는 과정 |
| MOCHI | 멀티오믹스 특성을 반영한 AI 기반 보간 모델 (원격 ML 서버 연동) |
| Verification | 구조·형식 수준의 사실 확인 검사 (헤더, 타입, ID 중복 등) — `/api/verification` |
| Validation | 의미·기준 수준의 품질 검사 (결측률 임계값, 값 범위, 교차 정합성 등) — `/api/validation` |
| Completeness | 전체 셀 중 결측이 없는 비율 (`100 - nan_percentage`) |
| Plausibility | 값이 기대 범위·분포 내에 있는지 확인하는 품질 차원 |
| Conformance | 형식·규약·ID 일관성 등 적합성을 확인하는 품질 차원 |
| job_id | 비동기 작업의 고유 식별자 (UUID) |
| FSD | Feature-Sliced Design — 프론트엔드 아키텍처 방법론 |

---

## 3. 개발 배경 및 목표

### 3.1 배경

DNA·RNA·Methyl·Protein 및 임상 메타데이터는 **파일(TSV/CSV/Excel/JSON 등)** 형태로 제공되는 경우가 많습니다. 다음과 같은 품질 이슈가 공통적으로 발생하며, 이를 **프로젝트 단위**로 수집·분석·검증·보간하는 **일관된 워크플로**가 필요합니다.

| 이슈 유형 | 예시 |
|-----------|------|
| 결측 | NaN 값, 부분 측정 실패 |
| 샘플 ID 불일치 | 오믹스 파일 간 샘플 집합 불일치 |
| 값 범위 이상 | 음수 발현값, 연령 0 미만 등 |
| 형식 오류 | 구분자 불일치, 날짜 형식 혼용 |
| 배치 효과 | 실험 배치 간 체계적 편향 |

### 3.2 개발 목표

| 목표 ID | 내용 |
|---------|------|
| G-1 | 프로젝트·파일 단위로 원시 데이터를 업로드·관리하고, 이후 분석 파이프라인의 입력으로 사용할 수 있을 것 |
| G-2 | 결측 요약·분포 등 **결측 현황**을 산출·조회할 수 있을 것 |
| G-3 | 운영 정책에 따른 **검증 규칙(Verification)** CRUD 및 대시보드·상태 조회를 지원할 것 |
| G-4 | **다차원 품질 지표(Validation)** 실행, 보고서 다운로드를 지원할 것 |
| G-5 | Mean·KNN·**MOCHI** 등 보간 방법과 **멀티오믹스 일괄 보간**을 지원하고, 장시간 작업은 **비동기(job_id)** 로 처리할 것 |
| G-6 | GPU·대규모 모델이 분리된 환경을 위해 **SSH(Jump Host 경유) 기반 원격 ML** 연동을 제공할 것 |
| G-7 | 웹 UI로 대시보드·데이터셋·규칙·검증·관리·결과를 제공하고, API 서버·MySQL·파일 저장소와 연동할 것 |

---

## 4. 개발 범위

### 4.1 기능 범위

| 영역 | 주요 구현 |
|------|-----------|
| 프로젝트·데이터 관리 | REST API: `/api/projects`, `/api/data` — CRUD, multipart 업로드, `uploads/project_*/raw` 연계 |
| 대시보드 | `/api/dashboard/stats` — 활성 프로젝트·품질 점수·검증·결측률 집계, 프론트 트렌드 차트 |
| 결측 분석 | `/api/missing-value/*` — 프로젝트별 요약·분포, `MissingValuePage` 3단 레이아웃 |
| 검증 규칙 (Verification) | `/api/verification/*` — 대시보드 카드·상태·규칙 CRUD, 전역/프로젝트별 규칙 구분 |
| 데이터 검증 (Validation) | `/api/validation/*` — 28개 품질 지표 비동기 실행·상태·프로젝트 규칙·보고서 다운로드 |
| 결측 보간 (Imputation) | `/api/imputation/*` — 방법 목록, 단일·멀티오믹스 실행, 상태·결과·오믹스별 다운로드 |
| 원격 ML 연동 | SSH 연결 테스트·모델 목록, MOCHI 파이프라인 |
| 프론트엔드 | React 19·TypeScript·Vite, FSD 레이어, 6개 라우트 페이지 |

### 4.2 비기능 범위

- **비동기 처리**: 검증·보간 등 장시간 작업은 FastAPI `BackgroundTasks` 및 `job_id` 폴링 패턴을 사용합니다.
- **저장**: MySQL 8.0(메타데이터), 로컬 파일 시스템(원시·보간 결과)입니다.
- **연동**: CORS 허용 Origin 구성, `GET /health` 헬스체크, Paramiko 기반 SSH 터널입니다.

### 4.3 개발 제외·한계

- 작업 상태 및 검증 파라미터(`validation rules`)의 **인메모리 보관**은 운영 확장 시 Redis·DB 영속화로 교체가 필요합니다.
- 사용자 **인증·인가** 기능은 현재 구현 범위에 포함되지 않습니다.
- 파일 처리는 **TSV·CSV** 파싱 기준이며, Excel·JSON 등은 업로드만 수신하고 분석 대상에서 제한될 수 있습니다.
- `validation_service.py`의 `run_validation` 및 `check_*` 함수들은 현재 라우트에서 호출되지 않습니다. `validation.py` 라우트는 파일 내부에 `_evaluate_gene_qc_rules`를 인라인으로 구현하여 사용하며, `validation_service.py`는 별도 리팩터링 대상으로 남아 있습니다.
- `imputation_service.py`의 `mean`·`knn`·`mice` 보간 메서드는 파일 경로를 `/home/humandeep/data-qc/uploads`로 하드코딩하고 있어, 해당 경로가 없는 환경에서는 실제 연산이 동작하지 않습니다. `_load_project_data` 메서드는 `NotImplementedError`를 raise하도록 구현되어 있어 현재 사용 불가 상태입니다.
- `multiomics_imputation_service.py`의 로컬 PyTorch 기반 `MultiOmicsImputationService`는 라우트에서 import되지 않으며, `/execute-multiomics`는 SSH 기반 `RemoteMultiOmicsImputationService`만 사용합니다.

---

## 5. 시스템 구조

### 5.1 전체 논리 구성

```
┌─────────────────────────────────────────────────────────┐
│              웹 클라이언트 (frontend)                     │
│  Dashboard / Dataset / Rules / Validation /              │
│  Management / Results / MissingValue                     │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP REST (axios)
┌───────────────────────▼─────────────────────────────────┐
│                  API 서버 (FastAPI)                       │
│  /api/projects   /api/data   /api/dashboard              │
│  /api/missing-value   /api/verification                  │
│  /api/validation      /api/imputation                    │
└──────┬──────────────────────────────────┬───────────────┘
       │ SQLAlchemy ORM                   │ 파일 I/O
┌──────▼──────────┐            ┌──────────▼─────────────┐
│   MySQL 8.0     │            │  파일 시스템              │
│ - projects      │            │  uploads/project_{id}/  │
│ - data_files    │            │    raw/  (원시 TSV/CSV) │
│ - missing_values│            │    imputed/ (보간 결과)  │
│ - verification_ │            └────────────────────────┘
│   rules/status  │
│ - imputation_   │            ┌────────────────────────┐
│   jobs          │            │   원격 ML 서버 (SSH)    │
└─────────────────┘            │   Jump Host → Final    │
                               │   MOCHI 모델 실행       │
                               └────────────────────────┘
```

### 5.2 사용자 워크플로

사용자는 다음 6단계의 선형 워크플로를 통해 데이터 품질 관리를 수행합니다.

```
1. 프로젝트 생성  (/dataset)
        ↓
2. 오믹스 파일 업로드  (/dataset)
        ↓
3. 결측 현황 확인  (/results)
        ↓
4. 품질 지표 임계값 설정  (/rules)
        ↓
5. 검증 실행 → 차원별 결과 확인  (/validation)
        ↓
6. 보간 실행 → 결과 파일 다운로드  (/management)
```

### 5.3 프론트엔드 라우팅 및 페이지 구성

| 경로 | 페이지 컴포넌트 | 네비게이션 레이블 | 기능 역할 |
|------|----------------|-----------------|-----------|
| `/` | `DashboardPage` | 메인 | 통계 카드·프로젝트 미리보기·품질 트렌드 차트 |
| `/dataset` | `DatasetPage` | 데이터셋 | 프로젝트·파일 생성·관리·삭제 |
| `/rules` | `RulesPage` | 검증규칙 | 기초·심화 품질 지표 임계값 설정 |
| `/validation` | `ValidationPage` | 품질검증 | 검증 실행·차원별 결과·진행 상태 |
| `/management` | `ManagementPage` | 품질관리 | 보간 전략·실행·미리보기 |
| `/results` | `ResultsPage` | 검증결과 | 처리 타임라인·품질 메트릭 조회 |

> `MissingValuePage`(`pages/missingvalue/`)와 `VerificationPage`(`pages/verification/`)는 컴포넌트로 구현되어 있으나, 현재 `AppRouter`에 라우트로 등록되지 않아 직접 접근할 수 없습니다.

> `ResultsPage`(`/results`)는 기존 검증 결과를 조회하는 전용 API가 없으며, `selectedProjectId`가 설정될 때마다 `executeValidation` → `getValidationStatus` 폴링을 **재실행**하는 방식으로 동작합니다. 결과 조회 전용 엔드포인트 분리가 후속 과제로 남아 있습니다.

### 5.4 프론트엔드 아키텍처 (FSD)

Feature-Sliced Design(FSD) 방법론을 적용하였으며, 레이어 간 의존성은 단방향(app → pages → widgets → entities → shared)입니다.

```
src/
├── app/            # 앱 진입점, 전역 레이아웃(AppLayout), 라우터(AppRouter), 전역 스타일
├── pages/          # 페이지 단위 기능 모듈
│   ├── dashboard/      # 라우트 등록 (/): DashboardPage
│   ├── dataset/        # 라우트 등록 (/dataset): DatasetPage
│   ├── rules/          # 라우트 등록 (/rules): RulesPage
│   ├── validation/     # 라우트 등록 (/validation): ValidationPage
│   ├── management/     # 라우트 등록 (/management): ManagementPage
│   ├── results/        # 라우트 등록 (/results): ResultsPage
│   ├── missingvalue/   # 미등록: MissingValuePage (AppRouter에 없음)
│   ├── verification/   # 미등록: VerificationPage (AppRouter에 없음)
│   └── error/          # NotFoundErrorPage (errorElement로 사용)
├── widgets/        # 재사용 가능한 공통 위젯 (PageHeader, CardTitle 등)
├── entities/       # 도메인 모델 & 타입 (Project 타입 등)
└── shared/
    ├── api/        # axios 클라이언트 (client.ts)
    ├── router/     # 경로 상수 (path.const.ts)
    ├── files/      # 파일 업로드 공통 컴포넌트
    └── styles/     # 공통 스타일·테마
```

> **FSD 준수 현황**: 폴더 구조는 규약을 따르고 있으나, 일부 코드에서 엄격한 단방향 의존성이 지켜지지 않습니다. `pages/dashboard/consts/dashboard.const.ts`의 상수를 다른 페이지 컴포넌트(`ProjectList`)가 import하는 **pages → pages 교차 의존**이 존재하며, 여러 페이지에서 `entities/projects`의 `Project` 타입 대신 인라인 인터페이스를 재정의하고 있습니다. `AppNav.tsx`는 구현되어 있으나 `AppLayout`에서 import되지 않아 미사용 상태입니다.

### 5.5 비동기 작업 패턴

검증·보간 등 장시간 작업은 서버 측에서 `BackgroundTasks`로 비동기 처리하며, 클라이언트는 `job_id`로 상태를 폴링합니다.

**서버 패턴**
```python
@router.post("/execute")
async def execute(project_id: int, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_run_task, job_id=job_id, project_id=project_id)
    return {"jobId": job_id, "status": "processing", "estimatedTime": 30}
```

**클라이언트 폴링 흐름**
```
실행 요청 → jobId 수신
  └── 폴링 루프
       ├── 주기적 대기 (검증: 1초 / 보간: 2초)
       ├── GET /status/{jobId}
       ├── status == "completed" → 결과 표시, 루프 종료
       ├── status == "failed"    → 오류 표시, 루프 종료
       └── 최대 횟수 초과         → 타임아웃 오류 표시
```

> 작업 상태는 현재 구현상 서비스 내 **메모리 딕셔너리**에 저장됩니다. 운영 환경에서는 Redis 또는 DB 영속화 방식으로 확장이 권장됩니다.

---

## 6. 데이터베이스 모델

MySQL 8.0에 SQLAlchemy ORM으로 관리되는 주요 테이블 구성입니다.

### 6.1 projects

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer PK | 프로젝트 식별자 |
| `name` | String(255) | 프로젝트명 |
| `description` | Text | 설명 |
| `data_type` | JSON | 오믹스 유형 목록 (예: `["전사체","대사체"]`) |
| `quality_score` | Float | 전체 품질 점수 (0~100) |
| `validation_status` | String | `작성중` / `처리중` / `검증완료` |
| `status` | String | `활성` / `비활성` / `완료` |
| `last_update` | String(100) | 마지막 갱신 표시 문자열 (예: `방금 전`) |
| `sample_count` | Integer | 샘플 수 |
| `dna_quality_score` | Float | DNA 오믹스 품질 점수 |
| `rna_quality_score` | Float | RNA 오믹스 품질 점수 |
| `methyl_quality_score` | Float | Methyl 오믹스 품질 점수 |
| `protein_quality_score` | Float | Protein 오믹스 품질 점수 |
| `sample_accuracy` | Float | 샘플 정확도 |
| `created_at` / `updated_at` | DateTime | 생성·수정 일시 |

> `data_files`, `missing_values`, `verification_rules`와 1:N 관계이며, 프로젝트 삭제 시 cascade 삭제가 적용됩니다.

### 6.2 data_files

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer PK | 파일 식별자 |
| `project_id` | Integer FK | 연결 프로젝트 |
| `name` | String(255) | 파일명 |
| `size` | String | 표시용 크기 (예: `1.2 GB`) |
| `file_path` | String(500) | 실제 저장 경로 (`uploads/project_{id}/raw/`) |
| `created_at` | DateTime | 업로드 일시 |

### 6.3 missing_values

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer PK | 분석 레코드 식별자 |
| `project_id` | Integer FK | 연결 프로젝트 |
| `total_missing_rate` | Float | 전체 결측률 (%) |
| `missing_sample_count` | Integer | 결측이 있는 샘플(행) 수 |
| `missing_gene_count` | Integer | 결측이 있는 유전자/feature(열) 수 |
| `total_cells` | Integer | 전체 셀(행×열) 수 |
| `distribution_data` | JSON | 결측률 구간별 분포 |
| `created_at` | DateTime | 생성 일시 |
| `updated_at` | DateTime | 최근 갱신 일시 |

### 6.4 verification_rules

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer PK | 규칙 식별자 |
| `project_id` | Integer FK (nullable) | NULL이면 전역(global) 규칙 |
| `label` | String(255) | 규칙 이름 |
| `status` | String | `active` / `inactive` |
| `category` | String | 분류 (정렬성, 정밀성, 완전성 등) |
| `metric` | String | 평가 메트릭명 (예: `read_mapping`) |
| `condition` | String | 비교 연산자 (`>=`, `<=`) |
| `threshold` | Integer | 기준값 |

### 6.5 verification_status

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer PK | 레코드 식별자 |
| `project_id` | Integer FK | 연결 프로젝트 |
| `label` | String(100) | 항목 레이블 (예: `정렬성`, `정밀성`) |
| `score` | Integer | 실제 측정 점수 |
| `standard` | Integer | 기준값 |
| `created_at` / `updated_at` | DateTime | 생성·수정 일시 |

### 6.6 imputation_jobs

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer PK | DB 기본 키 |
| `job_id` | String(100) UK | UUID 기반 작업 식별자 |
| `project_id` | Integer FK | 연결 프로젝트 |
| `method` | String | 보간 방법 (`mochi`, `knn`, `mean` 등) |
| `threshold` | Float | 보간 임계 결측률 (%) |
| `quality_threshold` | Float | 보간 후 최소 품질 점수 (%) |
| `options` | JSON | 추가 옵션 |
| `status` | String | `processing` / `completed` / `failed` |
| `progress` | Float | 진행률 (0.0~100.0) |
| `imputed_samples` | Integer | 보간된 샘플 수 |
| `imputed_features` | Integer | 보간된 feature 수 |
| `quality_score` | Float | 보간 후 품질 점수 |
| `output_file` | String | 결과 파일 경로 |
| `error_message` | Text | 실패 시 오류 메시지 |
| `completed_at` | DateTime | 완료 일시 |

> `imputation_jobs` 테이블은 스키마에 정의되어 있으나, 현재 HTTP 핸들러(`/api/imputation`)는 이 테이블을 직접 사용하지 않고 **서비스 인메모리 딕셔너리**로 작업 상태를 관리합니다.

---

## 7. 개발 환경 및 전제 조건

### 7.1 공통 전제 조건

| 항목 | 요건 |
|------|------|
| OS | macOS / Linux |
| MySQL | 8.0 이상 |
| 네트워크 | 원격 ML 서버 SSH 접근 가능 (운영 환경 시) |

### 7.2 백엔드 환경

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.10 이상 |
| 패키지 관리 | `pip` + `venv` |
| 주요 의존성 | FastAPI, Uvicorn, SQLAlchemy, PyMySQL, Pandas, NumPy, scikit-learn, SciPy, PyTorch, Paramiko |
| 설정 파일 | `backend/.env` (`.env.example` 참조) |
| 실행 | `python main.py` 또는 `./start.sh` |

**필수 환경 변수 (`backend/.env`)**

```
MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
ML_SERVER_JUMP_HOST, ML_SERVER_JUMP_PORT, ML_SERVER_JUMP_USER, ML_SERVER_JUMP_PASSWORD
ML_SERVER_FINAL_HOST, ML_SERVER_FINAL_USER, ML_SERVER_FINAL_PASSWORD
ML_MODEL_PATH
```

### 7.3 프론트엔드 환경

| 항목 | 내용 |
|------|------|
| 언어 | TypeScript 5.x |
| 런타임 | Node.js 18 이상 |
| 패키지 관리 | Yarn |
| 빌드 도구 | Vite |
| 실행 | `yarn start` (개발 서버 포트: 3000) |

---

## 8. 개발 단계 및 절차

개발은 **의존 관계가 낮은 기반층 → 데이터 입출력 → 분석·검증 → 보간·외부 연동 → UI 통합** 순으로 진행하는 것을 원칙으로 합니다.

### 8.1 1단계: 기반 인프라·API 골격

**목표**: 전체 백엔드·프론트엔드의 기술적 기반을 확립합니다.

- FastAPI 앱 진입점(`main.py`) 구성, CORS 허용 Origin 설정, 라우터 모듈 등록, `/health` 엔드포인트 추가.
- SQLAlchemy·MySQL 연결 설정, DB 세션 관리, 프로젝트·파일 등 **핵심 도메인 모델** 초기화.
- Pydantic v2 기반 요청·응답 스키마 정의.
- Vite·React 19·TypeScript 프로젝트 초기화, FSD 레이어 디렉터리 구조 확립.
- axios 공통 클라이언트(`shared/api/client.ts`), 경로 상수(`shared/router/path.const.ts`) 설정.
- **핵심 기술 결정**: 라우터 모듈 단위 분리 전략 수립 (projects, data, missing-value, verification, validation, imputation, dashboard).
- **산출**: 단일 API 서버·프론트엔드 개발 서버 실행 가능한 골격.

### 8.2 2단계: 프로젝트·데이터 파일 관리

**목표**: 모든 후속 분석의 공통 입력 경로를 확보합니다.

- 프로젝트 CRUD (`GET/POST/PUT/PATCH/DELETE /api/projects`), CSV 기반 메타 일괄 등록.
- `multipart/form-data` 파일 업로드 → `uploads/project_{id}/raw/{filename}` 저장 규약 정의.
- 파일 크기 단위 자동 변환(`_compute_total_size`), 프로젝트 삭제 시 파일·DB 레코드 cascade 처리.
- 프론트엔드 `DatasetPage`: 프로젝트 카드·파일 목록·생성·수정·삭제 모달 구현.
- **산출**: 후속 결측 분석·검증·보간의 공통 데이터 경로 확보.

### 8.3 3단계: 결측 분석·대시보드

**목표**: 데이터 품질 현황의 수치화 및 시각화 기반을 제공합니다.

- 결측 API: 프로젝트 목록, 요약 통계(전체 결측률·결측 샘플 수·결측 feature 수), 구간별 분포 집계.
- `missing_values` 테이블 갱신 로직 — Pandas를 이용한 NaN 카운트·비율 산출.
- 대시보드 통계 API (`/api/dashboard/stats`): 활성 프로젝트 수·평균 품질 점수·처리된 데이터셋 수·평균 결측률 집계.
- 프론트엔드 `DashboardPage`: 통계 카드 4개, 프로젝트 미리보기 카드 그리드, chart.js 기반 품질 트렌드 차트.
- 프론트엔드 `MissingValuePage`: 좌측(프로젝트 선택·보간 설정) / 우측(요약 카드 3종·분포 차트) 3단 레이아웃. 단, 현재 라우터에 등록되지 않아 별도 진입점이 없습니다.
- **산출**: 운영 현황 파악 및 결측 시각화·의사결정 근거.

> **현재 구현 한계**: `DashboardPage` 내 `ProjectList`·`DataManage`·`StatisticsList` 서브컴포넌트는 `DASHBOARD_PROJECTS`, `UPLOADED_DATA` 등 고정값을 사용하며 실제 API와 연결되지 않습니다. `RecentActivity` 컴포넌트는 API를 호출하도록 구현되어 있으나 `DashboardPage.tsx`에서 렌더링되지 않습니다.

### 8.4 4단계: 검증 규칙 관리 (Verification)

**목표**: 운영 정책 기반 품질 기준의 구성 관리 층을 구현합니다.

- 검증 규칙 CRUD (`GET/POST/PUT/DELETE /api/verification/rules`): 라벨·카테고리·메트릭·조건·임계값 저장.
- 전역(project_id=NULL) vs 프로젝트별 규칙 구분 처리.
- 검증 대시보드 카드 API: 총 샘플 수·통과율·경고 수·활성 규칙 수 집계.
- 검증 상태 목록 API: 라벨·실제 점수·기준값 비교.
- 프론트엔드 `RulesPage`: 기초 품질 지표(탭 1)·심화 품질 지표(탭 2) 구성, 오믹스별 결측 임계값 슬라이더.
- **산출**: 정책 기반 품질 기준 구성 관리 층.

> **현재 구현 한계**: `GET /api/verification/dashboard`는 `project_id`가 없는 경우 `"89.3%"`, `"49"` 등 더미 문자열을 반환합니다. 실제 DB 집계 연산으로 교체가 필요합니다. 

### 8.5 5단계: GENE-QC 데이터 검증 (Validation)

**목표**: 표준화된 다차원 품질 지표 엔진과 검증 보고서 생성을 구현합니다.

- `validation.py` 라우트 핸들러 내 GENE-QC 규칙 평가 로직(`_evaluate_gene_qc_rules`)으로 **28개 품질 지표** 실행.
  - **Completeness**: 헤더 존재, 컬럼·행 결측, 데이터셋 간 샘플 매칭, 메타데이터 연결성 등.
  - **Plausibility**: 값 범위, IQR 이상치, 성별·연령, 교차 상관, 배치 효과 등.
  - **Conformance**: 구분자 일관성, ID 중복·형식, 데이터 타입, 날짜 형식, 데이터셋 간 ID 일관성 등.
- 각 지표는 `metricId`(예: `comp_C002`, `conf_F001`), **심각도**(5단계), **기초/심화** 레벨로 관리.
- 비동기 실행 (`POST /api/validation/execute`) → `job_id` 반환 → 상태 폴링 (`GET /api/validation/status/{job_id}`).
- 프로젝트별 임계·옵션 저장/조회 (`POST/GET /api/validation/rules/{project_id}`). 단, 파라미터는 **DB가 아닌 서비스 인메모리 딕셔너리**에 저장됩니다.
- 검증 보고서 파일 응답 (`GET /api/validation/download-report/{project_id}`).
- 프론트엔드 `ValidationPage`: 진행 단계 스텝퍼, 차원별 결과 카드, 상세 결과 테이블.
- **산출**: 표준화된 지표 기반 품질 평가 및 다운로드 가능한 검증 보고서.

> **현재 구현 한계**: `validation_service.py`의 `run_validation` 및 `check_*` 함수들은 `validation.py` 라우트에서 import되지 않으며, 라우트는 내부에 `_evaluate_gene_qc_rules`를 인라인으로 구현하여 사용합니다. `validation_service.py`는 현재  호출되지 않는 데드 코드 상태로, 향후 서비스 계층으로 리팩터링이 필요합니다. 또한 Plausibility 지표 중 `plau_X001`·`plau_X002`는 "AI 모듈" skip으로 스텁 처리되어 있으며(`validation_service_ai_stubs.md` 참조), 실제 AI 기반 이상치 판별 로직은 미구현 상태입니다.

### 8.6 6단계: 결측 보간·원격 ML 연동

**목표**: 다양한 보간 방법과 원격 AI 모델 연동을 통해 결측값을 채웁니다.

- 보간 방법 목록 API (`GET /api/imputation/methods`): MOCHI·Mean·KNN·MissForest·GAIN·VAE 방법별 설명·예상 정확도 반환. 단, MissForest·GAIN·VAE는 현재 스텁(stub) 구현 상태로 고정된 임시 수치를 반환하며, 실제 연산은 미구현입니다.
- 단일 오믹스 보간 파이프라인 (`POST /api/imputation/execute`): `project_id`, `method`, `threshold`, `quality_threshold`, `options` 수신 → 백그라운드 실행 → `uploads/project_{id}/imputed/` 저장.
- 멀티오믹스 일괄 보간 (`POST /api/imputation/execute-multiomics`): RNA·Protein·Methyl 복수 오믹스 동시 처리.
- 오믹스별 결과 파일 다운로드 (`GET /api/imputation/download/{job_id}/{omics_type}`).
- `MLModelClient` (Paramiko): Jump Host → Final ML 서버 SSH 터널, 연결 테스트·모델 목록·파일 전송·스크립트 실행.
- **산출**: 통계·딥러닝·전용(MOCHI) 방법 선택형 보간 및 확장 가능한 ML 배치 연동.

> **현재 구현 한계**: `imputation_service.py`의 `mean`·`knn`·`mice` 보간 메서드는 파일 경로를 `/home/humandeep/data-qc/uploads`로 하드코딩하고 있어 해당 경로가 없는 환경에서 실제 연산이 동작하지 않습니다. `_load_project_data` 메서드는 `NotImplementedError`를 raise하여 사용 불가 상태입니다. 로컬 PyTorch 기반 `MultiOmicsImputationService`(`multiomics_imputation_service.py`)는 구현되어 있으나 **라우트에서 import되지 않으며**, `/execute-multiomics`는 SSH 기반 `RemoteMultiOmicsImputationService`만 사용합니다. MICE 보간 메서드(`_mice_imputation`)는 코드에 구현되어 있으나 `/api/imputation/methods` 목록에 포함되지 않아 클라이언트에서 선택 불가 상태입니다.

### 8.7 7단계: 프론트엔드 통합

**목표**: 백엔드 API와 연동된 end-to-end 사용자 워크플로 화면을 완성합니다.

- `AppLayout` (네비게이션 바): 메인·데이터셋·검증규칙·품질검증·품질관리·검증결과 6개 메뉴 구성.
- `AppRouter`: React Router v7 기반 lazy loading 라우팅 설정.
- 각 페이지의 API 연계: 공통 axios 클라이언트 + Pydantic 응답 모델 기반 TypeScript 타입 매핑.
- 공통 컴포넌트 정리: `PageHeader`, `CardTitle`, 파일 업로드 공통 컴포넌트, 공통 스타일·테마.
- MUI v7 + Styled-Components v6 혼용 스타일 전략 확립.
- **산출**: end-to-end 사용자 워크플로에 대응하는 화면.

> **현재 구현 한계**: `ResultsPage`·`PreviewResults`·`InterpolateSetting` 등 일부 컴포넌트에서 API 호스트를 `http://localhost:8005/api/...`로 **하드코딩**하고 있어 `VITE_API_BASE_URL` 환경 변수를 우회합니다.

### 8.8 8단계: 운영·품질 정비

**목표**: 실제 운영 환경에서 재현 가능한 배포·운영 전제를 확립합니다.

- 환경 변수 기반 ML 서버·DB 설정, 배포 환경별 CORS Origin 반영.
- 에러 페이지(`NotFoundErrorPage`), 로딩·폴링 UX 정비, 보고서·다운로드 흐름 검증.
- 백엔드 초기화 스크립트(`init_database.py`, `recreate_tables.py`) 및 실행 스크립트(`start.sh`) 정비.
- **산출**: 재현 가능한 배포·운영 전제 명시.

---

## 9. 단계별 주요 산출물

| 단계 | 산출물 유형 |
|------|-------------|
| 1 | FastAPI 앱 골격, DB 연결, FSD 디렉터리 구조, axios 클라이언트 |
| 2 | 프로젝트·파일 CRUD API, `uploads/` 저장 경로 규약, `DatasetPage` |
| 3 | 결측 통계·분포 API, 대시보드 집계 API, `DashboardPage`, `MissingValuePage` |
| 4 | 검증 규칙 CRUD API, 대시보드 카드·상태 API, `RulesPage` |
| 5 | 28개 품질 지표 엔진, 검증 job 흐름, 보고서 파일 생성, `ValidationPage` |
| 6 | 보간 서비스·파이프라인, SSH ML 클라이언트, 멀티오믹스 보간, 다운로드 API |
| 7 | 6개 페이지 통합, 공통 레이아웃·컴포넌트·스타일 |
| 8 | 운영 설정, 에러 핸들링, 초기화·실행 스크립트 |

---

## 10. 품질 및 위험 관리

| 항목 | 내용 |
|------|------|
| 인터페이스 안정성 | Pydantic v2 기반 응답 모델로 API 입출력 계약을 명확히 합니다. |
| 장시간 작업 | `BackgroundTasks` + `job_id` 폴링으로 타임아웃을 회피하고 클라이언트에서 상태를 추적합니다. |
| 데이터 일관성 | 프로젝트 단위 디렉터리·메타데이터 cascade 삭제 정책을 유지합니다. |
| 외부 ML 의존 | SSH 연결 테스트 API를 제공하고, ML 서버 가용성을 사전 검증할 수 있도록 합니다. |
| 상태 영속성 | 작업 상태 인메모리 보관 → 운영 확장 시 Redis·DB 영속화 전환을 후속 과제로 관리합니다. |
| 인증 부재 | 현재 Auth 미구현 — 운영 환경에서는 네트워크 수준 접근 제어 또는 인증 계층 추가가 필요합니다. |

---

## 11. 기술 스택

| 층 | 기술 | 버전 |
|----|------|------|
| 클라이언트 | React | 19 |
| | TypeScript | 5.x |
| | Vite | v7 |
| | MUI (Material UI) | v7 |
| | Styled Components | v6 |
| | React Router | v7 |
| | axios | 최신 |
| | chart.js / react-chartjs-2 | 최신 |
|| react-icons | v5 |
| 서버 | FastAPI | 최신 |
| | Uvicorn | 최신 |
| | Pydantic | v2 |
| | SQLAlchemy | 최신 |
| | PyMySQL | 최신 |
| 분석·보간 | Pandas | 최신 |
| | NumPy | 최신 |
| | scikit-learn | 최신 |
| | SciPy | 최신 |
| | PyTorch | 최신 |
| 저장 | MySQL | 8.0 |
| 원격 | Paramiko (SSH) | 최신 |

---

## 12. 관련 문서

| 문서 | 위치 | 내용 |
|------|------|------|
| 기능 설계서 | `docs/기능설계서_GENE-Q_특허제출용.md` | 모듈 기능·API 상세·DB 스키마·비동기 패턴 |
| 품질 지표 명세 | `docs/GENE-QC_지표설계_명세서_v2.md` | 28개 품질 지표 정의·수식·매핑 테이블 |

동일 내용은 한 문서에만 상세히 두고, 타 문서와는 교차 참조로 중복을 줄입니다.

---

## 13. 부록 — 백엔드 HTTP API 일람

| Method | Path | 기능 |
|--------|------|------|
| GET | `/api/projects` | 프로젝트 목록 |
| GET | `/api/projects/{id}` | 프로젝트 단건 |
| POST | `/api/projects` | 프로젝트 생성 |
| PUT | `/api/projects/{id}` | 프로젝트 전체 수정 |
| PATCH | `/api/projects/{id}/name` | 프로젝트명 변경 |
| DELETE | `/api/projects/{id}` | 프로젝트 삭제 |
| POST | `/api/projects/upload-csv` | CSV 기반 프로젝트 메타 일괄 등록 |
| GET | `/api/data` | 데이터 파일 목록 (`?project_id=`) |
| GET | `/api/data/{file_id}` | 데이터 파일 단건 |
| POST | `/api/data/upload` | 파일 업로드 (multipart) |
| DELETE | `/api/data/{file_id}` | 파일 삭제 |
| GET | `/api/missing-value/projects` | 결측 분석 가능 프로젝트 목록 |
| GET | `/api/missing-value/summary/{project_id}` | 결측 종합 분석 |
| GET | `/api/missing-value/summary/{project_id}/summary` | 결측 요약 카드 데이터 |
| GET | `/api/missing-value/summary/{project_id}/distribution` | 결측 분포 구간 데이터 |
| GET | `/api/dashboard/stats` | 대시보드 통계 집계 |
| GET | `/api/verification/dashboard` | 검증 대시보드 카드 (`?project_id=`) |
| GET | `/api/verification/status` | 검증 항목별 점수 상태 (`?project_id=`) |
| GET | `/api/verification/rules` | 검증 규칙 목록 (`?project_id=`) |
| POST | `/api/verification/rules` | 검증 규칙 생성 |
| PUT | `/api/verification/rules/{rule_id}` | 검증 규칙 수정 |
| DELETE | `/api/verification/rules/{rule_id}` | 검증 규칙 삭제 |
| POST | `/api/validation/execute` | 품질 지표 검증 실행 (`?project_id=`) |
| GET | `/api/validation/status/{job_id}` | 검증 작업 상태 조회 |
| POST | `/api/validation/rules/{project_id}` | 검증 파라미터 저장 |
| GET | `/api/validation/rules/{project_id}` | 검증 파라미터 조회 |
| GET | `/api/validation/download-report/{project_id}` | 검증 보고서 다운로드 |
| GET | `/api/imputation/methods` | 지원 보간 방법 목록 |
| POST | `/api/imputation/execute` | 단일 오믹스 보간 실행 |
| GET | `/api/imputation/status/{job_id}` | 보간 작업 상태 조회 |
| GET | `/api/imputation/results/{job_id}` | 보간 결과 메타 조회 |
| GET | `/api/imputation/ml-model/connection-test` | ML 서버 SSH 연결 테스트 |
| GET | `/api/imputation/ml-model/list` | 원격 ML 모델 목록 조회 |
| POST | `/api/imputation/execute-multiomics` | 멀티오믹스 일괄 보간 실행 |
| GET | `/api/imputation/download/{job_id}/{omics_type}` | 오믹스별 보간 결과 파일 다운로드 |
| GET | `/health` | API 서버 헬스체크 |

---

## 14. 변경 이력

| 버전 | 일자 | 내용 |
|------|------|------|
| 1.0 | 2026-04-17 | 초안 작성 (코드베이스 기준 개발 계획서) |
| 1.1 | 2026-04-17 | 특허 관련 문구 삭제, 일반 개발 계획서 형식으로 정리, 존댓말 통일 |
| 1.2 | 2026-04-17 | 목차 추가, 용어 정의, 이슈 유형 표, 시스템 구조 다이어그램, 사용자 워크플로, 프론트엔드 라우팅 표, FSD 레이어 구조, 비동기 패턴 상세, DB 모델 6종, 개발 환경·전제 조건, 기술 스택 버전, API 부록 추가 |
| 1.3 | 2026-04-17 | 코드베이스 실제 구현과 불일치 항목 정정: MissingValuePage 미라우팅, MissForest·GAIN·VAE 스텁 구현, validation 규칙 인메모리 저장, imputation_jobs 테이블 미사용, validation_service.py HTTP 미연동 |
| 1.4 | 2026-04-17 | 코드베이스 재검토 후 추가 정정: VerificationPage 미라우팅 누락 추가, FSD pages 목록 보완(missingvalue·verification·error), projects 테이블 last_update 컬럼 누락 추가, missing_values 테이블 created_at 누락 추가, verification_status 테이블 신규 문서화(6.5절 추가, imputation_jobs → 6.6 재번호), 기술 스택 Vite v7 버전 명시 및 react-icons v5 추가 |
| 1.5 | 2026-04-17 | 코드베이스 심층 분석 기반 불일치 13건 추가 기재: §4.3 한계 항목 4건 신규 추가(validation_service.py 데드 코드·imputation 경로 하드코딩·multiomics 미사용·프론트엔드 localhost 하드코딩); §5.3 ResultsPage 재실행 동작 주석; §5.4 FSD 규칙 위반 주석; §8.3 대시보드 목 데이터·RecentActivity 미렌더링; §8.4 verification 대시보드 더미 응답·RulesPage 버튼 미연결; §8.5 validation_service.py 데드 코드·plau_X001/plau_X002 스텁; §8.6 imputation 경로 하드코딩·MICE 미노출·MultiOmicsImputationService 미사용; §8.7 AppNav 미사용·DataAnalysis 주석 처리·API 호스트 하드코딩 |

---

본 문서는 소프트웨어 구현 및 개발 절차에 기반한 기술 설명입니다.
