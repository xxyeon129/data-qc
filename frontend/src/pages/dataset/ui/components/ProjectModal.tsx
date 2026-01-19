import { useState } from "react";
import * as S from "./projectModal.styles";
import { apiClient } from "@/shared/api";

interface ProjectModalProps {
  onClose: () => void;
  onProjectCreated?: () => void;
}

export const ProjectModal = ({ onClose, onProjectCreated }: ProjectModalProps) => {
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [dataTypes, setDataTypes] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDataTypeChange = (type: string) => {
    setDataTypes((prev) => (prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]));
  };

  const handleCreate = async () => {
    if (!projectName.trim()) {
      setError("프로젝트 이름을 입력해주세요.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await apiClient.createProject({
        name: projectName,
        description: projectDescription,
        dataType: dataTypes,
      });
      alert("프로젝트가 생성되었습니다!");
      onProjectCreated?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "프로젝트 생성에 실패했습니다.");
      console.error("Failed to create project:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <S.Modal onClick={(e) => e.target === e.currentTarget && onClose()}>
      <S.ModalContent>
        <S.ModalHeader>
          <S.ModalTitle>새 프로젝트 생성</S.ModalTitle>
        </S.ModalHeader>

        <S.ModalBody>
          <S.FormGroup>
            <S.FormLabel>프로젝트 이름</S.FormLabel>
            <S.FormInput type="text" placeholder="예: 당뇨병 오믹스 연구" value={projectName} onChange={(e) => setProjectName(e.target.value)} />
          </S.FormGroup>

          <S.FormGroup>
            <S.FormLabel>프로젝트 설명</S.FormLabel>
            <S.FormTextarea
              rows={3}
              placeholder="프로젝트에 대한 간단한 설명을 입력하세요"
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
            />
          </S.FormGroup>

          <S.FormGroup>
            <S.FormLabel>데이터 타입</S.FormLabel>
            <S.CheckboxGrid>
              {["유전체(Genomics)", "전사체(Transcriptomics)", "단백질체(Proteomics)", "대사체(Metabolomics)", "임상정보(Phenotype)"].map((type) => (
                <S.CheckboxLabel key={type}>
                  <input type="checkbox" checked={dataTypes.includes(type)} onChange={() => handleDataTypeChange(type)} />
                  {type}
                </S.CheckboxLabel>
              ))}
            </S.CheckboxGrid>
          </S.FormGroup>
        </S.ModalBody>

        {error && (
          <S.ModalBody>
            <div style={{ color: "red", marginBottom: "1rem" }}>{error}</div>
          </S.ModalBody>
        )}
        <S.ModalFooter>
          <S.Button $variant="secondary" onClick={onClose} disabled={loading}>
            취소
          </S.Button>
          <S.Button onClick={handleCreate} disabled={loading}>
            {loading ? "생성 중..." : "프로젝트 생성"}
          </S.Button>
        </S.ModalFooter>
      </S.ModalContent>
    </S.Modal>
  );
};
