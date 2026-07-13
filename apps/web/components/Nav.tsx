"use client";

// Sidebar nav — split out of app/layout.tsx (a Server Component, so it
// can still export `metadata`) specifically so the active link can be
// highlighted via usePathname(), part of docs/roadmap.md 3.8's design
// pass (see app/globals.css's module comment for the design system this
// belongs to).

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat" },
  { href: "/projects", label: "Projects" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/prompts", label: "Prompts" },
  { href: "/ops", label: "Ops" },
  { href: "/settings", label: "Settings" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="studio-nav">
      <div className="brand">Oren Studio AI</div>
      <div className="studio-nav-links">
        {NAV_ITEMS.map((item) => {
          // /projects should also highlight for /projects/[id] and its
          // sub-routes (e.g. /projects/[id]/storyboard) — startsWith,
          // not exact match, except for the root-ish routes.
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link key={item.href} href={item.href} data-active={active}>
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
