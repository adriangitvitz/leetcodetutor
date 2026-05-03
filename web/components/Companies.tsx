"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { CompanyEntry } from "@/lib/types";

type Props = {
  initial: CompanyEntry[];
};

export function CompaniesView({ initial }: Props) {
  const router = useRouter();
  const [query, setQuery] = useState("");

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return initial
      .filter((c) => !q || c.name.toLowerCase().includes(q))
      .sort((a, b) => (b.top_topic_score ?? 0) - (a.top_topic_score ?? 0));
  }, [initial, query]);

  return (
    <div className="catalog">
      <div className="catalog-head">
        <h1 className="catalog-title">
          By <em>company</em>,
          <br />
          by their <em>obsession</em>.
        </h1>
        <p className="catalog-lede">
          Each company has a topic it asks more than any other. Open a company to see the
          problems they ask most often, and the wider topic they're really testing for.
        </p>
      </div>

      <div className="catalog-controls">
        <div className="search">
          <span className="search-icon">Find</span>
          <input
            placeholder="Search companies…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
        </div>
      </div>

      <div className="company-grid">
        {rows.map((c) => (
          <button
            key={c.name}
            className="company-card"
            onClick={() => router.push(`/companies/${encodeURIComponent(c.name)}`)}
          >
            <div className="company-card-head">
              <div className="company-mark">{c.name[0]}</div>
              <div className="company-name">{c.name}</div>
              <div className="company-count">{c.problem_count} problems</div>
            </div>
            <div className="company-topic">
              <div className="company-topic-label">Most-asked topic</div>
              <div className="company-topic-value">{c.top_topic ?? "-"}</div>
            </div>
            <div className="company-fave">
              <div className="company-fave-label">Signature problem</div>
              <div className="company-fave-value">{c.signature_title ?? "-"}</div>
            </div>
          </button>
        ))}
      </div>

      <div className="catalog-footer">
        <span>
          {rows.length} companies shown · {initial.length} total
        </span>
      </div>
    </div>
  );
}
