# GENE-Q 멀티오믹스 데이터 품질 관리 시스템
## 기능 설계서

---

| 항목 | 내용 |
|------|------|
| 시스템 명칭 | GENE-Q |
| 문서 유형 | 기능 설계서 |
| 버전 | 1.0 |
| 작성 기준일 | 2026-04-17 |
| 관련 문서 | GENE-QC 지표설계 명세서 v2 |

---

## 문서 이력

| 버전 | 작성일 | 작성자 | 변경 내용 |
|------|--------|--------|-----------|
| 1.0 | 2026-04-17 | — | 최초 작성 |

---

## 목차

1. [문서 개요](#1-문서-개요)
2. [시스템 개요](#2-시스템-개요)
3. [기능 목록](#3-기능-목록)
4. [기능 상세 설계](#4-기능-상세-설계)
   - 4.1 프로젝트 및 데이터 파일 관리
   - 4.2 대시보드
   - 4.3 결측치 분석
   - 4.4 검증 규칙 관리 (Verification)
   - 4.5 데이터 품질 검증 (Validation)
   - 4.6 결과 보고서
   - 4.7 결측 보간 (Imputation)
   - 4.8 원격 ML 서버 연동
5. [인터페이스 설계](#5-인터페이스-설계)
6. [데이터베이스 설계](#6-데이터베이스-설계)

---

# 1. 문서 개요

## 1.1 목적

본 문서는 멀티오믹스(Multi-omics) 데이터 품질 관리 시스템 **GENE-Q**의 기능 구성, 화면 구조, 처리 흐름 및 인터페이스를 정의합니다. 본 설계서는 개발 구현의 기준 문서로 활용되며, 시스템이 제공하는 각 기능의 동작 방식을 명확히 기술합니다.

## 1.2 적용 범위

본 문서의 적용 범위는 다음과 같습니다.

- 웹 기반 사용자 인터페이스(프론트엔드) 기능
- REST API 서버(백엔드) 기능
- 데이터베이스 구조 및 파일 저장 구조
- 외부 ML 서버 연동 기능

## 1.3 용어 정의

| 용어 | 정의 |
|------|------|
| 오믹스(Omics) | 유전체(Genomics), 전사체(Transcriptomics), 메틸화(Methylation), 단백질체(Proteomics) 등 고차원 생물학 데이터의 총칭 |
| QC / 품질 관리 | 데이터의 완전성·타당성·적합성 등을 규칙 및 지표로 평가하는 과정 |
| 결측치 (Missing Value) | 수집되지 않거나 측정 실패로 인해 빈 값(NaN)으로 남겨진 데이터 셀 |
| 보간 (Imputation) | 결측값을 통계 또는 머신러닝 기반으로 추정하여 채우는 과정 |
| MOCHI | 멀티오믹스 데이터 특성을 반영한 AI 기반 보간 모델 |
| Verification | 데이터의 구조·형식 수준의 품질 검사 (헤더, 타입, ID 중복 등) |
| Validation | 데이터의 의미·기준 수준의 품질 검사 (결측률 임계값, 값 범위, 교차 정합성 등) |
| Completeness | 전체 셀 중 결측이 없는 비율 (`100% - 결측률`) |
| Job ID | 비동기 작업의 고유 식별자 (UUID 형식) |

---

# 2. 시스템 개요

## 2.1 배경 및 목표

멀티오믹스 연구에서는 DNA, RNA, Methylation, Protein 등 다양한 오믹스 데이터를 통합 분석합니다. 그러나 실제 데이터는 결측치, 이상값, 형식 불일치 등 품질 문제를 내포하는 경우가 많아, 분석 전 체계적인 품질 관리(QC)가 필수적입니다.

**GENE-Q**는 이러한 요구를 해소하기 위해 멀티오믹스 데이터의 **결측 분석 → 품질 검증 → AI 기반 보간**을 단일 웹 플랫폼에서 수행할 수 있는 시스템입니다.

## 2.2 핵심 기능 요약

| 번호 | 기능 | 설명 |
|------|------|------|
| 1 | 프로젝트·파일 관리 | 분석 단위 프로젝트 생성·관리 및 오믹스 데이터 파일 업로드 |
| 2 | 대시보드 | 전체 프로젝트 현황 및 품질 지표 한눈에 조회 |
| 3 | 결측치 분석 | 결측률 집계, 분포 시각화, 현황 파악 |
| 4 | 검증 규칙 관리 | 오믹스 데이터 품질 규칙(정렬성·정밀성·완전성) 관리 |
| 5 | 데이터 품질 검증 | 13개 표준 품질 지표 기반 검증 실행 및 결과 조회 |
| 6 | 결과 보고서 | 검증 결과 요약·시각화 및 보고서 파일 다운로드 |
| 7 | 결측 보간 | MOCHI, KNN, Mean 등 다양한 방법으로 결측치 대체 |
| 8 | 원격 ML 연동 | GPU 기반 AI 모델 서버와 SSH 터널 방식으로 연동 |

## 2.3 시스템 구성도

```
┌─────────────────────────────────────────────────────────┐
│              웹 클라이언트 (브라우저)                      │
│  대시보드 / 데이터셋 / 검증 규칙 / 품질 검증 /             │
│  데이터 관리 / 결과 보고서 / 결측치 분석                   │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP REST API
┌───────────────────────▼─────────────────────────────────┐
│                  API 서버 (FastAPI)                       │
│  /api/projects   /api/data       /api/dashboard          │
│  /api/missing-value              /api/verification        │
│  /api/validation                 /api/imputation          │
└──────┬──────────────────────────────────┬───────────────┘
       │ ORM                              │ 파일 I/O
┌──────▼──────────┐            ┌──────────▼─────────────┐
│   데이터베이스   │            │      파일 시스템         │
│   (MySQL 8.0)   │            │  uploads/project_{id}/  │
│                 │            │    raw/  (원시 데이터)   │
│  프로젝트·파일  │            │    imputed/ (보간 결과)  │
│  검증·보간 이력 │            └────────────────────────┘
└─────────────────┘
                               ┌────────────────────────┐
                               │   원격 ML 서버 (SSH)    │
                               │   Jump Host → ML 서버   │
                               │   MOCHI 모델 실행        │
                               └────────────────────────┘
```

## 2.4 기술 스택

| 구분 | 기술 |
|------|------|
| 클라이언트 | React 19, TypeScript, Vite, MUI v7, React Router v7, axios, chart.js |
| 서버 | FastAPI, Uvicorn, Pydantic v2, SQLAlchemy, PyMySQL |
| 데이터 처리 | Pandas, NumPy, scikit-learn, SciPy |
| AI / 딥러닝 | PyTorch (MOCHI 파이프라인), GAIN, VAE |
| 데이터베이스 | MySQL 8.0 |
| 원격 연산 | Paramiko (SSH 터널) |

## 2.5 사용자 워크플로

```
① 프로젝트 생성
        ↓
② 오믹스 파일 업로드 (TSV/CSV)
        ↓
③ 결측치 현황 확인
        ↓
④ 품질 검증 실행 → 차원별 결과 확인
        ↓
⑤ 결측 보간 실행 → 결과 파일 다운로드
```

---

# 3. 기능 목록

| 기능 ID | 기능명 | 관련 화면 | 관련 API |
|---------|--------|-----------|----------|
| F-01 | 프로젝트 생성·수정·삭제 | 데이터셋 관리 | `/api/projects` |
| F-02 | 오믹스 파일 업로드·조회·삭제 | 데이터셋 관리 | `/api/data` |
| F-03 | 프로젝트 메타 일괄 CSV 등록 | 데이터셋 관리 | `/api/projects/upload-csv` |
| F-04 | 대시보드 통계 조회 | 대시보드 | `/api/dashboard/stats` |
| F-05 | 결측치 요약 분석 | 결측치 분석 | `/api/missing-value/summary` |
| F-06 | 결측 분포 시각화 | 결측치 분석 | `/api/missing-value/summary/{id}/distribution` |
| F-07 | 검증 규칙 CRUD | 검증 규칙 관리 | `/api/verification/rules` |
| F-08 | 검증 대시보드 조회 | 검증 규칙 관리 | `/api/verification/dashboard` |
| F-09 | 품질 검증 실행 (비동기) | 품질 검증 | `/api/validation/execute` |
| F-10 | 검증 결과 조회 (차원별) | 품질 검증 | `/api/validation/status/{job_id}` |
| F-11 | 검증 파라미터 저장·조회 | 품질 검증 | `/api/validation/rules/{project_id}` |
| F-12 | 검증 보고서 다운로드 | 결과 보고서 | `/api/validation/download-report/{project_id}` |
| F-13 | 단일 오믹스 보간 실행 (비동기) | 데이터 관리 | `/api/imputation/execute` |
| F-14 | 멀티오믹스 일괄 보간 실행 (비동기) | 결측치 분석 | `/api/imputation/execute-multiomics` |
| F-15 | 보간 결과 파일 다운로드 | 데이터 관리 | `/api/imputation/download/{job_id}/{omics_type}` |
| F-16 | ML 서버 연결 상태 확인 | 데이터 관리 | `/api/imputation/ml-model/connection-test` |

---

# 4. 기능 상세 설계

---

## 4.1 프로젝트 및 데이터 파일 관리

**기능 ID**: F-01, F-02, F-03  
**관련 화면**: 데이터셋 관리 (`/dataset`)

### 4.1.1 기능 개요

분석의 기본 단위인 **프로젝트**를 생성·관리하고, 오믹스 원시 데이터 파일을 업로드·추적합니다. 프로젝트는 오믹스 유형, 품질 점수, 검증 상태 등의 메타데이터를 보유합니다.

### 4.1.2 주요 기능

**프로젝트 관리**

| 기능 | 설명 |
|------|------|
| 프로젝트 목록 조회 | 전체 프로젝트를 오믹스 유형·품질 점수·상태와 함께 목록으로 조회 |
| 프로젝트 생성 | 프로젝트명, 설명, 오믹스 유형 등 메타데이터를 입력하여 신규 프로젝트 생성 |
| 프로젝트 수정 | 프로젝트명 변경 또는 전체 정보 수정 |
| 프로젝트 삭제 | 프로젝트 삭제 시 연관된 파일, 결측 분석 레코드, 검증 규칙이 함께 삭제 |
| CSV 일괄 등록 | 프로젝트 메타데이터를 CSV 파일로 일괄 등록 |

**데이터 파일 관리**

| 기능 | 설명 |
|------|------|
| 파일 업로드 | TSV/CSV 형식의 오믹스 데이터 파일을 선택한 프로젝트에 업로드 |
| 파일 목록 조회 | 프로젝트별 업로드된 파일 목록(파일명, 크기, 업로드일) 조회 |
| 파일 삭제 | 개별 파일 삭제 |

### 4.1.3 처리 흐름

```
[프로젝트 생성]
사용자 → 프로젝트 정보 입력 → API 호출 → DB 저장 → 목록 갱신

[파일 업로드]
사용자 → 파일 선택 → Multipart 전송 → 서버 수신
  → uploads/project_{id}/raw/{파일명} 저장
  → DB에 파일명·크기·경로 기록
  → 업로드 완료 응답
```

### 4.1.4 프로젝트 응답 데이터

| 필드 | 설명 |
|------|------|
| `name` | 프로젝트명 |
| `data_type` | 오믹스 유형 목록 (예: `["전사체", "단백질체"]`) |
| `quality_score` | 전체 품질 점수 (0~100) |
| `validation_status` | 검증 상태 (`작성중` / `처리중` / `검증완료`) |
| `status` | 프로젝트 상태 (`활성` / `비활성` / `완료`) |
| `dna_quality_score` | DNA 오믹스 개별 품질 점수 |
| `rna_quality_score` | RNA 오믹스 개별 품질 점수 |
| `methyl_quality_score` | Methylation 오믹스 개별 품질 점수 |
| `protein_quality_score` | Protein 오믹스 개별 품질 점수 |
| `sample_count` | 샘플 수 |
| `total_file_size` | 업로드 파일 총 용량 (자동 계산) |

### 4.1.5 CSV 일괄 등록 응답

| 필드 | 설명 |
|------|------|
| `message` | 처리 결과 메시지 |
| `createdCount` | 생성된 프로젝트 수 |
| `totalRows` | CSV 전체 행 수 |
| `projects` | 생성된 프로젝트 목록 |
| `errors` | 실패 행 오류 메시지 목록 |

---

## 4.2 대시보드

**기능 ID**: F-04  
**관련 화면**: 대시보드 (`/`)

### 4.2.1 기능 개요

시스템 전체 현황을 한 화면에서 파악할 수 있는 대시보드를 제공합니다. 주요 통계 수치, 프로젝트 미리보기, 품질 트렌드, 최근 활동 내역을 표시합니다.

### 4.2.2 화면 구성

| 컴포넌트 | 역할 | 데이터 출처 |
|----------|------|-------------|
| 통계 카드 (4종) | 활성 프로젝트 수·평균 품질 점수·처리된 데이터셋 수·평균 결측률 표시 | `GET /api/dashboard/stats` |
| 프로젝트 미리보기 | 프로젝트명·오믹스 유형·품질 점수·상태·업데이트 시각을 카드 그리드로 표시 | `GET /api/projects` |
| 품질 트렌드 | 최대 5개 프로젝트의 오믹스별 품질 점수 막대 비교 | `GET /api/projects` |
| 최근 활동 | 최근 3개 프로젝트의 이름·데이터 유형·품질·상태 테이블 | `GET /api/projects` |
| 통계량 그래프 | 유전자 수·샘플 수·결측률 등 수치 및 Bar 차트 | — |

### 4.2.3 집계 항목

| 항목 | 산출 방법 |
|------|-----------|
| 활성 프로젝트 수 | 상태가 `활성`인 프로젝트 건수 |
| 평균 품질 점수 | 전체 프로젝트의 `quality_score` 평균 |
| 처리된 데이터셋 수 | `validation_status`가 `검증완료`인 프로젝트 건수 |
| 평균 결측률 | `missing_values` 테이블의 `total_missing_rate` 평균 |

---

## 4.3 결측치 분석

**기능 ID**: F-05, F-06  
**관련 화면**: 결측치 분석

### 4.3.1 기능 개요

프로젝트에 업로드된 오믹스 데이터의 결측치 현황을 분석하여 요약 지표와 분포 시각화 정보를 제공합니다. 보간 실행 전 데이터 상태를 파악하는 목적으로 사용됩니다.

### 4.3.2 화면 구성

```
┌────────────────────────┬──────────────────────────────────────┐
│  좌측 패널              │  우측 패널                            │
│  · 프로젝트 선택        │  · 결측치 분석 요약 카드 3종           │
│  · 보간 파라미터 설정   │  · 결측 분포 구간별 시각화             │
│  · 멀티오믹스 보간 실행 │                                       │
└────────────────────────┴──────────────────────────────────────┘
```

### 4.3.3 요약 카드 (3종)

| 유형 | 표시 항목 | 설명 |
|------|-----------|------|
| 전체 결측률 | 결측률 (%) | 데이터 전체 셀 대비 결측 셀 비율 |
| 결측 샘플 | 결측 샘플 수 / 전체 샘플 수 | 한 개 이상의 결측을 가진 샘플(행) 수 |
| 결측 유전자 | 결측 유전자 수 | 한 개 이상의 결측을 가진 유전자/feature(열) 수 |

### 4.3.4 결측 분포 구간

결측률을 5개 구간으로 나누어 각 구간에 속하는 샘플 수 및 유전자 수를 시각화합니다.

| 구간 | 의미 |
|------|------|
| 0~10% | 결측률 0% 이상 10% 미만 |
| 10~20% | 결측률 10% 이상 20% 미만 |
| 20~30% | 결측률 20% 이상 30% 미만 |
| 30~50% | 결측률 30% 이상 50% 미만 |
| 50% 이상 | 결측률 50% 초과 |

### 4.3.5 보간 설정 및 실행

좌측 패널에서 아래 파라미터를 슬라이더로 조정한 뒤 멀티오믹스 보간을 실행할 수 있습니다.

- 보간 임계값 (결측률 기준)
- 보간 후 최소 품질 기준

보간 실행 완료 후 RNA·Protein·Methyl 각각의 결과 파일 다운로드 버튼이 활성화됩니다.

---

## 4.4 검증 규칙 관리 (Verification)

**기능 ID**: F-07, F-08  
**관련 화면**: 검증 규칙 관리 (`/verification`)

### 4.4.1 기능 개요

오믹스 데이터의 정렬성·정밀성·완전성 기반 품질 규칙을 정의하고 관리합니다. 규칙은 DB에 저장되어 검증 실행 시 참조됩니다.

### 4.4.2 화면 구성 (3탭)

| 탭 | 기능 |
|----|------|
| 대시보드 탭 | 검증 현황 카드·품질 지표 바·추이 차트 표시 |
| 규칙 탭 | 검증 규칙 목록 조회 및 규칙 추가·수정·삭제 |
| 검증 실행 탭 | 프로젝트 선택·데이터 업로드·분석 타입 선택·규칙 선택·검증 실행 |

### 4.4.3 대시보드 탭

`GET /api/verification/dashboard` 호출로 아래 지표를 조회합니다.

| 지표 | 설명 |
|------|------|
| 총 검증 샘플 | 검증이 수행된 전체 샘플 수 |
| 검증 통과율 | 전체 검증 항목 중 통과 비율 |
| 경고 샘플 수 | 경고 이상 판정을 받은 샘플 수 |
| 활성 규칙 수 | 현재 활성화된 검증 규칙 수 |

### 4.4.4 규칙 탭

- 규칙은 **라벨·카테고리·메트릭·조건·임계값** 형태로 구성됩니다.
- 카테고리는 `정렬성`, `정밀성`, `완전성` 세 가지로 분류됩니다.

**기본 제공 규칙 샘플**

| 규칙명 | 카테고리 | 메트릭 | 조건 | 임계값 |
|--------|----------|--------|------|--------|
| 리드 정렬성 | 정렬성 | `read_mapping` | `>=` | 90 |
| 위양성 SNP calls | 정렬성 | `snp_calls` | `<=` | 5 |
| 동일 준비 동일 LC-MS | 정밀성 | `consistency` | `>=` | 85 |
| 기기 안정성 | 완전성 | `batch_drift` | `<=` | 10 |

### 4.4.5 검증 실행 탭

| 구성 요소 | 설명 |
|-----------|------|
| 프로젝트 선택 | 검증을 실행할 프로젝트를 선택 |
| 데이터 업로드 | FASTA, BAM, TSV 등 원시 데이터 파일 첨부 |
| 분석 타입 선택 | RNA-seq, DNA 등 분석 타입 선택 |
| 규칙 선택 | 적용할 검증 규칙 체크박스로 선택 |
| 검증 실행 | 선택된 프로젝트에 대해 품질 검증(Validation API) 실행 |

검증 실행 흐름:

```
검증 실행 버튼 클릭
  → POST /api/validation/execute
  → jobId 반환
  → 1초 간격 상태 폴링 (최대 30회)
  → 완료 시 결과 화면 표시
```

---

## 4.5 데이터 품질 검증 (Validation)

**기능 ID**: F-09, F-10, F-11  
**관련 화면**: 품질 검증 (`/validation`)

### 4.5.1 기능 개요

OMOP CDM DQM 기반 품질 지표 체계를 적용하여 오믹스 데이터 파일에 대해 표준화된 검증을 수행합니다. 검증 결과는 세 가지 품질 차원(Completeness·Plausibility·Conformance)으로 분류하여 제공됩니다.

### 4.5.2 품질 차원

| 차원 | 설명 | 예시 |
|------|------|------|
| Completeness (완전성) | 데이터의 존재 및 완성 여부 | 헤더 존재, 컬럼 결측, 행 완전성 |
| Plausibility (타당성) | 값의 현실적 타당성 | IQR 이상치, 발현값 하한, 분산=0 컬럼 |
| Conformance (적합성) | 형식·기준 준수 여부 | 구분자 일관성, ID 중복, 컬럼명 형식 |

### 4.5.3 심각도 분류

| 심각도 | 의미 | 판정 결과 |
|--------|------|-----------|
| `fatal` | 검증 불가 수준의 치명적 결함 | fail |
| `error` | 허용 불가 오류 | fail |
| `warning` | 주의가 필요한 경고 | warning |
| `convention` | 권고 기준 위반 | convention |
| `characterization` | 정보성 특성 파악 | pass |

### 4.5.4 검증 규칙 목록 (13개)

| 규칙 ID | 규칙명 | 차원 | 심각도 | 적용 대상 |
|---------|--------|------|--------|-----------|
| comp_F001 | 파일 헤더 존재 여부 | Completeness | fatal | 모든 파일 |
| comp_C001 | 샘플 ID 컬럼 필수 존재 | Completeness | fatal | 모든 파일 |
| comp_C002 | 컬럼별 결측률 검사 | Completeness | warning | 모든 파일 |
| comp_C003 | 행(샘플) 완전성 검사 (50% 기준) | Completeness | warning | 모든 파일 |
| comp_F003 | 전체 데이터 결측률 | Completeness | warning | 오믹스 파일 |
| plau_C001 | 발현값 하한 검사 (< -100 경보) | Plausibility | characterization | 오믹스 파일 |
| plau_C002 | 발현값 상한 검사 (최댓값 보고) | Plausibility | characterization | 오믹스 파일 |
| plau_C003 | IQR 기반 이상치 검사 (5% 임계값) | Plausibility | warning | 오믹스 파일 |
| plau_C004 | 상수값 컬럼 탐지 (분산=0) | Plausibility | warning | 오믹스 파일 |
| conf_F001 | 파일 형식(구분자) 일관성 | Conformance | fatal | 모든 파일 |
| conf_C001 | 샘플 ID 중복 검사 | Conformance | fatal | 모든 파일 |
| conf_C002 | 수치형 컬럼 데이터 타입 검사 | Conformance | error | 오믹스 파일 |
| conf_C003 | 컬럼명 형식 검사 (공백/특수문자) | Conformance | convention | 모든 파일 |

### 4.5.5 파일명 기반 데이터 타입 자동 추론

검증 실행 시 파일명에 포함된 키워드를 기준으로 오믹스 타입을 자동 분류하며, 타입별 기본 결측 임계값이 적용됩니다.

| 파일명 키워드 | 추론 타입 | 기본 결측 임계값 |
|---------------|-----------|-----------------|
| `rna`, `transcriptom`, `expression` | 전사체 (Transcriptomics) | 20.0% |
| `dna`, `snp`, `genomic` | 유전체 (Genomics) | 1.0% |
| `methylat`, `methyl`, `methy` | 유전체 (Genomics) | 1.0% |
| `protein`, `proteom`, `prot` | 단백질체 (Proteomics) | 25.0% |
| `metabol` | 대사체 (Metabolomics) | 25.0% |
| `meta`, `clinical`, `phenotype` | 임상 메타데이터 | 30.0% |
| 미매칭 | 미분류 | 30.0% |

> 프로젝트별로 저장된 임계값이 있는 경우, 기본값보다 우선 적용됩니다.

### 4.5.6 완전성 점수 산출

```
완전성 점수(%) = 100 - 결측률(%)
결측률(%)      = (결측 셀 수 / 전체 셀 수) × 100
```

### 4.5.7 검증 실행 흐름

```
클라이언트                              서버
    │                                     │
    │── POST /api/validation/execute ───▶ │
    │                                     ├─ 저장된 임계 규칙 로드
    │                                     ├─ Job ID(UUID) 생성
    │◀── { jobId, status:"processing" } ──┤
    │                                     ├─ 백그라운드 작업 실행
    │── GET /status/{jobId} (폴링) ──────▶ │   ├─ 파일 로드 및 타입 추론
    │◀── { status:"processing" } ─────── │   ├─ 13개 규칙 순차 실행
    │     (1초 간격, 최대 30회)            │   └─ 결과 집계 및 저장
    │── GET /status/{jobId} ────────────▶ │
    │◀── { status:"completed",            │
    │      results: { ... } }             │
```

### 4.5.8 검증 결과 응답 구조

```json
{
  "files": [
    {
      "filename": "rna_data.tsv",
      "inferred_type": "transcriptomics",
      "total_values": 1000000,
      "nan_count": 22500,
      "nan_percentage": 2.25,
      "completeness": 97.75,
      "shape": [200, 5000],
      "threshold_used": 20.0,
      "passed": true
    }
  ],
  "total_files": 2,
  "passed_files": 1,
  "all_passed": false,
  "completeness_scores": {
    "dna": 99.1,
    "rna": 97.75,
    "methyl": null,
    "protein": null
  },
  "rule_results": [
    {
      "ruleId": "comp_C002",
      "ruleName": "컬럼별 결측률 검사",
      "dimension": "Completeness",
      "severity": "warning",
      "fileName": "rna_data.tsv",
      "status": "warning",
      "message": "결측률 초과 컬럼 3개 — 최대 22.5%",
      "metricValue": 22.5,
      "threshold": 20.0
    }
  ],
  "dimension_summary": {
    "Completeness": { "pass": 4, "warning": 1, "fail": 0, "convention": 0, "total": 5 },
    "Plausibility": { "pass": 3, "warning": 1, "fail": 0, "convention": 0, "total": 4 },
    "Conformance": { "pass": 3, "warning": 0, "fail": 0, "convention": 1, "total": 4 }
  }
}
```

### 4.5.9 검증 결과 화면 구성 (ValidationPage)

| 컴포넌트 | 설명 |
|----------|------|
| 진행 단계 표시 | 데이터 로딩 → 지표 계산 → 결과 집계의 단계별 진행 상황 시각화 |
| 차원별 요약 카드 | Completeness·Plausibility·Conformance 3개 차원의 통과율 및 건수 표시 |
| 상세 결과 목록 | 차원별 그룹핑된 규칙별 판정 결과, 측정값, 임계값, 상세 메시지 표시 |

- 차원 카드 클릭 시 해당 차원의 결과만 필터링되어 표시됩니다.
- 점수 색상: 80% 이상 — 초록, 60~79% — 노랑, 60% 미만 — 빨강

### 4.5.10 검증 파라미터 저장·조회

`POST /api/validation/rules/{project_id}`로 프로젝트별 임계값을 저장합니다.

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `dna_threshold` | 1.0% | DNA 결측 허용 상한 |
| `rna_threshold` | 20.0% | RNA 결측 허용 상한 |
| `protein_threshold` | 25.0% | Protein 결측 허용 상한 |
| `methyl_threshold` | 25.0% | Methyl 결측 허용 상한 |
| `batch_effect_threshold` | 5.0% | 배치효과 허용 상한 |
| `sample_matching_enabled` | true | 샘플 매칭 검사 활성화 여부 |
| `range_validation_enabled` | true | 발현값 범위 검사 활성화 여부 |

---

## 4.6 결과 보고서

**기능 ID**: F-12  
**관련 화면**: 결과 보고서 (`/results`)

### 4.6.1 기능 개요

프로젝트의 품질 검증 결과를 요약·시각화하고, 보고서 파일을 다운로드합니다.

### 4.6.2 화면 구성

| 컴포넌트 | 설명 |
|----------|------|
| 품질 요약 | 품질 점수·샘플 수·결측률 등 핵심 지표 카드 표시 |
| 처리 타임라인 | 데이터 로딩 → 품질 검증 → 결측 분석 → 최종 완료 4단계 시각화 |
| 권고사항 | 결측률·통과 여부에 따라 자동 생성된 개선 권고사항 |
| 보고서 다운로드 | 검증 결과 전체를 파일로 내려받는 버튼 |

### 4.6.3 보고서 내용 구성

| 섹션 | 내용 |
|------|------|
| Executive Summary | 전체 검증 결과 요약 |
| Data Overview | 파일별 데이터 개요 (샘플 수, 유전자 수, 결측률 등) |
| Quality by Dimension | 차원별(Completeness·Plausibility·Conformance) 집계 결과 |
| Detailed Validation Results | 규칙별 상세 판정 결과 |
| File-Level Summary | 파일 단위 통과·경고·실패 요약 |
| Recommendations | 자동 생성 개선 권고사항 |

---

## 4.7 결측 보간 (Imputation)

**기능 ID**: F-13, F-14, F-15  
**관련 화면**: 데이터 관리 (`/management`)

### 4.7.1 기능 개요

결측률이 허용 범위를 초과하는 경우, 사용자가 선택한 방법으로 결측치를 보간하고, 결과 파일을 내려받을 수 있습니다. 단일 오믹스 보간과 멀티오믹스 일괄 보간을 모두 지원합니다.

### 4.7.2 지원 보간 방법

| 방법 ID | 표시명 | 알고리즘 설명 |
|---------|--------|---------------|
| `mochi` | MOCHI (권장) | 멀티오믹스 데이터 특성을 반영한 AI 기반 보간 모델, 원격 ML 서버에서 실행 |
| `mean` | Mean/Median | 컬럼별 평균/중앙값으로 결측치 대체 |
| `knn` | KNN | K-최근접 이웃 알고리즘 기반 보간 |
| `missforest` | MissForest | Random Forest 기반 반복적 보간 |
| `gain` | GAIN | Generative Adversarial Imputation Networks |
| `vae` | VAE | Variational Autoencoder 기반 보간 |

### 4.7.3 단일 오믹스 보간 흐름

```
POST /api/imputation/execute
  입력: project_id, method, threshold, quality_threshold

  서버 처리:
  ① Job ID(UUID) 생성 및 작업 등록
  ② 백그라운드 작업 실행
     · 프로젝트 원시 파일 로드
     · 선택된 방법으로 보간 실행
     · 결과 파일 저장 (uploads/project_{id}/imputed/)
  ③ 상태 응답 반환

GET /api/imputation/status/{job_id}  → 진행 중 / 완료 / 실패
GET /api/imputation/results/{job_id} → 완료 시 결과 메타 반환
```

### 4.7.4 멀티오믹스 일괄 보간 흐름

```
POST /api/imputation/execute-multiomics
  입력: project_id, threshold (기본 30%), quality_threshold (기본 85%)

  서버 처리:
  · RNA, Protein, Methyl 3종 데이터를 MOCHI 모델로 동시 보간
  · 오믹스별 결과 파일 저장

  완료 후 반환:
  · rna_missing_imputed, protein_missing_imputed, methyl_missing_imputed
  · total_samples, output_files

GET /api/imputation/download/{job_id}/{omics_type}
  omics_type: rna | protein | methyl → 해당 보간 결과 파일 다운로드
```

### 4.7.5 보간 결과 화면

보간 완료 후 다음 정보가 표시됩니다.

- RNA / Protein / Methyl 각 오믹스별 보간된 결측치 수
- 전체 처리 샘플 수
- 오믹스별 결과 파일 다운로드 버튼

---

## 4.8 원격 ML 서버 연동

**기능 ID**: F-16  
**관련 화면**: 데이터 관리 (연결 상태 표시)

### 4.8.1 기능 개요

GPU 기반 MOCHI 멀티오믹스 보간 모델을 웹/API 서버와 분리된 원격 환경에서 실행하기 위해 SSH 터널 방식의 연동을 제공합니다.

### 4.8.2 SSH 연결 구조

```
API 서버
  └── SSH 클라이언트 (Paramiko)
       ├── Jump Host 접속
       ├── direct-tcpip 채널 생성 (ProxyJump 방식)
       └── ML 서버 접속
            └── conda 환경 포함 명령 실행
```

### 4.8.3 원격 실행 단계

| 단계 | 설명 |
|------|------|
| ① 환경 점검 | conda, Python, PyTorch 설치 여부 확인 |
| ② 경로 초기화 | 원격 서버 홈 경로, 데이터 경로, 모델 체크포인트 경로 확인 |
| ③ 파일 전송 | 로컬 원시 TSV 파일을 SFTP로 원격 서버에 업로드 |
| ④ 보간 실행 | 원격 Python 스크립트 실행 → MOCHI 모델 로드 → 보간 수행 |
| ⑤ 결과 수신 | 보간 결과 파일을 SFTP로 로컬 서버에 다운로드 |

### 4.8.4 주요 API

| API | 설명 |
|-----|------|
| `GET /api/imputation/ml-model/connection-test` | SSH 터널 연결 가능 여부 확인 |
| `GET /api/imputation/ml-model/list` | 원격 서버에서 사용 가능한 모델 목록 조회 |

### 4.8.5 환경 변수 구성

| 변수명 | 설명 |
|--------|------|
| `ML_SERVER_JUMP_HOST` | Jump Host 주소 |
| `ML_SERVER_JUMP_PORT` | Jump Host 포트 |
| `ML_SERVER_JUMP_USER` | Jump Host 접속 사용자명 |
| `ML_SERVER_JUMP_PASSWORD` | Jump Host 접속 비밀번호 |
| `ML_SERVER_FINAL_HOST` | ML 서버 주소 |
| `ML_SERVER_FINAL_USER` | ML 서버 접속 사용자명 |
| `ML_SERVER_FINAL_PASSWORD` | ML 서버 접속 비밀번호 |
| `ML_MODEL_PATH` | 모델 체크포인트 파일 또는 디렉토리 경로 |

---

# 5. 인터페이스 설계

## 5.1 프론트엔드 라우팅

| URL 경로 | 페이지 컴포넌트 | 기능 |
|----------|----------------|------|
| `/` | 대시보드 | 전체 현황 통계·프로젝트 미리보기·품질 트렌드 |
| `/dataset` | 데이터셋 관리 | 프로젝트 생성·파일 업로드 관리 |
| `/verification` | 검증 규칙 관리 | 검증 규칙 CRUD·검증 실행 |
| `/validation` | 품질 검증 결과 | 검증 결과·차원별 분석 |
| `/management` | 데이터 관리 | 보간 설정·실행·결과 다운로드 |
| `/results` | 결과 보고서 | 품질 요약·타임라인·권고사항·보고서 다운로드 |

## 5.2 백엔드 API 목록

| Method | Path | 기능 |
|--------|------|------|
| GET | `/api/projects` | 프로젝트 목록 |
| GET | `/api/projects/{id}` | 프로젝트 단건 조회 |
| POST | `/api/projects` | 프로젝트 생성 |
| PUT | `/api/projects/{id}` | 프로젝트 전체 수정 |
| PATCH | `/api/projects/{id}/name` | 프로젝트명 변경 |
| DELETE | `/api/projects/{id}` | 프로젝트 삭제 |
| POST | `/api/projects/upload-csv` | CSV 기반 프로젝트 메타 일괄 등록 |
| GET | `/api/data` | 데이터 파일 목록 (`?project_id=`) |
| GET | `/api/data/{file_id}` | 데이터 파일 단건 조회 |
| POST | `/api/data/upload` | 파일 업로드 (`?project_id=`) |
| DELETE | `/api/data/{file_id}` | 파일 삭제 |
| GET | `/api/missing-value/projects` | 결측 분석 가능 프로젝트 목록 |
| GET | `/api/missing-value/summary/{project_id}` | 결측 종합 분석 (요약 + 분포) |
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

## 5.3 비동기 작업 처리 패턴

검증 및 보간 등 장시간 소요 작업은 FastAPI `BackgroundTasks`를 통해 비동기로 실행됩니다. 클라이언트는 Job ID를 발급받아 상태를 주기적으로 조회(폴링)합니다.

```
① 실행 요청 → Job ID 발급 (status: "processing")
② 클라이언트 폴링 루프
    └── GET /status/{jobId}
         ├── processing → 대기 후 재조회
         ├── completed  → 결과 표시
         └── failed     → 오류 메시지 표시
```

| 항목 | 검증 (Validation) | 보간 (Imputation) |
|------|------------------|------------------|
| 폴링 간격 | 1초 | 2초 |
| 최대 시도 | 30회 | 제한 없음 |
| 타임아웃 처리 | 30회 초과 시 오류 표시 | 완료/실패 시까지 대기 |

---

# 6. 데이터베이스 설계

## 6.1 테이블 목록

| 테이블명 | 설명 |
|----------|------|
| `projects` | 프로젝트 메타데이터 |
| `data_files` | 업로드 파일 정보 |
| `missing_values` | 결측치 분석 결과 |
| `verification_rules` | 검증 규칙 정의 |
| `verification_status` | 검증 항목별 점수 상태 |
| `imputation_jobs` | 보간 작업 이력 |

## 6.2 projects

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer PK | 프로젝트 식별자 |
| `name` | String(255) | 프로젝트명 |
| `description` | Text | 설명 |
| `data_type` | JSON | 오믹스 유형 목록 |
| `quality_score` | Float | 전체 품질 점수 (0~100) |
| `validation_status` | String | `작성중` / `처리중` / `검증완료` |
| `status` | String | `활성` / `비활성` / `완료` |
| `sample_count` | Integer | 샘플 수 |
| `dna_quality_score` | Float | DNA 오믹스 품질 점수 |
| `rna_quality_score` | Float | RNA 오믹스 품질 점수 |
| `methyl_quality_score` | Float | Methyl 오믹스 품질 점수 |
| `protein_quality_score` | Float | Protein 오믹스 품질 점수 |
| `sample_accuracy` | Float | 샘플 정확도 |
| `created_at` / `updated_at` | DateTime | 생성·수정 일시 |

**관계**: `data_files`, `missing_values`, `verification_rules`와 1:N 관계. 프로젝트 삭제 시 cascade 삭제 적용.

## 6.3 data_files

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer PK | 파일 식별자 |
| `project_id` | Integer FK | 연결 프로젝트 |
| `name` | String(255) | 파일명 |
| `size` | String | 표시용 크기 (예: `1.2 GB`) |
| `file_path` | String(500) | 실제 저장 경로 |
| `created_at` | DateTime | 업로드 일시 |

## 6.4 missing_values

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer PK | 분석 레코드 식별자 |
| `project_id` | Integer FK | 연결 프로젝트 |
| `total_missing_rate` | Float | 전체 결측률 (%) |
| `missing_sample_count` | Integer | 결측이 있는 샘플(행) 수 |
| `missing_gene_count` | Integer | 결측이 있는 유전자/feature(열) 수 |
| `total_cells` | Integer | 전체 셀 수 (행 × 열) |
| `distribution_data` | JSON | 결측률 구간별 분포 데이터 |
| `updated_at` | DateTime | 최근 갱신 일시 |

## 6.5 verification_status

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer PK | 레코드 식별자 |
| `project_id` | Integer FK | 연결 프로젝트 |
| `label` | String | 검증 항목명 |
| `score` | Integer | 실제 점수 |
| `standard` | Integer | 기준값 |
| `created_at` / `updated_at` | DateTime | 생성·수정 일시 |

## 6.6 imputation_jobs

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

## 6.7 파일 저장 구조

| 경로 | 저장 내용 |
|------|-----------|
| `uploads/project_{id}/raw/` | 업로드된 원시 TSV/CSV 파일 |
| `uploads/project_{id}/imputed/` | 보간 처리 완료된 결과 파일 |

## 6.8 데이터 흐름 요약

```
① 파일 업로드
   TSV/CSV → uploads/project_{id}/raw/

② 결측치 분석
   → missing_values 테이블에 집계 결과 저장

③ 품질 검증
   → 규칙 기반 지표 평가 → projects.quality_score 갱신

④ 결측 보간
   → uploads/project_{id}/imputed/ 결과 파일 저장
   → imputation_jobs 테이블에 이력 기록
```

---
