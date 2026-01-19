import styled from "styled-components";

export const ProjectCard = styled.div<{ $selected: boolean }>`
  background: white;
  border-radius: 12px;
  padding: 20px;
  border: 2px solid ${({ $selected }) => ($selected ? "#667eea" : "#e5e7eb")};
  cursor: pointer;
  transition: all 0.2s;
  position: relative;

  ${({ $selected }) =>
    $selected &&
    `
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.03), rgba(118, 75, 162, 0.03));
  `}

  &:hover {
    border-color: #667eea;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  }
`;

export const ProjectBadge = styled.div`
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 8px;
  background: #f0f9ff;
  color: #0284c7;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
`;

export const ProjectNameContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
`;

export const ProjectName = styled.h3`
  font-size: 18px;
  margin: 0;
  flex: 1;
`;

export const EditButton = styled.button`
  position: absolute;
  bottom: 12px;
  right: 48px;
  background: transparent;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
  opacity: 0.6;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    opacity: 1;
    background: #f1f5f9;
    transform: scale(1.1);
  }

  &:active {
    transform: scale(0.95);
  }
`;

export const NameEditContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
`;

export const NameInput = styled.input`
  padding: 8px 12px;
  border: 2px solid #667eea;
  border-radius: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  transition: all 0.2s;
  background: white;
  width: 100%;

  &:focus {
    outline: none;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

export const NameEditButtons = styled.div`
  display: flex;
  gap: 8px;
`;

export const NameEditButton = styled.button`
  background: #f1f5f9;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  color: #475569;

  &:hover:not(:disabled) {
    background: #e2e8f0;
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

export const NameError = styled.div`
  color: #ef4444;
  font-size: 12px;
  margin-top: 4px;
  padding: 4px 8px;
  background: #fef2f2;
  border-radius: 4px;
`;

export const ProjectDescription = styled.p`
  color: #64748b;
  font-size: 14px;
  margin-bottom: 16px;
`;

export const TagsContainer = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
`;

export const Tag = styled.span<{ $bg: string; $color: string }>`
  padding: 4px 8px;
  background: ${({ $bg }) => $bg};
  color: ${({ $color }) => $color};
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
`;

export const ProjectInfo = styled.div`
  display: flex;
  justify-content: space-between;
  color: #64748b;
  font-size: 13px;
`;

export const DeleteButton = styled.button`
  position: absolute;
  bottom: 12px;
  right: 12px;
  background: transparent;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
  opacity: 0.6;

  &:hover {
    opacity: 1;
    background: #fee2e2;
    transform: scale(1.1);
  }

  &:active {
    transform: scale(0.95);
  }
`;



