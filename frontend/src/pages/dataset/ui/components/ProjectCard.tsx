import { useState, useEffect } from "react";
import * as S from "./projectCard.styles";
import { EditProjectNameModal } from "./EditProjectNameModal";
import { apiClient } from "@/shared/api";

interface ProjectCardProps {
  project: {
    id: number;
    name: string;
    description: string;
    dataType: string[];
    lastUpdate: string;
    qualityScore: number;
    validationStatus: string;
    sampleCount: number;
    status: string;
    sample_accuracy: number;

    DNA_qualityScore: number;
    RNA_qualityScore: number;
    Protein_qualityScore: number;
  };
  selected: boolean;
  onClick: () => void;
  onDelete?: (projectId: number) => void;
  onNameUpdated?: () => void;
}

const tagColors: Record<string, { bg: string; color: string }> = {
  전사체: { bg: "#eff6ff", color: "#2563eb" },
  대사체: { bg: "#f0fdf4", color: "#16a34a" },
  메틸화: { bg: "#fce7f3", color: "#be185d" },
  "전체 오믹스": { bg: "#f3e8ff", color: "#7c3aed" },
};

export const ProjectCard = ({ project, selected, onClick, onDelete, onNameUpdated }: ProjectCardProps) => {
  const { id, name, description, dataType, lastUpdate, status } = project;
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState(name);
  const [updatingName, setUpdatingName] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);

  useEffect(() => {
    setEditedName(name);
  }, [name]);

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation(); // 카드 클릭 이벤트 전파 방지

    if (window.confirm(`"${name}" 프로젝트를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) {
      onDelete?.(id);
    }
  };

  const handleEditClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // 카드 클릭 이벤트 전파 방지
    setIsEditingName(true);
    setEditedName(name);
    setNameError(null);
  };

  const handleNameUpdate = async () => {
    if (!editedName.trim()) {
      setNameError("프로젝트 이름을 입력해주세요.");
      return;
    }

    if (editedName.trim() === name) {
      setIsEditingName(false);
      return;
    }

    try {
      setUpdatingName(true);
      setNameError(null);
      await apiClient.updateProjectName(id, editedName.trim());
      setIsEditingName(false);
      onNameUpdated?.();
    } catch (err) {
      setNameError(err instanceof Error ? err.message : "프로젝트 이름 변경에 실패했습니다.");
      console.error("Failed to update project name:", err);
    } finally {
      setUpdatingName(false);
    }
  };

  const handleNameEditCancel = () => {
    setEditedName(name);
    setIsEditingName(false);
    setNameError(null);
  };

  const handleNameKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !updatingName) {
      handleNameUpdate();
    } else if (e.key === "Escape") {
      handleNameEditCancel();
    }
  };

  const handleDoubleClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // 카드 클릭 이벤트 전파 방지
    setIsEditModalOpen(true);
  };

  const handleCardClick = () => {
    // 편집 모드일 때는 파일 업로드 모달을 열지 않음
    if (!isEditingName) {
      onClick();
    }
  };

  const handleInputClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // 카드 클릭 이벤트 전파 방지
  };

  const handleNameButtonClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // 카드 클릭 이벤트 전파 방지
  };

  return (
    <>
      <S.ProjectCard $selected={selected} onClick={handleCardClick} onDoubleClick={handleDoubleClick}>
        <S.ProjectBadge>{status}</S.ProjectBadge>

        {isEditingName ? (
          <S.NameEditContainer onClick={handleInputClick}>
            <S.NameInput
              type="text"
              value={editedName}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditedName(e.target.value)}
              onKeyDown={handleNameKeyPress}
              onClick={handleInputClick}
              autoFocus
              disabled={updatingName}
            />
            <S.NameEditButtons>
              <S.NameEditButton
                onClick={(e: React.MouseEvent) => {
                  handleNameButtonClick(e);
                  handleNameUpdate();
                }}
                disabled={updatingName}
                title="저장"
              >
                ✓
              </S.NameEditButton>
              <S.NameEditButton
                onClick={(e: React.MouseEvent) => {
                  handleNameButtonClick(e);
                  handleNameEditCancel();
                }}
                disabled={updatingName}
                title="취소"
              >
                ✕
              </S.NameEditButton>
            </S.NameEditButtons>
            {nameError && <S.NameError>{nameError}</S.NameError>}
          </S.NameEditContainer>
        ) : (
          <S.ProjectNameContainer>
            <S.ProjectName>{name}</S.ProjectName>
          </S.ProjectNameContainer>
        )}

        <S.ProjectDescription>{description}</S.ProjectDescription>

        <S.TagsContainer>
          {dataType.map((dataTag) => {
            const colors = tagColors[dataTag] || { bg: "#f1f5f9", color: "#475569" };
            return (
              <S.Tag key={dataTag} $bg={colors.bg} $color={colors.color}>
                {dataTag}
              </S.Tag>
            );
          })}
        </S.TagsContainer>

        <S.ProjectInfo>
          {/* <span>샘플: {sampleCount}</span> */}
          <span>업데이트: {lastUpdate}</span>
        </S.ProjectInfo>

        <S.EditButton onClick={handleEditClick} title="이름 수정">
          ✏️
        </S.EditButton>
        {onDelete && (
          <S.DeleteButton onClick={handleDelete} title="프로젝트 삭제">
            🗑️
          </S.DeleteButton>
        )}
      </S.ProjectCard>

      {isEditModalOpen && (
        <EditProjectNameModal
          projectId={id}
          currentName={name}
          onClose={() => setIsEditModalOpen(false)}
          onNameUpdated={() => {
            onNameUpdated?.();
            setIsEditModalOpen(false);
          }}
        />
      )}
    </>
  );
};
