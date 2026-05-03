"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import type { ChatMessage, Persona, Problem } from "@/lib/types";
import { PERSONAS } from "@/lib/explanations";
import { useSettings } from "./SettingsContext";

type Mode = "teacher" | "socratic" | "chat";

type Props = {
  problem: Problem;
};

function escapeHtml(s: string): string {
  return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function formatInline(s: string): string {
  return escapeHtml(s)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+?)`/g, "<code>$1</code>");
}

function formatMarkdownish(s: string): string {
  const paras = s.split("\n\n");
  return paras
    .map((p) => {
      if (p.startsWith("- ")) {
        const items = p
          .split("\n")
          .map((line) => `<li>${formatInline(line.replace(/^- /, ""))}</li>`)
          .join("");
        return `<ul>${items}</ul>`;
      }
      if (/^\d+\. /.test(p)) {
        const items = p
          .split("\n")
          .map((line) => `<li>${formatInline(line.replace(/^\d+\. /, ""))}</li>`)
          .join("");
        return `<ol>${items}</ol>`;
      }
      return `<p>${formatInline(p)}</p>`;
    })
    .join("");
}

type TeacherPayload = {
  plain: string;
  aha: string;
  strategy: string;
  code: string;
  complexity: { time: string; space: string; tdesc: string; sdesc: string };
};
type SocraticPayload = { questions: { q: string; hint: string }[] };

type FetchState<T> =
  | { kind: "idle" }
  | { kind: "loading"; cached?: T }
  | { kind: "ready"; payload: T; cached: boolean }
  | { kind: "error"; message: string };

class ApiError extends Error {
  status: number;
  requestId?: string;
  constructor(message: string, status: number, requestId?: string) {
    super(message);
    this.status = status;
    this.requestId = requestId;
  }
}

async function fetchExplain<T>(
  slug: string,
  body: {
    kind: "teacher" | "socratic";
    provider: string;
    model: string;
    persona: string;
    force?: boolean;
  },
  signal?: AbortSignal
): Promise<{ payload: T; cached: boolean }> {
  const r = await fetch(`/api/explain/${slug}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  const data = (await r.json().catch(() => ({}))) as {
    payload?: T;
    cached?: boolean;
    error?: string;
    requestId?: string;
  };
  if (!r.ok || !data.payload) {
    throw new ApiError(data.error ?? `HTTP ${r.status}`, r.status, data.requestId);
  }
  return { payload: data.payload, cached: !!data.cached };
}

async function callLLM(
  messages: ChatMessage[],
  opts: { provider?: string; model?: string; signal?: AbortSignal } = {}
): Promise<string> {
  const res = await fetch("/api/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, provider: opts.provider, model: opts.model }),
    signal: opts.signal,
  });
  const data = (await res.json().catch(() => ({}))) as {
    text?: string;
    error?: string;
    requestId?: string;
  };
  if (!res.ok) {
    throw new ApiError(data.error ?? `HTTP ${res.status}`, res.status, data.requestId);
  }
  return data.text ?? "";
}

function formatError(err: unknown): string {
  if (err instanceof ApiError) {
    const id = err.requestId ? ` · req ${err.requestId}` : "";
    return `${err.status} ${err.message}${id}`;
  }
  return err instanceof Error ? err.message : "Unknown error";
}

export function Tutor({ problem }: Props) {
  const [mode, setMode] = useState<Mode>("teacher");
  const [visited, setVisited] = useState<Record<Mode, boolean>>({
    teacher: true,
    socratic: false,
    chat: false,
  });
  const { persona } = useSettings();
  const p = PERSONAS[persona];

  const switchTo = (m: Mode) => {
    setMode(m);
    if (!visited[m]) setVisited((v) => ({ ...v, [m]: true }));
  };

  const wrap = (active: boolean): React.CSSProperties => ({
    display: active ? "contents" : "none",
  });

  return (
    <div className="tutor">
      <div className="tutor-head">
        <div className="tutor-title-row">
          <h2 className="tutor-title">Tutor</h2>
          <div className="tutor-persona">
            mode: <strong>{p.name}</strong>
          </div>
        </div>
        <div className="mode-tabs">
          <ModeTab mode={mode} target="teacher" glyph="T" label="Teacher" onSelect={switchTo} />
          <ModeTab mode={mode} target="socratic" glyph="S" label="Socratic" onSelect={switchTo} />
          <ModeTab mode={mode} target="chat" glyph="C" label="Chat" onSelect={switchTo} />
        </div>
      </div>

      {visited.teacher && (
        <div style={wrap(mode === "teacher")}>
          <TeacherMode problem={problem} opener={p.openerTeach} />
        </div>
      )}
      {visited.socratic && (
        <div style={wrap(mode === "socratic")}>
          <SocraticMode problem={problem} opener={p.openerSoc} persona={p} />
        </div>
      )}
      {visited.chat && (
        <div style={wrap(mode === "chat")}>
          <ChatMode problem={problem} opener={p.openerChat} persona={p} />
        </div>
      )}
    </div>
  );
}

function ModeTab({
  mode,
  target,
  glyph,
  label,
  onSelect,
}: {
  mode: Mode;
  target: Mode;
  glyph: string;
  label: string;
  onSelect: (m: Mode) => void;
}) {
  return (
    <button
      className={`mode-tab ${mode === target ? "active" : ""}`}
      onClick={() => onSelect(target)}
    >
      <span className="mode-tab-glyph">{glyph}</span> {label}
    </button>
  );
}

function TeacherMode({ problem, opener }: { problem: Problem; opener: string }) {
  const { provider, model, persona } = useSettings();
  const [state, setState] = useState<FetchState<TeacherPayload>>({ kind: "idle" });
  const [open, setOpen] = useState({
    plain: true,
    aha: false,
    strategy: false,
    code: false,
    complexity: false,
  });
  const toggle = (k: keyof typeof open) => setOpen((o) => ({ ...o, [k]: !o[k] }));

  const abortRef = useRef<AbortController | null>(null);

  const load = (force = false): AbortController | null => {
    if (!model) {
      setState({
        kind: "error",
        message: "Pick a model in the Tweaks panel to generate a fresh walkthrough.",
      });
      return null;
    }
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setState({ kind: "loading" });
    fetchExplain<TeacherPayload>(
      problem.slug,
      { kind: "teacher", provider, model, persona, force },
      ctrl.signal
    )
      .then(({ payload, cached }) => {
        if (ctrl.signal.aborted) return;
        setState({ kind: "ready", payload, cached });
      })
      .catch((err: unknown) => {
        if (ctrl.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) {
          return;
        }
        setState({ kind: "error", message: formatError(err) });
      });
    return ctrl;
  };

  useEffect(() => {
    const ctrl = load(false);
    return () => ctrl?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [problem.slug, provider, model, persona]);

  const sectionMeta: { k: keyof typeof open; title: string; sub: string }[] = [
    { k: "plain", title: "Plain-English", sub: "What the prompt actually asks" },
    { k: "aha", title: "The Aha Moment", sub: "The insight that unlocks it" },
    { k: "strategy", title: "Strategy", sub: "How to attack it, step by step" },
    { k: "code", title: "Reference Code", sub: "Canonical Python solution" },
    { k: "complexity", title: "Complexity", sub: "Time & space" },
  ];

  const renderBody = (k: keyof typeof open): ReactNode => {
    if (state.kind !== "ready") {
      return <SkeletonLines lines={3} />;
    }
    const ex = state.payload;
    switch (k) {
      case "plain":
        return <p dangerouslySetInnerHTML={{ __html: formatInline(ex.plain) }} />;
      case "aha":
        return <div dangerouslySetInnerHTML={{ __html: formatMarkdownish(ex.aha) }} />;
      case "strategy":
        return <div dangerouslySetInnerHTML={{ __html: formatMarkdownish(ex.strategy) }} />;
      case "code":
        return <div dangerouslySetInnerHTML={{ __html: ex.code }} />;
      case "complexity":
        return (
          <div className="complexity-grid">
            <div className="complexity-cell">
              <div className="cl">Time</div>
              <div className="cv">{ex.complexity.time}</div>
              <div className="cd">{ex.complexity.tdesc}</div>
            </div>
            <div className="complexity-cell">
              <div className="cl">Space</div>
              <div className="cv">{ex.complexity.space}</div>
              <div className="cd">{ex.complexity.sdesc}</div>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="tutor-body">
      <div className="teach-intro">{opener}</div>
      <StatusLine
        state={state}
        provider={provider}
        model={model}
        onRegenerate={() => load(true)}
      />
      {sectionMeta.map((it, i) => (
        <div key={it.k} className={`accordion-item ${open[it.k] ? "open" : ""}`}>
          <button className="accordion-head" onClick={() => toggle(it.k)}>
            <span className="accordion-num">{String(i + 1).padStart(2, "0")}</span>
            <span className="accordion-title">{it.title}</span>
            <span className="accordion-sub">{it.sub}</span>
            <span className="accordion-caret">›</span>
          </button>
          {open[it.k] && <div className="accordion-body">{renderBody(it.k)}</div>}
        </div>
      ))}
    </div>
  );
}

function SkeletonLines({ lines }: { lines: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 12,
            background: "linear-gradient(90deg, var(--ink-2) 25%, var(--ink-3) 50%, var(--ink-2) 75%)",
            backgroundSize: "200% 100%",
            animation: "shimmer 1.6s infinite linear",
            borderRadius: 3,
            width: i === lines - 1 ? "60%" : "100%",
          }}
        />
      ))}
      <style>{`@keyframes shimmer { from { background-position: 200% 0 } to { background-position: -200% 0 } }`}</style>
    </div>
  );
}

function StatusLine({
  state,
  provider,
  model,
  onRegenerate,
}: {
  state: FetchState<unknown>;
  provider: string;
  model: string;
  onRegenerate: () => void;
}) {
  const baseStyle: React.CSSProperties = {
    fontFamily: "var(--sans)",
    fontSize: 11,
    letterSpacing: "0.06em",
    color: "var(--paper-mute)",
    padding: "6px 0 14px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottom: "1px dashed var(--ink-4)",
    marginBottom: 14,
  };
  const right = (
    <button className="btn btn-ghost" onClick={onRegenerate} disabled={state.kind === "loading" || !model}>
      Regenerate
    </button>
  );
  if (state.kind === "loading") {
    return (
      <div style={baseStyle}>
        <span>
          generating with <strong style={{ color: "var(--amber)" }}>{model || "-"}</strong>…
        </span>
        {right}
      </div>
    );
  }
  if (state.kind === "error") {
    return (
      <div style={{ ...baseStyle, color: "var(--hard)" }}>
        <span>{(state as { message: string }).message}</span>
        {right}
      </div>
    );
  }
  if (state.kind === "ready") {
    return (
      <div style={baseStyle}>
        <span>
          {state.cached ? "cached" : "fresh"} · {provider} · <code style={{ fontFamily: "var(--mono)" }}>{model}</code>
        </span>
        {right}
      </div>
    );
  }
  return null;
}

function SocraticMode({
  problem,
  opener,
  persona,
}: {
  problem: Problem;
  opener: string;
  persona: Persona;
}) {
  const { provider, model, persona: personaKey } = useSettings();
  const [state, setState] = useState<FetchState<SocraticPayload>>({ kind: "idle" });
  const [step, setStep] = useState(0);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [thinking, setThinking] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  const load = (force = false): AbortController | null => {
    if (!model) {
      setState({
        kind: "error",
        message: "Pick a model in the Tweaks panel to generate Socratic questions.",
      });
      return null;
    }
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setState({ kind: "loading" });
    fetchExplain<SocraticPayload>(
      problem.slug,
      { kind: "socratic", provider, model, persona: personaKey, force },
      ctrl.signal
    )
      .then(({ payload, cached }) => {
        if (ctrl.signal.aborted) return;
        setState({ kind: "ready", payload, cached });
      })
      .catch((err: unknown) => {
        if (ctrl.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) {
          return;
        }
        setState({ kind: "error", message: formatError(err) });
      });
    return ctrl;
  };

  useEffect(() => {
    const ctrl = load(false);
    setStep(0);
    setAnswer("");
    setFeedback(null);
    return () => ctrl?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [problem.slug, provider, model, personaKey]);

  const questions = state.kind === "ready" ? state.payload.questions : [];
  const current = questions.length ? questions[Math.min(step, questions.length - 1)] : null;

  const submit = async () => {
    if (!answer.trim() || !current) return;
    setThinking(true);
    setFeedback(null);
    try {
      const prompt = `You are ${persona.name}, a ${persona.desc.toLowerCase()} algorithms tutor using the Socratic method. The student is working on "${problem.title}". You asked: "${current.q}". They replied: "${answer}". In 2-3 sentences: affirm what's right, gently correct what's off, and nudge them toward the next insight. Do not give the full answer. Be warm and brief.`;
      const reply = await callLLM([{ role: "user", content: prompt }], { provider, model });
      setFeedback(reply);
    } catch (err) {
      setFeedback(`(${formatError(err)}) Hint: ${current.hint}`);
    } finally {
      setThinking(false);
    }
  };

  const showHint = () => current && setFeedback(`Hint: ${current.hint}`);
  const next = () => {
    if (step < questions.length - 1) {
      setStep(step + 1);
      setAnswer("");
      setFeedback(null);
    }
  };
  const prev = () => {
    if (step > 0) {
      setStep(step - 1);
      setAnswer("");
      setFeedback(null);
    }
  };

  return (
    <div className="tutor-body">
      <div className="socratic">
        <div className="socratic-prompt">{opener}</div>
        <StatusLine
          state={state}
          provider={provider}
          model={model}
          onRegenerate={() => load(true)}
        />

        {current ? (
          <>
            <div className="socratic-q">
              <div className="qlabel">
                Question {step + 1} of {questions.length}
              </div>
              <p className="qtext">{current.q}</p>
            </div>

            <div className="socratic-answer">
              <textarea
                placeholder="Type your reasoning, even if you're not sure…"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
              />
              <div className="socratic-actions">
                <button
                  className="btn btn-primary"
                  onClick={submit}
                  disabled={thinking || !answer.trim()}
                >
                  {thinking ? "Thinking…" : "Reply"}
                </button>
                <button className="btn" onClick={showHint}>
                  Hint
                </button>
              </div>
            </div>

            {feedback && <div className="socratic-feedback">{feedback}</div>}

            <div className="socratic-nav">
              <button className="btn-ghost btn" onClick={prev} disabled={step === 0}>
                ← Previous
              </button>
              <div className="socratic-dots">
                {questions.map((_, i) => (
                  <span
                    key={i}
                    className={`socratic-dot ${i < step ? "done" : ""} ${i === step ? "active" : ""}`}
                  />
                ))}
              </div>
              <button
                className="btn-ghost btn"
                onClick={next}
                disabled={step === questions.length - 1}
              >
                Next →
              </button>
            </div>
          </>
        ) : (
          <div className="socratic-q">
            <div className="qlabel">Waiting for questions…</div>
            <SkeletonLines lines={2} />
          </div>
        )}
      </div>
    </div>
  );
}

function ChatMode({
  problem,
  opener,
  persona,
}: {
  problem: Problem;
  opener: string;
  persona: Persona;
}) {
  type Msg = { role: "user" | "bot"; text: string };
  const { provider, model } = useSettings();
  const [messages, setMessages] = useState<Msg[]>([{ role: "bot", text: opener }]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages([{ role: "bot", text: persona.openerChat }]);
  }, [problem.slug, persona.key, persona.openerChat]);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages, thinking]);

  const send = async (overrideText?: string) => {
    const text = (overrideText ?? input).trim();
    if (!text) return;
    const newMessages: Msg[] = [...messages, { role: "user", text }];
    setMessages(newMessages);
    setInput("");
    setThinking(true);
    try {
      const history = newMessages
        .map((m) => `${m.role === "user" ? "Student" : "Tutor"}: ${m.text}`)
        .join("\n");
      const prompt = `You are ${persona.name}, a ${persona.desc.toLowerCase()} algorithms tutor. The student is studying "${problem.title}" (${problem.difficulty}, tags: ${problem.topics}).\n\nConversation:\n${history}\n\nRespond as the tutor in a short, helpful way (3-5 sentences max). Stay in character.`;
      const reply = await callLLM([{ role: "user", content: prompt }], { provider, model });
      setMessages((m) => [...m, { role: "bot", text: reply }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "bot", text: `(${formatError(err)})` }]);
    } finally {
      setThinking(false);
    }
  };

  const suggestions = [
    `Give me a hint for ${problem.title}`,
    "What data structure should I reach for first?",
    "Explain it like I'm new to this",
    "What's a common mistake here?",
  ];

  return (
    <>
      <div className="tutor-body" ref={bodyRef}>
        <div className="chat">
          {messages.map((m, i) => (
            <div key={i} className={`chat-msg ${m.role}`}>
              <div className="who">{m.role === "user" ? "You" : persona.name}</div>
              <div className="bubble">{m.text}</div>
            </div>
          ))}
          {thinking && (
            <div className="chat-msg bot">
              <div className="who">{persona.name}</div>
              <div className="chat-thinking">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}
        </div>
      </div>
      <div className="chat-suggest">
        <span className="chat-suggest-label">Try asking</span>
        {suggestions.map((s, i) => (
          <button key={i} onClick={() => send(s)} disabled={thinking}>
            {s}
          </button>
        ))}
      </div>
      <div className="chat-composer">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          placeholder={`Ask ${persona.name.toLowerCase()} anything about this problem…`}
          rows={1}
        />
        <button
          className="chat-send"
          onClick={() => void send()}
          disabled={thinking || !input.trim()}
        >
          Send
        </button>
      </div>
    </>
  );
}
