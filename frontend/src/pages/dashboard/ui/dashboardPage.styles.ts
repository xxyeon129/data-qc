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

export const DashboardGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
  margin-bottom: 24px;
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

export const Button = styled.button<{ $variant?: "primary" | "secondary" }>`
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 8px;

  ${({ $variant }) =>
    $variant === "secondary"
      ? `
    background: #f1f5f9;
    color: #475569;
    
    &:hover {
      background: #e2e8f0;
    }
  `
      : `
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    
    &:hover {
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
      transform: translateY(-1px);
    }
  `}
`;

export const Select = styled.select`
  width: 150px;
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

export const SectionTitle = styled.h2`
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
`;

export const SectionSubTitle = styled.span`
  font-size: 13px;
  color: #94a3b8;
  font-weight: 400;
  margin-left: 8px;
`;

export const EmptyState = styled.div`
  padding: 48px 24px;
  text-align: center;
  color: #9ca3af;
  background: #f9fafb;
  border-radius: 10px;
  border: 1px dashed #e5e7eb;
  font-size: 14px;
`;



