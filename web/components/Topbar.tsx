"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Props = {
  problemTitle?: string;
  totalCount?: number;
    // @ts-ignore
    onOpenTweaks: () => void;
};

const TABS: { kind: "catalog" | "companies" | "stats"; href: string; label: string }[] = [
  { kind: "catalog", href: "/", label: "All problems" },
  { kind: "companies", href: "/companies", label: "By company" },
  { kind: "stats", href: "/stats", label: "Statistics" },
];

function activeTab(pathname: string): (typeof TABS)[number]["kind"] | "study" {
  if (pathname.startsWith("/problems/")) return "study";
  if (pathname.startsWith("/companies")) return "companies";
  if (pathname.startsWith("/stats")) return "stats";
  return "catalog";
}

export function Topbar({ problemTitle, totalCount, onOpenTweaks }: Props) {
  const pathname = usePathname() ?? "/";
  const active = activeTab(pathname);

  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">Leetcode Tutor</div>
        <div className="brand-sub">A reading room for algorithms</div>
      </div>

      <nav className="tabs">
        {TABS.map((t) => (
          <Link
            key={t.kind}
            href={t.href}
            className={`tab ${active === t.kind ? "active" : ""}`}
          >
            <span className="tab-label">{t.label}</span>
          </Link>
        ))}
      </nav>

      <div className="topbar-actions">
        {problemTitle ? (
          <>
            <div className="crumbs">
              <span className="active">{problemTitle}</span>
            </div>
            <Link href="/" className="topbar-back">
              ← Back to index
            </Link>
          </>
        ) : typeof totalCount === "number" ? (
          <div className="crumbs">
            <span>{totalCount} entries</span>
          </div>
        ) : null}
        <button className="topbar-back" onClick={onOpenTweaks} aria-label="Open tweaks panel">
          Tweaks
        </button>
      </div>
    </header>
  );
}
