"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Problem } from "@/lib/types";

type Props = {
  problems: Problem[];
  initialDifficulty?: Diff;
};

type Diff = "ALL" | "EASY" | "MEDIUM" | "HARD";

const DIFF_LABEL: Record<Exclude<Diff, "ALL">, string> = {
  EASY: "Easy",
  MEDIUM: "Medium",
  HARD: "Hard",
};

const SLUG_RE = /^[a-z0-9][a-z0-9-]*$/;

export function Catalog({ problems, initialDifficulty = "ALL" }: Props) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [diff, setDiff] = useState<Diff>(initialDifficulty);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const fn = (e: KeyboardEvent) => {
      const tag = (document.activeElement?.tagName ?? "").toUpperCase();
      if (e.key === "/" && tag !== "INPUT" && tag !== "TEXTAREA") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, []);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return problems
      .map((p, i) => ({ ...p, idx: i + 1 }))
      .filter(
        (r) => !q || r.title.toLowerCase().includes(q) || r.topics.toLowerCase().includes(q)
      );
  }, [problems, query]);

  const slugCandidate = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q || !SLUG_RE.test(q)) return null;
    if (rows.some((r) => r.slug === q)) return null;
    return q;
  }, [query, rows]);

  const open = (slug: string) => router.push(`/problems/${slug}`);

  const onDiff = (next: Diff) => {
    setDiff(next);
    const url = next === "ALL" ? "/" : `/?difficulty=${next}`;
    router.push(url);
  };

  return (
    <div className="catalog">
      <div className="catalog-head">
        <h1 className="catalog-title">
          A quiet place
          <br />
          to <em>study algorithms</em>.
        </h1>
        <p className="catalog-lede">
          The most-asked problems across hundreds of company interviews,
          arranged plainly. Pick one; a markdown study sheet opens on the
          left, and a patient tutor sits on the right ready to explain,
          to question, or to chat.
        </p>
      </div>

      <div className="catalog-controls">
        <div className="search">
          <span className="search-icon">Find</span>
          <input
            ref={inputRef}
            placeholder="Search by name, tag, or slug…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && slugCandidate) {
                e.preventDefault();
                open(slugCandidate);
              }
            }}
            autoFocus
          />
        </div>
        <div className="filter-group">
          <span className="filter-label">Difficulty</span>
          {(["ALL", "EASY", "MEDIUM", "HARD"] as Diff[]).map((d) => (
            <button
              key={d}
              className={`chip ${d === "EASY" ? "easy" : d === "MEDIUM" ? "med" : d === "HARD" ? "hard" : ""} ${diff === d ? "active" : ""}`}
              onClick={() => onDiff(d)}
            >
              {d === "ALL" ? "All" : DIFF_LABEL[d]}
            </button>
          ))}
        </div>
      </div>

      {slugCandidate && (
        <button className="slug-jump" onClick={() => open(slugCandidate)}>
          <span className="slug-jump-label">Open by slug</span>
          <code className="slug-jump-slug">{slugCandidate}</code>
          <span className="slug-jump-arrow">→</span>
        </button>
      )}

      <table className="ptable">
        <thead>
          <tr>
            <th className="c-num">№</th>
            <th>Problem</th>
            <th className="c-diff">Difficulty</th>
            <th className="c-acc">Acceptance</th>
            <th className="c-likes" style={{ textAlign: "right" }}>
              Companies
            </th>
            <th className="c-freq" style={{ textAlign: "right" }}>
              Freq
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={6} className="empty-state">
                {slugCandidate
                  ? <>nothing matches here — try opening <code>{slugCandidate}</code> directly above</>
                  : "- no matches -"}
              </td>
            </tr>
          )}
          {rows.map((r) => (
            <tr key={r.slug} onClick={() => open(r.slug)}>
              <td className="c-num">{String(r.idx).padStart(3, "0")}</td>
              <td className="c-title">
                <div className="title-text">{r.title}</div>
                <div className="title-meta">{r.topics}</div>
              </td>
              <td className="c-diff">
                <span
                  className={`diff-pill ${r.difficulty === "EASY" ? "easy" : r.difficulty === "MEDIUM" ? "med" : "hard"}`}
                >
                  {DIFF_LABEL[r.difficulty]}
                </span>
              </td>
              <td className="c-acc">
                {(r.acceptance_rate * 100).toFixed(1)}%
                <div className="acc-bar">
                  <div
                    className="acc-bar-fill"
                    style={{ width: `${r.acceptance_rate * 100}%` }}
                  />
                </div>
              </td>
              <td className="c-likes">{r.company_count}</td>
              <td className="c-freq">{r.mean_frequency.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="catalog-footer">
        <span>
          {rows.length} problems shown · {problems.length} total
        </span>
        <span>
          Press{" "}
          <kbd
            style={{
              fontFamily: "var(--mono)",
              fontSize: 10,
              background: "var(--ink-3)",
              padding: "2px 6px",
              borderRadius: 3,
            }}
          >
            /
          </kbd>{" "}
          to focus search
        </span>
      </div>
    </div>
  );
}
