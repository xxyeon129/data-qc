/**
 * @description GENE-QC 품질 차원별 요약 카드 (Completeness · Plausibility · Conformance)
 */

import type { DimensionStat } from "../ValidationPage";
import * as S from "./dimensionSummary.styles";

interface DimensionSummaryProps {
  dimensionSummary: {
    Completeness: DimensionStat;
    Plausibility: DimensionStat;
    Conformance: DimensionStat;
  };
  activeDimension: string;
  onDimensionChange: (dim: string) => void;
}

const DIMENSION_CONFIG = {
  Completeness: {
    label: "완전성",
    sublabel: "Completeness",
    description: "결측값·헤더·샘플 ID 검사",
    icon: "🗂️",
    bg: "#dbeafe",
    border: "#3b82f6",
    text: "#1d4ed8",
    activeBg: "#2563eb",
  },
  Plausibility: {
    label: "타당성",
    sublabel: "Plausibility",
    description: "이상치·분포·범위 검사",
    icon: "📊",
    bg: "#fef3c7",
    border: "#f59e0b",
    text: "#b45309",
    activeBg: "#d97706",
  },
  Conformance: {
    label: "적합성",
    sublabel: "Conformance",
    description: "형식·타입·중복 검사",
    icon: "✅",
    bg: "#d1fae5",
    border: "#10b981",
    text: "#047857",
    activeBg: "#059669",
  },
} as const;

const calcScore = (stat: DimensionStat): number => {
  if (stat.total === 0) return 0;
  return Math.round((stat.pass / stat.total) * 100);
};

const getScoreColor = (score: number): string => {
  if (score >= 80) return "#047857";
  if (score >= 60) return "#b45309";
  return "#dc2626";
};

const getBarColor = (score: number): string => {
  if (score >= 80) return "#10b981";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
};

export const DimensionSummary = ({
  dimensionSummary,
  activeDimension,
  onDimensionChange,
}: DimensionSummaryProps) => {
  const dimensions = Object.keys(DIMENSION_CONFIG) as Array<keyof typeof DIMENSION_CONFIG>;

  return (
    <S.Wrapper>
      <S.SectionTitle>품질 지표 차원별 결과</S.SectionTitle>
      <S.Grid>
        {/* 전체 보기 카드 */}
        <S.OverallCard
          $active={activeDimension === "all"}
          onClick={() => onDimensionChange("all")}
        >
          <S.OverallIcon>🔍</S.OverallIcon>
          <S.OverallLabel>전체 규칙</S.OverallLabel>
          <S.OverallStats>
            {dimensions.map((dim) => {
              const stat = dimensionSummary[dim];
              const cfg = DIMENSION_CONFIG[dim];
              return (
                <S.MiniStat key={dim} $color={cfg.text} $bg={cfg.bg}>
                  <span style={{ fontSize: 11 }}>{cfg.sublabel}</span>
                  <span style={{ fontWeight: 700 }}>{stat.pass}/{stat.total}</span>
                </S.MiniStat>
              );
            })}
          </S.OverallStats>
        </S.OverallCard>

        {/* 차원별 카드 */}
        {dimensions.map((dim) => {
          const cfg = DIMENSION_CONFIG[dim];
          const stat = dimensionSummary[dim];
          const score = calcScore(stat);
          const isActive = activeDimension === dim;

          return (
            <S.DimCard
              key={dim}
              $active={isActive}
              $activeBg={cfg.activeBg}
              $border={cfg.border}
              onClick={() => onDimensionChange(isActive ? "all" : dim)}
            >
              <S.DimHeader $bg={isActive ? cfg.activeBg : cfg.bg}>
                <S.DimIcon>{cfg.icon}</S.DimIcon>
                <div>
                  <S.DimLabel $color={isActive ? "#ffffff" : cfg.text}>
                    {cfg.label}
                  </S.DimLabel>
                  <S.DimSublabel $color={isActive ? "#ffffffcc" : cfg.text}>
                    {cfg.sublabel}
                  </S.DimSublabel>
                </div>
              </S.DimHeader>

              <S.DimBody>
                <S.ScoreRow>
                  <S.Score $color={getScoreColor(score)}>
                    {score}%
                  </S.Score>
                  <S.ScoreLabel>통과율</S.ScoreLabel>
                </S.ScoreRow>

                <S.BarTrack>
                  <S.BarFill
                    $width={score}
                    $color={getBarColor(score)}
                  />
                </S.BarTrack>

                <S.StatusRow>
                  <S.StatusBadge $color="#047857" $bg="#d1fae5">
                    통과 {stat.pass}
                  </S.StatusBadge>
                  {stat.warning > 0 && (
                    <S.StatusBadge $color="#b45309" $bg="#fef3c7">
                      경고 {stat.warning}
                    </S.StatusBadge>
                  )}
                  {stat.fail > 0 && (
                    <S.StatusBadge $color="#dc2626" $bg="#fee2e2">
                      실패 {stat.fail}
                    </S.StatusBadge>
                  )}
                  {stat.convention > 0 && (
                    <S.StatusBadge $color="#2563eb" $bg="#eff6ff">
                      권고 {stat.convention}
                    </S.StatusBadge>
                  )}
                </S.StatusRow>

                <S.Description>{cfg.description}</S.Description>
              </S.DimBody>
            </S.DimCard>
          );
        })}
      </S.Grid>
    </S.Wrapper>
  );
};
