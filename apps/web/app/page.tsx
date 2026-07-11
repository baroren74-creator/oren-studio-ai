import Link from "next/link";

export default function HomePage() {
  return (
    <div>
      <h1>Oren Studio AI</h1>
      <p>Phase 1 skeleton. Start with the Projects tab to create a project.</p>
      <p>
        <Link href="/projects">Go to Projects →</Link>
      </p>
    </div>
  );
}
