/**
 * @description 검증 규칙 설정 페이지
 */

import { useEffect, useState } from "react";
import { apiClient } from "../../../shared/api/client";
import * as S from "./rulesPage.styles";

type RuleLevel = "Basic" | "Advanced";
type RuleDimension = "FATAL" | "WARNING" | "ERROR" | "CHARACTERIZATION" | "CONVENTION";

interface Rule {
  id: string;
  name: string;
  tags: RuleDimension[];
  level: RuleLevel;
  description: string;
}

interface RuleCategory {
  id: string;
  name: string;
  rules: Rule[];
}

const RULE_CATEGORIES: RuleCategory[] = [
  {
    id: "completeness",
    name: "Completeness",
    rules: [
      {
        id: "file-header-existence",
        name: "File Header Existence",
        tags: ["FATAL"],
        level: "Basic",
        description: "Verifies that the file contains a header row with at least the minimum number of columns.",
      },
      {
        id: "required-sample-id-columns",
        name: "Required Sample ID Column",
        tags: ["FATAL"],
        level: "Basic",
        description: "Checks that the first column (Sample ID) exists without NULL values. Sample identifiers are required for cross-validation.",
      },
      {
        id: "column-level-missing-rate",
        name: "Column-level Missing Rate",
        tags: ["WARNING"],
        level: "Basic",
        description: "Measures the proportion of missing values (empty, NA, null, NaN) per column.",
      },
      {
        id: "row-sample-completeness",
        name: "Row (Sample) Completeness",
        tags: ["WARNING"],
        level: "Basic",
        description: "Checks that the proportion of valid values per row (sample) meets the threshold.",
      },
      {
        id: "overall-data-missing-rate",
        name: "Overall Data Missing Rate",
        tags: ["WARNING"],
        level: "Basic",
        description:
          "Measures the overall missing value proportion across the entire dataset. Recommended thresholds: DNA 99%. RNA 80%, Protein 75%.",
      },
      {
        id: "cross-dataset-sample-matching-rate",
        name: "Cross-Dataset Sample Matching Rate",
        tags: ["WARNING"],
        level: "Advanced",
        description: "Measures the proportion of shared sample IDs across multiple datasets.",
      },
      {
        id: "common-sample-count-across-datasets",
        name: "Common Sample Count Across Datasets",
        tags: ["ERROR"],
        level: "Advanced",
        description: "Counts the number of samples present in all registered datasets.",
      },
    ],
  },
  {
    id: "plausibility",
    name: "Plausibility",
    rules: [
      {
        id: "expression-value-lower-bound",
        name: "Expression Value Lower Bound",
        tags: ["CHARACTERIZATION"],
        level: "Basic",
        description: "Checks the proportion ot numeric expression values below the configured lower bound.",
      },
      {
        id: "expression-value-upper-bound",
        name: "Expression Value Upper Bound",
        tags: ["CHARACTERIZATION"],
        level: "Basic",
        description: "Checks the proportion of numeric expression values excedding the configured upper bound.",
      },
      {
        id: "iqr-based-outlier-detection",
        name: "IQR-Based Outlier Detection",
        tags: ["WARNING"],
        level: "Basic",
        description: "Detects outliers using the Interquartile Range (IQR × 1.5) method.",
      },
      {
        id: "zero-variance-column-detection",
        name: "Zero-Variance Column Detection",
        tags: ["WARNING"],
        level: "Basic",
        description: "Detects columns with zero variance (constant values only), indicating uninformative features.",
      },
      {
        id: "sex-gender-value-set-check",
        name: "Sex/Gender Value Set Check",
        tags: ["ERROR"],
        level: "Basic",
        description: "Validates that sex/gender column values belong to the allowed value set.",
      },
      {
        id: "age-value-range-check",
        name: "Age Value Range Check",
        tags: ["ERROR"],
        level: "Basic",
        description: "Validates that age column values fall within a plausible range (0-120).",
      },
      {
        id: "vital-status-value-set-check",
        name: "Vital Status Value Set Check",
        tags: ["CHARACTERIZATION"],
        level: "Basic",
        description: "Validates vital status values (Alive/Dead/Not Reported/0/1 etc.).",
      },
      {
        id: "survival-time-plausibility",
        name: "Survival Time Plausibility",
        tags: ["WARNING"],
        level: "Basic",
        description: "Cnecks survival time related columns are non-negative and in plausible range.",
      },
      {
        id: "temporal-plausibility-check",
        name: "Temporal Plausibility Check",
        tags: ["CHARACTERIZATION"],
        level: "Basic",
        description: "Checks temporal consistency across related fields (for example, start <= end and clinically plausible day offsets)",
      },
      {
        id: "exploratory-batch-separation",
        name: "Exploratory Batch Separation (PC1/PC2)",
        tags: ["CHARACTERIZATION"],
        level: "Advanced",
        description: "If batch labels are available, evaluates exploratory batch separation on PC1/PC2.",
      },
    ],
  },
  {
    id: "conformance",
    name: "Conformance",
    rules: [
      {
        id: "file-format-consistency",
        name: "File Format Consistency",
        tags: ["ERROR"],
        level: "Basic",
        description: "Validates that all rows have the same number of columns as the header.",
      },
      {
        id: "primary-key-uniqueness",
        name: "Primary Key Uniqueness",
        tags: ["ERROR"],
        level: "Basic",
        description: "Validates that all values in the first column (sample ID) are unique.",
      },
      {
        id: "expression-data-type-check",
        name: "Expression Data Type Check",
        tags: ["ERROR"],
        level: "Basic",
        description: "Validates that omics expression values (excluding the first column) are all numeric.",
      },
      {
        id: "sample-id-format-pattern",
        name: "Sample ID Format Pattern",
        tags: ["CONVENTION"],
        level: "Basic",
        description: "Validates that first column values match the specified regex pattern.",
      },
      {
        id: "negative-value-check-raw-count",
        name: "Negative Value Check (Raw Count)",
        tags: ["WARNING"],
        level: "Basic",
        description: "Detects negative values in raw count data, which may indicate data processing errors.",
      },
      {
        id: "batch-label-availability",
        name: "Batch Label Availability",
        tags: ["CONVENTION"],
        level: "Basic",
        description: "Checks whether batch labels exist in metadata columns (batch/plate/run/center/tss).",
      },
      {
        id: "cross-dataset-id-format-consistency",
        name: "Cross-Dataset ID Format Consistency",
        tags: ["WARNING"],
        level: "Advanced",
        description: "Validates that sample ID formats are consistent across multiple datasets.",
      },
    ],
  },
];

const ALL_RULE_IDS = new Set(RULE_CATEGORIES.flatMap((c) => c.rules.map((r) => r.id)));
const TOTAL_COUNT = ALL_RULE_IDS.size;

type TabType = "select" | "manage";

/* 커스텀 룰 모달용 타입 */
type ValidationType = "Threshold" | "Range" | "Value Set" | "Pattern (Regex)" | "Column Range" | "Categorical";
type DimensionOption = "Completeness" | "Plausibility" | "Conformance";
type SeverityOption = "Warning" | "Error" | "Info";
type MetricOption = "Missing Rate" | "Null Rate" | "Duplicate Rate";
type OperatorOption = "<=" | ">=" | "<" | ">" | "==" | "!=";

const VALIDATION_TYPES: ValidationType[] = ["Threshold", "Range", "Value Set", "Pattern (Regex)", "Column Range", "Categorical"];
const DIMENSION_OPTIONS: DimensionOption[] = ["Completeness", "Plausibility", "Conformance"];
const SEVERITY_OPTIONS: SeverityOption[] = ["Warning", "Error", "Info"];
const METRIC_OPTIONS: MetricOption[] = ["Missing Rate", "Null Rate", "Duplicate Rate"];
const OPERATOR_OPTIONS: OperatorOption[] = ["<=", ">=", "<", ">", "==", "!="];

interface NewRuleForm {
  ruleName: string;
  dimension: DimensionOption;
  severity: SeverityOption;
  validationType: ValidationType;
  targetColumn: string;
  min: string;
  max: string;
  regexPattern: string;
  allowedValues: string;
  maxCategories: string;
  metric: MetricOption;
  operator: OperatorOption;
  threshold: string;
}

const INITIAL_NEW_RULE_FORM: NewRuleForm = {
  ruleName: "",
  dimension: "Completeness",
  severity: "Warning",
  validationType: "Value Set",
  targetColumn: "",
  min: "",
  max: "",
  regexPattern: "",
  allowedValues: "",
  maxCategories: "50",
  metric: "Missing Rate",
  operator: "<=",
  threshold: "30",
};

/* 백엔드 응답 → 화면 표시용 커스텀 룰 타입 */
interface CustomRuleItem {
  id: number;
  name: string;
  dimension: string;
  severity: string;
  validationType: string;
  description: string;
  parameters: Record<string, unknown>;
}

/* 프론트엔드 ValidationType → 백엔드 validation_type 매핑 */
const VALIDATION_TYPE_TO_BACKEND: Record<ValidationType, string> = {
  Threshold: "threshold",
  Range: "range",
  "Value Set": "value_set",
  "Pattern (Regex)": "pattern",
  "Column Range": "column_range",
  Categorical: "categorical",
};

const VALIDATION_TYPE_LABEL: Record<string, string> = {
  threshold: "Threshold",
  range: "Range",
  value_set: "Value Set",
  pattern: "Pattern (Regex)",
  column_range: "Column Range",
  categorical: "Categorical",
};

/* 프론트엔드 Severity → 백엔드 severity 매핑 ("Info"는 유사 의미인 convention 으로 매핑) */
const SEVERITY_TO_BACKEND: Record<SeverityOption, string> = {
  Warning: "warning",
  Error: "error",
  Info: "convention",
};

/* 백엔드 응답 → 화면 표시용 severity 매핑 */
const SEVERITY_FROM_BACKEND: Record<string, string> = {
  warning: "Warning",
  error: "Error",
  fatal: "Error",
  convention: "Info",
  characterization: "Info",
};

/* 폼 데이터 → 백엔드 parameters 객체 변환 */
const buildParametersFromForm = (form: NewRuleForm): Record<string, unknown> => {
  switch (form.validationType) {
    case "Threshold":
      return {
        metric: form.metric,
        operator: form.operator,
        threshold: Number(form.threshold) || 0,
      };
    case "Range":
      return {
        min: Number(form.min) || 0,
        max: Number(form.max) || 0,
      };
    case "Value Set":
      return {
        target_column: form.targetColumn,
        allowed_values: form.allowedValues
          .split(",")
          .map((v) => v.trim())
          .filter(Boolean),
      };
    case "Pattern (Regex)":
      return {
        target_column: form.targetColumn,
        regex: form.regexPattern,
      };
    case "Column Range":
      return {
        target_column: form.targetColumn,
        min: Number(form.min) || 0,
        max: Number(form.max) || 0,
      };
    case "Categorical":
      return {
        target_column: form.targetColumn,
        max_categories: Number(form.maxCategories) || 0,
      };
    default:
      return {};
  }
};

/* parameters 객체 → 사람이 읽을 수 있는 설명 문자열 */
const buildDescriptionFromParameters = (validationType: string, parameters: Record<string, unknown>): string => {
  switch (validationType) {
    case "threshold": {
      const metric = parameters.metric ?? "value";
      const op = parameters.operator ?? "<=";
      const th = parameters.threshold ?? 0;
      return `${metric} ${op} ${th}`;
    }
    case "range":
      return `Range: ${parameters.min ?? "?"} ~ ${parameters.max ?? "?"}`;
    case "value_set": {
      const col = parameters.target_column ?? "?";
      const values = Array.isArray(parameters.allowed_values) ? (parameters.allowed_values as string[]).join(", ") : "";
      return `Column "${col}" must be in [${values}]`;
    }
    case "pattern":
      return `Column "${parameters.target_column ?? "?"}" must match /${parameters.regex ?? ""}/`;
    case "column_range":
      return `Column "${parameters.target_column ?? "?"}" range: ${parameters.min ?? "?"} ~ ${parameters.max ?? "?"}`;
    case "categorical":
      return `Column "${parameters.target_column ?? "?"}" max categories: ${parameters.max_categories ?? "?"}`;
    default:
      return "";
  }
};

export const RulesPage = () => {
  const [activeTab, setActiveTab] = useState<TabType>("manage");
  const [selectedRuleIds, setSelectedRuleIds] = useState<Set<string>>(new Set(ALL_RULE_IDS));
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [dimensionFilter, setDimensionFilter] = useState<string>("all");
  const [levelFilter, setLevelFilter] = useState<string>("all");
  const [isNewRuleModalOpen, setIsNewRuleModalOpen] = useState(false);
  const [newRuleForm, setNewRuleForm] = useState<NewRuleForm>(INITIAL_NEW_RULE_FORM);
  const [customRules, setCustomRules] = useState<CustomRuleItem[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 백엔드 응답을 화면용 CustomRuleItem 으로 정규화
  const normalizeRuleResponse = (raw: Record<string, unknown>): CustomRuleItem => {
    const parameters = (raw.parameters as Record<string, unknown>) ?? {};
    const validationType = (raw.validationType as string) ?? "";
    const description = (raw.description as string) || buildDescriptionFromParameters(validationType, parameters);
    return {
      id: Number(raw.id ?? 0),
      name: (raw.name as string) ?? "Custom Rule",
      dimension: (raw.dimension as string) ?? "Completeness",
      severity: SEVERITY_FROM_BACKEND[(raw.severity as string) ?? "warning"] ?? "Warning",
      validationType: VALIDATION_TYPE_LABEL[validationType] ?? validationType,
      description,
      parameters,
    };
  };

  // 마운트 시 커스텀 규칙 목록 로드
  useEffect(() => {
    const loadCustomRules = async () => {
      try {
        const result = (await apiClient.getCustomVerificationRules()) as Record<string, unknown>[];
        if (Array.isArray(result)) {
          setCustomRules(result.map(normalizeRuleResponse));
        }
      } catch (err) {
        console.error("커스텀 규칙 조회 실패:", err);
      }
    };
    loadCustomRules();
  }, []);

  const openNewRuleModal = () => {
    setNewRuleForm(INITIAL_NEW_RULE_FORM);
    setIsNewRuleModalOpen(true);
  };

  const closeNewRuleModal = () => {
    setIsNewRuleModalOpen(false);
  };

  const updateNewRuleForm = <K extends keyof NewRuleForm>(key: K, value: NewRuleForm[K]) => {
    setNewRuleForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleCreateNewRule = async () => {
    const trimmedName = newRuleForm.ruleName.trim();
    if (!trimmedName) {
      alert("Rule Name을 입력해주세요.");
      return;
    }
    if (isSubmitting) return;

    const parameters = buildParametersFromForm(newRuleForm);
    const description = buildDescriptionFromParameters(VALIDATION_TYPE_TO_BACKEND[newRuleForm.validationType], parameters);

    const payload = {
      name: trimmedName,
      dimension: newRuleForm.dimension,
      severity: SEVERITY_TO_BACKEND[newRuleForm.severity],
      qualityLevel: "basic",
      validationType: VALIDATION_TYPE_TO_BACKEND[newRuleForm.validationType],
      parameters,
      description,
      isCustom: true,
      enabled: true,
      dataTypes: [],
    };

    setIsSubmitting(true);
    try {
      const created = (await apiClient.createVerificationRule(payload)) as Record<string, unknown>;
      setCustomRules((prev) => [normalizeRuleResponse(created), ...prev]);
      closeNewRuleModal();
    } catch (err) {
      console.error("커스텀 규칙 생성 실패:", err);
      alert("커스텀 규칙 생성에 실패했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteCustomRule = async (ruleId: number) => {
    if (!window.confirm("이 커스텀 규칙을 삭제하시겠습니까?")) {
      return;
    }
    try {
      await apiClient.deleteVerificationRule(ruleId);
      setCustomRules((prev) => prev.filter((r) => r.id !== ruleId));
    } catch (err) {
      console.error("커스텀 규칙 삭제 실패:", err);
      alert("커스텀 규칙 삭제에 실패했습니다.");
    }
  };

  const toggleRule = (id: string) => {
    setSelectedRuleIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleSection = (id: string) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleCategorySelection = (category: RuleCategory) => {
    const categoryIds = category.rules.map((r) => r.id);
    const allSelected = categoryIds.every((id) => selectedRuleIds.has(id));
    setSelectedRuleIds((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        categoryIds.forEach((id) => next.delete(id));
      } else {
        categoryIds.forEach((id) => next.add(id));
      }
      return next;
    });
  };

  const filterRules = (rules: Rule[]) => {
    return rules.filter((rule) => {
      const matchSearch =
        searchQuery === "" ||
        rule.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rule.description.toLowerCase().includes(searchQuery.toLowerCase());
      const matchDimension = dimensionFilter === "all" || rule.tags.includes(dimensionFilter as RuleDimension);
      const matchLevel = levelFilter === "all" || rule.level === levelFilter;
      return matchSearch && matchDimension && matchLevel;
    });
  };

  const activeCount = selectedRuleIds.size;

  return (
    <S.Section>
      <S.PageTitleArea>
        <S.PageTitle>Rule</S.PageTitle>
        <S.PageSubtitle>OMOP CDM DQM-based · Completeness / Plausibility / Conformance rule management</S.PageSubtitle>
      </S.PageTitleArea>

      <S.Card>
        <S.CardHeader>
          <S.CardTitleGroup>
            <S.CardTitle>Quality Validation Rules</S.CardTitle>
            <S.CardSubtitle>OMOP CDM DQM-based · Completeness / Plausibility / Conformance framework</S.CardSubtitle>
          </S.CardTitleGroup>
          <S.BadgeGroup>
            <S.Badge $variant="green">Total {TOTAL_COUNT}</S.Badge>
            <S.Badge $variant="blue">Active {activeCount}</S.Badge>
          </S.BadgeGroup>
        </S.CardHeader>

        <S.TabRow>
          <S.Tab $active={activeTab === "select"} onClick={() => setActiveTab("select")}>
            Select Rules
          </S.Tab>
          <S.Tab $active={activeTab === "manage"} onClick={() => setActiveTab("manage")}>
            Manage Custom Rules
          </S.Tab>
        </S.TabRow>

        {/* Manage Custom Rules 탭 */}
        {activeTab === "manage" && (
          <S.TabContent>
            <S.ManageTopRow>
              <S.ManageDescription>Create and manage custom validation rules</S.ManageDescription>
              <S.NewRuleButton onClick={openNewRuleModal}>+ New Rule</S.NewRuleButton>
            </S.ManageTopRow>

            {customRules.length === 0 ? (
              <S.EmptyState>No custom rules yet. Click &quot;New Rule&quot; to create one.</S.EmptyState>
            ) : (
              <S.CustomRuleList>
                {customRules.map((rule) => (
                  <S.CustomRuleItem key={rule.id}>
                    <S.CustomRuleBody>
                      <S.CustomRuleHeader>
                        <S.CustomRuleName>{rule.name}</S.CustomRuleName>
                        <S.CustomRuleDimensionBadge $dimension={rule.dimension}>{rule.dimension}</S.CustomRuleDimensionBadge>
                        <S.CustomRuleSeverityBadge $severity={rule.severity}>{rule.severity}</S.CustomRuleSeverityBadge>
                        <S.CustomRuleTypeBadge>{rule.validationType}</S.CustomRuleTypeBadge>
                      </S.CustomRuleHeader>
                      {rule.description && <S.CustomRuleDescription>{rule.description}</S.CustomRuleDescription>}
                    </S.CustomRuleBody>
                    <S.CustomRuleDeleteButton onClick={() => handleDeleteCustomRule(rule.id)} title="Delete rule" aria-label="Delete rule">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M3 6h18" />
                        <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                      </svg>
                    </S.CustomRuleDeleteButton>
                  </S.CustomRuleItem>
                ))}
              </S.CustomRuleList>
            )}
          </S.TabContent>
        )}

        {/* Select Rules 탭 */}
        {activeTab === "select" && (
          <S.TabContent>
            <S.SelectRulesContainer>
              {/* 검색 & 필터 */}
              <S.SearchFilterRow>
                <S.SearchInputWrapper>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8" />
                    <path d="M21 21l-4.35-4.35" />
                  </svg>
                  <S.SearchInput type="text" placeholder="Search rules..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
                </S.SearchInputWrapper>
                <S.FilterSelect value={dimensionFilter} onChange={(e) => setDimensionFilter(e.target.value)}>
                  <option value="all">All Dimensions</option>
                  <option value="DNA">DNA</option>
                  <option value="RNA">RNA</option>
                  <option value="PROTEIN">PROTEIN</option>
                  <option value="METHYL">METHYL</option>
                  <option value="MULTI-MODAL">MULTI-MODAL</option>
                  <option value="CLINICAL">CLINICAL</option>
                </S.FilterSelect>
                <S.FilterSelect value={levelFilter} onChange={(e) => setLevelFilter(e.target.value)}>
                  <option value="all">All Levels</option>
                  <option value="Base">Base</option>
                  <option value="Advanced">Advanced</option>
                </S.FilterSelect>
              </S.SearchFilterRow>

              {/* 카테고리 섹션 */}
              {RULE_CATEGORIES.map((category) => {
                const filteredRules = filterRules(category.rules);
                const isOpen = !collapsedSections.has(category.id);
                const allSelected = category.rules.every((r) => selectedRuleIds.has(r.id));

                if (filteredRules.length === 0) return null;

                return (
                  <S.RuleCategorySection key={category.id}>
                    <S.CategoryHeader onClick={() => toggleSection(category.id)}>
                      <S.CategoryChevron $open={isOpen}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <path d="M6 9l6 6 6-6" />
                        </svg>
                      </S.CategoryChevron>
                      <S.CategoryName>{category.name}</S.CategoryName>
                      <S.CategoryCount>{category.rules.length} rules</S.CategoryCount>
                      <S.DeselectAllButton
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleCategorySelection(category);
                        }}
                      >
                        {allSelected ? "Deselect All" : "Select All"}
                      </S.DeselectAllButton>
                    </S.CategoryHeader>

                    {isOpen && (
                      <S.RuleList>
                        {filteredRules.map((rule) => (
                          <S.RuleItem key={rule.id} onClick={() => toggleRule(rule.id)}>
                            <S.RuleCheckbox
                              type="checkbox"
                              checked={selectedRuleIds.has(rule.id)}
                              onChange={() => toggleRule(rule.id)}
                              onClick={(e) => e.stopPropagation()}
                            />
                            <S.RuleInfo>
                              <S.RuleNameRow>
                                <S.RuleName>{rule.name}</S.RuleName>
                                {rule.tags.map((tag) => (
                                  <S.RuleTag key={tag} $tag={tag}>
                                    {tag}
                                  </S.RuleTag>
                                ))}
                                <S.RuleLevelBadge $level={rule.level}>{rule.level}</S.RuleLevelBadge>
                              </S.RuleNameRow>
                              <S.RuleDescription>{rule.description}</S.RuleDescription>
                            </S.RuleInfo>
                            <S.RuleStatusBadge>Active</S.RuleStatusBadge>
                          </S.RuleItem>
                        ))}
                      </S.RuleList>
                    )}
                  </S.RuleCategorySection>
                );
              })}
            </S.SelectRulesContainer>
          </S.TabContent>
        )}
      </S.Card>

      {isNewRuleModalOpen && (
        <S.ModalOverlay onClick={closeNewRuleModal}>
          <S.ModalContainer onClick={(e) => e.stopPropagation()}>
            <S.ModalTitle>New Custom Rule</S.ModalTitle>

            <S.ModalForm>
              {/* Rule Name */}
              <S.ModalField>
                <S.ModalLabel>Rule Name</S.ModalLabel>
                <S.ModalInput
                  type="text"
                  placeholder="e.g., Max Missing Rate per Column"
                  value={newRuleForm.ruleName}
                  onChange={(e) => updateNewRuleForm("ruleName", e.target.value)}
                />
              </S.ModalField>

              {/* Dimension & Severity */}
              <S.ModalRow $cols={2}>
                <S.ModalField>
                  <S.ModalLabel>Dimension</S.ModalLabel>
                  <S.ModalSelect value={newRuleForm.dimension} onChange={(e) => updateNewRuleForm("dimension", e.target.value as DimensionOption)}>
                    {DIMENSION_OPTIONS.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </S.ModalSelect>
                </S.ModalField>

                <S.ModalField>
                  <S.ModalLabel>Severity</S.ModalLabel>
                  <S.ModalSelect value={newRuleForm.severity} onChange={(e) => updateNewRuleForm("severity", e.target.value as SeverityOption)}>
                    {SEVERITY_OPTIONS.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </S.ModalSelect>
                </S.ModalField>
              </S.ModalRow>

              {/* Validation Type */}
              <S.ModalField>
                <S.ModalLabel>Validation Type</S.ModalLabel>
                <S.ModalSelect
                  value={newRuleForm.validationType}
                  onChange={(e) => updateNewRuleForm("validationType", e.target.value as ValidationType)}
                >
                  {VALIDATION_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </S.ModalSelect>
              </S.ModalField>

              {/* Validation Type별 동적 필드 */}
              {newRuleForm.validationType === "Threshold" && (
                <S.ModalRow $cols={3}>
                  <S.ModalField>
                    <S.ModalLabel>Metric</S.ModalLabel>
                    <S.ModalSelect value={newRuleForm.metric} onChange={(e) => updateNewRuleForm("metric", e.target.value as MetricOption)}>
                      {METRIC_OPTIONS.map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </S.ModalSelect>
                  </S.ModalField>
                  <S.ModalField>
                    <S.ModalLabel>Operator</S.ModalLabel>
                    <S.ModalSelect value={newRuleForm.operator} onChange={(e) => updateNewRuleForm("operator", e.target.value as OperatorOption)}>
                      {OPERATOR_OPTIONS.map((o) => (
                        <option key={o} value={o}>
                          {o}
                        </option>
                      ))}
                    </S.ModalSelect>
                  </S.ModalField>
                  <S.ModalField>
                    <S.ModalLabel>Threshold</S.ModalLabel>
                    <S.ModalInput type="number" value={newRuleForm.threshold} onChange={(e) => updateNewRuleForm("threshold", e.target.value)} />
                  </S.ModalField>
                </S.ModalRow>
              )}

              {newRuleForm.validationType === "Range" && (
                <S.ModalRow $cols={2}>
                  <S.ModalField>
                    <S.ModalLabel>Min</S.ModalLabel>
                    <S.ModalInput type="number" value={newRuleForm.min} onChange={(e) => updateNewRuleForm("min", e.target.value)} />
                  </S.ModalField>
                  <S.ModalField>
                    <S.ModalLabel>Max</S.ModalLabel>
                    <S.ModalInput type="number" value={newRuleForm.max} onChange={(e) => updateNewRuleForm("max", e.target.value)} />
                  </S.ModalField>
                </S.ModalRow>
              )}

              {newRuleForm.validationType === "Value Set" && (
                <S.ModalRow $cols={2}>
                  <S.ModalField>
                    <S.ModalLabel>Target Column</S.ModalLabel>
                    <S.ModalInput
                      type="text"
                      placeholder="e.g., sex"
                      value={newRuleForm.targetColumn}
                      onChange={(e) => updateNewRuleForm("targetColumn", e.target.value)}
                    />
                  </S.ModalField>
                  <S.ModalField>
                    <S.ModalLabel>Allowed Values (comma-separated)</S.ModalLabel>
                    <S.ModalInput
                      type="text"
                      placeholder="M, F, Unknown"
                      value={newRuleForm.allowedValues}
                      onChange={(e) => updateNewRuleForm("allowedValues", e.target.value)}
                    />
                  </S.ModalField>
                </S.ModalRow>
              )}

              {newRuleForm.validationType === "Pattern (Regex)" && (
                <S.ModalRow $cols={2}>
                  <S.ModalField>
                    <S.ModalLabel>Target Column</S.ModalLabel>
                    <S.ModalInput
                      type="text"
                      placeholder="first_column"
                      value={newRuleForm.targetColumn}
                      onChange={(e) => updateNewRuleForm("targetColumn", e.target.value)}
                    />
                  </S.ModalField>
                  <S.ModalField>
                    <S.ModalLabel>Regex Pattern</S.ModalLabel>
                    <S.ModalInput
                      type="text"
                      placeholder="^[A-Za-z0-9_.-]+$"
                      value={newRuleForm.regexPattern}
                      onChange={(e) => updateNewRuleForm("regexPattern", e.target.value)}
                    />
                  </S.ModalField>
                </S.ModalRow>
              )}

              {newRuleForm.validationType === "Column Range" && (
                <S.ModalRow $cols={3}>
                  <S.ModalField>
                    <S.ModalLabel>Target Column</S.ModalLabel>
                    <S.ModalInput
                      type="text"
                      placeholder="e.g., age"
                      value={newRuleForm.targetColumn}
                      onChange={(e) => updateNewRuleForm("targetColumn", e.target.value)}
                    />
                  </S.ModalField>
                  <S.ModalField>
                    <S.ModalLabel>Min</S.ModalLabel>
                    <S.ModalInput type="number" value={newRuleForm.min} onChange={(e) => updateNewRuleForm("min", e.target.value)} />
                  </S.ModalField>
                  <S.ModalField>
                    <S.ModalLabel>Max</S.ModalLabel>
                    <S.ModalInput type="number" value={newRuleForm.max} onChange={(e) => updateNewRuleForm("max", e.target.value)} />
                  </S.ModalField>
                </S.ModalRow>
              )}

              {newRuleForm.validationType === "Categorical" && (
                <S.ModalRow $cols={2}>
                  <S.ModalField>
                    <S.ModalLabel>Target Column</S.ModalLabel>
                    <S.ModalInput
                      type="text"
                      placeholder="e.g., sex"
                      value={newRuleForm.targetColumn}
                      onChange={(e) => updateNewRuleForm("targetColumn", e.target.value)}
                    />
                  </S.ModalField>
                  <S.ModalField>
                    <S.ModalLabel>Max Categories</S.ModalLabel>
                    <S.ModalInput
                      type="number"
                      value={newRuleForm.maxCategories}
                      onChange={(e) => updateNewRuleForm("maxCategories", e.target.value)}
                    />
                  </S.ModalField>
                </S.ModalRow>
              )}
            </S.ModalForm>

            <S.ModalActions>
              <S.ModalCancelButton onClick={closeNewRuleModal} disabled={isSubmitting}>
                Cancel
              </S.ModalCancelButton>
              <S.ModalCreateButton onClick={handleCreateNewRule} disabled={isSubmitting}>
                {isSubmitting ? "Creating..." : "Create"}
              </S.ModalCreateButton>
            </S.ModalActions>
          </S.ModalContainer>
        </S.ModalOverlay>
      )}
    </S.Section>
  );
};
