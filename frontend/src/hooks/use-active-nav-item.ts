import type { NavGroup } from "@/lib/header-nav-config";

export interface ActiveNavState {
  activeGroupId: string | null;
  activeSubLinkHref: string | null;
}

/**
 * Determines which navigation group and sub-link are active based on the current pathname.
 *
 * Logic:
 * 1. Iterates through navGroups in order
 * 2. For each group, checks if pathname starts with any of the group's `activeRoutes` prefixes
 * 3. The first matching group becomes `activeGroupId` (first match wins)
 * 4. For `activeSubLinkHref`, finds the first sub-link whose `href` exactly matches the pathname
 * 5. Returns at most one active group
 * 6. If no group matches, returns `{ activeGroupId: null, activeSubLinkHref: null }`
 */
export function useActiveNavItem(
  navGroups: NavGroup[],
  pathname: string,
): ActiveNavState {
  let activeGroupId: string | null = null;
  let activeSubLinkHref: string | null = null;

  for (const group of navGroups) {
    const isGroupActive = group.activeRoutes.some(
      (route) => pathname === route || pathname.startsWith(route + "/"),
    );

    if (isGroupActive) {
      activeGroupId = group.id;

      // Find exact sub-link match within this group
      const matchingLink = group.links.find((link) => link.href === pathname);
      if (matchingLink) {
        activeSubLinkHref = matchingLink.href;
      }

      break; // First match wins
    }
  }

  // If no group matched via activeRoutes, still check for exact sub-link match
  // across all groups (a sub-link href might not be covered by activeRoutes)
  if (activeGroupId === null) {
    for (const group of navGroups) {
      const matchingLink = group.links.find((link) => link.href === pathname);
      if (matchingLink) {
        activeGroupId = group.id;
        activeSubLinkHref = matchingLink.href;
        break;
      }
    }
  }

  return { activeGroupId, activeSubLinkHref };
}
