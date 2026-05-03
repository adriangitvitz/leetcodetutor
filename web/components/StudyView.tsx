"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import type { Problem } from "@/lib/types";
import { StudySheet } from "./StudySheet";
import { Tutor } from "./Tutor";

type Props = {
  problem: Problem;
};

export function StudyView({ problem }: Props) {
  const router = useRouter();

  useEffect(() => {
    const fn = (e: KeyboardEvent) => {
      const tag = (document.activeElement?.tagName ?? "").toUpperCase();
      if (e.key === "Escape" && tag !== "TEXTAREA") {
        e.preventDefault();
        router.push("/");
      }
    };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, [router]);

  return (
    <div className="study">
      <section className="study-pane study-left">
        <StudySheet problem={problem} />
      </section>
      <section className="study-pane study-right">
        <Tutor problem={problem} />
      </section>
    </div>
  );
}
