"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Persona } from "@/lib/types";

export type Provider = "openrouter" | "lmstudio" | "mlx";
export type Palette = "warm" | "slate";

type Settings = {
  persona: Persona["key"];
  provider: Provider;
  model: string;
  palette: Palette;
};

type Ctx = Settings & {
  setPersona: (k: Persona["key"]) => void;
  setProvider: (p: Provider) => void;
  setModel: (m: string) => void;
  setPalette: (p: Palette) => void;
};

const KEYS = {
  persona: "lct_persona",
  provider: "lct_provider",
  model: "lct_model",
  palette: "lct_palette",
} as const;

const DEFAULT_MODELS: Record<Provider, string> = {
  openrouter: "anthropic/claude-sonnet-4.5",
  lmstudio: "local-model",
  mlx: "mlx-community/Llama-3.2-3B-Instruct-4bit",
};

const DEFAULTS: Settings = {
  persona: "scholar",
  provider: "openrouter",
  model: DEFAULT_MODELS.openrouter,
  palette: "warm",
};

const PROVIDERS_SET: ReadonlySet<Provider> = new Set(["openrouter", "lmstudio", "mlx"]);
const PERSONAS_SET: ReadonlySet<Persona["key"]> = new Set(["scholar", "coach", "sage", "hacker"]);
const PALETTES_SET: ReadonlySet<Palette> = new Set(["warm", "slate"]);

function readPersona(): Persona["key"] {
  if (typeof window === "undefined") return DEFAULTS.persona;
  const raw = window.localStorage.getItem(KEYS.persona);
  return raw && PERSONAS_SET.has(raw as Persona["key"]) ? (raw as Persona["key"]) : DEFAULTS.persona;
}

function readProvider(): Provider {
  if (typeof window === "undefined") return DEFAULTS.provider;
  const raw = window.localStorage.getItem(KEYS.provider);
  return raw && PROVIDERS_SET.has(raw as Provider) ? (raw as Provider) : DEFAULTS.provider;
}

function readModel(provider: Provider): string {
  if (typeof window === "undefined") return DEFAULT_MODELS[provider];
  const stored = window.localStorage.getItem(KEYS.model);
  return stored && stored.trim() ? stored : DEFAULT_MODELS[provider];
}

function readPalette(): Palette {
  if (typeof window === "undefined") return DEFAULTS.palette;
  const raw = window.localStorage.getItem(KEYS.palette);
  return raw && PALETTES_SET.has(raw as Palette) ? (raw as Palette) : DEFAULTS.palette;
}

const SettingsCtx = createContext<Ctx>({
  ...DEFAULTS,
  setPersona: () => {},
  setProvider: () => {},
  setModel: () => {},
  setPalette: () => {},
});

function applyPaletteAttribute(palette: Palette) {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.theme = palette;
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(DEFAULTS);

  useEffect(() => {
    const provider = readProvider();
    const palette = readPalette();
    setSettings({
      persona: readPersona(),
      provider,
      model: readModel(provider),
      palette,
    });
    applyPaletteAttribute(palette);
  }, []);

  const setPersona = (k: Persona["key"]) => {
    setSettings((s) => ({ ...s, persona: k }));
    if (typeof window !== "undefined") window.localStorage.setItem(KEYS.persona, k);
  };

  const setProvider = (p: Provider) => {
    const defaultModel = DEFAULT_MODELS[p];
    setSettings((s) => ({ ...s, provider: p, model: defaultModel }));
    if (typeof window !== "undefined") {
      window.localStorage.setItem(KEYS.provider, p);
      window.localStorage.setItem(KEYS.model, defaultModel);
    }
  };
  const setModel = (m: string) => {
    setSettings((s) => ({ ...s, model: m }));
    if (typeof window !== "undefined") window.localStorage.setItem(KEYS.model, m);
  };
  const setPalette = (p: Palette) => {
    setSettings((s) => ({ ...s, palette: p }));
    if (typeof window !== "undefined") window.localStorage.setItem(KEYS.palette, p);
    applyPaletteAttribute(p);
  };

  return (
    <SettingsCtx.Provider value={{ ...settings, setPersona, setProvider, setModel, setPalette }}>
      {children}
    </SettingsCtx.Provider>
  );
}

export function useSettings(): Ctx {
  return useContext(SettingsCtx);
}

export function usePersona() {
  const { persona, setPersona } = useSettings();
  return { persona, setPersona };
}
