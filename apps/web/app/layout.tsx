import type { Metadata } from "next";
import Nav from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Oren Studio AI",
  description: "Personal agent-based content studio",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="studio-shell">
          <Nav />
          <main className="studio-main">{children}</main>
        </div>
      </body>
    </html>
  );
}
