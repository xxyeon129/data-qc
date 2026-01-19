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
  margin-bottom: 24px;
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

export const Tooltip = styled.span`
  position: relative;
  display: inline-block;
  margin-left: 8px;
  color: #64748b;
  cursor: help;
`;

export const TooltipText = styled.span`
  visibility: hidden;
  width: 200px;
  background: #1e293b;
  color: white;
  text-align: center;
  padding: 8px 12px;
  border-radius: 6px;
  position: absolute;
  z-index: 1;
  bottom: 125%;
  left: 50%;
  margin-left: -100px;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.3s;

  ${Tooltip}:hover & {
    visibility: visible;
    opacity: 1;
  }
`;

export const MethodDescription = styled.div<{ $color: string }>`
  padding: 12px;
  background: #f0f9ff;
  border-radius: 8px;
  margin-top: 12px;
  border-left: 3px solid ${({ $color }) => $color};
  margin-bottom: 16px;
`;

export const MethodTitle = styled.div`
  font-weight: 600;
  color: #1e40af;
  margin-bottom: 4px;
`;

export const MethodText = styled.div`
  font-size: 13px;
  color: #374151;
  line-height: 1.5;
`;

export const SliderGroup = styled.div`
  margin-bottom: 24px;
`;

export const SliderHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
`;

export const SliderLabel = styled.span`
  font-size: 14px;
  font-weight: 500;
  color: #374151;
`;

export const SliderValue = styled.span`
  padding: 4px 12px;
  background: #f0f9ff;
  color: #0284c7;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
`;

export const SliderTrack = styled.div`
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  position: relative;
  cursor: pointer;
`;

export const SliderFill = styled.div<{ $width: number }>`
  height: 100%;
  width: ${({ $width }) => $width}%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 4px;
  transition: width 0.2s;
  pointer-events: none;
`;

export const SliderThumb = styled.div<{ $left: number }>`
  position: absolute;
  top: 50%;
  left: ${({ $left }) => $left}%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  background: white;
  border: 3px solid #667eea;
  border-radius: 50%;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  cursor: grab;
  z-index: 2;
  pointer-events: none;
`;

export const HiddenRangeInput = styled.input`
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 100%;
  height: 28px;
  margin: 0;
  opacity: 0;
  cursor: pointer;
  z-index: 3;

  -webkit-appearance: none;
  appearance: none;
  background: transparent;
`;

export const SliderHelp = styled.div`
  font-size: 12px;
  color: #6b7280;
  margin-top: 8px;
`;

export const CheckboxContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

export const CheckboxLabel = styled.label`
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  cursor: pointer;
`;



