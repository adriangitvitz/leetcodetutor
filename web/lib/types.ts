export type Problem = {
  slug: string;
  link: string;
  title: string;
  difficulty: "EASY" | "MEDIUM" | "HARD";
  acceptance_rate: number;
  topics: string;
  company_count: number;
  mean_frequency: number;
  max_frequency: number;
  companies: string[];
};

export type Example = {
  input: string;
  output: string;
  explanation?: string;
};

export type Statement = {
  number: number | null;
  description: string;
  examples: Example[];
  constraints: string[];
};

export type Persona = {
  key: "scholar" | "coach" | "sage" | "hacker";
  name: string;
  desc: string;
  openerTeach: string;
  openerSoc: string;
  openerChat: string;
};

export type Explanation = {
  plain: string;
  aha: string;
  strategy: string;
  code: string;
  complexity: { time: string; space: string; tdesc: string; sdesc: string };
  socratic: { q: string; hint: string }[];
};

export type ChatMessage = { role: "user" | "assistant" | "system"; content: string };

export type CompanyEntry = {
  name: string;
  problem_count: number;
  top_topic: string | null;
  top_topic_score: number | null;
  signature_slug: string | null;
  signature_title: string | null;
};

export type CompanyList = { total: number; items: CompanyEntry[] };

export type AskEntry = {
  slug: string;
  title: string;
  difficulty: "EASY" | "MEDIUM" | "HARD";
  topics: string;
  link: string;
  frequency: number;
};

export type CompanyDetailResponse = {
  name: string;
  total_problems: number;
  top_topic: string | null;
  top_topic_score: number;
  avg_frequency: number;
  asks: AskEntry[];
};

export type TopProblem = {
  slug: string;
  title: string;
  difficulty: "EASY" | "MEDIUM" | "HARD";
  topics: string;
  link: string;
  company_count: number;
  mean_frequency: number;
  score: number;
};

export type TopTopic = { name: string; score: number };

export type StatsResponse = {
  top_problems: TopProblem[];
  top_topics: TopTopic[];
  difficulty_mix: { EASY: number; MEDIUM: number; HARD: number };
};
