import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Oren Studio AI",
  description: "Personal agent-based content studio",
};

const NAV_ITEMS = [
  { href: "/chat", label: "Chat" },
  { href: "/projects", label: "Projects" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/prompts", label: "Prompts" },
  { href: "/ops", label: "Ops" },
  { href: "/settings", label: "Settings" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="studio-shell">
          <nav className="studio-nav">
            <strong>Oren Studio AI</strong>
            <div style={{ marginTop: "1rem" }}>
              {NAV_ITEMS.map((item) => (
                <Link key={item.href} href={item.href}>
                  {item.label}
                </Link>
              ))}
            </div>
          </nav>
          <main className="studio-main">{children}</main>
        </div>
      </body>
    </html>
  );
}
