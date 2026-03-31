# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

**GENE-Q** - 멀티-오믹스 데이터 품질 관리(QC) 시스템.
DNA, RNA, Methyl, Protein 데이터의 결측치를 분석하고 AI 기반 보간(MOCHI 모델)을 실행하는 웹 기반 플랫폼.

- **프론트엔드**: `frontend/` — React 19 + TypeScript + Vite
- **백엔드**: `backend/` — FastAPI + SQLAlchemy + MySQL

## Common Commands

### 프론트엔드

```bash
cd frontend

yarn start          # 개발 서버 실행 (http://localhost:3000)
yarn build          # 프로덕션 빌드
yarn lint           # ESLint 검사
yarn format         # Prettier 포맷팅
yarn watch          # 타입 체크 (watch 모드)
```

### 백엔드

```bash
cd backend

source venv/bin/activate        # 가상환경 활성화 (Mac/Linux)
# 또는
venv\Scripts\activate           # 가상환경 활성화 (Windows)

python main.py                  # 백엔드 서버 실행 (http://localhost:8005)
# 또는
./start.sh                      # 백엔드 서버 실행 스크립트

python init_database.py         # 데이터베이스 초기화
python recreate_tables.py       # 테이블 재생성
```

## Architecture

### 전체 디렉토리 구조

```
gene/
├── frontend/               # React 19 프론트엔드
│   └── src/
│       ├── app/            # 앱 진입점, 레이아웃, 라우터, 전역 스타일
│       ├── pages/          # 페이지 컴포넌트 (FSD 아키텍처)
│       ├── entities/       # 도메인 모델 & 타입
│       ├── shared/         # 공유 유틸리티 (api, router, styles)
│       └── widgets/        # 재사용 가능한 공통 위젯
│
└── backend/                # FastAPI 백엔드
    ├── app/
    │   ├── api/routes/     # API 라우트
    │   ├── core/           # 핵심 설정 (config.py)
    │   ├── db/             # DB 세션, 초기화
    │   ├── models/         # SQLAlchemy 모델, Pydantic 스키마
    │   ├── services/       # 비즈니스 로직
    │   └── utils/
    ├── main.py             # FastAPI 앱 진입점
    ├── requirements.txt
    └── uploads/            # 업로드 파일 저장소 (project_*/raw, project_*/imputed)
```

### 프론트엔드 — Feature-Sliced Design (FSD)

FSD 아키텍처를 따릅니다. 레이어 간 단방향 의존성 (app → pages → widgets → entities → shared).

```
src/
├── app/
│   ├── App.tsx                 # 루트 컴포넌트
│   ├── main.tsx                # 진입점
│   ├── layout/                 # AppLayout, AppNav
│   ├── router/                 # AppRouter
│   └── styles/                 # 전역 스타일, reset.css
│
├── pages/
│   ├── dashboard/              # 대시보드
│   ├── dataset/                # 데이터셋 관리 (프로젝트 생성/파일 업로드)
│   ├── missingvalue/           # 결측치 분석
│   ├── verification/           # 검증 실행 & 검증 규칙
│   ├── validation/             # 검증 결과
│   ├── imputation/             # 데이터 보간
│   ├── management/             # 데이터 관리
│   ├── results/                # 결과 조회
│   ├── rules/                  # 품질 지표 규칙
│   └── error/                  # 404 에러 페이지
│
├── entities/
│   └── projects/               # Project 타입 정의
│
├── shared/
│   ├── api/                    # axios 클라이언트 (client.ts)
│   ├── router/                 # 라우트 경로 상수 (path.const.ts)
│   ├── files/                  # 공통 파일 업로드 컴포넌트
│   └── styles/                 # 공통 스타일, 테마
│
└── widgets/
    ├── header/                 # PageHeader
    └── title/                  # CardTitle
```

### 백엔드 — API 라우트

| 라우트 모듈 | 경로 prefix | 설명 |
|---|---|---|
| `projects.py` | `/api/projects` | 프로젝트 CRUD |
| `data.py` | `/api/data` | 파일 업로드 & 목록 |
| `missing_value.py` | `/api/missing-value` | 결측치 분석 |
| `verification.py` | `/api/verification` | 검증 실행 & 규칙 |
| `validation.py` | `/api/validation` | 검증 결과 |
| `imputation.py` | `/api/imputation` | 보간 실행 & 결과 |
| `dashboard.py` | `/api/dashboard` | 대시보드 통계 |

### 주요 기술 스택

**프론트엔드**
- React 19, TypeScript, Vite
- MUI v7, Styled Components v6
- React Router DOM v7, axios
- chart.js, react-chartjs-2

**백엔드**
- FastAPI, Uvicorn
- SQLAlchemy (ORM), PyMySQL
- Pydantic v2, python-dotenv
- Pandas, NumPy, scikit-learn, scipy
- PyTorch (MOCHI 보간 모델)
- Paramiko (원격 ML 서버 SSH 연결)

**데이터베이스**: MySQL 8.0

### 환경 변수 (backend/.env)

`backend/.env.example` 참조. 주요 항목:

```
MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
ML_SERVER_JUMP_HOST, ML_SERVER_JUMP_PORT, ML_SERVER_JUMP_USER, ML_SERVER_JUMP_PASSWORD
ML_SERVER_FINAL_HOST, ML_SERVER_FINAL_USER, ML_SERVER_FINAL_PASSWORD
ML_MODEL_PATH
```

### 백그라운드 작업 패턴

검증 및 보간 작업은 FastAPI `BackgroundTasks`로 비동기 실행됩니다. 클라이언트는 `job_id`로 작업 상태를 폴링합니다.

```python
@router.post("/execute")
async def execute(project_id: int, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_run_task, job_id=job_id, project_id=project_id)
    return {"jobId": job_id, "status": "processing"}
```

## 주요 기능

1. **대시보드** — 전체 프로젝트 통계, 데이터셋 완전성 시각화
2. **데이터셋 관리** — 프로젝트 생성/삭제, TSV/CSV/Excel/JSON 파일 업로드
3. **결측치 분석** — NaN 비율 계산, 완전성 점수 산출
4. **데이터 검증** — 데이터 타입별 임계값 기반 검증, 보고서 다운로드
5. **데이터 보간** — MOCHI(AI), MEAN, KNN 방법 지원, 결과 파일 다운로드

## Git Conventions

- 브랜치명: 이슈번호 또는 기능명 (예: `feedback-v1`)
- 커밋 형식: `Type: [기능명] 설명`
- Type: `Feat`, `Fix`, `Refactoring`, `Design`, `Test`, `Chore`, `Docs`, `Style`
- 설명은 한국어로 작성

## Language

코드 주석과 문서는 한국어로 작성합니다.
