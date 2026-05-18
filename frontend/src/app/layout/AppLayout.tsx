import { Outlet, useLocation, useNavigate } from "react-router-dom";
import type { IconType } from "react-icons";
import {
  FiHome,
  FiShield,
  FiCpu,
  FiMessageSquare,
  FiEye,
  FiSliders,
} from "react-icons/fi";
import { PATH_URL } from "@/shared";
import * as S from "./appLayout.styles";

type NavItem = {
  id: string;
  label: string;
  path: string;
  icon: IconType;
};

const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Dashboard", path: PATH_URL.MAIN, icon: FiHome },
  {
    id: "analysis",
    label: "Analysis",
    path: PATH_URL.DATASET,
    icon: FiMessageSquare,
  },
  { id: "rules", label: "Rule", path: PATH_URL.RULES, icon: FiSliders },
  {
    id: "validation",
    label: "Validation",
    path: PATH_URL.VALIDATION,
    icon: FiShield,
  },
  {
    id: "imputation",
    label: "Imputation",
    path: PATH_URL.MANAGEMENT,
    icon: FiCpu,
  },
  { id: "results", label: "Results", path: PATH_URL.RESULTS, icon: FiEye },
  
];

export const AppLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const isActive = (path: string) => {
    if (path === PATH_URL.MAIN) {
      return location.pathname === PATH_URL.MAIN;
    }
    return location.pathname.startsWith(path);
  };

  return (
    <S.Layout>
      <S.Navbar>
        <S.LogoSection>
          <S.LogoTitle>GENE-QC</S.LogoTitle>
          <S.LogoDivider />
          <S.LogoSubtext>
            <span>Genomic Data</span>
            <span>Quality Control</span>
          </S.LogoSubtext>
        </S.LogoSection>
        <S.NavMenu>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <S.NavItem
                key={item.id}
                $active={active}
                onClick={() => navigate(item.path)}
              >
                <Icon />
                {item.label}
              </S.NavItem>
            );
          })}
        </S.NavMenu>
      </S.Navbar>
      <S.Main>
        <Outlet />
      </S.Main>
    </S.Layout>
  );
};
