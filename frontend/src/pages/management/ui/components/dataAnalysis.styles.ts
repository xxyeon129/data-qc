import styled from "styled-components";

export const SettingCard = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
`;

export const SettingHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
`;

export const SettingIcon = styled.div`
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
`;

export const SettingTitle = styled.div`
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
`;

export const FormGroup = styled.div`
  margin-bottom: 20px;
`;

export const FormLabel = styled.label`
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
`;

export const FormSelect = styled.select`
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s;
  background: white;
  cursor: pointer;

  &:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }
`;

export const StatusContainer = styled.div`
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
  margin-top: 16px;
  margin-bottom: 16px;
`;

export const StatusTitle = styled.div`
  font-weight: 600;
  margin-bottom: 12px;
  color: #1e293b;
`;

export const OmicsItem = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding: 8px;
  background: white;
  border-radius: 6px;
`;

export const OmicsLeft = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`;

export const OmicsBadge = styled.span<{ $bg: string; $color: string }>`
  width: 40px;
  height: 40px;
  background: ${({ $bg }) => $bg};
  color: ${({ $color }) => $color};
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
`;

export const OmicsLabel = styled.div`
  font-size: 13px;
  color: #64748b;
`;

export const OmicsValue = styled.div<{ $color: string }>`
  font-weight: 600;
  color: ${({ $color }) => $color};
`;

export const OmicsRight = styled.div`
  text-align: right;
`;

export const OmicsCompleteness = styled.div<{ $color: string }>`
  font-weight: 700;
  color: ${({ $color }) => $color};
`;

export const Summary = styled.div`
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
`;

export const SummaryItem = styled.div`
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
  color: #64748b;

  &:last-child {
    margin-bottom: 0;
  }
`;

export const SummaryValue = styled.span<{ $color: string }>`
  font-weight: ${({ $color }) => ($color === "#667eea" ? "600" : "700")};
  color: ${({ $color }) => $color};
  font-size: ${({ $color }) => ($color === "#ef4444" ? "16px" : "13px")};
`;



