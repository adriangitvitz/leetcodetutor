"use client";

import { useRouter } from "next/navigation";
import type { StatsResponse } from "@/lib/types";

const DIFF_LABEL = { EASY: "Easy", MEDIUM: "Medium", HARD: "Hard" } as const;
const DIFF_CLASS = { EASY: "easy", MEDIUM: "med", HARD: "hard" } as const;

export function StatsView({ stats }: { stats: StatsResponse }) {
  const router = useRouter();
  const maxProb = stats.top_problems[0]?.score ?? 1;
  const maxTopic = stats.top_topics[0]?.score ?? 1;
  const totalDiff =
    stats.difficulty_mix.EASY + stats.difficulty_mix.MEDIUM + stats.difficulty_mix.HARD;
  const pct = (n: number) => Math.round((n / totalDiff) * 100);
  const totalTopicWeight = stats.top_topics.reduce((s, t) => s + t.score, 0) || 1;

  return (
    <div className="catalog">
      <div className="catalog-head">
        <h1 className="catalog-title">
          What the <em>world</em>
          <br />
          is really asking.
        </h1>
        <p className="catalog-lede">
          A bird's-eye reading of which problems and topics dominate technical interviews
          aggregated across every company we track.
        </p>
      </div>

      <div className="stats-grid">
        <section className="stats-block">
          <div className="md-section-label" style={{ marginTop: 0 }}>
            Most-asked problems
          </div>
          <div className="bar-list">
            {stats.top_problems.slice(0, 12).map((p, i) => (
              <button
                key={p.slug}
                className="bar-row"
                onClick={() => router.push(`/problems/${p.slug}`)}
              >
                <div className="bar-rank">{String(i + 1).padStart(2, "0")}</div>
                <div className="bar-label">
                  <div className="bar-title">{p.title}</div>
                  <div className="bar-sub">
                    <span className={`diff-pill ${DIFF_CLASS[p.difficulty]}`}>
                      {DIFF_LABEL[p.difficulty]}
                    </span>
                    <span className="bar-meta">
                      asked at {p.company_count} companies
                    </span>
                  </div>
                </div>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{ width: `${(p.score / maxProb) * 100}%` }}
                  />
                </div>
                <div className="bar-num" title="Mean frequency across asking companies">
                  {p.mean_frequency.toFixed(1)}%
                </div>
              </button>
            ))}
          </div>
        </section>

        <section className="stats-block">
          <div className="md-section-label" style={{ marginTop: 0 }}>
            Most-asked topics
          </div>
          <div className="bar-list">
            {stats.top_topics.map((t, i) => (
              <div key={t.name} className="bar-row static">
                <div className="bar-rank">{String(i + 1).padStart(2, "0")}</div>
                <div className="bar-label">
                  <div className="bar-title">{t.name}</div>
                </div>
                <div className="bar-track">
                  <div
                    className="bar-fill amber"
                    style={{ width: `${(t.score / maxTopic) * 100}%` }}
                  />
                </div>
                <div className="bar-num" title="Share of total topic weight">
                  {Math.round((t.score / totalTopicWeight) * 100)}%
                </div>
              </div>
            ))}
          </div>

          <div className="md-section-label">Difficulty mix of asked problems</div>
          <div className="diff-bar">
            <div
              className="diff-seg easy"
              style={{ width: `${(stats.difficulty_mix.EASY / totalDiff) * 100}%` }}
            >
              <span className="diff-seg-label">Easy</span>
              <span className="diff-seg-pct">{pct(stats.difficulty_mix.EASY)}%</span>
            </div>
            <div
              className="diff-seg med"
              style={{ width: `${(stats.difficulty_mix.MEDIUM / totalDiff) * 100}%` }}
            >
              <span className="diff-seg-label">Medium</span>
              <span className="diff-seg-pct">{pct(stats.difficulty_mix.MEDIUM)}%</span>
            </div>
            <div
              className="diff-seg hard"
              style={{ width: `${(stats.difficulty_mix.HARD / totalDiff) * 100}%` }}
            >
              <span className="diff-seg-label">Hard</span>
              <span className="diff-seg-pct">{pct(stats.difficulty_mix.HARD)}%</span>
            </div>
          </div>
          <p className="stats-note">
            Mediums dominate. Most interviewers reach for them because they discriminate
            without devolving into trivia.
          </p>
        </section>
      </div>
    </div>
  );
}
