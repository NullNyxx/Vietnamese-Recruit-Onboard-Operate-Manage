import type { LucideIcon } from "lucide-react";

export interface NavLink {
  href: string;
  label: string;
  icon?: LucideIcon;
  description?: string;
}

export interface NavGroup {
  id: string;
  label: string;
  icon?: LucideIcon;
  links: NavLink[];
  /** Route prefixes that mark this group as "active" */
  activeRoutes: string[];
}

export interface HeaderNavConfig {
  logo: {
    label: string;
    href: string;
  };
  groups: NavGroup[];
}
