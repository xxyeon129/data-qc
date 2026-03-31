# AI 모듈 담당자 구현 요청 사항

> 아래 항목들은 `validation_service.py`에 stub으로 처리되어 있으며,
> 통계/ML 전문 구현이 필요한 항목입니다.
> `_skip()` 반환 + "[AI 모듈] 별도 구현 필요" 메시지로 표시됩니다.

---

## [요청 1] plau_C003 — IQR 기반 이상치 탐지

- **현재 상태**: `check_plau_C003()` 함수 구현됨 (NumPy 기반 배치 IQR 연산)
- **성능 검토 필요**: RNA 데이터 기준 60,660 피처 × N 샘플 행렬에서
  `np.nanpercentile(..., axis=0)` 호출 시 메모리/시간 프로파일링 필요
- **최적화 방안**:
  - 청크(chunk) 처리: 피처를 1,000개씩 나누어 처리
  - 또는 scipy.stats.iqr() vectorized 버전 활용
  - 대안: Dask 기반 지연 계산

---

## [요청 2] plau_X002 — 오믹스 간 발현 상관관계 (cross_correlation)

- **현재 상태**: `check_cross_metrics()` 내에서 `_skip()` 반환 중
- **구현 필요 사항**:
  1. transcriptomics ↔ proteomics 파일 매핑 (공통 샘플 추출)
  2. 유전자/단백질 ID 매핑 테이블 필요 (gene_symbol → protein accession)
  3. Pearson/Spearman 상관계수 계산 (scipy.stats.pearsonr / spearmanr)
  4. 전체 상관관계 행렬의 평균/중앙값 반환
- **참고 파라미터**:
  ```json
  {
    "targetDataTypes": ["transcriptomics", "proteomics"],
    "minCorrelation": 0.3,
    "method": "pearson"
  }
  ```

---

## [요청 3] plau_X001 — 메타데이터-오믹스 Subtype 일관성

- **현재 상태**: `check_cross_metrics()` 내에서 `_skip()` 반환 중
- **구현 필요 사항**:
  1. metadata 파일의 `subtype` 컬럼 값 목록 추출
  2. omics 파일에서 subtype 관련 피처(gene signature) 정의 방법 결정
     - 옵션 A: PAM50 gene set 기반 분류
     - 옵션 B: 메타데이터 subtype 레이블과 mRNA 발현 패턴 비교
  3. 일관성 판단 기준(임계값) 정의 필요
- **참고 파라미터**:
  ```json
  {
    "matchColumn": "sample_id",
    "compareColumn": "subtype"
  }
  ```

---

## [요청 4] plau_C004 — 상수값 컬럼 탐지 (분산=0)

- **현재 상태**: `check_plau_C004()` 함수 구현됨 (`df.var(ddof=0) == 0`)
- **성능 검토 필요**: 60,660 피처 × N 샘플에서 `.var()` 전체 계산 프로파일링
- **최적화 방안**:
  - `(df == df.iloc[0]).all()` 방식으로 첫 행과 전체 비교 (메모리 효율적)
  - 또는 NumPy: `np.ptp(vals, axis=0) == 0` (peak-to-peak = 0)

---

## [요청 5] MOCHI 서비스 — dataType 체계 변경 대응

- **관련 파일**: `backend/app/services/multiomics_imputation_service.py`
- **변경 필요 사항**:
  - 현재: 하드코딩된 `RNA(60,660)`, `Protein(487)`, `Methyl(10,000)` 키명
  - 신규: `transcriptomics`, `proteomics`, `genomics` 키명으로 매핑 변경
  - Generator 초기화 로직 (`Gp`, `Gr`, `Gm`) 과 입출력 파라미터 확인 필요
- **구체적 변경 위치**:
  ```python
  # 기존
  data_type == "rna" → "transcriptomics"
  data_type == "protein" → "proteomics"
  data_type == "methyl" → "genomics" (또는 별도 methylation 타입)
  ```

---

## 우선순위 제안

| 순서 | 항목 | 이유 |
|------|------|------|
| 1 | MOCHI 타입 매핑 | 기존 보간 기능 정상화에 필수 |
| 2 | plau_C004 성능 | 이미 구현됨, 성능 검토만 필요 |
| 3 | plau_C003 성능 | 이미 구현됨, 성능 검토만 필요 |
| 4 | plau_X002 | ID 매핑 테이블 확보 후 구현 가능 |
| 5 | plau_X001 | subtype 정의 협의 후 구현 |
