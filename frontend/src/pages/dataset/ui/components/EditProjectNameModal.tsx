import { useState, useEffect } from "react";
import * as S from "./editProjectNameModal.styles";
import { apiClient } from "@/shared/api";

interface EditProjectNameModalProps {
  projectId: number;
  currentName: string;
  onClose: () => void;
  onNameUpdated?: () => void;
}

export const EditProjectNameModal = ({ projectId, currentName, onClose, onNameUpdated }: EditProjectNameModalProps) => {
  const [projectName, setProjectName] = useState(currentName);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setProjectName(currentName);
  }, [currentName]);

  const handleUpdate = async () => {
    if (!projectName.trim()) {
      setError("프로젝트 이름을 입력해주세요.");
      return;
    }

    if (projectName.trim() === currentName) {
      onClose();
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await apiClient.updateProjectName(projectId, projectName.trim());
      onNameUpdated?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "프로젝트 이름 변경에 실패했습니다.");
      console.error("Failed to update project name:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !loading) {
      handleUpdate();
    }
  };

  return (
    <S.Modal onClick={(e) => e.target === e.currentTarget && onClose()}>
      <S.ModalContent>
        <S.ModalHeader>
          <S.ModalTitle>프로젝트 이름 변경</S.ModalTitle>
        </S.ModalHeader>

        <S.ModalBody>
          <S.FormGroup>
            <S.FormLabel>프로젝트 이름</S.FormLabel>
            <S.FormInput
              type="text"
              placeholder="프로젝트 이름을 입력하세요"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              onKeyPress={handleKeyPress}
              autoFocus
            />
          </S.FormGroup>

          {error && <S.ErrorMessage>{error}</S.ErrorMessage>}
        </S.ModalBody>

        <S.ModalFooter>
          <S.Button $variant="secondary" onClick={onClose} disabled={loading}>
            취소
          </S.Button>
          <S.Button onClick={handleUpdate} disabled={loading}>
            {loading ? "변경 중..." : "변경하기"}
          </S.Button>
        </S.ModalFooter>
      </S.ModalContent>
    </S.Modal>
  );
};
