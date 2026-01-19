import { useState, useEffect, forwardRef, useImperativeHandle } from "react";
import * as S from "./projectManage.styles";
import { ProjectCard } from "./ProjectCard";
import { ProjectModal } from "./ProjectModal";
import { FileUploadModal } from "./FileUploadModal";
import { apiClient } from "@/shared/api";

interface Project {
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
}

export interface ProjectManageRef {
  refreshProjects: () => Promise<void>;
}

interface ProjectManageProps {
  onProjectCreated?: () => void;
}

export const ProjectManage = forwardRef<ProjectManageRef, ProjectManageProps>((props, ref) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isFileUploadModalOpen, setIsFileUploadModalOpen] = useState(false);
  const [selectedProjectForUpload, setSelectedProjectForUpload] = useState<Project | null>(null);
  const [selectedProject, setSelectedProject] = useState<number | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        setLoading(true);
        const data = (await apiClient.getProjects()) as Project[];
        setProjects(data);
        if (data && data.length > 0) {
          setSelectedProject(data[0].id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "프로젝트를 불러오는데 실패했습니다.");
        console.error("Failed to fetch projects:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, []);

  const handleProjectCreated = async () => {
    try {
      const data = (await apiClient.getProjects()) as Project[];
      setProjects(data);

      // 상위 컴포넌트에 프로젝트 생성 알림 (DataInput 갱신용)
      if (props.onProjectCreated) {
        props.onProjectCreated();
      }
    } catch (err) {
      console.error("Failed to refresh projects:", err);
    }
  };

  const handleProjectDelete = async (projectId: number) => {
    try {
      await apiClient.deleteProject(projectId);

      // 프로젝트 목록 갱신
      const data = (await apiClient.getProjects()) as Project[];
      setProjects(data);

      // 삭제된 프로젝트가 선택되어 있었다면 선택 해제
      if (selectedProject === projectId) {
        setSelectedProject(data.length > 0 ? data[0].id : null);
      }

      alert("프로젝트가 성공적으로 삭제되었습니다.");
    } catch (err) {
      console.error("Failed to delete project:", err);
      alert("프로젝트 삭제에 실패했습니다.");
    }
  };

  // 외부에서 프로젝트 목록을 새로고침할 수 있도록 ref 노출
  useImperativeHandle(ref, () => ({
    refreshProjects: handleProjectCreated,
  }));

  if (loading) {
    return (
      <S.Card>
        <S.CardHeader>
          <S.CardTitle>프로젝트 관리</S.CardTitle>
        </S.CardHeader>
        <div>로딩 중...</div>
      </S.Card>
    );
  }

  if (error) {
    return (
      <S.Card>
        <S.CardHeader>
          <S.CardTitle>프로젝트 관리</S.CardTitle>
        </S.CardHeader>
        <div>에러: {error}</div>
      </S.Card>
    );
  }

  return (
    <>
      <S.Card>
        <S.CardHeader>
          <S.CardTitle>프로젝트 관리</S.CardTitle>
          <S.Button onClick={() => setIsModalOpen(true)}>+ 새 프로젝트</S.Button>
        </S.CardHeader>

        <S.ProjectGrid>
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              selected={selectedProject === project.id}
              onClick={() => {
                setSelectedProject(project.id);
                setSelectedProjectForUpload(project);
                setIsFileUploadModalOpen(true);
              }}
              onDelete={handleProjectDelete}
              onNameUpdated={handleProjectCreated}
            />
          ))}
        </S.ProjectGrid>
      </S.Card>

      {isModalOpen && <ProjectModal onClose={() => setIsModalOpen(false)} onProjectCreated={handleProjectCreated} />}
      {isFileUploadModalOpen && selectedProjectForUpload && (
        <FileUploadModal
          projectId={selectedProjectForUpload.id}
          projectName={selectedProjectForUpload.name}
          onClose={() => {
            setIsFileUploadModalOpen(false);
            setSelectedProjectForUpload(null);
          }}
          onFileUploaded={() => {
            handleProjectCreated();
          }}
        />
      )}
    </>
  );
});

ProjectManage.displayName = "ProjectManage";
