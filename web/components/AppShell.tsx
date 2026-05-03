"use client";

import { useState, type ReactNode } from "react";
import { Topbar } from "./Topbar";
import { TweaksPanel } from "./TweaksPanel";
import { SettingsProvider } from "./SettingsContext";

type Props = {
  problemTitle?: string;
  totalCount?: number;
  children: ReactNode;
};

export function AppShell({ problemTitle, totalCount, children }: Props) {
  return (
    <SettingsProvider>
      <Shell problemTitle={problemTitle} totalCount={totalCount}>
        {children}
      </Shell>
    </SettingsProvider>
  );
}

function Shell({ problemTitle, totalCount, children }: Props) {
  const [showTweaks, setShowTweaks] = useState(false);

  return (
    <div className="app">
      <Topbar
        problemTitle={problemTitle}
        totalCount={totalCount}
        onOpenTweaks={() => setShowTweaks(true)}
      />
      {children}
      {showTweaks && <TweaksPanel onClose={() => setShowTweaks(false)} />}
    </div>
  );
}
