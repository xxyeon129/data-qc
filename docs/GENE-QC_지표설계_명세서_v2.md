# GENE-QC 품질지표 설계 명세서 v2.0
> OMOP CDM DQM 기반 · 오믹스 + 메타데이터 파일 검증 특화  
> 작성일: 2026-03-04 | 가천대학교 의료데이터연구실

---

## 0. 문서 목적

이 문서는 OMOP CDM DQM 지표 체계(dq_quality_metric.xlsx)를 파일 기반  
유전체 데이터 품질관리 도구(GENE-QC)에 맞게 재설계한 결과물입니다.

**적용 데이터 종류**

| 분류 | 포맷 | 구조 | 예시 |
|------|------|------|------|
| 오믹스 (omics) | TSV / CSV | Sample × Feature 행렬 | RNA-seq, DNA methylation, Proteomics, Metabolomics |
| 메타데이터 (metadata) | TSV / CSV | Sample × Clinical variable | 나이, 성별, 진단일, 병기 등 |

---

## 1. OMOP CDM DQM → GENE-QC 매핑 원칙

OMOP CDM DQM은 관계형 데이터베이스(테이블-컬럼-값) 구조를 전제로 설계된 지표 체계입니다.  
GENE-QC는 파일(TSV/CSV) 기반이므로 다음과 같이 계층을 변환합니다.

| OMOP 계층 | GENE-QC 계층 | 설명 |
|-----------|-------------|------|
| TABLE level | FILE level | 파일 전체 단위 검사 |
| FIELD level | COLUMN level | 파일 내 컬럼 단위 검사 |
| CONCEPT level | VALUE level | 컬럼 내 특정 값 검사 |
| Verification context | 구조/형식 검사 | 사실 확인 가능한 검사 (헤더, 타입, 형식 등) |
| Validation context | 의미/기준 검사 | 외부 기준과의 비교 (범위, 허용값 등) |

### 1.1 OMOP 지표 ID → GENE-QC metricId 대응표

| OMOP metric_id | OMOP metric_name | GENE-QC metricId | 적용 레벨 |
|---------------|-----------------|-----------------|---------|
| 1000 | cdmTable | conf_F001 | FILE |
| 1400 | cdmField | conf_C003 | COLUMN |
| 1500 | isRequired | comp_C001 | COLUMN |
| 1600 | cdmDatatype | conf_C002 | COLUMN |
| 1700 | isPrimaryKey | conf_C001 | COLUMN |
| 1800 | isForeignKey | conf_X001 | VALUE (교차) |
| 1900 | fkDomain / valueSet | conf_V001 | VALUE |
| 2200 | measureValueCompleteness | comp_C002 | COLUMN |
| 2255 | isConditionalRequired | comp_C004 | COLUMN (조건부) |
| 2600 | plausibleValueLow | plau_C001 | COLUMN |
| 2700 | plausibleValueHigh | plau_C002 | COLUMN |
| 2800 | plausibleTemporalAfter | plau_T001 | COLUMN |
| 3300 | plausibleStartBeforeEnd | plau_T002 | COLUMN |
| 3400 | plausibleGender | plau_V001 | VALUE |
| - (파생) | plausibleAge | plau_V002 | VALUE |
| - (파생) | IQR outlier | plau_C003 | COLUMN |
| - (파생) | zeroVariance | plau_C004 | COLUMN |
| - (파생) | crossSampleMatch | comp_X001 | VALUE (교차) |
| - (파생) | metaOmicsLinkage | comp_X003 | VALUE (교차) |
| - (파생) | crossOmicsCorrelation | plau_X002 | VALUE (교차) |

---

## 2. 전체 지표 목록

### 2.1 완전성 (Completeness) — 기초 품질

| metricId | 지표명 | metricLevel | context | subcategory | severity | 적용 데이터 |
|----------|--------|-------------|---------|-------------|----------|------------|
| comp_F001 | 파일 헤더 존재 여부 | FILE | Verification | Relational | fatal | omics + metadata |
| comp_C001 | 샘플 ID 컬럼 필수 존재 | COLUMN | Verification | Relational | fatal | omics + metadata |
| comp_C002 | 컬럼별 결측률 검사 | COLUMN | Verification | - | warning | omics + metadata |
| comp_C003 | 행(샘플) 완전성 검사 | COLUMN | Verification | - | warning | omics + metadata |
| comp_F003 | 전체 데이터 결측률 | FILE | Validation | - | warning | omics 전용 |
| comp_C004 | 조건부 필수 컬럼 검사 | COLUMN | Verification | Conditional | error | metadata 전용 |

**comp_C004 상세 (조건부 필수 — OMOP isConditionalRequired 파생)**
- 조건: 특정 컬럼이 존재하거나 특정 값을 가질 때, 다른 컬럼이 반드시 존재해야 함
- 예: diagnosis_date 컬럼이 있으면 diagnosis_code 컬럼도 필수
- 파라미터: conditionColumn, conditionValue, requiredColumn

### 2.2 완전성 (Completeness) — 심화 품질 (교차검증)

| metricId | 지표명 | metricLevel | context | subcategory | severity | 적용 데이터 |
|----------|--------|-------------|---------|-------------|----------|------------|
| comp_X001 | 데이터셋 간 샘플 매칭률 | VALUE | Validation | Relational | warning | omics + metadata |
| comp_X002 | 전체 데이터셋 공통 샘플 수 | VALUE | Validation | Relational | error | omics + metadata |
| comp_X003 | 메타데이터-오믹스 샘플 연결성 | VALUE | Validation | Relational | warning | metadata ↔ omics |

심화 품질 활성화 조건: 2개 이상 파일 등록 + 각 파일에 dataType 지정 완료

### 2.3 타당성 (Plausibility) — 기초 품질 (Atemporal)

| metricId | 지표명 | metricLevel | context | subcategory | severity | 적용 데이터 |
|----------|--------|-------------|---------|-------------|----------|------------|
| plau_C001 | 발현값 하한 검사 | COLUMN | Verification | Atemporal | characterization | omics 전용 |
| plau_C002 | 발현값 상한 검사 | COLUMN | Verification | Atemporal | characterization | omics 전용 |
| plau_C003 | IQR 기반 이상치 검사 | COLUMN | Verification | Atemporal | warning | omics 전용 |
| plau_C004 | 상수값 컬럼 탐지 (분산=0) | COLUMN | Verification | Atemporal | warning | omics 전용 |
| plau_V001 | 성별 값 허용범위 검사 | VALUE | Validation | Atemporal | error | metadata 전용 |
| plau_V002 | 연령 값 범위 검사 | VALUE | Validation | Atemporal | error | metadata 전용 |
| plau_V003 | 수치형 컬럼 음수값 허용 검사 | VALUE | Verification | Atemporal | warning | omics 선택 |

**plau_V003 상세**: 발현량 데이터에서 음수값이 허용되지 않아야 하는 경우(예: raw count 데이터)
- 파라미터: targetColumn, allowNegative (boolean)

### 2.4 타당성 (Plausibility) — 기초 품질 (Temporal)

| metricId | 지표명 | metricLevel | context | subcategory | severity | 적용 데이터 |
|----------|--------|-------------|---------|-------------|----------|------------|
| plau_T001 | 날짜 순서 타당성 (시작 <= 종료) | COLUMN | Verification | Temporal | error | metadata 전용 |
| plau_T002 | 진단일-출생일 순서 검사 | COLUMN | Verification | Temporal | error | metadata 전용 |

**plau_T002 상세** (OMOP plausibleAfterBirth 파생):
- 진단일/등록일이 출생일 이후인지 확인
- 파라미터: birthColumn, eventColumn

### 2.5 타당성 (Plausibility) — 심화 품질

| metricId | 지표명 | metricLevel | context | subcategory | severity | 적용 데이터 |
|----------|--------|-------------|---------|-------------|----------|------------|
| plau_X001 | 메타데이터-오믹스 subtype 일관성 | VALUE | Validation | Atemporal | convention | metadata ↔ transcriptomics/proteomics |
| plau_X002 | 오믹스 간 발현 상관관계 | VALUE | Validation | Atemporal | warning | transcriptomics ↔ proteomics |

### 2.6 적합성 (Conformance) — 기초 품질 (Relational)

| metricId | 지표명 | metricLevel | context | subcategory | severity | 적용 데이터 |
|----------|--------|-------------|---------|-------------|----------|------------|
| conf_F001 | 파일 형식(구분자) 일관성 | FILE | Verification | Relational | fatal | omics + metadata |
| conf_C001 | 샘플 ID 중복 검사 | COLUMN | Verification | Relational | fatal | omics + metadata |
| conf_C003 | 컬럼명 형식 검사 (공백/특수문자) | COLUMN | Verification | Relational | convention | omics + metadata |
| conf_C004 | 샘플 ID 형식 검사 (정규식) | COLUMN | Verification | Relational | convention | omics + metadata |

### 2.7 적합성 (Conformance) — 기초 품질 (Value)

| metricId | 지표명 | metricLevel | context | subcategory | severity | 적용 데이터 |
|----------|--------|-------------|---------|-------------|----------|------------|
| conf_C002 | 수치형 컬럼 데이터 타입 검사 | COLUMN | Verification | Value | error | omics 전용 |
| conf_V001 | 허용값 목록 준수 검사 | VALUE | Verification | Value | error | metadata 전용 |
| conf_V002 | 날짜 형식 표준 검사 | VALUE | Verification | Value | error | metadata 전용 |

**conf_V002 상세** (OMOP cdmDatatype 파생):
- 날짜 컬럼이 지정된 형식(YYYY-MM-DD 등)을 따르는지 확인
- 파라미터: targetColumn, dateFormat

### 2.8 적합성 (Conformance) — 심화 품질

| metricId | 지표명 | metricLevel | context | subcategory | severity | 적용 데이터 |
|----------|--------|-------------|---------|-------------|----------|------------|
| conf_X001 | 데이터셋 간 ID 형식 일관성 | VALUE | Verification | Relational | error | omics + metadata |

---

## 3. 데이터 유형별 적용 가능 지표 매트릭스

| metricId | genomics | transcriptomics | proteomics | metabolomics | metadata |
|----------|:--------:|:---------------:|:----------:|:------------:|:--------:|
| comp_F001 | O | O | O | O | O |
| comp_C001 | O | O | O | O | O |
| comp_C002 | O | O | O | O | O |
| comp_C003 | O | O | O | O | O |
| comp_F003 | O | O | O | O | - |
| comp_C004 | - | - | - | - | O |
| comp_X001 | O | O | O | O | O |
| comp_X002 | O | O | O | O | O |
| comp_X003 | O | O | O | O | O(기준) |
| plau_C001 | O | O | O | O | - |
| plau_C002 | O | O | O | O | - |
| plau_C003 | O | O | O | O | - |
| plau_C004 | O | O | O | O | - |
| plau_V001 | - | - | - | - | O |
| plau_V002 | - | - | - | - | O |
| plau_V003 | O | O | O | O | - |
| plau_T001 | - | - | - | - | O |
| plau_T002 | - | - | - | - | O |
| plau_X001 | - | O | O | - | O |
| plau_X002 | - | O | O | - | - |
| conf_F001 | O | O | O | O | O |
| conf_C001 | O | O | O | O | O |
| conf_C002 | O | O | O | O | - |
| conf_C003 | O | O | O | O | O |
| conf_C004 | O | O | O | O | O |
| conf_V001 | - | - | - | - | O |
| conf_V002 | - | - | - | - | O |
| conf_X001 | O | O | O | O | O |

---

## 4. 검증 유형(validationType) 정의 및 파라미터 스키마

### 4.1 기초 검증 유형

**threshold — 임계값 비교**
```json
{
  "metric": "missing_rate | row_completeness | total_missing_rate | outlier_rate_iqr | zero_variance_columns",
  "operator": "<= | >= | < | > | ==",
  "threshold": 30,
  "unit": "% | 개 | 점"
}
```
적용 지표: comp_C002, comp_C003, comp_F003, plau_C003, plau_C004

**range — 값 범위 검사 (오믹스 발현값)**
```json
{
  "min": -100,
  "max": 100,
  "unit": "발현값 단위"
}
```
적용 지표: plau_C001, plau_C002

**column_range — 특정 컬럼 값 범위**
```json
{
  "targetColumn": "age",
  "min": 0,
  "max": 120
}
```
적용 지표: plau_V002

**value_set — 허용값 목록 검사**
```json
{
  "targetColumn": "sex",
  "allowedValues": ["M", "F", "male", "female", "Unknown"]
}
```
적용 지표: plau_V001, conf_V001

**date_order — 날짜 순서 검사**
```json
{
  "startColumn": "start_date",
  "endColumn": "end_date"
}
```
적용 지표: plau_T001, plau_T002

**date_format — 날짜 형식 검사**
```json
{
  "targetColumn": "diagnosis_date",
  "dateFormat": "YYYY-MM-DD"
}
```
적용 지표: conf_V002

**duplicate_check — 중복값 검사**
```json
{
  "targetColumn": "first_column | custom_column_name"
}
```
적용 지표: conf_C001

**regex_pattern — 정규식 패턴 검사**
```json
{
  "targetColumn": "sample_id",
  "pattern": "^[A-Za-z0-9_-]+$",
  "patternDescription": "영문자, 숫자, _, - 만 허용"
}
```
적용 지표: conf_C004

**datatype_check — 데이터 타입 검사**
```json
{
  "expectedType": "numeric | integer | string | date",
  "targetColumn": "all_except_first | specific_column_name",
  "excludeColumns": ["sample_id", "SampleID"]
}
```
적용 지표: conf_C002

**file_format — 파일 형식(구분자) 일관성**
```json
{
  "checkDelimiterConsistency": true
}
```
적용 지표: conf_F001

**header_exists — 헤더 행 존재 여부**
```json
{
  "minColumns": 2
}
```
적용 지표: comp_F001

**column_exists — 필수 컬럼 존재 여부**
```json
{
  "targetColumn": "first_column | specific_column_name",
  "customColumn": ""
}
```
적용 지표: comp_C001

**column_format — 컬럼명 형식 검사**
```json
{
  "allowedPattern": "^[a-zA-Z0-9_.가-힣-]+$",
  "disallowedChars": [" ", "/", "\\", "\"", "'"]
}
```
적용 지표: conf_C003

**conditional_required — 조건부 필수 컬럼**
```json
{
  "conditionColumn": "diagnosis_date",
  "conditionValue": null,
  "requiredColumn": "diagnosis_code"
}
```
적용 지표: comp_C004

**negative_check — 음수값 허용 검사**
```json
{
  "targetColumn": "all_except_first",
  "allowNegative": false
}
```
적용 지표: plau_V003

### 4.2 교차(심화) 검증 유형

**cross_threshold — 다중 파일 임계값 비교**
```json
{
  "metric": "sample_matching_rate | common_sample_count | meta_omics_linkage",
  "operator": ">=",
  "threshold": 80,
  "unit": "% | 개"
}
```
적용 지표: comp_X001, comp_X002, comp_X003

**cross_correlation — 교차 발현 상관관계**
```json
{
  "targetDataTypes": ["transcriptomics", "proteomics"],
  "minCorrelation": 0.3,
  "method": "pearson | spearman"
}
```
적용 지표: plau_X002

**cross_consistency — 교차 일관성 검사**
```json
{
  "matchColumn": "sample_id",
  "compareColumn": "subtype"
}
```
적용 지표: plau_X001

**cross_format — 다중 파일 ID 형식 일관성**
```json
{
  "compareColumn": "sample_id"
}
```
적용 지표: conf_X001

---

## 5. 커스텀 규칙 필드 정의

### 5.1 확정 필드 (피드백 260122 기준 — 반드시 포함)

| 필드명 | 타입 | 허용값 | 설명 |
|--------|------|--------|------|
| name | string | - | 규칙 이름 (사용자 정의) |
| dimension | enum | Completeness, Plausibility, Conformance | 품질 차원 |
| level | enum | basic, advanced | 품질 수준 (기초/심화) |
| severity | enum | fatal, error, warning, convention, characterization | 심각도 |
| description | string | - | 규칙 설명 |
| dataTypes | array | genomics, transcriptomics, proteomics, metabolomics, metadata | 적용 데이터 유형 |

### 5.2 검증 수행 필드

| 필드명 | 타입 | 허용값 | 설명 |
|--------|------|--------|------|
| validationType | enum | 위 4.1~4.2 목록 | 검증 유형 |
| parameters | object | validationType별 스키마 | 검증 파라미터 |

### 5.3 OMOP CDM DQM 확장 필드 (내부 추적용)

| 필드명 | 타입 | 허용값 | 설명 |
|--------|------|--------|------|
| metricId | string | comp_*, plau_*, conf_* | 내부 지표 ID |
| metricLevel | enum | FILE, COLUMN, VALUE | OMOP 계층 대응 |
| context | enum | Verification, Validation | 검증 맥락 |
| subcategory | enum | Relational, Atemporal, Temporal, Value, Conditional, Computational | OMOP subcategory 대응 |
| isCustom | boolean | true, false | 사용자 정의 규칙 여부 |
| createdAt | datetime | ISO 8601 | 생성일시 |
| author | string | - | 생성자 |

### 5.4 심각도(severity) 값 정의

| severity | 의미 | 처리 방향 |
|----------|------|----------|
| fatal | 데이터 사용 불가, 즉시 수정 필수 | 검증 중단 또는 최우선 처리 |
| error | 분석 결과에 심각한 영향 | 수정 권고 |
| warning | 주의 필요, 사용 가능 | 검토 후 판단 |
| convention | 표준 준수 권고 | 권고사항 |
| characterization | 데이터 분포 프로파일링 (합격/불합격 없음) | 참고용 |

---

## 6. 코드 적용 가이드 (JSX 구조 변경사항)

### 6.1 상수 선언 위치 — 컴포넌트 외부 최상단

```javascript
// 컴포넌트 함수 밖 (최상단)
const ALL_DATA_TYPES = ['genomics', 'transcriptomics', 'proteomics', 'metabolomics', 'metadata'];
const OMICS_TYPES    = ['genomics', 'transcriptomics', 'proteomics', 'metabolomics'];

const DATA_TYPE_LABELS = {
  genomics:        '유전체 (DNA)',
  transcriptomics: '전사체 (RNA)',
  proteomics:      '단백질체',
  metabolomics:    '대사체',
  metadata:        '메타데이터 (임상정보)'
};

const SEVERITY_CONFIG = {
  fatal:           { label: 'FATAL',           color: '#dc2626', bg: '#fef2f2' },
  error:           { label: 'ERROR',           color: '#ea580c', bg: '#fff7ed' },
  warning:         { label: 'WARNING',         color: '#ca8a04', bg: '#fefce8' },
  convention:      { label: 'CONVENTION',      color: '#2563eb', bg: '#eff6ff' },
  characterization:{ label: 'CHARACTERIZATION',color: '#6b7280', bg: '#f9fafb' }
};
```

### 6.2 규칙 관리 2페이지 구조

```javascript
// 상태 변수
const [rulesSubTab, setRulesSubTab] = useState('select'); // 'select' | 'manage'

// 렌더링
{activeTab === 'rules' && (
  <>
    {/* 서브탭 */}
    <div>
      <button onClick={() => setRulesSubTab('select')}>규칙 선택</button>
      <button onClick={() => setRulesSubTab('manage')}>규칙 관리</button>
    </div>

    {rulesSubTab === 'select' && <RuleSelectionPage />}
    {rulesSubTab === 'manage' && <RuleManagementPage />}
  </>
)}
```

### 6.3 파일 업로드 CSV/TSV 구분자 자동 감지

```javascript
const detectDelimiter = (content) => {
  const firstLine = content.split('\n')[0];
  const tabCount   = (firstLine.match(/\t/g) || []).length;
  const commaCount = (firstLine.match(/,/g)  || []).length;
  return tabCount >= commaCount ? '\t' : ',';
};

// handleFileUpload 내 사용
const delimiter  = detectDelimiter(content);
const headers    = lines[0].split(delimiter);
const rows       = lines.slice(1).map(line => line.split(delimiter));
```

### 6.4 파일명 기반 데이터 유형 자동 추론

```javascript
const inferDataType = (fileName) => {
  const lower = fileName.toLowerCase();
  if (lower.includes('rna') || lower.includes('transcriptom') || lower.includes('expression')) 
    return 'transcriptomics';
  if (lower.includes('dna') || lower.includes('methylat') || lower.includes('snp') || lower.includes('genomic')) 
    return 'genomics';
  if (lower.includes('protein') || lower.includes('proteom')) 
    return 'proteomics';
  if (lower.includes('metabol')) 
    return 'metabolomics';
  if (lower.includes('meta') || lower.includes('clinical') || lower.includes('phenotype')) 
    return 'metadata';
  return '';
};
```

---

## 7. 피드백 260122 반영사항 정리

### 7.1 메인 페이지 프로젝트 카드

표시 항목:
- 전체 샘플 수
- 데이터 파일 종류 태그 (DNA, RNA, Protein 등)
- 총 데이터 용량
- 생성일자 / 완료여부 / 진행중 상태 배지
- 검증 완료시: 결과 요약 (통과/경고/실패 건수)
- 검증 미완료시: "검증 수행 시 통계량 확인이 가능합니다"

### 7.2 품질검증 워크플로우 (Option B — 자동 반영)

```
검증수행(1) → 품질관리(2) [보간/수정] → 자동 재검증 → 결과도출(3)
```

품질관리 완료 후 파일이 자동으로 프로젝트에 적용되어 재검증 결과 도출.
별도 다운로드 후 재업로드 불필요.

### 7.3 규칙 UI 2페이지 분리

- Page 1 (규칙 선택): 프로젝트별 적용 규칙 체크박스 선택
  - 차원별 그룹화 (완전성 / 타당성 / 적합성)
  - 기초/심화 필터
  - 업로드된 파일의 dataType에 맞는 규칙 자동 필터링
- Page 2 (규칙 관리): 전체 규칙 조회/수정/삭제 + 커스텀 규칙 추가
  - 수정 모달: 확정 5개 필드 + 검증유형/파라미터

### 7.4 커스텀 규칙 UI 필드 순서

1. 규칙 이름
2. 품질 차원 (select)
3. 품질 수준 (select)
4. 심각도 (select)
5. 설명 (textarea)
6. 적용 데이터 유형 (checkbox group)
7. 검증 유형 (select) → 동적 파라미터 폼 표시
8. 검증 파라미터 (dynamic form)

---

## 8. 미결 사항

| 항목 | 상태 | 비고 |
|------|------|------|
| 보간 이외의 데이터 수정 기능 범위 | 확인 중 | 필터링? 이상치 대체? 정규화? |
| 결과보고서 PDF 포함 통계량 정의 | 확인 중 | 선행논문 기반 예시 제공 예정 |
| 배치효과(BatchEval) 지표 연동 | 예정 | 심화 Plausibility 확장 |
| VCF 파서 구현 | 예정 | Variant x Sample 역전 구조 |
| proMODMatcher 샘플 정확도 검증 연동 | 예정 | 심화 Completeness 확장 |
