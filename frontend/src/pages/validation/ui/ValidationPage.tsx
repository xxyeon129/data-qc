/**
 * @description 품질 검증 페이지
 * GENE-QC 품질 지표 (Completeness · Plausibility · Conformance) 기반 검증 결과 표시
 */

import { useState, useEffect, useRef } from "react";
import * as S from "./validationPage.styles";
import { ProgressSteps } from "./components/ProgressSteps";
import { DimensionSummary } from "./components/DimensionSummary";
import { ValidationResults } from "./components/ValidationResults";
import { apiClient } from "@/shared/api/client";

const INITIAL_POLL_INTERVAL_MS = 1000;
const MAX_POLL_INTERVAL_MS = 5000;

interface Project {
  id: number;
  name: string;
}

export interface RuleResult {
  ruleId: string;
  ruleName: string;
  dimension: "Completeness" | "Plausibility" | "Conformance";
  level: "basic" | "advanced";
  severity: "fatal" | "error" | "warning" | "convention" | "characterization";
  fileName: string;
  status: "pass" | "warning" | "fail" | "convention";
  message: string;
  metricValue: number | null;
  threshold: number | null;
}

export interface DimensionStat {
  pass: number;
  warning: number;
  fail: number;
  convention: number;
  total: number;
}

export interface ValidationResult {
  files: Array<{
    filename: string;
    data_type: string;
    inferred_type?: string;
    total_values: number;
    nan_count: number;
    nan_percentage: number;
    completeness: number;
    shape: number[];
    passed: boolean;
    threshold_used?: number;
  }>;
  total_files: number;
  passed_files: number;
  all_passed: boolean;
  rule_results?: RuleResult[];
  dimension_summary?: {
    Completeness: DimensionStat;
    Plausibility: DimensionStat;
    Conformance: DimensionStat;
  };
}

export const ValidationPage = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeDimension, setActiveDimension] = useState<string>("all");

  // 언마운트 시 진행 중인 폴링을 중단해 stale state 업데이트를 방지.
  // StrictMode의 이중 마운트(mount → cleanup → mount)에서도 새 마운트마다
  // 폴링이 가능하도록 마운트 시점에 항상 false로 리셋한다.
  const isCancelledRef = useRef(false);

  useEffect(() => {
    isCancelledRef.current = false;
    fetchProjects();
    return () => {
      isCancelledRef.current = true;
    };
  }, []);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const data = (await apiClient.getProjects()) as Project[];
      setProjects(data);
      if (data.length > 0) {
        setSelectedProjectId(data[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch projects:", err);
      setError("프로젝트 목록을 불러오는데 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  /**
   * 검증 작업 상태를 작업이 끝날 때까지 폴링합니다.
   * - 검증 시간이 아무리 길어도 중도에 포기하지 않습니다 (백엔드는 DB에 결과를 영속 저장).
   * - 폴링 간격은 1초에서 시작해 점진적으로 5초까지 늘려 서버 부하를 줄입니다.
   * - 일시적인 네트워크 오류는 폴링을 종료시키지 않고 다음 주기에 재시도합니다.
   */
  const pollValidationStatus = async (jobId: string) => {
    let pollInterval = INITIAL_POLL_INTERVAL_MS;

    while (!isCancelledRef.current) {
      await new Promise((resolve) => setTimeout(resolve, pollInterval));
      if (isCancelledRef.current) return;

      try {
        const status: any = await apiClient.getValidationStatus(jobId);

        if (status.status === "completed") {
          setValidationResult(status.results);
          setValidating(false);
          return;
        }
        if (status.status === "failed") {
          setError(status.error || "검증 실패");
          setValidating(false);
          return;
        }
      } catch (err) {
        // 일시적 네트워크/서버 오류는 폴링을 종료시키지 않고 다음 주기에 재시도
        console.warn("Validation status polling error, retrying:", err);
      }

      pollInterval = Math.min(pollInterval + 1000, MAX_POLL_INTERVAL_MS);
    }
  };

  const handleExecuteValidation = async () => {
    if (!selectedProjectId) {
      alert("프로젝트를 선택해주세요.");
      return;
    }

    try {
      setValidating(true);
      setError(null);
      setValidationResult(null);
      setActiveDimension("all");

      const response: any = await apiClient.executeValidation(selectedProjectId);
      await pollValidationStatus(response.jobId);
    } catch (err) {
      console.error("Validation error:", err);
      setError(err instanceof Error ? err.message : "검증 중 오류가 발생했습니다.");
      setValidating(false);
    }
  };

  /**
   * 원격 MOCHI 모델 기반 AI 일관성 검증.
   * RNA + Protein + Methyl 세 오믹스가 모두 등록된 프로젝트에서만 의미가 있고,
   * 학습 차원과 입력 차원이 다르면 백엔드에서 명확한 오류로 실패한다.
   */
  const handleExecuteAIValidation = async () => {
    if (!selectedProjectId) {
      alert("프로젝트를 선택해주세요.");
      return;
    }
    if (
      !confirm(
        "원격 MOCHI 모델 기반 AI 일관성 검증을 실행합니다. " +
          "RNA / Protein / Methyl 세 오믹스 파일이 모두 필요하며, " +
          "GPU 환경에 따라 최대 몇 분이 소요될 수 있습니다. 계속할까요?"
      )
    ) {
      return;
    }

    try {
      setValidating(true);
      setError(null);
      setValidationResult(null);
      setActiveDimension("all");

      const response: any = await apiClient.executeAIValidation(selectedProjectId, 0.3);
      await pollValidationStatus(response.jobId);
    } catch (err) {
      console.error("AI validation error:", err);
      setError(err instanceof Error ? err.message : "AI 일관성 검증 중 오류가 발생했습니다.");
      setValidating(false);
    }
  };

  return (
    <S.Section>
      <S.Card>
        <S.CardHeader>
          <S.CardTitle>데이터 품질 검증</S.CardTitle>
          <S.HeaderActions>
            <S.Select value={selectedProjectId || ""} onChange={(e) => setSelectedProjectId(Number(e.target.value))} disabled={loading || validating}>
              <option value="">프로젝트 선택</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </S.Select>
            <S.Button onClick={handleExecuteValidation} disabled={!selectedProjectId || validating}>
              {validating ? "검증 중..." : "검증 실행"}
            </S.Button>
            <S.Button
              onClick={handleExecuteAIValidation}
              disabled={!selectedProjectId || validating}
              title="원격 MOCHI 모델로 RNA·Protein·Methyl 교차 예측 일관성을 측정합니다 (advanced)"
            >
              AI 일관성 검증
            </S.Button>
          </S.HeaderActions>
        </S.CardHeader>

        {error && <S.AlertBox $variant="error">❌ {error}</S.AlertBox>}

        {validating && <S.AlertBox $variant="info">⏳ 검증 작업이 진행 중입니다...</S.AlertBox>}

        <ProgressSteps validationResult={validationResult} validating={validating} />
      </S.Card>

      {/* 차원별 요약 카드 */}
      {validationResult?.dimension_summary && (
        <DimensionSummary
          dimensionSummary={validationResult.dimension_summary}
          activeDimension={activeDimension}
          onDimensionChange={setActiveDimension}
        />
      )}

      {/* 상세 결과 */}
      <S.Card>
        <S.CardHeader>
          <S.CardTitle>검증 상세 결과</S.CardTitle>
          {validationResult && (
            <S.ResultBadge $passed={validationResult.all_passed}>{validationResult.all_passed ? "✓ 검증 완료" : "⚠ 검증 주의"}</S.ResultBadge>
          )}
        </S.CardHeader>
        <ValidationResults validationResult={validationResult} activeDimension={activeDimension} />
      </S.Card>
    </S.Section>
  );
};
