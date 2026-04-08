import type { Project } from "@/entities";
import * as S from "./projectPreviewCard.styles";

interface ProjectPreviewCardProps {
  project: Project;
}

const DATA_TYPE_LABELS: Record<string, string> = {
  DNA: "DNA",
  RNA: "RNA",
  Methyl: "Methyl",
  Protein: "Protein",
  기타: "기타",
};

interface OmicsEntry {
  key: string;
  score: number;
}

export const ProjectPreviewCard = ({ project }: ProjectPreviewCardProps) => {
  const omicsTypes: OmicsEntry[] = [];
  if (project.DNA_qualityScore !== undefined && project.DNA_qualityScore !== null)
    omicsTypes.push({ key: "DNA", score: project.DNA_qualityScore });
  if (project.RNA_qualityScore !== undefined && project.RNA_qualityScore !== null)
    omicsTypes.push({ key: "RNA", score: project.RNA_qualityScore });
  if (project.Methyl_qualityScore !== undefined && project.Methyl_qualityScore !== null)
    omicsTypes.push({ key: "Methyl", score: project.Methyl_qualityScore });
  if (project.Protein_qualityScore !== undefined && project.Protein_qualityScore !== null)
    omicsTypes.push({ key: "Protein", score: project.Protein_qualityScore });

  const displayTypes = omicsTypes.length > 0
    ? omicsTypes.map((o) => o.key)
    : project.dataType ?? [];

  const hasScores = omicsTypes.length > 0;

  const sampleCount = project.sampleCount
    ? project.sampleCount.toLocaleString("ko-KR")
    : "-";

  const createdAt = project.createdAt ?? "-";
  const totalSize = project.totalSize ?? "-";

  return (
    <S.Card>
      {/* 상단: 프로젝트명 + 상태 배지 */}
      <S.CardTopRow>
        <S.ProjectName>{project.name}</S.ProjectName>
        <S.StatusBadge $status={project.status}>{project.status}</S.StatusBadge>
      </S.CardTopRow>

      {/* 설명 */}
      {project.description && (
        <S.Description>{project.description}</S.Description>
      )}

      {/* 오믹스 타입 칩 */}
      {displayTypes.length > 0 && (
        <S.OmicsRow>
          {displayTypes.map((type) => (
            <S.OmicsChip key={type} $type={type}>
              {DATA_TYPE_LABELS[type] ?? type}
            </S.OmicsChip>
          ))}
        </S.OmicsRow>
      )}

      <S.Divider />

      {/* 기본 통계: 샘플 수 / 총 용량 / 생성 일자 */}
      <S.StatsRow>
        <S.StatItem>
          <S.StatLabel>샘플 수</S.StatLabel>
          <S.StatValue>{sampleCount}</S.StatValue>
        </S.StatItem>
        <S.StatItem>
          <S.StatLabel>총 용량</S.StatLabel>
          <S.StatValue>{totalSize}</S.StatValue>
        </S.StatItem>
        <S.StatItem>
          <S.StatLabel>생성 일자</S.StatLabel>
          <S.StatValue>{createdAt}</S.StatValue>
        </S.StatItem>
      </S.StatsRow>

      {/* 검증 결과 섹션 */}
      <S.ValidationSection>
        {hasScores ? (
          <>
            <S.ValidationTitle>검증 결과 요약</S.ValidationTitle>
            <S.OmicsScoreRow>
              {omicsTypes.map(({ key, score }) => (
                <S.OmicsScoreItem key={key}>
                  <S.OmicsScoreLabel $type={key}>{key}</S.OmicsScoreLabel>
                  <S.OmicsScoreBar>
                    <S.OmicsScoreFill $pct={score} $type={key} />
                  </S.OmicsScoreBar>
                  <S.OmicsScoreText>{score.toFixed(1)}%</S.OmicsScoreText>
                </S.OmicsScoreItem>
              ))}
            </S.OmicsScoreRow>
          </>
        ) : (
          <S.ValidationPlaceholder>
            {"ℹ 검증 수행 시 통계량 확인이 가능합니다"}
          </S.ValidationPlaceholder>
        )}
      </S.ValidationSection>
    </S.Card>
  );
};
