/**
 * @description 메인 대시보드 페이지
 */

import * as S from "./dashboardPage.styles";
import { StatCard } from "./components/StatCard";
import { QualityTrend } from "./components/QualityTrend";
import { ProjectPreviewCard } from "./components/ProjectPreviewCard";
import { PreviewGrid } from "./components/projectPreviewCard.styles";
import { apiClient } from "@/shared/api";
import type { Project } from "@/entities";
import { useEffect, useState } from "react";

interface DashboardStats {
  activeProjects: number;
  avgQuality: string;
  processedDatasets: number;
  avgMissingRate: string;
}

export const DashboardPage = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      const [projectsData, statsData] = await Promise.all([
        apiClient.getProjects() as Promise<Project[]>,
        apiClient.getDashboardStats() as Promise<DashboardStats>,
      ]);
      setProjects(projectsData);
      setStats(statsData);
    };
    fetchData();
  }, []);

  return (
    <S.Section>
      <S.DashboardGrid>
        <StatCard value={stats?.activeProjects.toString() || "0"} label="활성 프로젝트" color="blue" />
        <StatCard value={stats?.avgQuality || "0%"} label="평균 데이터 품질" color="green" />
        <StatCard value={stats?.processedDatasets.toString() || "0"} label="처리된 데이터셋" color="yellow" />
        <StatCard value={stats?.avgMissingRate || "0%"} label="평균 결측률" color="purple" />
      </S.DashboardGrid>

      {/* 프로젝트 미리보기 섹션 */}
      <S.Card>
        <S.CardHeader>
          <div>
            <S.SectionTitle>
              프로젝트 관리
              <S.SectionSubTitle>{projects.length}개 프로젝트</S.SectionSubTitle>
            </S.SectionTitle>
          </div>
        </S.CardHeader>
        {projects.length === 0 ? (
          <S.EmptyState>등록된 프로젝트가 없습니다.</S.EmptyState>
        ) : (
          <PreviewGrid>
            {projects.map((project) => (
              <ProjectPreviewCard key={project.id} project={project} />
            ))}
          </PreviewGrid>
        )}
      </S.Card>

      <S.Card>
        <S.CardHeader>
          <S.SectionTitle>품질 트렌드</S.SectionTitle>
          <S.Select>
            <option>최근 7일</option>
            <option>최근 30일</option>
            <option>최근 90일</option>
          </S.Select>
        </S.CardHeader>
        <QualityTrend />
      </S.Card>
    </S.Section>
  );
};
