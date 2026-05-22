import styled from "styled-components";

export const Section = styled.section`
  display: block;
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

/* 페이지 상단 타이틀 영역 */
export const PageTitleArea = styled.div`
  margin-bottom: 24px;
`;

export const PageTitle = styled.h1`
  font-size: 24px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 4px 0;
`;

export const PageSubtitle = styled.p`
  font-size: 13px;
  color: #6b7280;
  margin: 0;
`;

/* 카드 */
export const Card = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
`;

export const CardHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
`;

export const CardTitleGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

export const CardTitle = styled.h2`
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  margin: 0;
`;

export const CardSubtitle = styled.p`
  font-size: 13px;
  color: #6b7280;
  margin: 0;
`;

export const BadgeGroup = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`;

export const Badge = styled.span<{ $variant: "green" | "blue" }>`
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  ${({ $variant }) => ($variant === "green" ? `background: #d1fae5; color: #065f46;` : `background: #dbeafe; color: #1d4ed8;`)}
`;

/* 탭 */
export const TabRow = styled.div`
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 0;
`;

export const Tab = styled.button<{ $active: boolean }>`
  padding: 8px 16px;
  border: none;
  border-radius: 6px 6px 0 0;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  background: ${({ $active }) => ($active ? "#111827" : "transparent")};
  color: ${({ $active }) => ($active ? "white" : "#6b7280")};
  position: relative;
  bottom: -1px;

  &:hover {
    background: ${({ $active }) => ($active ? "#111827" : "#f3f4f6")};
    color: ${({ $active }) => ($active ? "white" : "#374151")};
  }
`;

/* 탭 콘텐츠 공통 */
export const TabContent = styled.div``;

/* Manage Custom Rules 탭 */
export const ManageTopRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
`;

export const ManageDescription = styled.p`
  font-size: 13px;
  color: #6b7280;
  margin: 0;
`;

export const NewRuleButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: #1d4ed8;
  }
`;

export const EmptyState = styled.div`
  border: 1.5px dashed #d1d5db;
  border-radius: 8px;
  padding: 40px 24px;
  text-align: center;
  color: #9ca3af;
  font-size: 14px;
`;

/* ─────────────────────────────────────────
   Manage Custom Rules — 리스트 UI
───────────────────────────────────────── */

export const CustomRuleList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 10px;
`;

export const CustomRuleItem = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  transition: border-color 0.15s, box-shadow 0.15s;

  &:hover {
    border-color: #c7d2fe;
    box-shadow: 0 1px 3px rgba(99, 102, 241, 0.08);
  }
`;

export const CustomRuleBody = styled.div`
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
`;

export const CustomRuleHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
`;

export const CustomRuleName = styled.span`
  font-size: 14px;
  font-weight: 600;
  color: #111827;
`;

export const CustomRuleDimensionBadge = styled.span<{ $dimension: string }>`
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
  ${({ $dimension }) => {
    switch ($dimension) {
      case "Completeness":
        return "background: #dbeafe; color: #1e40af;";
      case "Plausibility":
        return "background: #ede9fe; color: #5b21b6;";
      case "Conformance":
        return "background: #d1fae5; color: #065f46;";
      default:
        return "background: #f3f4f6; color: #374151;";
    }
  }}
`;

export const CustomRuleSeverityBadge = styled.span<{ $severity: string }>`
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
  ${({ $severity }) => {
    const lower = $severity.toLowerCase();
    if (lower === "error" || lower === "fatal") {
      return "background: #fee2e2; color: #991b1b;";
    }
    if (lower === "warning") {
      return "background: #fef3c7; color: #92400e;";
    }
    return "background: #e0f2fe; color: #075985;";
  }}
`;

export const CustomRuleTypeBadge = styled.span`
  font-size: 10px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f3f4f6;
  color: #4b5563;
  white-space: nowrap;
`;

export const CustomRuleDescription = styled.p`
  font-size: 12px;
  color: #6b7280;
  margin: 0;
  line-height: 1.5;
`;

export const CustomRuleDeleteButton = styled.button`
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: white;
  color: #9ca3af;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background: #fef2f2;
    color: #dc2626;
    border-color: #fecaca;
  }
`;

/* Select Rules 탭 — 기존 스타일 유지 */
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

export const SectionTitle = styled.h3`
  margin: 24px 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
`;

export const SaveButtonContainer = styled.div`
  margin-top: 24px;
  padding: 16px;
  background: linear-gradient(135deg, #f0f9ff, #faf5ff);
  border-radius: 8px;
`;

export const Button = styled.button<{ $fullWidth?: boolean }>`
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  ${({ $fullWidth }) => $fullWidth && "width: 100%;"}

  &:hover {
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }
`;

export const FormGroup = styled.div`
  margin-bottom: 20px;
`;

export const FormLabel = styled.label`
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
`;

export const FormSelect = styled.select`
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  color: #1f2937;
  background-color: white;
  cursor: pointer;
  transition: all 0.2s;

  &:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  &:disabled {
    background-color: #f3f4f6;
    cursor: not-allowed;
  }
`;

/* ─────────────────────────────────────────
   Select Rules 탭 — 새 레이아웃
───────────────────────────────────────── */

export const SelectRulesContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
`;

export const SearchFilterRow = styled.div`
  display: flex;
  gap: 10px;
  align-items: center;
`;

export const SearchInputWrapper = styled.div`
  position: relative;
  flex: 1;

  svg {
    position: absolute;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: #9ca3af;
    pointer-events: none;
  }
`;

export const SearchInput = styled.input`
  width: 100%;
  padding: 8px 12px 8px 32px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
  color: #374151;
  background: white;
  box-sizing: border-box;

  &::placeholder {
    color: #9ca3af;
  }

  &:focus {
    outline: none;
    border-color: #6366f1;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.08);
  }
`;

export const FilterSelect = styled.select`
  padding: 8px 28px 8px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
  color: #374151;
  background: white;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;

  &:focus {
    outline: none;
    border-color: #6366f1;
  }
`;

export const RuleCategorySection = styled.div`
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
`;

export const CategoryHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f9fafb;
  cursor: pointer;
  user-select: none;

  &:hover {
    background: #f3f4f6;
  }
`;

export const CategoryChevron = styled.span<{ $open: boolean }>`
  display: flex;
  align-items: center;
  color: #6b7280;
  transition: transform 0.2s;
  transform: ${({ $open }) => ($open ? "rotate(0deg)" : "rotate(-90deg)")};
`;

export const CategoryName = styled.span`
  font-size: 14px;
  font-weight: 600;
  color: #111827;
`;

export const CategoryCount = styled.span`
  font-size: 11px;
  font-weight: 500;
  color: #6b7280;
  background: #e5e7eb;
  padding: 2px 8px;
  border-radius: 10px;
`;

export const DeselectAllButton = styled.button`
  margin-left: auto;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  color: #374151;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;

  &:hover {
    background: #f9fafb;
    border-color: #9ca3af;
  }
`;

export const RuleList = styled.div`
  display: flex;
  flex-direction: column;
`;

export const RuleItem = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 11px 16px;
  border-bottom: 1px solid #f3f4f6;
  cursor: pointer;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: #fafafa;
  }
`;

export const RuleCheckbox = styled.input`
  width: 15px;
  height: 15px;
  margin-top: 2px;
  cursor: pointer;
  accent-color: #2563eb;
  flex-shrink: 0;
`;

export const RuleInfo = styled.div`
  flex: 1;
  min-width: 0;
`;

export const RuleNameRow = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
`;

export const RuleName = styled.span`
  font-size: 13px;
  font-weight: 600;
  color: #111827;
`;

export const RuleTag = styled.span<{ $tag: string }>`
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  white-space: nowrap;
  ${({ $tag }) => {
    switch ($tag) {
      case "FATAL":
        return "background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5;";
      case "ERROR":
        return "background: #fff7ed; color: #ea580c; border: 1px solid #fdba74;";
      case "WARNING":
        return "background: #fffbeb; color: #d97706; border: 1px solid #fcd34d;";
      case "CHARACTERIZATION":
        return "background: #f9fafb; color: #6b7280; border: 1px solid #d1d5db;";
      case "CONVENTION":
        return "background: #eff6ff; color: #2563eb; border: 1px solid #93c5fd;";
      default:
        return "background: #f3f4f6; color: #374151;";
    }
  }}
`;

export const RuleLevelBadge = styled.span<{ $level: "Basic" | "Advanced" }>`
  font-size: 10px;
  font-weight: 500;
  padding: 1px 7px;
  border-radius: 4px;
  white-space: nowrap;
  ${({ $level }) => ($level === "Basic" ? "background: #f3f4f6; color: #4b5563;" : "background: #fef9c3; color: #854d0e;")}
`;

export const RuleDescription = styled.p`
  font-size: 11px;
  color: #6b7280;
  margin: 3px 0 0 0;
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

export const RuleStatusBadge = styled.span`
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 20px;
  background: #d1fae5;
  color: #065f46;
  margin-top: 1px;
  white-space: nowrap;
`;

/* ─────────────────────────────────────────
   New Custom Rule 모달
───────────────────────────────────────── */

export const ModalOverlay = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(17, 24, 39, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: overlayFade 0.15s ease-out;

  @keyframes overlayFade {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
`;

export const ModalContainer = styled.div`
  width: 100%;
  max-width: 520px;
  background: white;
  border-radius: 14px;
  padding: 24px 24px 20px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.18);
  animation: modalIn 0.18s ease-out;

  @keyframes modalIn {
    from {
      opacity: 0;
      transform: translateY(8px) scale(0.98);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }
`;

export const ModalTitle = styled.h3`
  margin: 0 0 18px 0;
  font-size: 17px;
  font-weight: 700;
  color: #111827;
`;

export const ModalForm = styled.div`
  display: flex;
  flex-direction: column;
  gap: 14px;
`;

export const ModalRow = styled.div<{ $cols?: number }>`
  display: grid;
  grid-template-columns: repeat(${({ $cols }) => $cols ?? 1}, 1fr);
  gap: 12px;
`;

export const ModalField = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
`;

export const ModalLabel = styled.label`
  font-size: 13px;
  font-weight: 600;
  color: #374151;
`;

export const ModalInput = styled.input`
  width: 100%;
  padding: 9px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  color: #111827;
  background: white;
  box-sizing: border-box;
  transition: border-color 0.15s, box-shadow 0.15s;

  &::placeholder {
    color: #9ca3af;
  }

  &:focus {
    outline: none;
    border-color: #6366f1;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
  }
`;

export const ModalSelect = styled.select`
  width: 100%;
  padding: 9px 32px 9px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  color: #111827;
  background: white;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  box-sizing: border-box;
  transition: border-color 0.15s, box-shadow 0.15s;

  &:focus {
    outline: none;
    border-color: #6366f1;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
  }
`;

export const ModalActions = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
`;

export const ModalCancelButton = styled.button`
  padding: 8px 16px;
  background: white;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;

  &:hover {
    background: #f9fafb;
    border-color: #9ca3af;
  }
`;

export const ModalCreateButton = styled.button`
  padding: 8px 20px;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;

  &:hover {
    background: #1d4ed8;
  }
`;
