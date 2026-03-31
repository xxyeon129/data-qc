import React, { useState, useCallback } from 'react';

// ── 전역 상수: 컴포넌트 외부에 선언 (getDefaultRules 내부 참조 문제 방지) ──
const ALL_DATA_TYPES = ['genomics', 'transcriptomics', 'proteomics', 'metabolomics', 'metadata'];
const OMICS_TYPES    = ['genomics', 'transcriptomics', 'proteomics', 'metabolomics'];


const SEVERITY_CONFIG = {
  fatal:            { label: 'FATAL',            color: '#dc2626', bg: '#fef2f2', border: '#fca5a5' },
  error:            { label: 'ERROR',            color: '#ea580c', bg: '#fff7ed', border: '#fdba74' },
  warning:          { label: 'WARNING',          color: '#ca8a04', bg: '#fefce8', border: '#fde047' },
  convention:       { label: 'CONVENTION',       color: '#2563eb', bg: '#eff6ff', border: '#93c5fd' },
  characterization: { label: 'CHARACTERIZATION', color: '#6b7280', bg: '#f9fafb', border: '#d1d5db' }
};

// 파일명 기반 데이터 유형 자동 추론
const inferDataType = (fileName) => {
  const lower = fileName.toLowerCase();
  if (lower.includes('rna') || lower.includes('transcriptom') || lower.includes('expression')) return 'transcriptomics';
  if (lower.includes('dna') || lower.includes('methylat') || lower.includes('snp') || lower.includes('genomic')) return 'genomics';
  if (lower.includes('protein') || lower.includes('proteom')) return 'proteomics';
  if (lower.includes('metabol')) return 'metabolomics';
  if (lower.includes('meta') || lower.includes('clinical') || lower.includes('phenotype')) return 'metadata';
  return '';
};

// CSV/TSV 구분자 자동 감지
const detectDelimiter = (content) => {
  const firstLine = content.split('\n')[0];
  const tabCount   = (firstLine.match(/\t/g) || []).length;
  const commaCount = (firstLine.match(/,/g)  || []).length;
  return tabCount >= commaCount ? '\t' : ',';
};
import { 
  CheckCircle, XCircle, AlertTriangle, Upload, Settings, Play, Plus, 
  Trash2, Edit3, Search, Filter, Download, FileText, Database,
  ChevronDown, ChevronRight, Info, HelpCircle, Layers, Link2
} from 'lucide-react';

const OmicsQualityValidator = () => {
  // 탭 상태
  const [activeTab, setActiveTab] = useState('validation');
  const [activeRuleTab, setActiveRuleTab] = useState('basic'); // basic or advanced
  const [rulesSubTab, setRulesSubTab] = useState('select');    // 'select' | 'manage'
  
  // 데이터 관리
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [selectedDataType, setSelectedDataType] = useState('');
  
  // 규칙 관리
  const [rules, setRules] = useState(getDefaultRules());
  const [selectedRules, setSelectedRules] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterDimension, setFilterDimension] = useState('all');
  const [filterLevel, setFilterLevel] = useState('all');
  
  // 규칙 생성/편집 모달
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [ruleForm, setRuleForm] = useState(getEmptyRuleForm());
  
  // 검증 상태
  const [isValidating, setIsValidating] = useState(false);
  const [validationResults, setValidationResults] = useState(null);
  
  // 카테고리 확장 상태
  const [expandedDimensions, setExpandedDimensions] = useState({
    Completeness: true,
    Plausibility: true,
    Conformance: true
  });

  // 기본 규칙 정의
  // ── 데이터 유형: 전역 상수 ALL_DATA_TYPES, OMICS_TYPES 사용 ──

  function getDefaultRules() {
    return [
      // ═══════════════════════════════════════════════════════
      // COMPLETENESS (완전성)  ── 기초 품질 (FILE / COLUMN level)
      // OMOP 대응: cdmTable, isRequired, measureValueCompleteness 등
      // ═══════════════════════════════════════════════════════
      {
        id: 'comp_F001',
        metricId: 'comp_F001',
        metricLevel: 'FILE',
        context: 'Verification',
        subcategory: 'Relational',
        name: '파일 헤더 존재 여부',          // OMOP: cdmTable
        dimension: 'Completeness',
        level: 'basic',
        description: '파일에 헤더 행이 존재하고 1개 이상의 컬럼을 포함하는지 확인합니다.',
        dataTypes: ALL_DATA_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'header_exists',
        parameters: { minColumns: 2 },
        severity: 'fatal'
      },
      {
        id: 'comp_C001',
        metricId: 'comp_C001',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: 'Relational',
        name: '샘플 ID 컬럼 필수 존재',        // OMOP: isRequired
        dimension: 'Completeness',
        level: 'basic',
        description: '첫 번째 컬럼(샘플 ID)이 NULL 없이 존재하는지 확인합니다. 샘플 식별자가 없으면 교차 검증이 불가합니다.',
        dataTypes: ALL_DATA_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'column_exists',
        parameters: { targetColumn: 'first_column', customColumn: '' },
        severity: 'fatal'
      },
      {
        id: 'comp_C002',
        metricId: 'comp_C002',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: null,
        name: '컬럼별 결측률 검사',             // OMOP: measureValueCompleteness
        dimension: 'Completeness',
        level: 'basic',
        description: '각 컬럼의 결측값(빈 값, NA, null, NaN) 비율을 검사합니다.',
        dataTypes: ALL_DATA_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'threshold',
        parameters: { metric: 'missing_rate', operator: '<=', threshold: 30, unit: '%' },
        severity: 'warning'
      },
      {
        id: 'comp_C003',
        metricId: 'comp_C003',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: null,
        name: '행(샘플) 완전성 검사',
        dimension: 'Completeness',
        level: 'basic',
        description: '각 행(샘플)에서 유효한 값의 비율이 임계값 이상인지 검사합니다.',
        dataTypes: ALL_DATA_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'threshold',
        parameters: { metric: 'row_completeness', operator: '>=', threshold: 50, unit: '%' },
        severity: 'warning'
      },
      {
        id: 'comp_F003',
        metricId: 'comp_F003',
        metricLevel: 'FILE',
        context: 'Validation',
        subcategory: null,
        name: '전체 데이터 결측률',             // OMOP: measureSampleCompleteness
        dimension: 'Completeness',
        level: 'basic',
        description: '전체 데이터셋의 결측값 비율을 검사합니다. 오믹스 데이터 전용 (DNA 99%, RNA 80%, Protein 75% 기준 권고).',
        dataTypes: OMICS_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'threshold',
        parameters: { metric: 'total_missing_rate', operator: '<=', threshold: 20, unit: '%' },
        severity: 'warning'
      },

      // ── Completeness 심화 품질 (교차 검증) ────────────────
      // OMOP 대응: isForeignKey (교차 ID 검사), measurePersonCompleteness
      {
        id: 'comp_X001',
        metricId: 'comp_X001',
        metricLevel: 'VALUE',
        context: 'Validation',
        subcategory: 'Relational',
        name: '데이터셋 간 샘플 매칭률',        // OMOP: isForeignKey (교차 적용)
        dimension: 'Completeness',
        level: 'advanced',
        description: '여러 데이터셋 간 공통으로 존재하는 샘플 ID의 비율을 검사합니다.',
        dataTypes: ALL_DATA_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'cross_threshold',
        parameters: { metric: 'sample_matching_rate', operator: '>=', threshold: 80, unit: '%' },
        severity: 'warning'
      },
      {
        id: 'comp_X002',
        metricId: 'comp_X002',
        metricLevel: 'VALUE',
        context: 'Validation',
        subcategory: 'Relational',
        name: '전체 데이터셋 공통 샘플 수',
        dimension: 'Completeness',
        level: 'advanced',
        description: '모든 등록된 데이터셋에 공통으로 존재하는 샘플의 수를 검사합니다.',
        dataTypes: ALL_DATA_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'cross_threshold',
        parameters: { metric: 'common_sample_count', operator: '>=', threshold: 10, unit: '개' },
        severity: 'error'
      },
      {
        id: 'comp_X003',
        metricId: 'comp_X003',
        metricLevel: 'VALUE',
        context: 'Validation',
        subcategory: 'Relational',
        name: '메타데이터-오믹스 샘플 연결성',
        dimension: 'Completeness',
        level: 'advanced',
        description: '메타데이터의 샘플 ID가 각 오믹스 파일에 모두 존재하는지 확인합니다 (단방향: 메타 → 오믹스).',
        dataTypes: ['metadata', 'genomics', 'transcriptomics', 'proteomics', 'metabolomics'],
        enabled: true,
        isCustom: false,
        validationType: 'cross_threshold',
        parameters: { metric: 'meta_omics_linkage', operator: '>=', threshold: 95, unit: '%' },
        severity: 'warning'
      },

      // ═══════════════════════════════════════════════════════
      // PLAUSIBILITY (타당성) ── 기초 품질 (Atemporal)
      // OMOP 대응: plausibleValueLow, plausibleValueHigh, plausibleGender, plausibleAge
      // ═══════════════════════════════════════════════════════
      {
        id: 'plau_C001',
        metricId: 'plau_C001',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: 'Atemporal',
        name: '발현값 하한 검사',               // OMOP: plausibleValueLow
        dimension: 'Plausibility',
        level: 'basic',
        description: '수치형 발현값이 설정된 하한값 미만인 비율을 검사합니다.',
        dataTypes: OMICS_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'range',
        parameters: { min: -100, max: null },
        severity: 'characterization'
      },
      {
        id: 'plau_C002',
        metricId: 'plau_C002',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: 'Atemporal',
        name: '발현값 상한 검사',               // OMOP: plausibleValueHigh
        dimension: 'Plausibility',
        level: 'basic',
        description: '수치형 발현값이 설정된 상한값을 초과하는 비율을 검사합니다.',
        dataTypes: OMICS_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'range',
        parameters: { min: null, max: 100 },
        severity: 'characterization'
      },
      {
        id: 'plau_C003',
        metricId: 'plau_C003',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: 'Atemporal',
        name: 'IQR 기반 이상치 검사',
        dimension: 'Plausibility',
        level: 'basic',
        description: 'IQR(사분위수 범위) 방법(×1.5)으로 이상치 비율을 검사합니다.',
        dataTypes: OMICS_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'threshold',
        parameters: { metric: 'outlier_rate_iqr', operator: '<=', threshold: 5, unit: '%', iqr_multiplier: 1.5 },
        severity: 'warning'
      },
      {
        id: 'plau_C004',
        metricId: 'plau_C004',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: 'Atemporal',
        name: '상수값 컬럼 탐지 (분산=0)',      // OMOP: plausibleValueLow/High 파생
        dimension: 'Plausibility',
        level: 'basic',
        description: '분산이 0인 컬럼(상수값만 있는 컬럼)을 탐지합니다. 정보가 없는 피처입니다.',
        dataTypes: OMICS_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'threshold',
        parameters: { metric: 'zero_variance_columns', operator: '<=', threshold: 0, unit: '개' },
        severity: 'warning'
      },
      // ── 메타데이터 전용 Plausibility ────────────────────────
      {
        id: 'plau_V001',
        metricId: 'plau_V001',
        metricLevel: 'VALUE',
        context: 'Validation',
        subcategory: 'Atemporal',
        name: '성별 값 허용범위 검사',          // OMOP: plausibleGender
        dimension: 'Plausibility',
        level: 'basic',
        description: '성별(sex/gender) 컬럼의 값이 허용된 목록 내에 있는지 검사합니다.',
        dataTypes: ['metadata'],
        enabled: true,
        isCustom: false,
        validationType: 'value_set',
        parameters: {
          targetColumn: 'sex',
          allowedValues: ['M', 'F', 'male', 'female', 'Male', 'Female', '남', '여', 'Unknown', 'unknown']
        },
        severity: 'error'
      },
      {
        id: 'plau_V002',
        metricId: 'plau_V002',
        metricLevel: 'VALUE',
        context: 'Validation',
        subcategory: 'Atemporal',
        name: '연령 값 범위 검사',              // OMOP: plausibleAge (파생)
        dimension: 'Plausibility',
        level: 'basic',
        description: '연령(age) 컬럼의 값이 합리적 범위(0~120) 내에 있는지 검사합니다.',
        dataTypes: ['metadata'],
        enabled: true,
        isCustom: false,
        validationType: 'column_range',
        parameters: { targetColumn: 'age', min: 0, max: 120 },
        severity: 'error'
      },
      // ── Plausibility Temporal (메타데이터 날짜 검사) ──────
      {
        id: 'plau_T001',
        metricId: 'plau_T001',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: 'Temporal',
        name: '날짜 순서 타당성 검사',           // OMOP: plausibleTemporalAfter
        dimension: 'Plausibility',
        level: 'basic',
        description: '시작일이 종료일보다 앞서는지 확인합니다. (예: 진단일 < 종료일)',
        dataTypes: ['metadata'],
        enabled: true,
        isCustom: false,
        validationType: 'date_order',
        parameters: { startColumn: 'start_date', endColumn: 'end_date' },
        severity: 'characterization'
      },
      // ── Plausibility 심화 품질 ───────────────────────────────
      {
        id: 'plau_X001',
        metricId: 'plau_X001',
        metricLevel: 'VALUE',
        context: 'Validation',
        subcategory: 'Atemporal',
        name: '메타데이터-오믹스 subtype 일관성',
        dimension: 'Plausibility',
        level: 'advanced',
        description: '메타데이터의 subtype 정보와 오믹스 데이터 간 표현형 일관성을 검사합니다.',
        dataTypes: ['metadata', 'transcriptomics', 'proteomics'],
        enabled: true,
        isCustom: false,
        validationType: 'cross_consistency',
        parameters: { matchColumn: 'sample_id', compareColumn: 'subtype' },
        severity: 'convention'
      },
      {
        id: 'plau_X002',
        metricId: 'plau_X002',
        metricLevel: 'VALUE',
        context: 'Validation',
        subcategory: 'Atemporal',
        name: '오믹스 간 발현 상관관계',
        dimension: 'Plausibility',
        level: 'advanced',
        description: 'RNA 발현량과 단백질 발현량 간 상관관계가 합리적인 범위인지 검사합니다.',
        dataTypes: ['transcriptomics', 'proteomics'],
        enabled: true,
        isCustom: false,
        validationType: 'cross_correlation',
        parameters: { minCorrelation: 0.3, maxCorrelation: 1.0 },
        severity: 'warning'
      },

      // ═══════════════════════════════════════════════════════
      // CONFORMANCE (적합성) ── 기초 품질
      // OMOP 대응: cdmField, cdmDatatype, isPrimaryKey, isForeignKey, valueSet 등
      // ═══════════════════════════════════════════════════════
      {
        id: 'conf_F001',
        metricId: 'conf_F001',
        metricLevel: 'FILE',
        context: 'Verification',
        subcategory: 'Relational',
        name: '파일 형식(구분자) 일관성',       // OMOP: cdmTable 구조 준수
        dimension: 'Conformance',
        level: 'basic',
        description: '파일의 구분자(TSV:\t, CSV:,)가 모든 행에서 일관되게 사용되는지 검사합니다.',
        dataTypes: ALL_DATA_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'file_format',
        parameters: { checkDelimiterConsistency: true },
        severity: 'fatal'
      },
      {
        id: 'conf_C001',
        metricId: 'conf_C001',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: 'Relational',
        name: '샘플 ID 중복 검사',              // OMOP: isPrimaryKey
        dimension: 'Conformance',
        level: 'basic',
        description: '샘플 ID 컬럼에 중복값이 없는지 검사합니다. 중복 ID는 데이터 오염을 의미합니다.',
        dataTypes: ALL_DATA_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'duplicate_check',
        parameters: { targetColumn: 'first_column' },
        severity: 'fatal'
      },
      {
        id: 'conf_C002',
        metricId: 'conf_C002',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: 'Value',
        name: '수치형 컬럼 데이터 타입 검사',   // OMOP: cdmDatatype
        dimension: 'Conformance',
        level: 'basic',
        description: '오믹스 발현값 컬럼이 수치형 데이터인지 검사합니다.',
        dataTypes: OMICS_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'datatype_check',
        parameters: { expectedType: 'numeric', excludeColumns: ['sample_id', 'sample', 'SampleID'] },
        severity: 'error'
      },
      {
        id: 'conf_C003',
        metricId: 'conf_C003',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: 'Relational',
        name: '컬럼명 형식 검사 (헤더 표준)',   // OMOP: cdmField
        dimension: 'Conformance',
        level: 'basic',
        description: '컬럼명에 공백이나 특수문자(/, \\, 따옴표)가 포함되어 있지 않은지 검사합니다.',
        dataTypes: ALL_DATA_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'column_format',
        parameters: { allowedPattern: '^[a-zA-Z0-9_.\\-가-힣]+$', disallowedChars: [' ', '/', '\\', '"', "'"] },
        severity: 'convention'
      },
      // ── 메타데이터 전용 Conformance ────────────────────────
      {
        id: 'conf_V001',
        metricId: 'conf_V001',
        metricLevel: 'VALUE',
        context: 'Verification',
        subcategory: 'Value',
        name: '허용값 목록 준수 검사',           // OMOP: fkDomain / valueSet
        dimension: 'Conformance',
        level: 'basic',
        description: '범주형 컬럼의 값이 사전 정의된 허용값 목록에 포함되는지 검사합니다. (예: 성별 = M/F/Unknown)',
        dataTypes: ['metadata'],
        enabled: true,
        isCustom: false,
        validationType: 'value_set',
        parameters: {
          targetColumn: 'gender',
          allowedValues: ['male', 'female', 'Male', 'Female', 'M', 'F', 'not reported', 'Unknown']
        },
        severity: 'error'
      },
      {
        id: 'conf_C004',
        metricId: 'conf_C004',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: 'Relational',
        name: '샘플 ID 형식 검사 (정규식)',
        dimension: 'Conformance',
        level: 'basic',
        description: '샘플 ID가 지정된 형식 패턴을 따르는지 검사합니다.',
        dataTypes: ALL_DATA_TYPES,
        enabled: false,
        isCustom: false,
        validationType: 'regex_pattern',
        parameters: {
          targetColumn: 'first_column',
          pattern: '^[A-Za-z0-9_\\-]+$',
          patternDescription: '영문자, 숫자, _, - 만 허용'
        },
        severity: 'convention'
      },
      // ── Conformance 심화 품질 ────────────────────────────────
      {
        id: 'conf_X001',
        metricId: 'conf_X001',
        metricLevel: 'VALUE',
        context: 'Verification',
        subcategory: 'Relational',
        name: '데이터셋 간 ID 형식 일관성',      // OMOP: isForeignKey
        dimension: 'Conformance',
        level: 'advanced',
        description: '모든 데이터셋의 샘플 ID 형식이 동일한 패턴을 가지는지 검사합니다.',
        dataTypes: ALL_DATA_TYPES,
        enabled: true,
        isCustom: false,
        validationType: 'cross_format',
        parameters: { compareColumn: 'sample_id' },
        severity: 'error'
      },

      // ── 추가 지표: comp_C004 (조건부 필수 컬럼) ─────────────────
      {
        id: 'comp_C004',
        metricId: 'comp_C004',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: 'Conditional',
        name: '조건부 필수 컬럼 검사',            // OMOP: isConditionalRequired (2255)
        dimension: 'Completeness',
        level: 'basic',
        description: '특정 컬럼이 존재할 때 다른 컬럼도 반드시 존재해야 하는지 검사합니다. 예: diagnosis_date 존재 시 diagnosis_code 필수',
        dataTypes: ['metadata'],
        enabled: false,
        isCustom: false,
        validationType: 'conditional_required',
        parameters: { conditionColumn: 'diagnosis_date', conditionValue: null, requiredColumn: 'diagnosis_code' },
        severity: 'error'
      },

      // ── 추가 지표: plau_V003 (음수값 검사) ──────────────────────
      {
        id: 'plau_V003',
        metricId: 'plau_V003',
        metricLevel: 'VALUE',
        context: 'Verification',
        subcategory: 'Atemporal',
        name: '수치형 컬럼 음수값 검사',
        dimension: 'Plausibility',
        level: 'basic',
        description: 'Raw count 데이터 등 음수값이 허용되지 않아야 하는 오믹스 데이터에서 음수값 존재 여부를 검사합니다.',
        dataTypes: OMICS_TYPES,
        enabled: false,
        isCustom: false,
        validationType: 'negative_check',
        parameters: { targetColumn: 'all_except_first', allowNegative: false },
        severity: 'warning'
      },

      // ── 추가 지표: plau_T002 (진단일-출생일 순서) ───────────────
      {
        id: 'plau_T002',
        metricId: 'plau_T002',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: 'Temporal',
        name: '진단일-출생일 순서 검사',           // OMOP: plausibleAfterBirth (3100)
        dimension: 'Plausibility',
        level: 'basic',
        description: '진단일이 출생일 이후인지 확인합니다. 출생 전 진단 기록은 데이터 오류를 의미합니다.',
        dataTypes: ['metadata'],
        enabled: false,
        isCustom: false,
        validationType: 'date_order',
        parameters: { startColumn: 'birth_date', endColumn: 'diagnosis_date' },
        severity: 'error'
      },

      // ── 추가 지표: conf_V002 (날짜 형식 표준) ───────────────────
      {
        id: 'conf_V002',
        metricId: 'conf_V002',
        metricLevel: 'VALUE',
        context: 'Verification',
        subcategory: 'Value',
        name: '날짜 형식 표준 검사',               // OMOP: cdmDatatype (1600) 파생
        dimension: 'Conformance',
        level: 'basic',
        description: '날짜 컬럼이 지정된 표준 형식(YYYY-MM-DD 등)을 따르는지 검사합니다.',
        dataTypes: ['metadata'],
        enabled: false,
        isCustom: false,
        validationType: 'date_format',
        parameters: { targetColumn: 'diagnosis_date', dateFormat: 'YYYY-MM-DD' },
        severity: 'error'
      },

      // ═══════════════════════════════════════════════════════════════
      // BATCH EFFECT (배치효과) ── 심화 품질 · BatchEval 연동
      // 출처: Zhang et al. 2024 GigaByte doi:10.46471/gigabyte.108
      //       STOmics/BatchEval (github.com/STOmics/BatchEval)
      //
      // 연동 방식:
      //   plau_B001 ~ plau_B002 : 브라우저에서 직접 계산 가능
      //   plau_B003 ~ plau_B006 : BatchEval Python 실행 결과를 사용자가 입력
      //                           (PCA/UMAP + AnnData 필요 → 브라우저 계산 불가)
      // ═══════════════════════════════════════════════════════════════

      // ── 1. 브라우저 직접 계산 가능 지표 ─────────────────────────
      {
        id: 'plau_B001',
        metricId: 'plau_B001',
        metricLevel: 'COLUMN',
        context: 'Verification',
        subcategory: 'Atemporal',
        name: '배치 레이블 컬럼 존재 및 분포',
        dimension: 'Plausibility',
        level: 'advanced',
        description: '배치(플랫폼/기관/시점) 레이블 컬럼이 메타데이터 또는 오믹스 데이터에 존재하는지 확인하고, 배치별 샘플 수의 균형을 검사합니다. 배치 레이블이 없으면 이후 배치효과 평가가 불가합니다.',
        dataTypes: ALL_DATA_TYPES,
        enabled: false,
        isCustom: false,
        validationType: 'batch_label_check',
        parameters: {
          batchColumn: 'batch',
          maxImbalanceRatio: 5   // 가장 큰 배치 / 가장 작은 배치 최대 비율
        },
        severity: 'warning'
      },
      {
        id: 'plau_B002',
        metricId: 'plau_B002',
        metricLevel: 'VALUE',
        context: 'Verification',
        subcategory: 'Atemporal',
        name: '배치별 발현값 평균 편차',
        dimension: 'Plausibility',
        level: 'advanced',
        description: '배치 간 전체 발현값 평균의 상대적 편차(CV%)를 검사합니다. 편차가 크면 배치효과가 존재할 가능성을 나타냅니다. BatchEval의 도메인 추정 점수 계산 전 사전 선별 지표로 활용합니다.',
        dataTypes: OMICS_TYPES,
        enabled: false,
        isCustom: false,
        validationType: 'batch_mean_deviation',
        parameters: {
          batchColumn: 'batch',
          maxCVPercent: 30   // 배치 간 평균 CV(%) 임계값
        },
        severity: 'warning'
      },

      // ── 2. BatchEval Python 외부 연동 지표 ──────────────────────
      //    사전 계산된 점수를 사용자가 입력 (external_score 타입)
      {
        id: 'plau_B003',
        metricId: 'plau_B003',
        metricLevel: 'VALUE',
        context: 'Validation',
        subcategory: 'Computational',
        name: 'k-BET 수락률 [BatchEval 외부 연동]',
        dimension: 'Plausibility',
        level: 'advanced',
        description: 'k-nearest neighbor Batch Effect Test(Büttner et al. 2019)의 수락률(accept rate)입니다. 낮을수록 배치효과가 심함을 의미합니다. BatchEval Python 실행 후 결과값을 입력하세요. (계산 기반: Chi-square 검정, PCA 차원축소 필요)',
        dataTypes: OMICS_TYPES,
        enabled: false,
        isCustom: false,
        validationType: 'external_score',
        parameters: {
          scoreName: 'kBET_accept_rate',
          operator: '>=',
          threshold: 0.05,
          unit: '비율(0~1)',
          toolName: 'BatchEval',
          toolVersion: '',
          note: 'kBET accept rate ≥ 0.05 권고. 값이 낮을수록 배치효과 심함.'
        },
        severity: 'characterization'
      },
      {
        id: 'plau_B004',
        metricId: 'plau_B004',
        metricLevel: 'VALUE',
        context: 'Validation',
        subcategory: 'Computational',
        name: 'iLISI / cLISI F1 점수 [BatchEval 외부 연동]',
        dimension: 'Plausibility',
        level: 'advanced',
        description: 'iLISI(배치 혼합도)와 cLISI(생물학적 분산 보존도)의 F1 조화평균 점수입니다. 높을수록 배치가 잘 제거되면서 생물학적 신호는 보존됨을 의미합니다. BatchEval Python 실행 후 결과값을 입력하세요.',
        dataTypes: OMICS_TYPES,
        enabled: false,
        isCustom: false,
        validationType: 'external_score',
        parameters: {
          scoreName: 'F1_LISI',
          operator: '>=',
          threshold: 0.5,
          unit: '점수(0~1)',
          toolName: 'BatchEval',
          toolVersion: '',
          note: 'F1_LISI = 2×(1-cLISI)×iLISI / [(1-cLISI)+iLISI]. 높을수록 우수.'
        },
        severity: 'characterization'
      },
      {
        id: 'plau_B005',
        metricId: 'plau_B005',
        metricLevel: 'VALUE',
        context: 'Validation',
        subcategory: 'Computational',
        name: '배치 도메인 추정 점수 [BatchEval 외부 연동]',
        dimension: 'Plausibility',
        level: 'advanced',
        description: '신경망 분류기가 각 샘플이 어느 배치에서 왔는지 예측한 정확도입니다. 낮을수록(≈ 2% 수준) 배치 간 데이터가 잘 혼합된 것을 의미합니다. BatchEval Python 실행 후 결과값을 입력하세요.',
        dataTypes: OMICS_TYPES,
        enabled: false,
        isCustom: false,
        validationType: 'external_score',
        parameters: {
          scoreName: 'batch_domain_estimate',
          operator: '<=',
          threshold: 0.1,
          unit: '비율(0~1)',
          toolName: 'BatchEval',
          toolVersion: '',
          note: '≤ 0.1(10%) 권고. 배치 추정 정확도가 낮을수록 잘 혼합된 데이터.'
        },
        severity: 'characterization'
      },
      {
        id: 'plau_B006',
        metricId: 'plau_B006',
        metricLevel: 'VALUE',
        context: 'Validation',
        subcategory: 'Computational',
        name: 'BatchEval 종합 배치효과 점수 [BatchEval 외부 연동]',
        dimension: 'Plausibility',
        level: 'advanced',
        description: 'BatchEval이 산출하는 kBET, iLISI/cLISI F1, 배치 추정 점수를 가중 평균한 종합 점수입니다. 높을수록 배치효과가 잘 제거된 통합 데이터임을 의미합니다.',
        dataTypes: OMICS_TYPES,
        enabled: false,
        isCustom: false,
        validationType: 'external_score',
        parameters: {
          scoreName: 'BatchEval_comprehensive_score',
          operator: '>=',
          threshold: 0.6,
          unit: '점수(0~1)',
          toolName: 'BatchEval',
          toolVersion: '',
          note: 'BatchEval 메인 페이지 종합 점수. ≥ 0.6 권고.'
        },
        severity: 'characterization'
      }
    ];
  }

  function getEmptyRuleForm() {
    return {
      name: '',
      // ── 확정 필드 (커스텀 규칙 기본 구성) ──────────────────
      dimension: 'Completeness',           // Completeness | Plausibility | Conformance
      level: 'basic',                      // basic | advanced
      severity: 'warning',                 // fatal | error | warning | convention | characterization
      description: '',
      dataTypes: [],                       // genomics | transcriptomics | proteomics | metabolomics | metadata
      validationType: 'threshold',
      parameters: {},
      // ── OMOP CDM DQM 정렬 확장 필드 ───────────────────────
      metricId: '',                        // OMOP metric_id 대응 (예: comp_C002)
      metricLevel: 'COLUMN',              // FILE | COLUMN | VALUE
      context: 'Verification',            // Verification | Validation
      subcategory: '',                    // Relational|Atemporal|Temporal|Value|Conditional|Computational
      isCustom: true,
      createdAt: new Date().toISOString(),
      author: ''
    };
  }

  // 규칙 필터링
  const filteredRules = rules.filter(rule => {
    const matchesSearch = rule.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         rule.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesDimension = filterDimension === 'all' || rule.dimension === filterDimension;
    const matchesLevel = filterLevel === 'all' || rule.level === filterLevel;
    return matchesSearch && matchesDimension && matchesLevel;
  });

  // 차원별 규칙 그룹화
  const groupedRules = filteredRules.reduce((acc, rule) => {
    if (!acc[rule.dimension]) {
      acc[rule.dimension] = [];
    }
    acc[rule.dimension].push(rule);
    return acc;
  }, {});

  // 파일 업로드 처리
  const handleFileUpload = useCallback((event) => {
    const files = Array.from(event.target.files);
    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target.result;
        const delimiter = detectDelimiter(content);
        const lines = content.split('\n').filter(line => line.trim());
        const headers = lines[0].split(delimiter);
        const rows = lines.slice(1).map(line => line.split(delimiter));
        const autoDataType = inferDataType(file.name);
        
        setUploadedFiles(prev => [...prev, {
          id: Date.now() + Math.random(),
          name: file.name,
          size: file.size,
          delimiter,
          headers,
          rows,
          rowCount: rows.length,
          colCount: headers.length,
          dataType: autoDataType
        }]);
      };
      reader.readAsText(file);
    });
  }, []);

  // 파일 삭제
  const removeFile = (fileId) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  // 파일 데이터 타입 설정
  const setFileDataType = (fileId, dataType) => {
    setUploadedFiles(prev => prev.map(f => 
      f.id === fileId ? { ...f, dataType } : f
    ));
  };

  // 규칙 선택 토글
  const toggleRuleSelection = (ruleId) => {
    setSelectedRules(prev => 
      prev.includes(ruleId) 
        ? prev.filter(id => id !== ruleId)
        : [...prev, ruleId]
    );
  };

  // 차원별 전체 선택
  const toggleDimensionSelection = (dimension) => {
    const dimensionRuleIds = filteredRules
      .filter(r => r.dimension === dimension && r.enabled)
      .map(r => r.id);
    
    const allSelected = dimensionRuleIds.every(id => selectedRules.includes(id));
    
    if (allSelected) {
      setSelectedRules(prev => prev.filter(id => !dimensionRuleIds.includes(id)));
    } else {
      setSelectedRules(prev => [...new Set([...prev, ...dimensionRuleIds])]);
    }
  };

  // 규칙 활성화/비활성화
  const toggleRuleEnabled = (ruleId) => {
    setRules(prev => prev.map(r => 
      r.id === ruleId ? { ...r, enabled: !r.enabled } : r
    ));
  };

  // 규칙 삭제
  const deleteRule = (ruleId) => {
    setRules(prev => prev.filter(r => r.id !== ruleId));
    setSelectedRules(prev => prev.filter(id => id !== ruleId));
  };

  // 규칙 편집 시작
  const startEditRule = (rule) => {
    setEditingRule(rule);
    setRuleForm({ ...rule });
    setShowRuleModal(true);
  };

  // 새 규칙 생성 시작
  const startCreateRule = () => {
    setEditingRule(null);
    setRuleForm({
      ...getEmptyRuleForm(),
      id: 'custom_' + Date.now()
    });
    setShowRuleModal(true);
  };

  // 규칙 저장
  const saveRule = () => {
    if (!ruleForm.name.trim()) {
      alert('규칙 이름을 입력해주세요.');
      return;
    }
    
    if (editingRule) {
      setRules(prev => prev.map(r => r.id === editingRule.id ? { ...ruleForm } : r));
    } else {
      setRules(prev => [...prev, { ...ruleForm, enabled: true }]);
    }
    
    setShowRuleModal(false);
    setEditingRule(null);
    setRuleForm(getEmptyRuleForm());
  };

  // 검증 실행
  const runValidation = async () => {
    if (uploadedFiles.length === 0) {
      alert('검증할 데이터를 업로드해주세요.');
      return;
    }
    
    if (selectedRules.length === 0) {
      alert('적용할 규칙을 선택해주세요.');
      return;
    }

    setIsValidating(true);
    
    // 시뮬레이션을 위한 딜레이
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    const results = [];
    const selectedRuleObjects = rules.filter(r => selectedRules.includes(r.id));
    
    // 기초 품질 검증 (단일 데이터)
    const basicRules = selectedRuleObjects.filter(r => r.level === 'basic');
    uploadedFiles.forEach(file => {
      basicRules.forEach(rule => {
        const result = executeValidation(rule, file);
        results.push({
          ...result,
          fileName: file.name,
          ruleName: rule.name,
          dimension: rule.dimension,
          level: rule.level,
          severity: rule.severity
        });
      });
    });
    
    // 심화 품질 검증 (다중 데이터)
    const advancedRules = selectedRuleObjects.filter(r => r.level === 'advanced');
    if (uploadedFiles.length >= 2 && advancedRules.length > 0) {
      advancedRules.forEach(rule => {
        const result = executeCrossValidation(rule, uploadedFiles);
        results.push({
          ...result,
          fileName: '다중 데이터셋',
          ruleName: rule.name,
          dimension: rule.dimension,
          level: rule.level,
          severity: rule.severity
        });
      });
    }
    
    setValidationResults(results);
    setIsValidating(false);
  };

  // 단일 데이터 검증 실행
  const executeValidation = (rule, file) => {
    // 실제 검증 로직 시뮬레이션
    const randomPass = Math.random() > 0.3;
    
    switch (rule.validationType) {
      case 'threshold':
        if (rule.parameters.metric === 'missing_rate') {
          const missingRate = calculateMissingRate(file);
          const passed = eval(`${missingRate} ${rule.parameters.operator} ${rule.parameters.threshold}`);
          return {
            passed,
            status: passed ? 'pass' : (rule.severity === 'error' ? 'fail' : 'warning'),
            message: passed 
              ? `결측률 ${missingRate.toFixed(1)}% - 기준 충족`
              : `결측률 ${missingRate.toFixed(1)}% - 기준(${rule.parameters.operator} ${rule.parameters.threshold}%) 미충족`,
            details: { missingRate }
          };
        }
        return { passed: randomPass, status: randomPass ? 'pass' : 'warning', message: '검증 완료' };
        
      case 'uniqueness':
        const duplicateCount = Math.floor(Math.random() * 3);
        return {
          passed: duplicateCount === 0,
          status: duplicateCount === 0 ? 'pass' : 'fail',
          message: duplicateCount === 0 
            ? '중복 식별자 없음'
            : `${duplicateCount}개의 중복 식별자 발견`,
          details: { duplicateCount }
        };
        
      case 'data_type':
        const invalidTypeCount = Math.floor(Math.random() * 5);
        return {
          passed: invalidTypeCount === 0,
          status: invalidTypeCount === 0 ? 'pass' : 'fail',
          message: invalidTypeCount === 0
            ? '모든 값이 수치형입니다'
            : `${invalidTypeCount}개 컬럼에서 비수치형 값 발견`,
          details: { invalidTypeCount }
        };
        
      case 'value_set': {
        const targetCol = rule.parameters.targetColumn;
        const allowedVals = rule.parameters.allowedValues || [];
        const colIdx = file.headers.findIndex(h => h.toLowerCase() === targetCol.toLowerCase());
        if (colIdx === -1) return { passed: false, status: 'warning', message: `컬럼 '${targetCol}'을 찾을 수 없습니다.`, details: {} };
        const invalid = file.rows.filter(row => { const v = row[colIdx]; return v && v.trim() && !allowedVals.includes(v.trim()); });
        return { passed: invalid.length === 0, status: invalid.length === 0 ? 'pass' : 'fail',
          message: invalid.length === 0 ? `'${targetCol}' 허용값 검사 통과` : `허용되지 않은 값 ${invalid.length}개: ${[...new Set(invalid.map(r=>r[colIdx]))].slice(0,3).join(', ')}`,
          details: { targetColumn: targetCol, invalidCount: invalid.length } };
      }
      case 'date_order': {
        const sIdx = file.headers.findIndex(h => h.toLowerCase() === (rule.parameters.startColumn||'').toLowerCase());
        const eIdx = file.headers.findIndex(h => h.toLowerCase() === (rule.parameters.endColumn||'').toLowerCase());
        if (sIdx === -1 || eIdx === -1) return { passed: false, status: 'warning', message: '날짜 컬럼을 찾을 수 없습니다.', details: {} };
        const violated = file.rows.filter(row => { const s=new Date(row[sIdx]),e=new Date(row[eIdx]); return !isNaN(s)&&!isNaN(e)&&s>e; });
        return { passed: violated.length === 0, status: violated.length === 0 ? 'pass' : 'fail',
          message: violated.length === 0 ? `날짜 순서 정상 (${rule.parameters.startColumn} ≤ ${rule.parameters.endColumn})` : `날짜 역전 ${violated.length}건 발견`,
          details: { violationCount: violated.length } };
      }
      case 'duplicate_check': {
        const colIdx = rule.parameters.targetColumn === 'first_column' ? 0 : file.headers.findIndex(h=>h===(rule.parameters.customColumn||''));
        const vals = file.rows.map(r=>r[colIdx]).filter(v=>v&&v.trim());
        const seen = new Set(); const dupes = vals.filter(v=>{ const d=seen.has(v); seen.add(v); return d; });
        return { passed: dupes.length === 0, status: dupes.length === 0 ? 'pass' : 'fail',
          message: dupes.length === 0 ? '중복값 없음 (고유 ID 확인)' : `중복값 ${dupes.length}개 발견`,
          details: { duplicateCount: dupes.length } };
      }
      case 'datatype_check': {
        const expectedType = rule.parameters.expectedType || 'numeric';
        const cols = rule.parameters.targetColumn === 'all_except_first' ? file.headers.slice(1) : file.headers.slice(0,1);
        const invalidCols = cols.filter(col => {
          const ci = file.headers.indexOf(col);
          const vals = file.rows.map(r=>r[ci]).filter(v=>v&&v.trim());
          return expectedType==='numeric' ? !vals.every(v=>!isNaN(parseFloat(v))) : expectedType==='integer' ? !vals.every(v=>Number.isInteger(Number(v))) : false;
        });
        return { passed: invalidCols.length === 0, status: invalidCols.length === 0 ? 'pass' : 'fail',
          message: invalidCols.length === 0 ? `전체 컬럼 ${expectedType} 타입 검증 통과` : `타입 불일치 ${invalidCols.length}개 컬럼: ${invalidCols.slice(0,3).join(', ')}`,
          details: { expectedType, invalidColumns: invalidCols } };
      }
      case 'file_format': {
        const expected = file.headers.length;
        const bad = file.rows.filter(r=>r.length!==expected);
        return { passed: bad.length===0, status: bad.length===0?'pass':'fail',
          message: bad.length===0 ? `파일 형식 일관성 정상 (${expected}컬럼)` : `${bad.length}개 행에서 컬럼 수 불일치`,
          details: { expectedColumns: expected, inconsistentRows: bad.length } };
      }
      case 'column_range': {
        const tCol = rule.parameters.targetColumn;
        const ci = file.headers.findIndex(h=>h.toLowerCase()===tCol.toLowerCase());
        if (ci===-1) return { passed:false, status:'warning', message:`컬럼 '${tCol}' 없음`, details:{} };
        const oor = file.rows.filter(r=>{ const v=parseFloat(r[ci]); if(isNaN(v))return false; return (rule.parameters.min!==undefined&&v<rule.parameters.min)||(rule.parameters.max!==undefined&&v>rule.parameters.max); });
        return { passed: oor.length===0, status: oor.length===0?'pass':'fail',
          message: oor.length===0 ? `'${tCol}' 값 범위 검사 통과` : `범위 벗어난 값 ${oor.length}개 발견`,
          details: { outOfRangeCount: oor.length } };
      }
      case 'header_exists': {
        const ok = file.headers && file.headers.length>=(rule.parameters.minColumns||1);
        return { passed:ok, status:ok?'pass':'fail', message:ok?`헤더 확인 (${file.headers.length}컬럼)`:`헤더 없음/컬럼 부족`, details:{} };
      }
      case 'column_exists': {
        const tCol = rule.parameters.targetColumn==='first_column' ? (file.headers[0]||null) : (rule.parameters.customColumn||rule.parameters.targetColumn);
        const exists = tCol && (rule.parameters.targetColumn==='first_column' ? !!file.headers[0] : file.headers.some(h=>h.toLowerCase()===tCol.toLowerCase()));
        return { passed:!!exists, status:exists?'pass':'fail', message:exists?`필수 컬럼 '${tCol}' 존재`:`필수 컬럼 '${tCol}' 없음`, details:{} };
      }
      case 'regex_pattern': {
        const tCol = rule.parameters.targetColumn==='first_column' ? file.headers[0] : rule.parameters.targetColumn;
        const ci = file.headers.findIndex(h=>h===tCol||h.toLowerCase()===tCol.toLowerCase());
        let pat; try { pat = new RegExp(rule.parameters.pattern); } catch(e) { return {passed:false,status:'warning',message:'정규식 오류',details:{}}; }
        const bad = file.rows.filter(r=>{ const v=r[ci]; return v&&v.trim()&&!pat.test(v.trim()); });
        return { passed:bad.length===0, status:bad.length===0?'pass':'fail',
          message:bad.length===0?'패턴 검사 통과':`패턴 불일치 ${bad.length}건`, details:{invalidCount:bad.length} };
      }
      case 'conditional_required': {
        const { conditionColumn, requiredColumn } = rule.parameters;
        const condIdx = file.headers.findIndex(h => h.toLowerCase() === (conditionColumn||'').toLowerCase());
        const reqIdx  = file.headers.findIndex(h => h.toLowerCase() === (requiredColumn||'').toLowerCase());
        if (condIdx === -1) return { passed: true, status: 'pass', message: `조건 컬럼 '${conditionColumn}' 없음 - 검사 건너뜀`, details: {} };
        if (reqIdx === -1) return { passed: false, status: 'fail', message: `필수 컬럼 '${requiredColumn}'이 없습니다`, details: {} };
        return { passed: true, status: 'pass', message: `'${conditionColumn}' 조건부 필수 컬럼 '${requiredColumn}' 존재 확인`, details: {} };
      }
      case 'negative_check': {
        const excludeFirst = rule.parameters.targetColumn === 'all_except_first';
        const checkCols = excludeFirst ? file.headers.slice(1) : [rule.parameters.targetColumn];
        let negCount = 0;
        checkCols.forEach(col => {
          const ci = file.headers.indexOf(col);
          if (ci === -1) return;
          file.rows.forEach(row => { const v = parseFloat(row[ci]); if (!isNaN(v) && v < 0) negCount++; });
        });
        return { passed: negCount === 0, status: negCount === 0 ? 'pass' : 'warning',
          message: negCount === 0 ? '음수값 없음 (Raw count 검증 통과)' : `음수값 ${negCount}건 발견`,
          details: { negativeCount: negCount } };
      }
      case 'date_format': {
        const { targetColumn, dateFormat } = rule.parameters;
        const ci = file.headers.findIndex(h => h.toLowerCase() === (targetColumn||'').toLowerCase());
        if (ci === -1) return { passed: false, status: 'warning', message: `날짜 컬럼 '${targetColumn}' 없음`, details: {} };
        const isoPattern = /^\d{4}-\d{2}-\d{2}$/;
        const invalid = file.rows.filter(r => { const v = r[ci]; return v && v.trim() && !isoPattern.test(v.trim()); });
        return { passed: invalid.length === 0, status: invalid.length === 0 ? 'pass' : 'fail',
          message: invalid.length === 0 ? `'${targetColumn}' 날짜 형식 ${dateFormat} 준수` : `형식 불일치 ${invalid.length}건`,
          details: { invalidCount: invalid.length } };
      }

      // ── BatchEval 연동 검증 ──────────────────────────────────
      case 'batch_label_check': {
        const bCol = rule.parameters.batchColumn || 'batch';
        const ci = file.headers.findIndex(h => h.toLowerCase() === bCol.toLowerCase());
        if (ci === -1) return {
          passed: false, status: 'warning',
          message: `배치 레이블 컬럼 '${bCol}'을 찾을 수 없습니다. 배치효과 평가 불가.`,
          details: { batchColumnFound: false }
        };
        const batchGroups = {};
        file.rows.forEach(r => {
          const v = (r[ci] || '').trim();
          if (v) batchGroups[v] = (batchGroups[v] || 0) + 1;
        });
        const counts = Object.values(batchGroups);
        const maxRatio = counts.length > 1 ? Math.max(...counts) / Math.min(...counts) : 1;
        const maxAllowed = rule.parameters.maxImbalanceRatio || 5;
        const balanced = maxRatio <= maxAllowed;
        return {
          passed: balanced,
          status: balanced ? 'pass' : 'warning',
          message: balanced
            ? `배치 레이블 '${bCol}' 확인. ${Object.keys(batchGroups).length}개 배치, 불균형 비율 ${maxRatio.toFixed(1)}x`
            : `배치 불균형 감지: ${maxRatio.toFixed(1)}x (기준 ${maxAllowed}x). BatchEval 실행 전 확인 필요.`,
          details: { batchGroups, imbalanceRatio: maxRatio, batchCount: Object.keys(batchGroups).length }
        };
      }
      case 'batch_mean_deviation': {
        const bCol = rule.parameters.batchColumn || 'batch';
        const ci = file.headers.findIndex(h => h.toLowerCase() === bCol.toLowerCase());
        if (ci === -1) return { passed: false, status: 'warning', message: `배치 컬럼 '${bCol}' 없음`, details: {} };
        const featureCols = file.headers.slice(1).filter((h, i) => i + 1 !== ci);
        const batchMeans = {};
        file.rows.forEach(r => {
          const b = (r[ci] || '').trim();
          if (!b) return;
          if (!batchMeans[b]) batchMeans[b] = { sum: 0, count: 0 };
          featureCols.forEach((_, fi) => {
            const v = parseFloat(r[fi + 1]);
            if (!isNaN(v)) { batchMeans[b].sum += v; batchMeans[b].count++; }
          });
        });
        const means = Object.values(batchMeans).map(g => g.count > 0 ? g.sum / g.count : 0);
        if (means.length < 2) return { passed: true, status: 'pass', message: '배치 수 부족 (2개 이상 필요)', details: {} };
        const globalMean = means.reduce((a, b) => a + b, 0) / means.length;
        const cv = globalMean !== 0 ? (Math.sqrt(means.reduce((a, m) => a + Math.pow(m - globalMean, 2), 0) / means.length) / Math.abs(globalMean)) * 100 : 0;
        const maxCV = rule.parameters.maxCVPercent || 30;
        const passed = cv <= maxCV;
        return {
          passed,
          status: passed ? 'pass' : 'warning',
          message: passed
            ? `배치 간 발현 평균 CV ${cv.toFixed(1)}% — 배치효과 낮음 가능성`
            : `배치 간 발현 평균 CV ${cv.toFixed(1)}% (기준 ${maxCV}%) — BatchEval 정밀 검사 권고`,
          details: { cv: cv.toFixed(2), batchCount: means.length, batchMeans: Object.fromEntries(Object.entries(batchMeans).map(([k, v]) => [k, v.count > 0 ? (v.sum/v.count).toFixed(4) : 0])) }
        };
      }
      case 'external_score': {
        // BatchEval 등 외부 도구 사전 계산 점수를 사용자가 입력한 경우 평가
        const inputScore = rule.parameters._inputScore;
        if (inputScore === undefined || inputScore === null || inputScore === '') {
          return {
            passed: null, status: 'pending',
            message: `⚙️ [${rule.parameters.toolName || '외부 도구'}] 사전 계산 필요 — ${rule.parameters.scoreName} 점수를 입력하세요.`,
            details: { pending: true, scoreName: rule.parameters.scoreName }
          };
        }
        const score = parseFloat(inputScore);
        if (isNaN(score)) return { passed: false, status: 'warning', message: '유효하지 않은 점수 입력', details: {} };
        const op = rule.parameters.operator || '>=';
        const thr = rule.parameters.threshold;
        // eslint-disable-next-line no-eval
        const passed = eval(`${score} ${op} ${thr}`);
        return {
          passed,
          status: passed ? 'pass' : 'warning',
          message: passed
            ? `${rule.parameters.scoreName}: ${score} ${op} ${thr} — 기준 충족`
            : `${rule.parameters.scoreName}: ${score} (기준 ${op} ${thr}) — 기준 미충족`,
          details: { score, threshold: thr, operator: op, scoreName: rule.parameters.scoreName }
        };
      }
      default:
        return { passed: randomPass, status: randomPass ? 'pass' : 'warning', message: '검증 완료' };
    }
  };

  // 다중 데이터 교차 검증
  const executeCrossValidation = (rule, files) => {
    switch (rule.validationType) {
      case 'cross_threshold':
        if (rule.parameters.metric === 'sample_matching_rate') {
          // 샘플 매칭률 계산 시뮬레이션
          const matchingRate = 75 + Math.random() * 20;
          const passed = eval(`${matchingRate} ${rule.parameters.operator} ${rule.parameters.threshold}`);
          return {
            passed,
            status: passed ? 'pass' : 'warning',
            message: `샘플 매칭률: ${matchingRate.toFixed(1)}% (${files.length}개 데이터셋 비교)`,
            details: { matchingRate, fileCount: files.length }
          };
        }
        if (rule.parameters.metric === 'common_sample_count') {
          const commonCount = Math.floor(30 + Math.random() * 50);
          const passed = commonCount >= rule.parameters.threshold;
          return {
            passed,
            status: passed ? 'pass' : 'fail',
            message: `공통 샘플 수: ${commonCount}개 (기준: ${rule.parameters.threshold}개 이상)`,
            details: { commonCount }
          };
        }
        break;
        
      case 'cross_format':
        const formatConsistent = Math.random() > 0.2;
        return {
          passed: formatConsistent,
          status: formatConsistent ? 'pass' : 'fail',
          message: formatConsistent 
            ? '모든 데이터셋의 ID 형식이 일치합니다'
            : 'ID 형식이 일치하지 않는 데이터셋이 있습니다',
          details: {}
        };
        
      default:
        return { passed: true, status: 'pass', message: '교차 검증 완료' };
    }
    
    return { passed: true, status: 'pass', message: '교차 검증 완료' };
  };

  // 결측률 계산
  const calculateMissingRate = (file) => {
    let totalCells = 0;
    let missingCells = 0;
    
    file.rows.forEach(row => {
      row.forEach(cell => {
        totalCells++;
        if (!cell || cell.trim() === '' || cell.toLowerCase() === 'na' || 
            cell.toLowerCase() === 'null' || cell.toLowerCase() === 'nan') {
          missingCells++;
        }
      });
    });
    
    return totalCells > 0 ? (missingCells / totalCells) * 100 : 0;
  };

  // 결과 내보내기
  const exportResults = () => {
    if (!validationResults) return;
    
    const exportData = {
      exportDate: new Date().toISOString(),
      totalRules: selectedRules.length,
      totalFiles: uploadedFiles.length,
      results: validationResults
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `quality_validation_results_${new Date().toISOString().slice(0,10)}.json`;
    a.click();
  };

  // 검증 유형별 파라미터 폼
  const renderParameterForm = () => {
    switch (ruleForm.validationType) {
      case 'threshold':
        return (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>측정 지표</label>
              <select
                value={ruleForm.parameters.metric || ''}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, metric: e.target.value }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
              >
                <option value="">선택</option>
                <option value="missing_rate">결측률</option>
                <option value="row_completeness">행 완전성</option>
                <option value="total_missing_rate">전체 결측률</option>
                <option value="outlier_rate_iqr">이상치 비율 (IQR)</option>
                <option value="zero_variance_columns">분산 0 컬럼 수</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>비교 연산자</label>
              <select
                value={ruleForm.parameters.operator || '<='}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, operator: e.target.value }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
              >
                <option value="<=">≤ (이하)</option>
                <option value=">=">≥ (이상)</option>
                <option value="<">&lt; (미만)</option>
                <option value=">">&gt; (초과)</option>
                <option value="==">= (같음)</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>임계값</label>
              <input
                type="number"
                value={ruleForm.parameters.threshold || ''}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, threshold: parseFloat(e.target.value) }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
                placeholder="예: 30"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>단위</label>
              <select
                value={ruleForm.parameters.unit || '%'}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, unit: e.target.value }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
              >
                <option value="%">%</option>
                <option value="개">개</option>
                <option value="점">점</option>
              </select>
            </div>
          </div>
        );
        
      case 'range':
        return (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>최소값</label>
              <input
                type="number"
                value={ruleForm.parameters.min ?? ''}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, min: parseFloat(e.target.value) }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
                placeholder="예: -100"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>최대값</label>
              <input
                type="number"
                value={ruleForm.parameters.max ?? ''}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, max: parseFloat(e.target.value) }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
                placeholder="예: 100"
              />
            </div>
          </div>
        );
        
      case 'pattern':
        return (
          <div style={{ display: 'grid', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>대상 컬럼</label>
              <input
                type="text"
                value={ruleForm.parameters.targetColumn || ''}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, targetColumn: e.target.value }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
                placeholder="예: sample"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>
                정규표현식 패턴
                <span style={{ color: '#94a3b8', marginLeft: '8px' }}>
                  <HelpCircle size={12} style={{ display: 'inline', verticalAlign: 'middle' }} />
                </span>
              </label>
              <input
                type="text"
                value={ruleForm.parameters.pattern || ''}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, pattern: e.target.value }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontFamily: 'monospace'
                }}
                placeholder="예: ^TCGA-[A-Z0-9]{2}-[A-Z0-9]{4}"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>패턴 설명</label>
              <input
                type="text"
                value={ruleForm.parameters.patternDescription || ''}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, patternDescription: e.target.value }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
                placeholder="예: TCGA-XX-XXXX 형식"
              />
            </div>
          </div>
        );
        
      case 'categorical':
        return (
          <div style={{ display: 'grid', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>대상 컬럼</label>
              <input
                type="text"
                value={ruleForm.parameters.targetColumn || ''}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, targetColumn: e.target.value }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
                placeholder="예: gender.demographic"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>
                허용 값 목록 (쉼표로 구분)
              </label>
              <input
                type="text"
                value={(ruleForm.parameters.allowedValues || []).join(', ')}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { 
                    ...prev.parameters, 
                    allowedValues: e.target.value.split(',').map(v => v.trim()).filter(v => v)
                  }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
                placeholder="예: male, female, not reported"
              />
            </div>
          </div>
        );
        
      case 'cross_threshold':
        return (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>교차 검증 지표</label>
              <select
                value={ruleForm.parameters.metric || ''}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, metric: e.target.value }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
              >
                <option value="">선택</option>
                <option value="sample_matching_rate">샘플 매칭률</option>
                <option value="common_sample_count">공통 샘플 수</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>비교 연산자</label>
              <select
                value={ruleForm.parameters.operator || '>='}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, operator: e.target.value }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
              >
                <option value=">=">≥ (이상)</option>
                <option value="<=">≤ (이하)</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>임계값</label>
              <input
                type="number"
                value={ruleForm.parameters.threshold || ''}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, threshold: parseFloat(e.target.value) }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>단위</label>
              <select
                value={ruleForm.parameters.unit || '%'}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, unit: e.target.value }
                }))}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
              >
                <option value="%">%</option>
                <option value="개">개</option>
              </select>
            </div>
          </div>
        );
        
      case 'value_set':
        return (
          <div style={{ display: 'grid', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>대상 컬럼명</label>
              <input type="text"
                value={ruleForm.parameters.targetColumn || ''}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, targetColumn: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                placeholder="예: sex, gender, status"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>
                허용값 목록 <span style={{ color: '#94a3b8', fontWeight: 400 }}>(쉼표로 구분)</span>
              </label>
              <input type="text"
                value={(ruleForm.parameters.allowedValues || []).join(', ')}
                onChange={(e) => setRuleForm(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, allowedValues: e.target.value.split(',').map(v => v.trim()).filter(Boolean) }
                }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                placeholder="예: Male, Female, Unknown"
              />
              {(ruleForm.parameters.allowedValues || []).length > 0 && (
                <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {(ruleForm.parameters.allowedValues || []).map((v, i) => (
                    <span key={i} style={{ padding: '3px 10px', background: '#eff6ff', color: '#1d4ed8', borderRadius: '12px', fontSize: '12px', fontWeight: 600 }}>{v}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        );

      case 'date_order':
        return (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>시작 날짜 컬럼</label>
              <input type="text"
                value={ruleForm.parameters.startColumn || ''}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, startColumn: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                placeholder="예: diagnosis_date, start_date"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>종료 날짜 컬럼</label>
              <input type="text"
                value={ruleForm.parameters.endColumn || ''}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, endColumn: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                placeholder="예: death_date, end_date"
              />
            </div>
            <div style={{ gridColumn: '1/-1', padding: '10px 14px', background: '#fefce8', border: '1px solid #fde047', borderRadius: '8px', fontSize: '12px', color: '#713f12' }}>
              ⚠️ OMOP: plausibleTemporalAfter — 시작 컬럼의 날짜가 종료 컬럼보다 앞서야 합니다.
            </div>
          </div>
        );

      case 'duplicate_check':
        return (
          <div>
            <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>중복 검사 대상 컬럼</label>
            <select
              value={ruleForm.parameters.targetColumn || 'first_column'}
              onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, targetColumn: e.target.value } }))}
              style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
            >
              <option value="first_column">첫 번째 컬럼 (샘플 ID)</option>
              <option value="custom">직접 입력</option>
            </select>
            {ruleForm.parameters.targetColumn === 'custom' && (
              <input type="text" placeholder="컬럼명 입력"
                value={ruleForm.parameters.customColumn || ''}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, customColumn: e.target.value } }))}
                style={{ width: '100%', marginTop: '8px', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
              />
            )}
          </div>
        );

      case 'datatype_check':
        return (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>대상 컬럼</label>
              <select
                value={ruleForm.parameters.targetColumn || 'all_except_first'}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, targetColumn: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
              >
                <option value="all_except_first">샘플 ID 제외 전체 컬럼</option>
                <option value="first_column">첫 번째 컬럼만</option>
                <option value="custom">직접 지정</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>기대 데이터 타입</label>
              <select
                value={ruleForm.parameters.expectedType || 'numeric'}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, expectedType: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
              >
                <option value="numeric">수치형 (numeric)</option>
                <option value="integer">정수형 (integer)</option>
                <option value="string">문자형 (string)</option>
                <option value="date">날짜형 (date)</option>
              </select>
            </div>
          </div>
        );

      case 'file_format':
        return (
          <div style={{ padding: '16px', background: '#f0fdf4', border: '1px solid #86efac', borderRadius: '8px' }}>
            <div style={{ fontWeight: 600, fontSize: '13px', color: '#14532d', marginBottom: '8px' }}>파일 형식 자동 감지</div>
            <div style={{ fontSize: '12px', color: '#166534' }}>
              확장자 기준으로 구분자를 자동 감지합니다:<br/>
              • <code style={{ background: '#dcfce7', padding: '1px 4px', borderRadius: '3px' }}>.tsv / .txt</code> → 탭(\t) 구분자<br/>
              • <code style={{ background: '#dcfce7', padding: '1px 4px', borderRadius: '3px' }}>.csv</code> → 쉼표(,) 구분자<br/>
              모든 행에서 구분자 수가 일치하는지 검사합니다. (OMOP: cdmTable 구조 준수)
            </div>
          </div>
        );

      case 'cross_correlation':
        return (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>상관 방법</label>
              <select
                value={ruleForm.parameters.method || 'pearson'}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, method: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
              >
                <option value="pearson">Pearson (선형)</option>
                <option value="spearman">Spearman (순위)</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>최소 상관계수</label>
              <input type="number" step="0.05" min="0" max="1"
                value={ruleForm.parameters.minCorrelation ?? 0.3}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, minCorrelation: parseFloat(e.target.value) } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>최대 상관계수</label>
              <input type="number" step="0.05" min="0" max="1"
                value={ruleForm.parameters.maxCorrelation ?? 1.0}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, maxCorrelation: parseFloat(e.target.value) } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
              />
            </div>
            <div style={{ gridColumn: '1/-1', padding: '10px 14px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '8px', fontSize: '12px', color: '#1e3a8a' }}>
              💡 OMOP: Computational subcategory — RNA-Protein 발현 상관관계 r ≥ 0.3 권고 (심화 검증)
            </div>
          </div>
        );

      case 'column_range':
        return (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>대상 컬럼명</label>
              <input type="text"
                value={ruleForm.parameters.targetColumn || ''}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, targetColumn: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                placeholder="예: age, year_of_birth"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>최소값</label>
              <input type="number"
                value={ruleForm.parameters.min ?? ''}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, min: parseFloat(e.target.value) } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                placeholder="예: 0"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>최대값</label>
              <input type="number"
                value={ruleForm.parameters.max ?? ''}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, max: parseFloat(e.target.value) } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                placeholder="예: 120"
              />
            </div>
          </div>
        );

      case 'batch_label_check':
        return (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>배치 레이블 컬럼명</label>
              <input type="text"
                value={ruleForm.parameters.batchColumn || 'batch'}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, batchColumn: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                placeholder="예: batch, platform, site"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>최대 불균형 비율 (최대/최소 배치 크기)</label>
              <input type="number" min="1" step="1"
                value={ruleForm.parameters.maxImbalanceRatio ?? 5}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, maxImbalanceRatio: parseFloat(e.target.value) } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
              />
            </div>
            <div style={{ gridColumn: '1/-1', padding: '10px 14px', background: '#f0fdf4', border: '1px solid #86efac', borderRadius: '8px', fontSize: '12px', color: '#14532d' }}>
              💡 배치 레이블이 없으면 kBET, iLISI/cLISI 등 BatchEval 지표 계산이 불가합니다. 브라우저에서 직접 계산 가능한 사전 확인 지표입니다.
            </div>
          </div>
        );

      case 'batch_mean_deviation':
        return (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>배치 레이블 컬럼명</label>
              <input type="text"
                value={ruleForm.parameters.batchColumn || 'batch'}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, batchColumn: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                placeholder="예: batch, platform"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>최대 허용 CV% (배치 간 평균 편차)</label>
              <input type="number" min="0" max="100"
                value={ruleForm.parameters.maxCVPercent ?? 30}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, maxCVPercent: parseFloat(e.target.value) } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
              />
            </div>
            <div style={{ gridColumn: '1/-1', padding: '10px 14px', background: '#fefce8', border: '1px solid #fde047', borderRadius: '8px', fontSize: '12px', color: '#713f12' }}>
              ⚠️ BatchEval의 kBET/iLISI 대체재가 아닙니다. 사전 선별용 지표입니다. 정밀 평가는 BatchEval Python 실행이 필요합니다.
            </div>
          </div>
        );

      case 'external_score':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ padding: '12px 16px', background: '#eff6ff', border: '1px solid #93c5fd', borderRadius: '8px', fontSize: '12px', color: '#1e40af' }}>
              <div style={{ fontWeight: 700, marginBottom: '6px' }}>⚙️ 외부 도구 연동 지표 — {ruleForm.parameters.toolName || 'BatchEval'}</div>
              <div>{ruleForm.parameters.note || 'BatchEval Python 실행 후 계산된 점수를 아래에 입력하세요.'}</div>
              <div style={{ marginTop: '6px', fontFamily: 'monospace', fontSize: '11px', background: '#dbeafe', padding: '6px 8px', borderRadius: '4px' }}>
                pip install BatchEval → python batcheval run [options]
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>지표명 (scoreName)</label>
                <input type="text"
                  value={ruleForm.parameters.scoreName || ''}
                  onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, scoreName: e.target.value } }))}
                  style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', fontFamily: 'monospace' }}
                  placeholder="예: kBET_accept_rate"
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>비교 연산자</label>
                <select
                  value={ruleForm.parameters.operator || '>='}
                  onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, operator: e.target.value } }))}
                  style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                >
                  <option value=">=">≥ 이상</option>
                  <option value="<=">≤ 이하</option>
                  <option value=">">{'>'} 초과</option>
                  <option value="<">{'<'} 미만</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>기준값</label>
                <input type="number" step="0.01"
                  value={ruleForm.parameters.threshold ?? ''}
                  onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, threshold: parseFloat(e.target.value) } }))}
                  style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                  placeholder="예: 0.05"
                />
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>도구명</label>
                <input type="text"
                  value={ruleForm.parameters.toolName || 'BatchEval'}
                  onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, toolName: e.target.value } }))}
                  style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>버전 (선택)</label>
                <input type="text"
                  value={ruleForm.parameters.toolVersion || ''}
                  onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, toolVersion: e.target.value } }))}
                  style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                  placeholder="예: 1.0.0"
                />
              </div>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>사전 계산된 점수 입력 <span style={{ color: '#ef4444', fontWeight: 700 }}>*</span></label>
              <input type="number" step="0.001"
                value={ruleForm.parameters._inputScore ?? ''}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, _inputScore: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '2px solid #3b82f6', borderRadius: '8px', fontSize: '14px' }}
                placeholder="BatchEval 실행 결과값 (예: 0.73)"
              />
            </div>
          </div>
        );

      case 'conditional_required':
        return (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>조건 컬럼 (이 컬럼이 존재할 때)</label>
              <input type="text"
                value={ruleForm.parameters.conditionColumn || ''}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, conditionColumn: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                placeholder="예: diagnosis_date"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>필수 컬럼 (반드시 있어야 할 컬럼)</label>
              <input type="text"
                value={ruleForm.parameters.requiredColumn || ''}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, requiredColumn: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                placeholder="예: diagnosis_code"
              />
            </div>
            <div style={{ gridColumn: '1/-1', padding: '10px 14px', background: '#fefce8', border: '1px solid #fde047', borderRadius: '8px', fontSize: '12px', color: '#713f12' }}>
              ⚠️ OMOP: isConditionalRequired (2255) — 조건 컬럼이 존재할 때 필수 컬럼도 존재해야 합니다.
            </div>
          </div>
        );

      case 'negative_check':
        return (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>검사 대상 컬럼</label>
              <select
                value={ruleForm.parameters.targetColumn || 'all_except_first'}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, targetColumn: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
              >
                <option value="all_except_first">샘플 ID 제외 전체 컬럼</option>
                <option value="custom">특정 컬럼 지정</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>음수값 허용</label>
              <select
                value={ruleForm.parameters.allowNegative ? 'true' : 'false'}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, allowNegative: e.target.value === 'true' } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
              >
                <option value="false">허용 안 함 (Raw count 등)</option>
                <option value="true">허용 (log-transformed 등)</option>
              </select>
            </div>
          </div>
        );

      case 'date_format':
        return (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>날짜 컬럼명</label>
              <input type="text"
                value={ruleForm.parameters.targetColumn || ''}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, targetColumn: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
                placeholder="예: diagnosis_date, birth_date"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>기대 날짜 형식</label>
              <select
                value={ruleForm.parameters.dateFormat || 'YYYY-MM-DD'}
                onChange={(e) => setRuleForm(prev => ({ ...prev, parameters: { ...prev.parameters, dateFormat: e.target.value } }))}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px' }}
              >
                <option value="YYYY-MM-DD">YYYY-MM-DD (ISO 표준)</option>
                <option value="YYYYMMDD">YYYYMMDD</option>
                <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                <option value="MM/DD/YYYY">MM/DD/YYYY</option>
              </select>
            </div>
          </div>
        );

      default:
        return (
          <div style={{ 
            padding: '20px', 
            background: '#f8fafc', 
            borderRadius: '8px',
            textAlign: 'center',
            color: '#64748b'
          }}>
            검증 유형을 선택하면 파라미터 설정이 표시됩니다.
          </div>
        );
    }
  };

  // 차원 색상
  const getDimensionColor = (dimension) => {
    const colors = {
      'Completeness': { bg: '#dbeafe', border: '#3b82f6', text: '#1d4ed8' },
      'Plausibility': { bg: '#fef3c7', border: '#f59e0b', text: '#b45309' },
      'Conformance': { bg: '#d1fae5', border: '#10b981', text: '#047857' }
    };
    return colors[dimension] || { bg: '#f1f5f9', border: '#94a3b8', text: '#475569' };
  };

  // 수준 뱃지
  const getLevelBadge = (level) => {
    if (level === 'basic') {
      return (
        <span style={{
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '11px',
          fontWeight: '600',
          background: '#f1f5f9',
          color: '#475569'
        }}>
          기초
        </span>
      );
    }
    return (
      <span style={{
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '11px',
        fontWeight: '600',
        background: 'linear-gradient(135deg, #8b5cf6, #6366f1)',
        color: 'white'
      }}>
        심화
      </span>
    );
  };

  return (
    <div style={{ 
      fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, sans-serif',
      minHeight: '100vh',
      background: '#ffffff'
    }}>
      <style>{`@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');`}</style>
      
      {/* 헤더 */}
      <header style={{
        background: 'white',
        borderBottom: '1px solid #e2e8f0',
        padding: '16px 32px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ 
              fontSize: '24px', 
              fontWeight: '700', 
              color: '#0f172a',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <Database size={28} style={{ color: '#2563eb' }} />
              GENE-QC 품질 검증 도구
            </h1>
            <p style={{ fontSize: '14px', color: '#64748b', marginTop: '4px' }}>
              Completeness · Plausibility · Conformance 기반 멀티오믹스 데이터 품질 관리
            </p>
          </div>
          
          {/* 탭 네비게이션 */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setActiveTab('validation')}
              style={{
                padding: '10px 20px',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: '600',
                cursor: 'pointer',
                background: activeTab === 'validation' ? '#2563eb' : '#f1f5f9',
                color: activeTab === 'validation' ? 'white' : '#475569',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <Play size={16} />
              품질 검증
            </button>
            <button
              onClick={() => setActiveTab('rules')}
              style={{
                padding: '10px 20px',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: '600',
                cursor: 'pointer',
                background: activeTab === 'rules' ? '#2563eb' : '#f1f5f9',
                color: activeTab === 'rules' ? 'white' : '#475569',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <Settings size={16} />
              규칙 관리
            </button>
          </div>
        </div>
      </header>

      {/* 메인 컨텐츠 */}
      <main style={{ padding: '24px 32px' }}>
        {activeTab === 'validation' ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            {/* 왼쪽: 데이터 업로드 & 규칙 선택 */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* 데이터 업로드 */}
              <div style={{
                background: 'white',
                border: '1px solid #e2e8f0',
                borderRadius: '12px',
                padding: '24px'
              }}>
                <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#0f172a', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Upload size={18} />
                  데이터 업로드
                </h3>
                
                <label style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '32px',
                  border: '2px dashed #cbd5e1',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  background: '#f8fafc'
                }}>
                  <FileText size={40} color="#94a3b8" />
                  <p style={{ marginTop: '12px', fontSize: '14px', fontWeight: '600', color: '#475569' }}>
                    TSV/CSV 파일을 드래그하거나 클릭하여 업로드
                  </p>
                  <p style={{ marginTop: '4px', fontSize: '12px', color: '#94a3b8' }}>
                    여러 파일을 동시에 업로드할 수 있습니다 (심화 품질 검증 시)
                  </p>
                  <input
                    type="file"
                    accept=".tsv,.csv,.txt"
                    multiple
                    onChange={handleFileUpload}
                    style={{ display: 'none' }}
                  />
                </label>

                {uploadedFiles.length > 0 && (
                  <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {uploadedFiles.map((file, idx) => (
                      <div key={file.id} style={{
                        padding: '16px',
                        background: '#f8fafc',
                        borderRadius: '10px',
                        border: '1px solid #e2e8f0'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                          <div>
                            <div style={{ fontSize: '14px', fontWeight: '600', color: '#0f172a' }}>
                              {idx + 1}. {file.name}
                            </div>
                            <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                              {file.rowCount.toLocaleString()} 행 × {file.colCount} 열
                            </div>
                          </div>
                          <button
                            onClick={() => removeFile(file.id)}
                            style={{
                              padding: '6px',
                              background: 'transparent',
                              border: 'none',
                              cursor: 'pointer',
                              color: '#ef4444'
                            }}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                        <select
                          value={file.dataType}
                          onChange={(e) => setFileDataType(file.id, e.target.value)}
                          style={{
                            width: '100%',
                            padding: '10px 12px',
                            border: '1px solid #e2e8f0',
                            borderRadius: '8px',
                            fontSize: '13px',
                            background: 'white'
                          }}
                        >
                          <option value="">데이터 유형 선택</option>
                          <option value="metadata">메타데이터 (Metadata)</option>
                          <option value="genomics">유전체 (Genomics)</option>
                          <option value="transcriptomics">전사체 (Transcriptomics)</option>
                          <option value="proteomics">단백질체 (Proteomics)</option>
                          <option value="metabolomics">대사체 (Metabolomics)</option>
                        </select>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* 규칙 선택 */}
              <div style={{
                background: 'white',
                border: '1px solid #e2e8f0',
                borderRadius: '12px',
                padding: '24px',
                flex: 1,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <CheckCircle size={18} />
                    검증 규칙 선택
                  </h3>
                  <div style={{ 
                    padding: '6px 12px', 
                    background: '#2563eb', 
                    borderRadius: '20px',
                    color: 'white',
                    fontSize: '12px',
                    fontWeight: '600'
                  }}>
                    {selectedRules.length}개 선택됨
                  </div>
                </div>

                {/* 필터 */}
                <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                  <select
                    value={filterLevel}
                    onChange={(e) => setFilterLevel(e.target.value)}
                    style={{
                      padding: '8px 12px',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      fontSize: '13px',
                      background: 'white'
                    }}
                  >
                    <option value="all">전체 수준</option>
                    <option value="basic">기초 품질</option>
                    <option value="advanced">심화 품질</option>
                  </select>
                  <select
                    value={filterDimension}
                    onChange={(e) => setFilterDimension(e.target.value)}
                    style={{
                      padding: '8px 12px',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      fontSize: '13px',
                      background: 'white'
                    }}
                  >
                    <option value="all">전체 차원</option>
                    <option value="Completeness">Completeness</option>
                    <option value="Plausibility">Plausibility</option>
                    <option value="Conformance">Conformance</option>
                  </select>
                </div>

                {/* 규칙 목록 */}
                <div style={{ flex: 1, overflowY: 'auto', marginBottom: '16px' }}>
                  {['Completeness', 'Plausibility', 'Conformance'].map(dimension => {
                    const dimensionRules = groupedRules[dimension] || [];
                    if (dimensionRules.length === 0) return null;
                    
                    const dimColor = getDimensionColor(dimension);
                    const allSelected = dimensionRules.filter(r => r.enabled).every(r => selectedRules.includes(r.id));
                    
                    return (
                      <div key={dimension} style={{ marginBottom: '12px' }}>
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '10px 12px',
                            background: dimColor.bg,
                            borderRadius: '8px',
                            cursor: 'pointer',
                            border: `1px solid ${dimColor.border}`
                          }}
                          onClick={() => setExpandedDimensions(prev => ({ ...prev, [dimension]: !prev[dimension] }))}
                        >
                          {expandedDimensions[dimension] ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                          <input
                            type="checkbox"
                            checked={allSelected && dimensionRules.filter(r => r.enabled).length > 0}
                            onChange={() => toggleDimensionSelection(dimension)}
                            onClick={(e) => e.stopPropagation()}
                            style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                          />
                          <span style={{ fontWeight: '700', color: dimColor.text }}>{dimension}</span>
                          <span style={{ fontSize: '12px', color: dimColor.text, marginLeft: 'auto' }}>
                            {dimensionRules.filter(r => r.enabled).length}개 규칙
                          </span>
                        </div>
                        
                        {expandedDimensions[dimension] && (
                          <div style={{ paddingLeft: '20px', marginTop: '8px' }}>
                            {dimensionRules.map(rule => (
                              <div
                                key={rule.id}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '10px',
                                  padding: '10px 12px',
                                  background: selectedRules.includes(rule.id) ? '#f0f9ff' : 'transparent',
                                  borderRadius: '8px',
                                  marginBottom: '4px',
                                  opacity: rule.enabled ? 1 : 0.5
                                }}
                              >
                                <input
                                  type="checkbox"
                                  checked={selectedRules.includes(rule.id)}
                                  onChange={() => toggleRuleSelection(rule.id)}
                                  disabled={!rule.enabled}
                                  style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                                />
                                {getLevelBadge(rule.level)}
                                <div style={{ flex: 1 }}>
                                  <div style={{ fontSize: '13px', fontWeight: '600', color: '#0f172a' }}>{rule.name}</div>
                                  <div style={{ fontSize: '11px', color: '#64748b' }}>{rule.description}</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* 검증 실행 버튼 */}
                <button
                  onClick={runValidation}
                  disabled={isValidating || uploadedFiles.length === 0 || selectedRules.length === 0}
                  style={{
                    width: '100%',
                    padding: '14px',
                    background: (isValidating || uploadedFiles.length === 0 || selectedRules.length === 0) 
                      ? '#cbd5e1' 
                      : 'linear-gradient(135deg, #2563eb, #1d4ed8)',
                    border: 'none',
                    borderRadius: '10px',
                    color: 'white',
                    fontSize: '15px',
                    fontWeight: '700',
                    cursor: (isValidating || uploadedFiles.length === 0 || selectedRules.length === 0) ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px'
                  }}
                >
                  <Play size={18} />
                  {isValidating ? '검증 중...' : '품질 검증 실행'}
                </button>
              </div>
            </div>

            {/* 오른쪽: 검증 결과 */}
            <div style={{
              background: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '12px',
              padding: '24px',
              display: 'flex',
              flexDirection: 'column'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileText size={18} />
                  검증 결과
                </h3>
                {validationResults && (
                  <button
                    onClick={exportResults}
                    style={{
                      padding: '8px 16px',
                      background: '#f1f5f9',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      fontSize: '13px',
                      fontWeight: '600',
                      color: '#475569',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <Download size={14} />
                    JSON 내보내기
                  </button>
                )}
              </div>

              {!validationResults ? (
                <div style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#94a3b8'
                }}>
                  <Layers size={64} />
                  <p style={{ marginTop: '16px', fontSize: '15px', fontWeight: '600' }}>검증 결과가 여기에 표시됩니다</p>
                  <p style={{ marginTop: '8px', fontSize: '13px' }}>데이터와 규칙을 선택한 후 검증을 실행하세요</p>
                </div>
              ) : (
                <div style={{ flex: 1, overflowY: 'auto' }}>
                  {/* 요약 카드 */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '20px' }}>
                    <div style={{
                      padding: '16px',
                      background: '#d1fae5',
                      borderRadius: '10px',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '28px', fontWeight: '700', color: '#047857' }}>
                        {validationResults.filter(r => r.status === 'pass').length}
                      </div>
                      <div style={{ fontSize: '12px', fontWeight: '600', color: '#047857' }}>통과</div>
                    </div>
                    <div style={{
                      padding: '16px',
                      background: '#fef3c7',
                      borderRadius: '10px',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '28px', fontWeight: '700', color: '#b45309' }}>
                        {validationResults.filter(r => r.status === 'warning').length}
                      </div>
                      <div style={{ fontSize: '12px', fontWeight: '600', color: '#b45309' }}>경고</div>
                    </div>
                    <div style={{
                      padding: '16px',
                      background: '#fee2e2',
                      borderRadius: '10px',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '28px', fontWeight: '700', color: '#dc2626' }}>
                        {validationResults.filter(r => r.status === 'fail').length}
                      </div>
                      <div style={{ fontSize: '12px', fontWeight: '600', color: '#dc2626' }}>실패</div>
                    </div>
                    {validationResults.filter(r => r.status === 'pending').length > 0 && (
                      <div style={{
                        padding: '16px',
                        background: '#dbeafe',
                        borderRadius: '10px',
                        textAlign: 'center'
                      }}>
                        <div style={{ fontSize: '28px', fontWeight: '700', color: '#1d4ed8' }}>
                          {validationResults.filter(r => r.status === 'pending').length}
                        </div>
                        <div style={{ fontSize: '12px', fontWeight: '600', color: '#1d4ed8' }}>점수 미입력</div>
                      </div>
                    )}
                  </div>

                  {/* 상세 결과 */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {validationResults.map((result, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '14px 16px',
                          borderRadius: '10px',
                          border: '1px solid',
                          borderColor: result.status === 'pass' ? '#6ee7b7' : result.status === 'warning' ? '#fcd34d' : result.status === 'pending' ? '#93c5fd' : '#fca5a5',
                          background: result.status === 'pass' ? '#f0fdf4' : result.status === 'warning' ? '#fffbeb' : result.status === 'pending' ? '#eff6ff' : '#fef2f2'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                          {result.status === 'pass' ? (
                            <CheckCircle size={18} color="#047857" />
                          ) : result.status === 'warning' ? (
                            <AlertTriangle size={18} color="#b45309" />
                          ) : result.status === 'pending' ? (
                            <span style={{ fontSize: '16px' }}>⚙️</span>
                          ) : (
                            <XCircle size={18} color="#dc2626" />
                          )}
                          <span style={{ fontWeight: '700', color: '#0f172a', fontSize: '14px' }}>{result.ruleName}</span>
                          {getLevelBadge(result.level)}
                          <span style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '10px',
                            fontWeight: '600',
                            background: getDimensionColor(result.dimension).bg,
                            color: getDimensionColor(result.dimension).text
                          }}>
                            {result.dimension}
                          </span>
                        </div>
                        <div style={{ fontSize: '13px', color: '#475569', marginLeft: '28px' }}>
                          <div>{result.message}</div>
                          <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                            파일: {result.fileName}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* 규칙 관리 탭 — 2페이지 구조 (피드백 260122) */
          <div>
            {/* 서브탭: 규칙 선택 / 규칙 관리 */}
            <div style={{ display: 'flex', gap: '4px', marginBottom: '24px', background: '#f1f5f9', borderRadius: '10px', padding: '4px', width: 'fit-content' }}>
              <button
                onClick={() => setRulesSubTab('select')}
                style={{
                  padding: '8px 20px', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: '600',
                  cursor: 'pointer',
                  background: rulesSubTab === 'select' ? 'white' : 'transparent',
                  color: rulesSubTab === 'select' ? '#0f172a' : '#64748b',
                  boxShadow: rulesSubTab === 'select' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
                }}
              >
                검증 규칙 선택
              </button>
              <button
                onClick={() => setRulesSubTab('manage')}
                style={{
                  padding: '8px 20px', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: '600',
                  cursor: 'pointer',
                  background: rulesSubTab === 'manage' ? 'white' : 'transparent',
                  color: rulesSubTab === 'manage' ? '#0f172a' : '#64748b',
                  boxShadow: rulesSubTab === 'manage' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
                }}
              >
                전체 규칙 관리
              </button>
            </div>

            {rulesSubTab === 'select' && (
              <div style={{ marginBottom: '16px', padding: '12px 16px', background: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe', fontSize: '13px', color: '#1e40af' }}>
                <strong>Page 1 — 규칙 선택</strong>: 이번 품질검증에 사용할 규칙을 선택합니다. 선택된 규칙은 [품질 검증] 탭에서 바로 적용됩니다.
              </div>
            )}

            {rulesSubTab === 'manage' && (
              <div style={{ marginBottom: '16px', padding: '12px 16px', background: '#f0fdf4', borderRadius: '8px', border: '1px solid #86efac', fontSize: '13px', color: '#14532d' }}>
                <strong>Page 2 — 규칙 관리</strong>: 시스템에 등록된 전체 규칙을 조회, 수정, 삭제하거나 커스텀 규칙을 추가합니다.
              </div>
            )}

            {/* 규칙 관리 헤더 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <div style={{ position: 'relative' }}>
                  <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
                  <input
                    type="text"
                    placeholder="규칙 검색..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{
                      padding: '10px 12px 10px 38px',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      fontSize: '14px',
                      width: '280px'
                    }}
                  />
                </div>
                <select
                  value={filterDimension}
                  onChange={(e) => setFilterDimension(e.target.value)}
                  style={{
                    padding: '10px 16px',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    fontSize: '14px'
                  }}
                >
                  <option value="all">전체 차원</option>
                  <option value="Completeness">Completeness</option>
                  <option value="Plausibility">Plausibility</option>
                  <option value="Conformance">Conformance</option>
                </select>
                <select
                  value={filterLevel}
                  onChange={(e) => setFilterLevel(e.target.value)}
                  style={{
                    padding: '10px 16px',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    fontSize: '14px'
                  }}
                >
                  <option value="all">전체 수준</option>
                  <option value="basic">기초 품질</option>
                  <option value="advanced">심화 품질</option>
                </select>
              </div>
              <button
                onClick={startCreateRule}
                style={{
                  padding: '10px 20px',
                  background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
                  border: 'none',
                  borderRadius: '10px',
                  color: 'white',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <Plus size={18} />
                커스텀 규칙 추가
              </button>
            </div>

            {/* 규칙 목록 */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {['Completeness', 'Plausibility', 'Conformance'].map(dimension => {
                const dimensionRules = groupedRules[dimension] || [];
                if (dimensionRules.length === 0) return null;
                
                const dimColor = getDimensionColor(dimension);
                
                return (
                  <div key={dimension} style={{
                    background: 'white',
                    border: '1px solid #e2e8f0',
                    borderRadius: '12px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      padding: '16px 20px',
                      background: dimColor.bg,
                      borderBottom: `2px solid ${dimColor.border}`,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px'
                    }}>
                      <span style={{ fontSize: '18px', fontWeight: '700', color: dimColor.text }}>{dimension}</span>
                      <span style={{ fontSize: '13px', color: dimColor.text }}>
                        ({dimensionRules.length}개 규칙)
                      </span>
                    </div>
                    
                    <div style={{ padding: '12px' }}>
                      {dimensionRules.map(rule => (
                        <div
                          key={rule.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            padding: '16px',
                            borderRadius: '10px',
                            background: '#f8fafc',
                            marginBottom: '8px',
                            opacity: rule.enabled ? 1 : 0.6
                          }}
                        >
                          <div style={{ flex: 1 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', flexWrap: 'wrap' }}>
                              {getLevelBadge(rule.level)}
                              <span style={{ fontWeight: '700', color: '#0f172a', fontSize: '15px' }}>{rule.name}</span>
                              <span style={{
                                padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: '700',
                                background: SEVERITY_CONFIG[rule.severity]?.bg || '#f8fafc',
                                color: SEVERITY_CONFIG[rule.severity]?.color || '#64748b',
                                border: '1px solid ' + (rule.severity==='fatal'?'#fca5a5':rule.severity==='error'?'#fed7aa':rule.severity==='warning'?'#fde047':rule.severity==='characterization'?'#86efac':'#e2e8f0')
                              }}>
                                {rule.severity==='characterization'?'PROFILE':(rule.severity||'warning').toUpperCase()}
                              </span>
                              {(rule.id.startsWith('custom_')||rule.isCustom) && (
                                <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: '600', background: '#ddd6fe', color: '#7c3aed' }}>커스텀</span>
                              )}
                            </div>
                            <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '8px' }}>{rule.description}</p>
                            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
                              {rule.metricId && <span style={{ padding: '2px 7px', background: '#fefce8', border: '1px solid #fde68a', borderRadius: '4px', fontSize: '10px', fontWeight: '700', color: '#92400e', fontFamily: 'monospace' }}>{rule.metricId}</span>}
                              {rule.metricLevel && <span style={{ padding: '2px 7px', background: '#f1f5f9', borderRadius: '4px', fontSize: '10px', color: '#475569' }}>{rule.metricLevel}</span>}
                              {rule.context && <span style={{ padding: '2px 7px', background: rule.context==='Verification'?'#eff6ff':'#fdf4ff', borderRadius: '4px', fontSize: '10px', color: rule.context==='Verification'?'#1d4ed8':'#7c3aed' }}>{rule.context}</span>}
                              {rule.subcategory && <span style={{ padding: '2px 7px', background: '#f0fdf4', borderRadius: '4px', fontSize: '10px', color: '#15803d' }}>{rule.subcategory}</span>}
                              <span style={{ margin: '0 2px', color: '#e2e8f0' }}>|</span>
                              {rule.dataTypes.map(type => (
                                <span key={type} style={{ padding: '3px 8px', background: '#e0e7ff', borderRadius: '4px', fontSize: '11px', fontWeight: '500', color: '#3730a3' }}>
                                  {type}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            <button
                              onClick={() => toggleRuleEnabled(rule.id)}
                              style={{
                                padding: '8px 14px',
                                background: rule.enabled ? '#d1fae5' : '#f1f5f9',
                                border: `1px solid ${rule.enabled ? '#10b981' : '#cbd5e1'}`,
                                borderRadius: '6px',
                                fontSize: '12px',
                                fontWeight: '600',
                                cursor: 'pointer',
                                color: rule.enabled ? '#047857' : '#64748b'
                              }}
                            >
                              {rule.enabled ? '활성' : '비활성'}
                            </button>
                            <button
                              onClick={() => startEditRule(rule)}
                              style={{
                                padding: '8px',
                                background: 'white',
                                border: '1px solid #e2e8f0',
                                borderRadius: '6px',
                                cursor: 'pointer'
                              }}
                            >
                              <Edit3 size={16} color="#64748b" />
                            </button>
                            <button
                              onClick={() => deleteRule(rule.id)}
                              style={{
                                padding: '8px',
                                background: '#fee2e2',
                                border: '1px solid #fca5a5',
                                borderRadius: '6px',
                                cursor: 'pointer'
                              }}
                            >
                              <Trash2 size={16} color="#dc2626" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>

      {/* 규칙 생성/편집 모달 */}
      {showRuleModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'white',
            borderRadius: '16px',
            padding: '28px',
            width: '700px',
            maxHeight: '90vh',
            overflowY: 'auto'
          }}>
            <h2 style={{ fontSize: '20px', fontWeight: '700', color: '#0f172a', marginBottom: '24px' }}>
              {editingRule ? '규칙 수정' : '새 커스텀 규칙 생성'}
            </h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* 기본 정보 */}
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>
                  규칙 이름 *
                </label>
                <input
                  type="text"
                  value={ruleForm.name}
                  onChange={(e) => setRuleForm(prev => ({ ...prev, name: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    border: '1px solid #e2e8f0',
                    borderRadius: '10px',
                    fontSize: '14px'
                  }}
                  placeholder="예: 컬럼별 결측률 검사"
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>
                    품질 차원 *
                  </label>
                  <select
                    value={ruleForm.dimension}
                    onChange={(e) => setRuleForm(prev => ({ ...prev, dimension: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '12px 14px',
                      border: '1px solid #e2e8f0',
                      borderRadius: '10px',
                      fontSize: '14px'
                    }}
                  >
                    <option value="Completeness">Completeness (완전성)</option>
                    <option value="Plausibility">Plausibility (타당성)</option>
                    <option value="Conformance">Conformance (적합성)</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>
                    품질 수준 *
                  </label>
                  <select
                    value={ruleForm.level}
                    onChange={(e) => setRuleForm(prev => ({ ...prev, level: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '12px 14px',
                      border: '1px solid #e2e8f0',
                      borderRadius: '10px',
                      fontSize: '14px'
                    }}
                  >
                    <option value="basic">기초 품질 (단일 데이터)</option>
                    <option value="advanced">심화 품질 (다중 데이터)</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>
                    심각도 *
                  </label>
                  <select
                    value={ruleForm.severity}
                    onChange={(e) => setRuleForm(prev => ({ ...prev, severity: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '12px 14px',
                      border: '1px solid #e2e8f0',
                      borderRadius: '10px',
                      fontSize: '14px'
                    }}
                  >
                    <option value="error">Error (오류)</option>
                    <option value="warning">Warning (경고)</option>
                    <option value="info">Info (정보)</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>
                  설명
                </label>
                <textarea
                  value={ruleForm.description}
                  onChange={(e) => setRuleForm(prev => ({ ...prev, description: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    border: '1px solid #e2e8f0',
                    borderRadius: '10px',
                    fontSize: '14px',
                    minHeight: '80px',
                    resize: 'vertical'
                  }}
                  placeholder="이 규칙이 무엇을 검사하는지 설명해주세요"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>
                  적용 데이터 유형
                </label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {['metadata', 'genomics', 'transcriptomics', 'proteomics', 'metabolomics'].map(type => (
                    <label key={type} style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '8px 12px',
                      background: ruleForm.dataTypes.includes(type) ? '#dbeafe' : '#f8fafc',
                      border: `1px solid ${ruleForm.dataTypes.includes(type) ? '#3b82f6' : '#e2e8f0'}`,
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontSize: '13px'
                    }}>
                      <input
                        type="checkbox"
                        checked={ruleForm.dataTypes.includes(type)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setRuleForm(prev => ({ ...prev, dataTypes: [...prev.dataTypes, type] }));
                          } else {
                            setRuleForm(prev => ({ ...prev, dataTypes: prev.dataTypes.filter(t => t !== type) }));
                          }
                        }}
                        style={{ width: '14px', height: '14px' }}
                      />
                      {type}
                    </label>
                  ))}
                </div>
              </div>

              {/* 검증 유형 선택 */}
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>
                  검증 유형 *
                </label>
                <select
                  value={ruleForm.validationType}
                  onChange={(e) => setRuleForm(prev => ({ 
                    ...prev, 
                    validationType: e.target.value,
                    parameters: {} 
                  }))}
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    border: '1px solid #e2e8f0',
                    borderRadius: '10px',
                    fontSize: '14px'
                  }}
                >
                  <optgroup label="기초 품질 (단일 파일)">
                    <option value="threshold">임계값 비교 (threshold)</option>
                    <option value="range">값 범위 검사 (range)</option>
                    <option value="column_range">컬럼 범위 검사 (column_range)</option>
                    <option value="value_set">허용값 집합 검사 (value_set)</option>
                    <option value="regex_pattern">정규식 패턴 검사 (regex_pattern)</option>
                    <option value="duplicate_check">중복값 검사 (duplicate_check)</option>
                    <option value="datatype_check">데이터 타입 검사 (datatype_check)</option>
                    <option value="column_exists">컬럼 존재 여부 (column_exists)</option>
                    <option value="date_order">날짜 순서 검사 (date_order)</option>
                    <option value="date_format">날짜 형식 표준 (date_format)</option>
                    <option value="negative_check">음수값 검사 (negative_check)</option>
                    <option value="conditional_required">조건부 필수 컬럼 (conditional_required)</option>
                    <option value="file_format">파일 형식 일관성 (file_format)</option>
                    <option value="header_exists">헤더 존재 여부 (header_exists)</option>
                  </optgroup>
                  <optgroup label="심화 품질 (다중 파일 교차)">
                    <option value="cross_threshold">교차 임계값 비교 (cross_threshold)</option>
                    <option value="cross_correlation">교차 상관관계 (cross_correlation)</option>
                    <option value="cross_consistency">교차 일관성 검사 (cross_consistency)</option>
                    <option value="cross_format">ID 형식 일관성 (cross_format)</option>
                  </optgroup>
                  <optgroup label="배치효과 (BatchEval 연동)">
                    <option value="batch_label_check">배치 레이블 확인 — 직접 계산 (batch_label_check)</option>
                    <option value="batch_mean_deviation">배치 간 발현 편차 — 직접 계산 (batch_mean_deviation)</option>
                    <option value="external_score">외부 점수 입력 — BatchEval 연동 (external_score)</option>
                  </optgroup>
                </select>
              </div>

              {/* OMOP 정렬 필드 (접기 가능) */}
              <div style={{ border: '1px solid #e2e8f0', borderRadius: '10px', padding: '16px', background: '#f8fafc' }}>
                <div style={{ fontSize: '12px', fontWeight: '700', color: '#64748b', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  OMOP CDM DQM 정렬 필드 <span style={{ fontWeight: 400, color: '#94a3b8' }}>(선택사항)</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>검사 수준 (metricLevel)</label>
                    <select
                      value={ruleForm.metricLevel || 'COLUMN'}
                      onChange={(e) => setRuleForm(prev => ({ ...prev, metricLevel: e.target.value }))}
                      style={{ width: '100%', padding: '8px 10px', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '13px', background: 'white' }}
                    >
                      <option value="FILE">FILE (파일 수준)</option>
                      <option value="COLUMN">COLUMN (컬럼 수준)</option>
                      <option value="VALUE">VALUE (값 수준)</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>검사 구분 (context)</label>
                    <select
                      value={ruleForm.context || 'Verification'}
                      onChange={(e) => setRuleForm(prev => ({ ...prev, context: e.target.value }))}
                      style={{ width: '100%', padding: '8px 10px', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '13px', background: 'white' }}
                    >
                      <option value="Verification">Verification (구조 검사)</option>
                      <option value="Validation">Validation (의미 검사)</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>하위 분류 (subcategory)</label>
                    <select
                      value={ruleForm.subcategory || ''}
                      onChange={(e) => setRuleForm(prev => ({ ...prev, subcategory: e.target.value }))}
                      style={{ width: '100%', padding: '8px 10px', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '13px', background: 'white' }}
                    >
                      <option value="">— 없음 —</option>
                      <option value="Relational">Relational (구조)</option>
                      <option value="Atemporal">Atemporal (공간적)</option>
                      <option value="Temporal">Temporal (시간적)</option>
                      <option value="Value">Value (값)</option>
                      <option value="Conditional">Conditional (조건부)</option>
                      <option value="Computational">Computational (계산적)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* 검증 파라미터 */}
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>
                  검증 파라미터
                </label>
                {renderParameterForm()}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '28px' }}>
              <button
                onClick={() => {
                  setShowRuleModal(false);
                  setEditingRule(null);
                  setRuleForm(getEmptyRuleForm());
                }}
                style={{
                  padding: '12px 24px',
                  background: '#f1f5f9',
                  border: '1px solid #e2e8f0',
                  borderRadius: '10px',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  color: '#475569'
                }}
              >
                취소
              </button>
              <button
                onClick={saveRule}
                style={{
                  padding: '12px 24px',
                  background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
                  border: 'none',
                  borderRadius: '10px',
                  color: 'white',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                {editingRule ? '수정 완료' : '규칙 생성'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OmicsQualityValidator;
