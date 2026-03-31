import * as S from "./progressSteps.styles";
import type { ValidationResult } from "../ValidationPage";

interface ProgressStepsProps {
  validationResult: ValidationResult | null;
  validating?: boolean;
}

const STEP_LABELS = ["데이터 로드", "형식 검사", "품질 검증", "보고서 생성"];

type StepStatus = "completed" | "active" | "pending";

function getStepStatus(stepIndex: number, isDone: boolean, validating: boolean): StepStatus {
  if (isDone) return "completed";
  if (validating && stepIndex <= 1) return "completed";
  if (validating && stepIndex === 2) return "active";
  return "pending";
}

function getStepNumber(stepIndex: number, isDone: boolean, validating: boolean): string {
  const status = getStepStatus(stepIndex, isDone, validating);
  if (status === "completed") return "✓";
  return String(stepIndex + 1);
}

export const ProgressSteps = ({ validationResult, validating = false }: ProgressStepsProps) => {
  const isDone = !!validationResult;

  return (
    <S.ProgressSteps>
      {STEP_LABELS.map((label, index) => {
        const status = getStepStatus(index, isDone, validating);
        const number = getStepNumber(index, isDone, validating);
        return (
          <S.ProgressStep key={label} $status={status}>
            <S.ProgressCircle $status={status}>{number}</S.ProgressCircle>
            <S.ProgressLabel>{label}</S.ProgressLabel>
          </S.ProgressStep>
        );
      })}
    </S.ProgressSteps>
  );
};
