import styled from "styled-components";

export const Wrapper = styled.div`
  margin-bottom: 24px;
`;

export const SectionTitle = styled.h3`
  font-size: 15px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 14px;
`;

export const Grid = styled.div`
  display: grid;
  grid-template-columns: 180px repeat(3, 1fr);
  gap: 16px;

  @media (max-width: 900px) {
    grid-template-columns: 1fr 1fr;
  }
`;

export const OverallCard = styled.div<{ $active: boolean }>`
  background: ${({ $active }) => ($active ? "#f0f9ff" : "white")};
  border: 2px solid ${({ $active }) => ($active ? "#0ea5e9" : "#e5e7eb")};
  border-radius: 12px;
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: #0ea5e9;
    box-shadow: 0 2px 8px rgba(14, 165, 233, 0.15);
  }
`;

export const OverallIcon = styled.div`
  font-size: 28px;
`;

export const OverallLabel = styled.div`
  font-size: 14px;
  font-weight: 600;
  color: #374151;
`;

export const OverallStats = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
`;

export const MiniStat = styled.div<{ $color: string; $bg: string }>`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
  background: ${({ $bg }) => $bg};
  color: ${({ $color }) => $color};
  border-radius: 6px;
  font-size: 11px;
`;

export const DimCard = styled.div<{
  $active: boolean;
  $activeBg: string;
  $border: string;
}>`
  background: white;
  border: 2px solid ${({ $active, $border }) => ($active ? $border : "#e5e7eb")};
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: ${({ $active }) => ($active ? "0 4px 12px rgba(0,0,0,0.1)" : "none")};

  &:hover {
    border-color: ${({ $border }) => $border};
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }
`;

export const DimHeader = styled.div<{ $bg: string }>`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: ${({ $bg }) => $bg};
  transition: background 0.2s;
`;

export const DimIcon = styled.div`
  font-size: 22px;
`;

export const DimLabel = styled.div<{ $color: string }>`
  font-size: 14px;
  font-weight: 700;
  color: ${({ $color }) => $color};
`;

export const DimSublabel = styled.div<{ $color: string }>`
  font-size: 11px;
  color: ${({ $color }) => $color};
  margin-top: 1px;
`;

export const DimBody = styled.div`
  padding: 16px;
`;

export const ScoreRow = styled.div`
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 8px;
`;

export const Score = styled.div<{ $color: string }>`
  font-size: 30px;
  font-weight: 700;
  color: ${({ $color }) => $color};
`;

export const ScoreLabel = styled.div`
  font-size: 12px;
  color: #9ca3af;
`;

export const BarTrack = styled.div`
  height: 6px;
  background: #f3f4f6;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 12px;
`;

export const BarFill = styled.div<{ $width: number; $color: string }>`
  height: 100%;
  width: ${({ $width }) => $width}%;
  background: ${({ $color }) => $color};
  border-radius: 3px;
  transition: width 0.5s ease;
`;

export const StatusRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
`;

export const StatusBadge = styled.span<{ $color: string; $bg: string }>`
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  color: ${({ $color }) => $color};
  background: ${({ $bg }) => $bg};
`;

export const Description = styled.div`
  font-size: 11px;
  color: #9ca3af;
  border-top: 1px solid #f3f4f6;
  padding-top: 8px;
  margin-top: 4px;
`;
