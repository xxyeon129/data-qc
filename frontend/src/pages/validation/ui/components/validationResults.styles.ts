import styled from "styled-components";

export const ResultsWrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
`;

export const EmptyState = styled.div`
  padding: 48px 24px;
  text-align: center;
  color: #9ca3af;
`;

export const EmptyIcon = styled.div`
  font-size: 48px;
  margin-bottom: 12px;
`;

export const EmptyText = styled.p`
  font-size: 15px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 6px;
`;

export const EmptySubText = styled.p`
  font-size: 13px;
  color: #9ca3af;
`;

/* 요약 집계 */
export const SummaryRow = styled.div`
  display: flex;
  gap: 12px;
  padding: 4px 0 8px;
`;

export const SummaryCard = styled.div<{ $color: string; $bg: string }>`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16px 24px;
  border-radius: 10px;
  background: ${({ $bg }) => $bg};
  color: ${({ $color }) => $color};
  min-width: 80px;
`;

export const SummaryCount = styled.div`
  font-size: 28px;
  font-weight: 700;
`;

export const SummaryLabel = styled.div`
  font-size: 12px;
  font-weight: 600;
  margin-top: 4px;
`;

/* 차원별 그룹 */
export const DimGroup = styled.div`
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
`;

export const DimGroupHeader = styled.div<{ $bg: string; $border: string }>`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: ${({ $bg }) => $bg};
  cursor: pointer;
  user-select: none;

  &:hover {
    filter: brightness(0.97);
  }
`;

export const DimGroupToggle = styled.span`
  font-size: 14px;
  color: #6b7280;
  width: 16px;
`;

export const DimGroupName = styled.span<{ $color: string }>`
  font-size: 14px;
  font-weight: 700;
  color: ${({ $color }) => $color};
  flex: 1;
`;

export const DimGroupMeta = styled.span<{ $color: string }>`
  font-size: 12px;
  font-weight: 600;
  color: ${({ $color }) => $color};
`;

/* 규칙 목록 */
export const RuleList = styled.div`
  display: flex;
  flex-direction: column;
`;

export const RuleRow = styled.div<{ $bg: string }>`
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
  background: white;
  transition: background 0.15s;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: ${({ $bg }) => $bg};
  }
`;

export const RuleStatus = styled.div<{ $color: string; $bg: string }>`
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: ${({ $bg }) => $bg};
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
`;

export const StatusIcon = styled.span`
  font-size: 13px;
  font-weight: 700;
`;

export const RuleMain = styled.div`
  flex: 1;
  min-width: 0;
`;

export const RuleNameRow = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
`;

export const RuleName = styled.span`
  font-size: 13px;
  font-weight: 600;
  color: #111827;
`;

export const RuleId = styled.span`
  font-size: 11px;
  color: #9ca3af;
  font-family: monospace;
`;

export const SeverityBadge = styled.span<{ $color: string; $bg: string }>`
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  color: ${({ $color }) => $color};
  background: ${({ $bg }) => $bg};
`;

export const LevelBadge = styled.span`
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  color: white;
`;

export const RuleMessage = styled.div`
  font-size: 12px;
  color: #4b5563;
  margin-bottom: 3px;
`;

export const RuleFilename = styled.div`
  font-size: 11px;
  color: #9ca3af;
`;

export const RuleMetric = styled.div`
  flex-shrink: 0;
  text-align: right;
  min-width: 70px;
`;

export const MetricValue = styled.div`
  font-size: 15px;
  font-weight: 700;
  color: #374151;
`;

export const MetricThreshold = styled.div`
  font-size: 10px;
  color: #9ca3af;
`;

/* 레거시 테이블 (호환용) */
export const TableWrapper = styled.div`
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
`;

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  background: white;

  th {
    background: #f9fafb;
    padding: 12px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    border-bottom: 1px solid #e5e7eb;
  }

  td {
    padding: 12px;
    font-size: 14px;
    color: #1f2937;
    border-bottom: 1px solid #f3f4f6;
  }

  tr:hover {
    background: #f9fafb;
  }
`;

export const Status = styled.span<{ $color: string }>`
  color: ${({ $color }) => $color};
  font-weight: 600;
`;
