# 코드 리뷰: feedback-v2
- 대상 브랜치: `feedback-v2`

## 변경 사항 요약

`docs/GENE-QC_지표설계_명세서_v2.md` 의 OMOP CDM DQM 기반 28개 품질지표 체계를
백엔드 실 서비스 로직에 실제로 연동시키기 위한 대규모 정합화 작업.

기존 백엔드는 `validation_service.py` 에 28개 지표가 정의되어 있으나
HTTP 엔드포인트가 해당 모듈을 import 하지 않고 `validation.py` 내부의 자체 함수
(`_evaluate_gene_qc_rules`, 13개 규칙)만 실행해 명세서 대비 ~45% 만 동작하고 있었음.
또한 metabolomics → Methyl 라벨 매핑 버그, `_mochi_imputation` 의 mock 결과 반환,
`/home/humandeep` 원격 경로 하드코딩, macOS 전용 `cupsfilter` 의존,
in‑memory 검증 결과 저장(서버 재시작 시 손실) 등 다수의 정합성·신뢰성 결함이 존재.

본 변경은 다음을 목표로 진행:

1. 28개 지표 전수 활성화 — API → `validation_service.run_validation()` 일원화
2. 명세서 §5.1~5.3 의 신규 규칙 필드를 DB 모델에 반영
3. 검증 작업 결과 DB 영속화
4. dataType 5종(genomics/transcriptomics/proteomics/metabolomics/metadata) 일관 적용
5. 원격 AI(MOCHI) 보간의 차원 하드코딩 제거 및 mock fallback 제거
6. 크로스 플랫폼 PDF 보고서 생성

## 구현 방식 설명

### 검증 흐름 재배치

이전:
```
POST /api/validation/execute
   → _evaluate_gene_qc_rules (13개, 라우트 내부)
   → 결과 in‑memory validation_jobs dict 저장
```

이후:
```
POST /api/validation/execute (project_id + 선택적 enabledMetrics/paramsOverrides)
   → ValidationJob 행 생성(status=processing)
   → background_task → validation_service.run_validation()
        ① DataFile.data_type 또는 파일명 추론으로 file_data_types 구성
        ② Project.legacy_validation_thresholds 가 있으면 자동 paramsOverrides 변환
        ③ 28개 metric 함수 실행
   → ValidationJob.results JSON 저장 (completed/failed)
   → Project.{5종}_quality_score / quality_score / validation_status 동기화
```

### 규칙 모델 마이그레이션

명세서 §5.1~5.3 의 11개 필드를 `VerificationRule` 에 추가하고
옛 4필드(category/metric/condition/threshold)는 응답에서 자동 매핑해 하위 호환.

| 명세서 §5 영역 | 신규 컬럼 |
| -------- | -------- |
| §5.1 확정 | name, dimension, quality_level, severity, description, data_types(JSON) |
| §5.2 검증 수행 | validation_type, parameters(JSON) |
| §5.3 OMOP 추적 | metric_id, metric_level, context, is_custom, enabled, author |

차원 ↔ 옛 한글 카테고리 매핑은 라우트 직렬화 단계에서만 수행
(DB에는 명세서 영문값만 저장).

### 보간 흐름 일원화

이전:
```
method="mochi" → ImputationService._mochi_imputation
   → 존재하지 않는 mochi_model.py SSH 실행 시도
   → 실패 시 하드코딩 mock(quality_score 97.3) 반환  ←  치명적 거짓 결과
```

이후:
```
method="mochi" → _run_multiomics_imputation (자동 라우팅)
   → RemoteMultiOmicsImputationService (paramiko jump SSH)
       ① 로컬 raw/*.tsv SFTP 업로드
       ② impute_multiomics.py 자동 생성/존재 확인
       ③ 입력 데이터 shape 로 dim_rna/dim_protein/dim_methyl 동적 결정
       ④ checkpoint 차원 불일치 시 즉시 RuntimeError
       ⑤ 결과 TSV + statistics.json 다운로드
```

## 주요 변경 포인트

### `backend/app/models/base.py`
- `VerificationRule`: 명세서 §5 의 11개 신규 컬럼 추가, 옛 4필드 완전 제거
- `ValidationJob` 신규 테이블 — 검증 결과 영속화
- `Project`: 5종 dataType 품질점수 컬럼 추가(`genomics/transcriptomics/proteomics/metabolomics/metadata_quality_score`),
  옛 컬럼은 하위 호환용으로 유지, `legacy_validation_thresholds` JSON 컬럼 추가
- `DataFile`: `data_type` 컬럼 추가 (명세서 §3 5종 직접 저장)

### `backend/app/models/schemas.py`
- `VerificationRule` Pydantic 스키마를 신규 11필드 + 옛 6필드 **모두 Optional** 로 변경
  → 프론트엔드가 어느 쪽 포맷으로 보내도 수용

### `backend/app/api/routes/validation.py`
- `_evaluate_gene_qc_rules` (13개) 완전 삭제, `validation_service.run_validation()` 로 위임 → **28개 지표 활성화**
- `validation_jobs / validation_rules` in‑memory dict 제거 → `ValidationJob` 테이블 영속화
- `_legacy_params_overrides()` — 옛 7필드 임계값을 명세서 §4 의 `paramsOverrides` 형식(comp_C002/comp_F003)으로 자동 변환
- PDF 리포트: `subprocess.run(["cupsfilter", ...])` 제거, reportlab 기반 한글 폰트 자동 등록 PDF 빌더로 교체
- `dtype_label_map` 의 잘못된 `metabolomics → Methyl` 매핑 완전 제거
- 명세서 §3 5종 dataType 그대로 `Project.{type}_quality_score` 에 기록

### `backend/app/api/routes/verification.py`
- 신규/옛 양쪽 스키마 동시 수용을 위한 `_payload_to_rule_fields()` / `_rule_to_response()` 어댑터 함수 추가
- 차원 ↔ 한글 카테고리 매핑 테이블(`_DIMENSION_TO_LEGACY_CATEGORY`)을 한 곳에 모음
- 입력에서 `metric_id` 가 명세서에 존재하면 `METRIC_METADATA` 에서 level/context/dimension/severity 자동 보정
- `enabled` 컬럼 활용한 활성 규칙 카운트로 통일 (옛 `status='active'` 문자열 비교 제거)

### `backend/app/api/routes/imputation.py`
- `MOCK_IMPUTATION_METHODS` → `AVAILABLE_IMPUTATION_METHODS` 로 개명, mock 항목(MissForest/GAIN/VAE) 제거
- `POST /execute` 에서 `method == "mochi"` 요청을 `_run_multiomics_imputation` 으로 자동 라우팅
- 보간 결과 파일 경로 헬퍼 `_resolve_imputed_file_path` 추가

### `backend/app/api/routes/projects.py`
- `project_to_dict()` 에 5종 dataType 점수 키 추가, 옛 컬럼은 폴백으로 사용

### `backend/app/api/routes/data.py`
- 파일 업로드 시 `_infer_data_type()` 호출하여 `DataFile.data_type` 컬럼에 자동 저장

### `backend/app/services/imputation_service.py`
- `_mochi_imputation` / `_missforest` / `_gain` / `_vae` mock 메서드 **전면 제거**
- `/home/humandeep/data-qc/uploads` 하드코딩 → `UPLOADS_DIR` (4곳)
- `_read_omics_file` / `_write_omics_file` 헬퍼 신설 → TSV + CSV 모두 지원
- `_run_per_file_imputer` 공용 루프로 mean/knn 의 중복 코드 통합
- `method="mochi"` 호출 시 명확한 `ValueError` 발생 (mock 반환 금지)

### `backend/app/services/remote_multiomics_service.py`
- 원격 `impute_multiomics.py` 스크립트의 `dim_rna=60660 / dim_protein=487 / dim_methyl=10000` 하드코딩 제거
- 입력 데이터 `df.shape[0]` 로부터 차원 동적 결정
- checkpoint 차원 불일치 시 즉시 `RuntimeError` (사일런트 실패 방지)
- 입력 파일 매처를 TSV + CSV 모두 지원하도록 확장
- 필수 3종 파일(rna/protein/methyl) 누락 시 명확한 에러

### `backend/app/services/validation_service.py`
- `_infer_data_type()` 키워드 매칭 정확도 보강 — clinical/phenotype 우선 매칭, `methyl→genomics` 명확화, `meta` 부분 매칭은 마지막 fallback

### `backend/app/db/init_db.py`
- `_seed_verification_rules()` 신설 — `get_default_rules()` 의 28개 GENE-QC 규칙을 전역 규칙으로 자동 시드 (`metric_id` 중복 시 건너뜀)
- 시드 데이터의 `data_type` 을 한글 → 명세서 영문 5종 으로 변경(`"전사체"→"transcriptomics"` 등)
- 옛 옵션 컬럼(`dna_quality_score` 등) 대신 5종 신규 컬럼에 시드

### `backend/requirements.txt`
- `reportlab>=4.0.0` 추가 (cupsfilter 대체)

## 데이터 흐름 & 연관 관계

```
[Frontend]
   │
   │ POST /api/validation/execute?project_id=X
   │      body: { enabledMetrics?, paramsOverrides? }
   ▼
[validation.py 라우트]
   ├─ DB(ValidationJob.create status=processing)
   └─ BackgroundTasks
         └─> _run_validation_task
                ├─ DB → file_data_types (DataFile.data_type | _infer_data_type)
                ├─ DB → legacy_validation_thresholds → paramsOverrides 변환
                ├─ validation_service.run_validation()
                │     ├─ check_comp_F001 / conf_F001 (raw_content)
                │     ├─ pd.read_csv (delimiter 자동감지, TSV/CSV)
                │     ├─ 19개 COLUMN 지표 (omics/metadata 데이터타입 가드)
                │     └─ check_cross_metrics (6개 X-지표)
                ├─ DB(ValidationJob.update status=completed, results JSON)
                └─ DB(Project.{5종}_quality_score, quality_score, validation_status)

[Frontend]
   │ GET /api/validation/status/{job_id}
   │ GET /api/validation/download-report/{project_id}  (reportlab PDF)
   ▼
```

보간 흐름:
```
POST /api/imputation/execute  body:{method, project_id, threshold, ...}
   ├─ method=mochi → _run_multiomics_imputation → RemoteMultiOmicsImputationService (SSH)
   └─ method=mean|knn|mice → ImputationService.run_imputation (로컬 sklearn)
                                  └─ UPLOADS_DIR/project_{id}/raw → imputed
```

규칙 CRUD:
```
GET /api/verification/rules
   ▼
[verification.py]
   └─ DB VerificationRule (28개 시드 + 사용자 정의)
       → _rule_to_response (신규 + 옛 필드 모두 포함)
```

## 잠재적 리스크 & 주의사항

### 1. DB 스키마 변경에 따른 마이그레이션 필요
- `verification_rules` 테이블의 옛 컬럼(`label/status/category/metric/condition/threshold`)이 제거되고
  명세서 §5 의 11개 신규 컬럼이 추가됨
- `projects` 테이블에 5종 dataType 점수 컬럼 + `legacy_validation_thresholds` 추가
- `data_files` 테이블에 `data_type` 컬럼 추가
- `validation_jobs` 테이블 신규
- **`recreate_tables.py` 또는 `init_database.py` 실행 필수**. Alembic 등 마이그레이션 도구를 사용하지 않는 프로젝트라 기존 데이터는 손실됨.

### 2. MySQL 인증 실패 미해결
- 터미널 로그에 `Access denied for user 'root'@'localhost' (1045)` 가 반복 발생 중
- `backend/.env` 의 `MYSQL_PASSWORD` 가 실제 DB 비밀번호와 불일치
- 본 PR 범위에서는 코드 외 설정 이슈라 수정하지 않음. 별도 안내 필요.

### 3. ValidationJob 결과 JSON 크기
- 28개 지표 × 다중 파일 × `affectedItems` 리스트(최대 20개)가 `ValidationJob.results` 단일 JSON 컬럼에 저장됨
- MySQL JSON 컬럼은 최대 1GB지만, 대용량 RNA 파일(60K 피처)에서 violated columns 가 수천 개가 나오면 JSON 직렬화·역직렬화 비용이 커질 수 있음
- 후속 개선 시 `metric_results` 별도 테이블로 정규화 가능

### 4. 한글 폰트 자동 등록 — 환경 의존
- `download_validation_report` 에서 시도하는 폰트 후보는 macOS / Ubuntu 기본 경로 위주
- 다른 Linux 배포판(CentOS, Alpine) 환경에서는 폰트가 없어 KoreanFont 등록 실패 → Helvetica 폴백 → 한글 깨짐 발생 가능
- 운영 환경별로 컨테이너에 NanumGothic 등 폰트를 추가 설치하거나 폰트 경로를 환경변수로 추출하는 후속 작업 필요

### 5. MOCHI 차원 동적 결정 시 가정
- 원격 `impute_multiomics.py` 가 `df.shape[0]` 을 feature 수로 사용 — 즉 **행=feature, 열=sample** 구조 가정
- 명세서 §0 의 "Sample × Feature 행렬" 과 가정 방향이 반대. 명세서대로 첫 컬럼이 sample_id 인 long-format 일 경우 차원이 뒤바뀜
- 기존 코드도 동일한 가정을 사용했고 운영 데이터가 (genes × samples) 형식임을 전제로 학습된 가중치를 사용 중이므로 본 PR에서는 가정 유지. 그러나 명세서와 실제 데이터 형식의 합의가 필요함.

### 6. 옛 한글 카테고리 매핑 추정치
- `_DIMENSION_TO_LEGACY_CATEGORY`: `Plausibility→"타당성"`, `Conformance→"적합성"` 으로 변환
- 기존 프론트엔드 샘플(`VERIFICATION_RULES_SAMPLES`) 의 카테고리는 `"정렬성/정밀성/완전성"` 으로, 신규 라벨과 일치하지 않음
- 프론트엔드의 `$category` 스타일 분기가 옛 라벨에만 색상을 매핑한다면 신규 카테고리는 기본 색으로 표시될 가능성 있음. 프론트엔드 라벨 사전 점검 필요.

### 7. `validation.py` 의 `LEGACY_THRESHOLD_KEYS` 미사용
- 모듈 상단에 정의되어 있으나 실제로는 참조되지 않는 dead code
- 추후 paramsOverrides 변환 로직 확장에 사용할 의도였으나 현재 `_legacy_params_overrides` 가 직접 키를 호출
- 다음 커밋에서 제거 권장

### 8. `plau_X001` / `plau_X002` 는 stub 유지
- AI 모듈 담당자 영역(`validation_service_ai_stubs.md`)으로 명세서에서 분리되어 있음
- 본 PR 범위에서 stub 유지. 결과 응답에는 `"[건너뜀] [AI 모듈] 별도 구현 필요"` 메시지로 노출됨.

## 개선 제안

### 1. `_legacy_params_overrides` 의 매핑 일반화
현재 `dna/rna/protein/methyl_threshold` 4개의 평균을 `comp_C002` / `comp_F003` 의 threshold 로 일괄 적용함. 명세서 §3 의 데이터타입별 임계값(`DEFAULT_MISSING_THRESHOLDS`)과 의미가 다를 수 있어, **dataType 별 paramsOverride** 로 분기 가능하도록 확장 권장.

```python
def _legacy_params_overrides(rules):
    # AS-IS: 단일 평균값 → comp_C002 / comp_F003 전역 적용
    # TO-BE: dataType별 분기 (validation_service 의 per-file 호출에서 활용)
    return {
        "comp_C002": {"threshold_by_data_type": {
            "genomics":        rules.get("dna_threshold"),
            "transcriptomics": rules.get("rna_threshold"),
            ...
        }},
    }
```
이를 위해서는 `validation_service.run_validation()` 의 params_overrides 시그니처도 dataType 인지하도록 확장 필요.

### 2. `ValidationJob` 결과 JSON 분리
중장기적으로 `validation_job_metrics` 테이블을 별도로 두고 `validation_job_id, metric_id, passed, value, details` 컬럼으로 정규화하면 통계 집계가 빨라짐.

### 3. `verification.py` 의 응답 직렬화 책임 분리
`_rule_to_response()` 는 라우트 모듈에 있는데 `validation.py` 등 다른 모듈에서도 동일한 직렬화가 필요해질 수 있음. `app/serializers/` 또는 Pydantic response model 로 추출 권장.

### 4. `_infer_data_type` 단일 위치화
명세서 §6.4 의 추론 로직이 `validation_service.py`, `data.py`, `validation.py` (간접적) 세 곳에서 사용. 본 PR에서 `validation_service._infer_data_type` 한 곳으로 통일했으나, 향후 케이스 확장 시 한 곳만 수정하면 되도록 `utils/data_type.py` 로 분리 권장.

### 5. `RemoteMultiOmicsImputationService` 의 conda 경로 탐색 횟수
원격에서 PyTorch 가능한 Python 환경을 9개 후보 경로 + 4개 conda activation 시도까지 13회 SSH 왕복을 수행함. 첫 성공 시 결과를 `Project` 또는 캐시 테이블에 저장해 재사용하면 보간 시작 시간을 크게 줄일 수 있음.

## 총평

명세서 v2 의 OMOP CDM DQM 28개 지표 체계가 정의만 되어 있고 실 동작은 13개에 그쳤던
구조적 결함을 정합화하는 변경. 핵심 변경은 다음 3가지로 요약:

1. **검증 흐름**: `validation.py` 라우트 → `validation_service` 위임 (이전: 자체 함수 13개 → 이후: 명세서 28개)
2. **데이터 모델**: 명세서 §5 의 11필드를 DB 에 1:1 반영, 결과 in-memory → DB 영속화
3. **보간 흐름**: mock fallback / 하드코딩 차원 / 잘못된 경로 모두 제거하고 원격 AI 경로 단일화

코드 가독성 측면에서 큰 함수의 분해(`_run_per_file_imputer` 등)와 어댑터 분리
(`_rule_to_response` / `_payload_to_rule_fields`)로 중복이 줄었음.

리스크는 주로 **운영 측 후속 조치**에 집중됨 — DB 재생성 필요, MySQL 인증 정정,
배포 환경 한글 폰트 설치, 프론트엔드 카테고리 라벨 정합성 확인.

명세서 일치도 환산:
| 영역 | 이전 | 이후 |
| ---- | ---- | ---- |
| API 활성 지표 수 | 13 / 28 | 28 / 28 (X-지표 2개는 명세서상 stub) |
| 명세서 §5 필드 DB 반영 | 0 / 11 | 11 / 11 |
| dataType 5종 일관성 | 부분(라벨링 버그 포함) | 일관 |
| 검증 결과 영속화 | in-memory | DB |
| 보간 mock 반환 | ❌ | ✅ 제거 |
| 크로스 플랫폼 PDF | ❌ (macOS only) | ✅ |

후속으로 다음 PR 로 권장:
- Alembic 도입 또는 마이그레이션 스크립트 작성
- 프론트엔드 카테고리/라벨 명세서 영문 5종으로 표준화
- `validation_job_metrics` 정규화
