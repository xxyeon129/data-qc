import styled from "styled-components";

export const Section = styled.section`
  display: block;
  padding: 24px;
  animation: fadeIn 0.3s ease-in-out;

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
`;

export const Card = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
`;

export const CardHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
`;

export const CardTitle = styled.h2`
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
`;

export const HeaderActions = styled.div`
  display: flex;
  gap: 12px;
  align-items: center;
`;

export const Select = styled.select`
  width: 200px;
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

export const Button = styled.button`
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;

  &:hover:not(:disabled) {
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

export const AlertBox = styled.div<{ $variant: "error" | "info" }>`
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px;
  font-weight: 500;

  ${({ $variant }) =>
    $variant === "error"
      ? `
    background: #fef2f2;
    color: #dc2626;
    border: 1px solid #fca5a5;
  `
      : `
    background: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
  `}
`;

export const ResultBadge = styled.span<{ $passed: boolean }>`
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;

  ${({ $passed }) =>
    $passed
      ? `
    background: #d1fae5;
    color: #047857;
  `
      : `
    background: #fef3c7;
    color: #b45309;
  `}
`;
