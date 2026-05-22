import { useState, useEffect } from "react";
import * as S from "./summaryStats.styles";
import { apiClient } from "@/shared/api/client";

interface SummaryStatsProps {
  selectedProjectId: number | null;
}

interface ValidationResult {
  files: Array<{
    filename: string;
    total_values: number;
    nan_count: number;
    nan_percentage: number;
    shape: number[];
    passed: boolean;
  }>;
  total_files: number;
  passed_files: number;
  all_passed: boolean;
}

export const SummaryStats = ({ selectedProjectId }: SummaryStatsProps) => {
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedProjectId) {
      fetchValidationResult();
    }
  }, [selectedProjectId]);

  const fetchValidationResult = async () => {
    if (!selectedProjectId) return;

    try {
      setLoading(true);
      const response: any = await apiClient.executeValidation(selectedProjectId);
      const jobId = response.jobId;

      // Poll for status
      let attempts = 0;
      const maxAttempts = 30;

      while (attempts < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        const status: any = await apiClient.getValidationStatus(jobId);

        if (status.status === "completed") {
          setValidationResult(status.results);
          setLoading(false);
          return;
        } else if (status.status === "failed") {
          setLoading(false);
          return;
        }
        attempts++;
      }
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch validation result:", err);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <S.StatsGrid>
        <div style={{ padding: "2rem", textAlign: "center", color: "#666" }}>검증 결과를 불러오는 중...</div>
      </S.StatsGrid>
    );
  }

  if (!validationResult) {
    return (
      <S.StatsGrid>
        <div style={{ padding: "2rem", textAlign: "center", color: "#666" }}>프로젝트를 선택하여 검증 결과를 확인하세요.</div>
      </S.StatsGrid>
    );
  }

  console.log(validationResult);

  // Calculate statistics from validation result
  const totalSamples = validationResult.files.reduce((acc, file) => {
    return Math.max(acc, file.shape[1] || 0);
  }, 0);

  const totalNanCount = validationResult.files.reduce((acc, file) => acc + file.nan_count, 0);
  const totalValues = validationResult.files.reduce((acc, file) => acc + file.total_values, 0);
  const overallNanPercentage = totalValues > 0 ? ((totalNanCount / totalValues) * 100).toFixed(2) : "0.00";

  const qualityScore = validationResult.all_passed ? 100 - parseFloat(overallNanPercentage) : 0;
  const issueCount = validationResult.files.filter((f) => f.nan_percentage > 10).length;

  const stats = [
    {
      value: `${qualityScore.toFixed(1)}%`,
      label: "전체 품질 점수",
      color: qualityScore >= 90 ? "#10b981" : qualityScore >= 70 ? "#f59e0b" : "#ef4444",
    },
    {
      value: totalSamples.toString(),
      label: "검증된 샘플",
      color: "#3b82f6",
    },
    {
      value: issueCount.toString(),
      label: "보간 권장 파일",
      color: issueCount === 0 ? "#10b981" : "#f59e0b",
    },
    {
      value: `${overallNanPercentage}%`,
      label: "전체 결측률",
      color: parseFloat(overallNanPercentage) < 10 ? "#10b981" : parseFloat(overallNanPercentage) < 30 ? "#f59e0b" : "#ef4444",
    },
  ];

  return (
    <S.StatsGrid>
      {stats.map((stat, index) => (
        <S.StatItem key={index}>
          <S.StatValue $color={stat.color}>{stat.value}</S.StatValue>
          <S.StatLabel>{stat.label}</S.StatLabel>
        </S.StatItem>
      ))}
    </S.StatsGrid>
  );
};
