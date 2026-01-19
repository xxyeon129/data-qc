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

export const Alert = styled.div<{ $type: "info" | "success" | "warning" | "danger" }>`
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  align-items: start;
  gap: 12px;
  background: #eff6ff;
  border-left: 4px solid #3b82f6;

  > div {
    flex: 1;

    > div:first-child {
      font-weight: 600;
      margin-bottom: 4px;
      color: #1f2937;
    }

    > div:last-child {
      font-size: 14px;
      color: #4b5563;
    }
  }
`;

export const ImputationContainer = styled.div`
`;



