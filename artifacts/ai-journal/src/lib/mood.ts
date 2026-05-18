// Mood states map 1-5 integers to a semantic state with emoji + label.
// The integer is stored in DB (preserves backwards compatibility & enables
// numerical trend analysis), but UI always shows the labelled state.

export interface MoodState {
  value: number; // 1-5
  emoji: string;
  label: string;
  color: string; // tailwind text color class
  bg: string; // tailwind bg color class
}

export const MOOD_STATES: MoodState[] = [
  { value: 5, emoji: "💪", label: "順利突破", color: "text-emerald-600", bg: "bg-emerald-500/10" },
  { value: 4, emoji: "💡", label: "靈光一閃", color: "text-amber-600",   bg: "bg-amber-500/10"   },
  { value: 3, emoji: "😐", label: "推進中",   color: "text-slate-600",   bg: "bg-slate-500/10"   },
  { value: 2, emoji: "🤔", label: "邏輯卡關", color: "text-blue-600",    bg: "bg-blue-500/10"    },
  { value: 1, emoji: "😩", label: "遇到瓶頸", color: "text-rose-600",    bg: "bg-rose-500/10"    },
];

export function getMoodState(value: number | null | undefined): MoodState | null {
  if (value === null || value === undefined) return null;
  return MOOD_STATES.find((s) => s.value === value) ?? null;
}

export function formatMood(value: number | null | undefined): string {
  const s = getMoodState(value);
  return s ? `${s.emoji} ${s.label}` : "";
}
