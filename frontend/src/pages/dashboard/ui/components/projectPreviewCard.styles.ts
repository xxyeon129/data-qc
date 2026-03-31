import styled from "styled-components";

const OMICS_COLORS: Record<string, string> = {
  DNA: "#3b82f6",
  RNA: "#f59e0b",
  Methyl: "#10b981",
  Protein: "#8b5cf6",
};

const STATUS_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  완료: { bg: "#d1fae5", text: "#065f46", dot: "#10b981" },
  진행중: { bg: "#dbeafe", text: "#1e40af", dot: "#3b82f6" },
  대기: { bg: "#fef3c7", text: "#92400e", dot: "#f59e0b" },
  활성: { bg: "#dbeafe", text: "#1e40af", dot: "#3b82f6" },
  작성중: { bg: "#f1f5f9", text: "#475569", dot: "#94a3b8" },
};

export { OMICS_COLORS, STATUS_COLORS };

export const PreviewGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
`;

export const Card = styled.div`
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e7eb;
  transition: box-shadow 0.2s, transform 0.2s;
  cursor: default;

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    transform: translateY(-2px);
  }
`;

export const CardTopRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 6px;
`;

export const ProjectName = styled.h3`
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  margin: 0;
  line-height: 1.4;
  flex: 1;
  padding-right: 12px;
  word-break: break-word;
`;

export const StatusBadge = styled.span<{ $status: string }>`
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;

  ${({ $status }) => {
    const s = STATUS_COLORS[$status] ?? STATUS_COLORS["작성중"];
    return `background: ${s.bg}; color: ${s.text};`;
  }}

  &::before {
    content: "";
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    ${({ $status }) => {
      const s = STATUS_COLORS[$status] ?? STATUS_COLORS["작성중"];
      return `background: ${s.dot};`;
    }}
  }
`;

export const Description = styled.p`
  font-size: 13px;
  color: #6b7280;
  margin: 0 0 12px 0;
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
`;

export const OmicsRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
`;

export const OmicsChip = styled.span<{ $type: string }>`
  padding: 2px 9px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;

  ${({ $type }) => {
    const color = OMICS_COLORS[$type] ?? "#6b7280";
    return `
      background: ${color}18;
      color: ${color};
      border: 1px solid ${color}40;
    `;
  }}
`;

export const Divider = styled.hr`
  border: none;
  border-top: 1px solid #f3f4f6;
  margin: 0 0 12px 0;
`;

export const StatsRow = styled.div`
  display: flex;
  gap: 0;
`;

export const StatItem = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;

  & + & {
    padding-left: 12px;
    border-left: 1px solid #f3f4f6;
    margin-left: 12px;
  }
`;

export const StatLabel = styled.span`
  font-size: 11px;
  color: #9ca3af;
  font-weight: 500;
`;

export const StatValue = styled.span`
  font-size: 14px;
  font-weight: 700;
  color: #1f2937;
`;

export const ValidationSection = styled.div`
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
`;

export const ValidationPlaceholder = styled.div`
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 9px 12px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.4;
`;

export const ValidationTitle = styled.div`
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
`;

export const OmicsScoreRow = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
`;

export const OmicsScoreItem = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`;

export const OmicsScoreLabel = styled.span<{ $type: string }>`
  min-width: 52px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  ${({ $type }) => {
    const color = OMICS_COLORS[$type] ?? "#6b7280";
    return `color: ${color};`;
  }}
`;

export const OmicsScoreBar = styled.div`
  flex: 1;
  height: 14px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
`;

export const OmicsScoreFill = styled.div<{ $pct: number; $type: string }>`
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  width: ${({ $pct }) => `${Math.min($pct, 100)}%`};
  ${({ $type }) => {
    const color = OMICS_COLORS[$type] ?? "#6b7280";
    return `background: ${color};`;
  }}
`;

export const OmicsScoreText = styled.span`
  min-width: 42px;
  text-align: right;
  font-size: 11px;
  font-weight: 700;
  color: #374151;
`;
