"use client";

import { useEffect, useMemo, useState } from "react";
import type { Persona } from "@/lib/types";
import { PERSONAS } from "@/lib/explanations";
import { useSettings, type Palette, type Provider } from "./SettingsContext";

type Props = {
  onClose: () => void;
};

const PERSONA_ORDER: { k: Persona["key"]; glyph: string }[] = [
  { k: "scholar", glyph: "S" },
  { k: "coach", glyph: "C" },
  { k: "sage", glyph: "Z" },
  { k: "hacker", glyph: "H" },
];

const PROVIDER_ORDER: { k: Provider; label: string }[] = [
  { k: "openrouter", label: "OpenRouter" },
  { k: "lmstudio", label: "LM Studio" },
  { k: "mlx", label: "MLX" },
];

const PALETTE_ORDER: { k: Palette; label: string; hint: string }[] = [
  { k: "warm", label: "Warm", hint: "amber on near-black" },
  { k: "slate", label: "Slate", hint: "cool gray + cyan" },
];

type ModelOption = { id: string; name: string; context_length?: number };

export function TweaksPanel({ onClose }: Props) {
  const { persona, setPersona, provider, setProvider, model, setModel, palette, setPalette } = useSettings();
  const [models, setModels] = useState<ModelOption[]>([]);
  const [modelLoading, setModelLoading] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    let cancelled = false;
    setModelLoading(true);
    setModelError(null);
    setModels([]);
    fetch(`/api/models?provider=${provider}`)
      .then(async (r) => {
        const data = (await r.json()) as { models?: ModelOption[]; error?: string };
        if (cancelled) return;
        setModels(data.models ?? []);
        if (data.error) setModelError(data.error);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setModelError(err instanceof Error ? err.message : "Network error");
      })
      .finally(() => {
        if (!cancelled) setModelLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [provider]);

  const filteredModels = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return models.slice(0, 200);
    return models.filter((m) => m.id.toLowerCase().includes(q) || m.name.toLowerCase().includes(q)).slice(0, 200);
  }, [models, filter]);

  return (
    <div className="tweaks-panel" style={{ width: 340, maxHeight: "80vh", overflowY: "auto" }}>
      <div className="tweaks-head">
        <span>Tweaks</span>
        <button className="tweaks-close" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>

      <div className="tweaks-group">
        <div className="tweaks-label">Palette</div>
        <div style={{ display: "flex", gap: 6 }}>
          {PALETTE_ORDER.map(({ k, label, hint }) => (
            <button
              key={k}
              className={`chip ${palette === k ? "active" : ""}`}
              onClick={() => setPalette(k)}
              style={{ flex: 1, justifyContent: "center", flexDirection: "column", padding: "8px 10px" }}
              title={hint}
            >
              <span style={{ display: "block" }}>{label}</span>
              <span
                style={{
                  display: "block",
                  marginTop: 2,
                  fontSize: 10,
                  color: "var(--paper-faint)",
                  fontStyle: "normal",
                }}
              >
                {hint}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="tweaks-group">
        <div className="tweaks-label">AI personality</div>
        <div className="tweaks-options">
          {PERSONA_ORDER.map(({ k, glyph }) => {
            const info = PERSONAS[k];
            return (
              <div
                key={k}
                className={`tweak-opt ${persona === k ? "active" : ""}`}
                onClick={() => setPersona(k)}
              >
                <div className="tweak-opt-glyph">{glyph}</div>
                <div>
                  <div className="tweak-opt-name">{info.name}</div>
                  <div className="tweak-opt-desc">{info.desc}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="tweaks-group">
        <div className="tweaks-label">Provider</div>
        <div style={{ display: "flex", gap: 6 }}>
          {PROVIDER_ORDER.map(({ k, label }) => (
            <button
              key={k}
              className={`chip ${provider === k ? "active" : ""}`}
              onClick={() => setProvider(k)}
              style={{ flex: 1, justifyContent: "center" }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="tweaks-group">
        <div className="tweaks-label">
          Model {modelLoading && <span style={{ marginLeft: 6, opacity: 0.6 }}>loading…</span>}
        </div>

        <input
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder={
            provider === "openrouter"
              ? "anthropic/claude-sonnet-4.5"
              : provider === "lmstudio"
                ? "local-model"
                : "mlx-community/Llama-3.2-3B-Instruct-4bit"
          }
          style={{
            width: "100%",
            background: "var(--ink-1)",
            border: "1px solid var(--ink-4)",
            borderRadius: 4,
            padding: "8px 10px",
            color: "var(--paper)",
            fontFamily: "var(--mono)",
            fontSize: 12,
            outline: "none",
          }}
        />

        {modelError && (
          <div
            style={{
              marginTop: 6,
              fontSize: 11,
              color: "var(--paper-mute)",
              fontFamily: "var(--serif)",
              fontStyle: "normal",
            }}
          >
            {modelError}
          </div>
        )}

        {models.length > 0 && (
          <>
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder={`Filter ${models.length} models…`}
              style={{
                width: "100%",
                marginTop: 8,
                background: "var(--ink-1)",
                border: "1px solid var(--ink-4)",
                borderRadius: 4,
                padding: "6px 10px",
                color: "var(--paper)",
                fontFamily: "var(--sans)",
                fontSize: 12,
                outline: "none",
              }}
            />
            <div
              style={{
                marginTop: 6,
                maxHeight: 180,
                overflowY: "auto",
                border: "1px solid var(--ink-4)",
                borderRadius: 4,
                fontFamily: "var(--mono)",
                fontSize: 11,
              }}
            >
              {filteredModels.map((m) => (
                <div
                  key={m.id}
                  onClick={() => setModel(m.id)}
                  style={{
                    padding: "5px 9px",
                    cursor: "pointer",
                    background: model === m.id ? "var(--ink-3)" : "transparent",
                    color: model === m.id ? "var(--amber)" : "var(--paper-dim)",
                    borderBottom: "1px solid var(--ink-3)",
                  }}
                  title={m.name}
                >
                  {m.id}
                  {m.context_length && (
                    <span style={{ float: "right", color: "var(--paper-faint)" }}>
                      {Math.round(m.context_length / 1000)}k
                    </span>
                  )}
                </div>
              ))}
              {filteredModels.length === 0 && (
                <div style={{ padding: 10, color: "var(--paper-mute)", fontStyle: "normal" }}>
                  no matches
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
