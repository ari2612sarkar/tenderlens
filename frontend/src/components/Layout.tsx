import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/analyze", label: "Analyze a tender" },
  { to: "/profile", label: "Company profile" },
  { to: "/schemes", label: "Schemes" },
];

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-rule bg-paper/95">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <NavLink to="/" className="flex items-center gap-2 text-lg font-extrabold tracking-tight" style={{ fontStretch: "118%" }}>
            <svg width="26" height="26" viewBox="0 0 64 64" aria-hidden>
              <circle cx="32" cy="32" r="24" fill="none" stroke="var(--color-stamp)" strokeWidth="5" />
              <path d="M21 33l7 7 15-16" fill="none" stroke="var(--color-stamp)" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            TenderLens
          </NavLink>
          <nav className="flex flex-wrap gap-1 text-[0.95rem]">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 font-medium ${isActive ? "bg-stamp-soft text-stamp" : "text-ink-soft hover:text-ink"}`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t border-rule">
        <div className="mx-auto max-w-6xl px-4 py-6 text-sm text-ink-soft sm:px-6">
          <p>
            TenderLens runs on Amazon Bedrock, AWS Step Functions and AWS Lambda. Built for AWS Zero to Shipped 2026 by Valivo.ai.
          </p>
          <p className="mt-1">It's a decision aid, not legal advice. Always confirm requirements against the tender before you bid.</p>
        </div>
      </footer>
    </div>
  );
}
