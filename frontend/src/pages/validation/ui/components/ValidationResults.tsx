/**
 * @description 검증 상세 결과 — GENE-QC 규칙별 통과/경고/실패 표시
 */

import { useState } from "react";
import type { ValidationResult, RuleResult } from "../ValidationPage";
import * as S from "./validationResults.styles";

interface ValidationResultsProps {
  validationResult: ValidationResult | null;
  activeDimension: string;
}

const SEVERITY_CONFIG = {
  fatal: { label: "FATAL", color: "#dc2626", bg: "#fef2f2" },
  error: { label: "ERROR", color: "#ea580c", bg: "#fff7ed" },
  warning: { label: "WARNING", color: "#ca8a04", bg: "#fefce8" },
  convention: { label: "CONVENTION", color: "#2563eb", bg: "#eff6ff" },
  characterization: { label: "CHAR.", color: "#6b7280", bg: "#f9fafb" },
} as const;

const STATUS_CONFIG = {
  pass: { icon: "✓", label: "통과", color: "#047857", bg: "#d1fae5" },
  warning: { icon: "⚠", label: "경고", color: "#b45309", bg: "#fef3c7" },
  fail: { icon: "✕", label: "실패", color: "#dc2626", bg: "#fee2e2" },
  convention: { icon: "●", label: "권고", color: "#2563eb", bg: "#eff6ff" },
} as const;

const DIMENSION_COLORS = {
  Completeness: { text: "#1d4ed8", bg: "#dbeafe" },
  Plausibility: { text: "#b45309", bg: "#fef3c7" },
  Conformance: { text: "#047857", bg: "#d1fae5" },
} as const;

export const ValidationResults = ({ validationResult, activeDimension }: ValidationResultsProps) => {
  const [expandedDims, setExpandedDims] = useState<Record<string, boolean>>({
    Completeness: true,
    Plausibility: true,
    Conformance: true,
  });

  if (!validationResult) {
    return (
      <S.EmptyState>
        <S.EmptyIcon>🔍</S.EmptyIcon>
        <S.EmptyText>검증을 실행하여 상세 결과를 확인하세요.</S.EmptyText>
        <S.EmptySubText>
          Completeness · Plausibility · Conformance 지표별 결과가 표시됩니다.
        </S.EmptySubText>
      </S.EmptyState>
    );
  }

  const ruleResults = validationResult.rule_results;

  // rule_results가 없으면 기존 파일 기반 결과 표시
  if (!ruleResults || ruleResults.length === 0) {
    return <LegacyResults validationResult={validationResult} />;
  }

  const filtered = activeDimension === "all"
    ? ruleResults
    : ruleResults.filter(r => r.dimension === activeDimension);

  const dimensions = ["Completeness", "Plausibility", "Conformance"] as const;
  const groupedByDim = dimensions.reduce((acc, dim) => {
    acc[dim] = filtered.filter(r => r.dimension === dim);
    return acc;
  }, {} as Record<string, RuleResult[]>);

  const totalPass = filtered.filter(r => r.status === "pass").length;
  const totalWarn = filtered.filter(r => r.status === "warning").length;
  const totalFail = filtered.filter(r => r.status === "fail").length;
  const totalConv = filtered.filter(r => r.status === "convention").length;

  return (
    <S.ResultsWrapper>
      {/* 요약 집계 */}
      <S.SummaryRow>
        <S.SummaryCard $color="#047857" $bg="#d1fae5">
          <S.SummaryCount>{totalPass}</S.SummaryCount>
          <S.SummaryLabel>통과</S.SummaryLabel>
        </S.SummaryCard>
        <S.SummaryCard $color="#b45309" $bg="#fef3c7">
          <S.SummaryCount>{totalWarn}</S.SummaryCount>
          <S.SummaryLabel>경고</S.SummaryLabel>
        </S.SummaryCard>
        <S.SummaryCard $color="#dc2626" $bg="#fee2e2">
          <S.SummaryCount>{totalFail}</S.SummaryCount>
          <S.SummaryLabel>실패</S.SummaryLabel>
        </S.SummaryCard>
        {totalConv > 0 && (
          <S.SummaryCard $color="#2563eb" $bg="#eff6ff">
            <S.SummaryCount>{totalConv}</S.SummaryCount>
            <S.SummaryLabel>권고</S.SummaryLabel>
          </S.SummaryCard>
        )}
      </S.SummaryRow>

      {/* 차원별 그룹 */}
      {dimensions.map((dim) => {
        const rules = groupedByDim[dim];
        if (rules.length === 0) return null;

        const dimColor = DIMENSION_COLORS[dim];
        const isExpanded = expandedDims[dim] !== false;
        const passCount = rules.filter(r => r.status === "pass").length;

        return (
          <S.DimGroup key={dim}>
            <S.DimGroupHeader
              $bg={dimColor.bg}
              $border={dimColor.bg}
              onClick={() => setExpandedDims(prev => ({ ...prev, [dim]: !isExpanded }))}
            >
              <S.DimGroupToggle>{isExpanded ? "▾" : "▸"}</S.DimGroupToggle>
              <S.DimGroupName $color={dimColor.text}>{dim}</S.DimGroupName>
              <S.DimGroupMeta $color={dimColor.text}>
                {passCount}/{rules.length}개 통과
              </S.DimGroupMeta>
            </S.DimGroupHeader>

            {isExpanded && (
              <S.RuleList>
                {rules.map((rule, idx) => {
                  const statusCfg = STATUS_CONFIG[rule.status] ?? STATUS_CONFIG.pass;
                  const severityCfg = SEVERITY_CONFIG[rule.severity] ?? SEVERITY_CONFIG.warning;

                  return (
                    <S.RuleRow key={`${rule.ruleId}-${idx}`} $bg={statusCfg.bg}>
                      <S.RuleStatus $color={statusCfg.color} $bg={statusCfg.bg}>
                        <S.StatusIcon>{statusCfg.icon}</S.StatusIcon>
                      </S.RuleStatus>

                      <S.RuleMain>
                        <S.RuleNameRow>
                          <S.RuleName>{rule.ruleName}</S.RuleName>
                          <S.RuleId>{rule.ruleId}</S.RuleId>
                          <S.SeverityBadge $color={severityCfg.color} $bg={severityCfg.bg}>
                            {severityCfg.label}
                          </S.SeverityBadge>
                          {rule.level === "advanced" && (
                            <S.LevelBadge>심화</S.LevelBadge>
                          )}
                        </S.RuleNameRow>
                        <S.RuleMessage>{rule.message}</S.RuleMessage>
                        <S.RuleFilename>📄 {rule.fileName}</S.RuleFilename>
                      </S.RuleMain>

                      {rule.metricValue !== null && rule.threshold !== null && (
                        <S.RuleMetric>
                          <S.MetricValue>{rule.metricValue}</S.MetricValue>
                          <S.MetricThreshold>임계: {rule.threshold}</S.MetricThreshold>
                        </S.RuleMetric>
                      )}
                    </S.RuleRow>
                  );
                })}
              </S.RuleList>
            )}
          </S.DimGroup>
        );
      })}
    </S.ResultsWrapper>
  );
};

/** 기존 파일 기반 결과 (rule_results 없을 때 호환용) */
const LegacyResults = ({ validationResult }: { validationResult: ValidationResult }) => {
  const results = validationResult.files.map(file => ({
    item: file.filename,
    result: file.passed ? "통과" : "실패",
    issue: `${file.nan_percentage}% 결측 (${file.nan_count?.toLocaleString()}/${file.total_values?.toLocaleString()})`,
    action: file.nan_percentage > 10 ? "보간(Imputation) 권장" : "-",
    status: file.passed ? "완료" : "주의",
    statusColor: file.passed ? "#10b981" : "#ef4444",
    dataSize: `${file.shape[0]} × ${file.shape[1]}`,
  }));

  return (
    <S.TableWrapper>
      <S.Table>
        <thead>
          <tr>
            <th>파일명</th>
            <th>데이터 크기</th>
            <th>결측 정보</th>
            <th>권장 조치</th>
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
                  {results.map((result) => (
                    <tr key={result.item}>
              <td style={{ fontWeight: "500" }}>{result.item}</td>
              <td>{result.dataSize}</td>
              <td>{result.issue}</td>
              <td>{result.action}</td>
              <td>
                <S.Status $color={result.statusColor}>
                  {result.status === "완료" ? "✓ 통과" : "⚠ 주의"}
                </S.Status>
              </td>
            </tr>
          ))}
        </tbody>
      </S.Table>
    </S.TableWrapper>
  );
};
