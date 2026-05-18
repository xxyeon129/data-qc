import styled from "styled-components";

export const Layout = styled.div`
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 100vh;
`;

export const Navbar = styled.nav`
  background: white;
  border-bottom: 1px solid ${({ theme }) => theme.colors.border.gray};
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 32px;
  gap: 48px;
`;

export const LogoSection = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
`;

export const LogoTitle = styled.div`
  font-size: 20px;
  font-weight: 700;
  color: ${({ theme }) => theme.colors.blue.primary};
  letter-spacing: -0.02em;
`;

export const LogoDivider = styled.div`
  width: 1px;
  height: 32px;
  background: ${({ theme }) => theme.colors.text.lightGray};
`;

export const LogoSubtext = styled.div`
  display: flex;
  flex-direction: column;
  font-size: 11px;
  line-height: 1.35;
  color: ${({ theme }) => theme.colors.text.lightGray};
  font-weight: 400;
`;

export const NavMenu = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
`;

export const NavItem = styled.button<{ $active: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: ${({ $active, theme }) =>
    $active ? theme.colors.blue.primary : "transparent"};
  border: none;
  border-radius: 9999px;
  font-size: 14px;
  font-weight: 500;
  color: ${({ $active, theme }) =>
    $active ? "white" : theme.colors.text.darkGray};
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
  white-space: nowrap;

  svg {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
  }

  &:hover {
    background: ${({ $active, theme }) =>
      $active ? theme.colors.blue.primary : "#f3f4f6"};
    color: ${({ $active, theme }) =>
      $active ? "white" : theme.colors.text.default};
  }
`;

export const Main = styled.main`
  margin-top: 64px;
  min-height: calc(100vh - 64px);
  background: #f0f2f5;
  padding: 24px;
`;
