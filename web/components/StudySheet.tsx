"use client";

import { useEffect, useState, type ReactNode } from "react";
import type { Problem, Statement } from "@/lib/types";

type Props = {
  problem: Problem;
};

const DIFF_LABEL: Record<Problem["difficulty"], string> = {
  EASY: "Easy",
  MEDIUM: "Medium",
  HARD: "Hard",
};

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; statement: Statement }
  | { kind: "error"; message: string };

export function StudySheet({ problem }: Props) {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    fetch(`/api/statement/${problem.slug}`)
      .then(async (r) => {
        const data = await r.json();
        if (cancelled) return;
        if (!r.ok) {
          setState({ kind: "error", message: data?.error ?? `HTTP ${r.status}` });
          return;
        }
        setState({ kind: "ready", statement: data as Statement });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Network error";
        setState({ kind: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, [problem.slug]);

  return (
    <div className="md-doc">
      {state.kind === "ready" && state.statement.number !== null && (
        <div className="md-num">Problem № {state.statement.number}</div>
      )}
      <h1 className="md-title">{problem.title}</h1>

      <div className="md-meta">
        <div>
          <span className="meta-label">Difficulty</span>
          <span
            className={`diff-pill ${problem.difficulty === "EASY" ? "easy" : problem.difficulty === "MEDIUM" ? "med" : "hard"}`}
          >
            {DIFF_LABEL[problem.difficulty]}
          </span>
        </div>
        <div style={{ flex: 1 }}>
          <span className="meta-label">Tags</span>
          <span style={{ color: "var(--paper-dim)" }}>{problem.topics}</span>
        </div>
        <a href={problem.link} target="_blank" rel="noreferrer">
          Source ↗
        </a>
      </div>

      {state.kind === "loading" && (
        <p className="md-p" style={{ color: "var(--paper-mute)", fontStyle: "normal" }}>
          Loading problem statement…
        </p>
      )}

      {state.kind === "error" && (
        <>
          <div className="md-section-label">Statement unavailable</div>
          <p className="md-p" style={{ color: "var(--paper-dim)" }}>
            {state.message}
          </p>
          <p className="md-p" style={{ color: "var(--paper-mute)", fontSize: 14 }}>
            Try running{" "}
            <code style={{ fontFamily: "var(--mono)" }}>
              make fetch slug={problem.slug}
            </code>{" "}
            from the repo root.
          </p>
        </>
      )}

      {state.kind === "ready" && <Sections statement={state.statement} />}
    </div>
  );
}

function Sections({ statement }: { statement: Statement }) {
  return (
    <>
      <div className="md-section-label">Description</div>
      {statement.description.split("\n\n").map((para, i) => (
        <p key={i} className="md-p">
          {renderInline(para)}
        </p>
      ))}

      {statement.examples.length > 0 && (
        <>
          <div className="md-section-label">Examples</div>
          {statement.examples.map((ex, i) => (
            <div key={i} className="md-example">
              <div className="md-example-label">Example {i + 1}</div>
              <div className="md-io-row">
                <div className="md-io-label">Input</div>
                <div className="md-io-val">{ex.input}</div>
              </div>
              <div className="md-io-row">
                <div className="md-io-label">Output</div>
                <div className="md-io-val">{ex.output}</div>
              </div>
              {ex.explanation && (
                <div className="md-io-row">
                  <div className="md-io-label">Note</div>
                  <div
                    className="md-io-val"
                    style={{ fontFamily: "var(--serif)", fontStyle: "normal" }}
                  >
                    {ex.explanation}
                  </div>
                </div>
              )}
            </div>
          ))}
        </>
      )}

      {statement.constraints.length > 0 && (
        <>
          <div className="md-section-label">Constraints</div>
          <ul className="md-ul">
            {statement.constraints.map((c, i) => (
              <li key={i} className="md-li">
                {renderInline(c)}
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}

function renderInline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let remaining = text;
  let key = 0;
  const patterns: { re: RegExp; tag: "strong" | "em" | "code" }[] = [
    { re: /\*\*(.+?)\*\*/, tag: "strong" },
    { re: /\*(.+?)\*/, tag: "em" },
    { re: /`([^`]+?)`/, tag: "code" },
  ];
  while (remaining.length) {
    let earliest: { tag: "strong" | "em" | "code"; match: RegExpMatchArray; index: number } | null = null;
    for (const p of patterns) {
      const m = remaining.match(p.re);
      if (m && m.index !== undefined && (earliest === null || m.index < earliest.index)) {
        earliest = { tag: p.tag, match: m, index: m.index };
      }
    }
    if (!earliest) {
      parts.push(remaining);
      break;
    }
    if (earliest.index > 0) parts.push(remaining.slice(0, earliest.index));
    const Tag = earliest.tag;
    parts.push(<Tag key={key++}>{earliest.match[1]}</Tag>);
    remaining = remaining.slice(earliest.index + earliest.match[0].length);
  }
  return parts;
}
