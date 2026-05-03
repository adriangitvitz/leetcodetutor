"use client";

import { useRouter } from "next/navigation";
import type { AskEntry, CompanyDetailResponse } from "@/lib/types";

type Props = {
  detail: CompanyDetailResponse;
  related: AskEntry[];
};

const DIFF_LABEL = { EASY: "Easy", MEDIUM: "Medium", HARD: "Hard" } as const;
const DIFF_CLASS = { EASY: "easy", MEDIUM: "med", HARD: "hard" } as const;

export function CompanyDetail({ detail, related }: Props) {
  const router = useRouter();
  const open = (slug: string) => router.push(`/problems/${slug}`);

  const sortedAsks = [...detail.asks].sort((a, b) => b.frequency - a.frequency);
  const featuredCount = Math.min(6, Math.ceil(sortedAsks.length * 0.5));
  const featured = sortedAsks.slice(0, featuredCount);
  const rest = sortedAsks.slice(featuredCount);

  return (
    <div className="catalog">
      <button className="back-link" onClick={() => router.push("/companies")}>
        ← All companies
      </button>

      <div className="company-detail-head">
        <div className="company-mark large">{detail.name[0]}</div>
        <div>
          <h1 className="catalog-title" style={{ fontSize: 48, marginBottom: 12 }}>
            {detail.name}
          </h1>
          <div className="company-detail-meta">
            <div>
              <span className="meta-k">Most-asked topic</span>
              <span className="meta-v amber">{detail.top_topic ?? "-"}</span>
            </div>
            <div>
              <span className="meta-k">Problems tracked</span>
              <span className="meta-v">{detail.total_problems}</span>
            </div>
            <div>
              <span className="meta-k">Avg frequency</span>
              <span className="meta-v">{Math.round(detail.avg_frequency)}%</span>
            </div>
          </div>
        </div>
      </div>

      {featured.length > 0 && (
        <>
          <div className="md-section-label">Asked most often at {detail.name}</div>
          <div className="featured-grid">
            {featured.map((a) => (
              <button key={a.slug} className="featured-card" onClick={() => open(a.slug)}>
                <div className="featured-freq">
                  <div className="freq-bar">
                    <div className="freq-bar-fill" style={{ width: `${a.frequency}%` }} />
                  </div>
                  <div className="freq-num">{Math.round(a.frequency)}%</div>
                </div>
                <div className="featured-title">{a.title}</div>
                <div className="featured-meta">
                  <span className={`diff-pill ${DIFF_CLASS[a.difficulty]}`}>
                    {DIFF_LABEL[a.difficulty]}
                  </span>
                  <span className="featured-tags">{a.topics}</span>
                </div>
              </button>
            ))}
          </div>
        </>
      )}

      {rest.length > 0 && (
        <>
          <div className="md-section-label">Also asked at {detail.name}</div>
          <table className="ptable">
            <thead>
              <tr>
                <th>Problem</th>
                <th className="c-diff">Difficulty</th>
                <th className="c-acc">Frequency</th>
              </tr>
            </thead>
            <tbody>
              {rest.map((a) => (
                <tr key={a.slug} onClick={() => open(a.slug)}>
                  <td className="c-title">
                    <div className="title-text">{a.title}</div>
                    <div className="title-meta">{a.topics}</div>
                  </td>
                  <td className="c-diff">
                    <span className={`diff-pill ${DIFF_CLASS[a.difficulty]}`}>
                      {DIFF_LABEL[a.difficulty]}
                    </span>
                  </td>
                  <td className="c-acc">
                    {Math.round(a.frequency)}%
                    <div className="acc-bar">
                      <div
                        className="acc-bar-fill"
                        style={{ width: `${a.frequency}%`, background: "var(--amber-dim)" }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {related.length > 0 && (
        <>
          <div className="md-section-label">
            Related problems · {detail.top_topic ?? "-"}
          </div>
          <p className="related-lede">
            {detail.name} hasn't been seen asking these directly but they live in the same
            topic, and the patterns transfer.
          </p>
          <table className="ptable">
            <thead>
              <tr>
                <th>Problem</th>
                <th className="c-diff">Difficulty</th>
                <th className="c-acc">Mean Freq</th>
              </tr>
            </thead>
            <tbody>
              {related.map((p) => (
                <tr key={p.slug} onClick={() => open(p.slug)}>
                  <td className="c-title">
                    <div className="title-text">{p.title}</div>
                    <div className="title-meta">{p.topics}</div>
                  </td>
                  <td className="c-diff">
                    <span className={`diff-pill ${DIFF_CLASS[p.difficulty]}`}>
                      {DIFF_LABEL[p.difficulty]}
                    </span>
                  </td>
                  <td className="c-acc">{p.frequency.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
