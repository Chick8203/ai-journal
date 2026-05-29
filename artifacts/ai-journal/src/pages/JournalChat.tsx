import { useState, useEffect, useMemo, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  MessageCircle,
  Send,
  Loader2,
  Sparkles,
  RefreshCcw,
  Check,
  X,
  Bot,
  User,
  Search,
  Target,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  Lightbulb,
  Clock,
  Package,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { MOOD_STATES } from "@/lib/mood";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface DraftEntry {
  title: string;
  content: string;
  mood: number;
  tags: string[];
  suggestedProjectId: number | null;
}

interface BottleneckResult {
  efficiency: { trend: "improving" | "declining" | "stable"; score: number };
  bottlenecks: string[];
  suggestions: string[];
  summary: string;
}

interface DecomposeStep {
  stepNumber: number;
  title: string;
  description: string;
  estimatedTime: string;
  deliverable: string;
}

interface DecomposeResult {
  goal: string;
  steps: DecomposeStep[];
  totalEstimatedTime: string;
}

interface ChatResponse {
  action: "ask" | "draft" | "bottleneck" | "decompose";
  message: string;
  draft?: DraftEntry;
  result?: BottleneckResult | DecomposeResult;
}

interface Project {
  id: number;
  name: string;
}

const OPENING_MESSAGE =
  "嗨 👋 我是你的 AI 助理。跟我聊聊吧 — 你可以記今天的日誌、請我分析某段時間的瓶頸（例如「分析這個禮拜的瓶頸」）、或一起拆解一個目標，我會根據你說的內容自動調整。";

// LocalStorage persistence ----------------------------------------------------
const STORAGE_KEY = "ai-journal-chat-state-v1";

interface PersistedState {
  messages: ChatMessage[];
  draft: DraftEntry | null;
  draftTitle: string;
  draftContent: string;
  draftMood: number;
  draftTags: string;
  draftProjectId: number | null;
  draftSaved: boolean;
  bottleneck: BottleneckResult | null;
  decompose: DecomposeResult | null;
}

const DEFAULT_STATE: PersistedState = {
  messages: [{ role: "assistant", content: OPENING_MESSAGE }],
  draft: null,
  draftTitle: "",
  draftContent: "",
  draftMood: 3,
  draftTags: "",
  draftProjectId: null,
  draftSaved: false,
  bottleneck: null,
  decompose: null,
};

function loadPersistedState(): PersistedState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_STATE;
    const parsed = JSON.parse(raw);
    return { ...DEFAULT_STATE, ...parsed };
  } catch {
    return DEFAULT_STATE;
  }
}

function savePersistedState(state: PersistedState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // localStorage might be full or disabled; silent fail is fine
  }
}

export default function JournalChat() {
  const { toast } = useToast();
  // Load persisted state once on mount
  const initial = useMemo(loadPersistedState, []);

  const [projects, setProjects] = useState<Project[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>(initial.messages);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Draft state
  const [draft, setDraft] = useState<DraftEntry | null>(initial.draft);
  const [draftProjectId, setDraftProjectId] = useState<number | null>(initial.draftProjectId);
  const [draftTitle, setDraftTitle] = useState(initial.draftTitle);
  const [draftContent, setDraftContent] = useState(initial.draftContent);
  const [draftMood, setDraftMood] = useState(initial.draftMood);
  const [draftTags, setDraftTags] = useState(initial.draftTags);
  const [draftSaved, setDraftSaved] = useState(initial.draftSaved);
  const [saving, setSaving] = useState(false);

  // Result state for bottleneck / decompose
  const [bottleneck, setBottleneck] = useState<BottleneckResult | null>(initial.bottleneck);
  const [decompose, setDecompose] = useState<DecomposeResult | null>(initial.decompose);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-persist on every relevant state change
  useEffect(() => {
    savePersistedState({
      messages,
      draft,
      draftTitle,
      draftContent,
      draftMood,
      draftTags,
      draftProjectId,
      draftSaved,
      bottleneck,
      decompose,
    });
  }, [
    messages,
    draft,
    draftTitle,
    draftContent,
    draftMood,
    draftTags,
    draftProjectId,
    draftSaved,
    bottleneck,
    decompose,
  ]);

  useEffect(() => {
    apiFetch<Project[]>("/api/projects")
      .then((data) => setProjects(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, draft, bottleneck, decompose]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    const newMessages: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages(newMessages);
    setLoading(true);
    try {
      const data = await apiFetch<ChatResponse>("/api/ai/journal-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: newMessages,
          mode: "auto",
          projects: projects.map((p) => ({ id: p.id, name: p.name })),
          days: 0,
        }),
      });
      setMessages((prev) => [...prev, { role: "assistant", content: data.message }]);

      if (data.action === "draft" && data.draft) {
        setDraft(data.draft);
        setDraftSaved(false); // new draft is unsaved by default
        setDraftTitle(data.draft.title || "");
        setDraftContent(data.draft.content);
        setDraftMood(data.draft.mood);
        setDraftTags(data.draft.tags.join(", "));
        setDraftProjectId(
          data.draft.suggestedProjectId !== null && data.draft.suggestedProjectId !== undefined
            ? data.draft.suggestedProjectId
            : projects[0]?.id ?? null
        );
      } else if (data.action === "bottleneck" && data.result) {
        setBottleneck(data.result as BottleneckResult);
      } else if (data.action === "decompose" && data.result) {
        setDecompose(data.result as DecomposeResult);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ 我這邊出了一點問題，要不要再試一次？" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!draft || !draftProjectId) {
      toast({ title: "請選擇要儲存到哪個專案", variant: "destructive" });
      return;
    }
    setSaving(true);
    try {
      const tags = draftTags
        .split(/[,，、]/)
        .map((t) => t.trim())
        .filter(Boolean);
      await apiFetch("/api/entries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: format(new Date(), "yyyy-MM-dd"),
          title: draftTitle.trim() || null,
          content: draftContent,
          projectId: draftProjectId,
          template: "freeform",
          mood: draftMood,
          tags,
        }),
      });
      toast({ title: "✅ 日誌已儲存", description: "可以到「撰寫日誌」或專案頁查看" });
      setDraftSaved(true);
      // Keep the card visible (don't reset). User can close via the X button.
    } catch {
      toast({ title: "儲存失敗", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setMessages([{ role: "assistant", content: OPENING_MESSAGE }]);
    setInput("");
    setDraft(null);
    setDraftSaved(false);
    setDraftTitle("");
    setDraftContent("");
    setDraftMood(3);
    setDraftTags("");
    setDraftProjectId(null);
    setBottleneck(null);
    setDecompose(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
            <MessageCircle className="w-6 h-6 text-primary" />
            AI 對話
          </h2>
          <p className="text-muted-foreground mt-1 text-sm">
            跟 AI 聊聊，依照你的描述自動整理成日誌、分析瓶頸或拆解目標。
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleReset} className="shrink-0">
          <RefreshCcw className="w-3.5 h-3.5 mr-1.5" />
          重新開始
        </Button>
      </div>

      <Card className="overflow-hidden">
        <div
          ref={scrollRef}
          className="max-h-[480px] overflow-y-auto p-5 space-y-4 bg-muted/30"
        >
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={cn(
                "flex gap-3",
                m.role === "user" ? "flex-row-reverse" : "flex-row"
              )}
            >
              <div
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                  m.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-card border border-border"
                )}
              >
                {m.role === "user" ? (
                  <User className="w-4 h-4" />
                ) : (
                  <Bot className="w-4 h-4 text-primary" />
                )}
              </div>
              <div
                className={cn(
                  "max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap",
                  m.role === "user"
                    ? "bg-primary text-primary-foreground rounded-tr-sm"
                    : "bg-card border border-border rounded-tl-sm"
                )}
              >
                {m.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-card border border-border flex items-center justify-center">
                <Bot className="w-4 h-4 text-primary" />
              </div>
              <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3">
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-border bg-card p-4">
          <div className="flex gap-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="輸入訊息... (Enter 送出，Shift+Enter 換行)"
              rows={2}
              disabled={loading}
              className="resize-none"
            />
            <Button onClick={handleSend} disabled={loading || !input.trim()} className="shrink-0">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </Card>

      {draft && (
        <Card className={cn(
          "border-primary/30",
          draftSaved ? "bg-emerald-500/5 border-emerald-500/30" : "bg-primary/5"
        )}>
          <CardHeader>
            <div className="flex items-start justify-between gap-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Sparkles className={cn("w-4 h-4", draftSaved ? "text-emerald-600" : "text-primary")} />
                日誌草稿
                {draftSaved && (
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
                    <Check className="w-3 h-3" /> 已儲存
                  </span>
                )}
              </CardTitle>
              <button
                type="button"
                onClick={() => { setDraft(null); setDraftSaved(false); }}
                disabled={saving}
                className="text-muted-foreground hover:text-foreground p-1 -mt-1 -mr-1 rounded transition-colors disabled:opacity-50"
                title="關閉草稿（繼續對話）"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="draft-title">標題</Label>
              <Input
                id="draft-title"
                value={draftTitle}
                onChange={(e) => setDraftTitle(e.target.value)}
                maxLength={80}
                placeholder="一句話總結這篇日誌"
                className="bg-card"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="draft-content">內容</Label>
              <Textarea
                id="draft-content"
                value={draftContent}
                onChange={(e) => setDraftContent(e.target.value)}
                rows={10}
                className="bg-card"
              />
              <p className="text-xs text-muted-foreground">
                你可以直接編輯，AI 整理的版本不一定完美
              </p>
            </div>

            <div className="space-y-2">
              <Label>當下狀態</Label>
              <div className="flex flex-wrap gap-2">
                {MOOD_STATES.map((m) => {
                  const active = draftMood === m.value;
                  return (
                    <button
                      key={m.value}
                      type="button"
                      onClick={() => setDraftMood(m.value)}
                      className={cn(
                        "flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-sm transition-colors select-none",
                        active
                          ? cn("border-primary font-medium", m.bg, m.color)
                          : "border-border bg-card text-muted-foreground hover:border-muted-foreground/50 hover:text-foreground"
                      )}
                    >
                      <span>{m.emoji}</span>
                      <span>{m.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>專案</Label>
                <Select
                  value={draftProjectId?.toString() ?? ""}
                  onValueChange={(v) => setDraftProjectId(Number(v))}
                >
                  <SelectTrigger className="bg-card">
                    <SelectValue placeholder="選擇專案" />
                  </SelectTrigger>
                  <SelectContent>
                    {projects.map((p) => (
                      <SelectItem key={p.id} value={p.id.toString()}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>標籤（逗號分隔）</Label>
                <Input
                  value={draftTags}
                  onChange={(e) => setDraftTags(e.target.value)}
                  placeholder="例如：工作, 反思, 學習"
                  className="bg-card"
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button
                onClick={handleSaveDraft}
                disabled={saving || !draftProjectId || draftSaved}
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                ) : (
                  <Check className="w-4 h-4 mr-1.5" />
                )}
                {draftSaved ? "已儲存" : "儲存為日誌"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {bottleneck && (
        <Card className="bg-primary/5 border-primary/30">
          <CardHeader>
            <div className="flex items-start justify-between gap-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Search className="w-4 h-4 text-primary" />
                瓶頸分析結果
              </CardTitle>
              <button
                type="button"
                onClick={() => setBottleneck(null)}
                className="text-muted-foreground hover:text-foreground p-1 -mt-1 -mr-1 rounded transition-colors"
                title="關閉結果（繼續對話）"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-center gap-4 p-4 rounded-lg bg-card border border-border">
              <div className="flex-shrink-0">
                {bottleneck.efficiency.trend === "improving" ? (
                  <TrendingUp className="w-8 h-8 text-emerald-500" />
                ) : bottleneck.efficiency.trend === "declining" ? (
                  <TrendingDown className="w-8 h-8 text-rose-500" />
                ) : (
                  <Minus className="w-8 h-8 text-slate-500" />
                )}
              </div>
              <div className="flex-1">
                <div className="text-xs text-muted-foreground">效率評分</div>
                <div className="text-2xl font-bold">{Math.round(bottleneck.efficiency.score)}<span className="text-base text-muted-foreground">/100</span></div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  趨勢：
                  {bottleneck.efficiency.trend === "improving"
                    ? "改善中"
                    : bottleneck.efficiency.trend === "declining"
                    ? "下降中"
                    : "穩定"}
                </div>
              </div>
            </div>

            {bottleneck.summary && (
              <p className="text-sm leading-relaxed bg-card border border-border rounded-lg p-4">
                {bottleneck.summary}
              </p>
            )}

            {bottleneck.bottlenecks.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-medium flex items-center gap-1.5 text-rose-700 dark:text-rose-400">
                  <AlertCircle className="w-3.5 h-3.5" /> 找到的瓶頸
                </h3>
                <ul className="space-y-1.5">
                  {bottleneck.bottlenecks.map((b, i) => (
                    <li key={i} className="text-sm flex gap-2 pl-2">
                      <span className="text-rose-500 shrink-0">•</span>
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {bottleneck.suggestions.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-medium flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400">
                  <Lightbulb className="w-3.5 h-3.5" /> 具體建議
                </h3>
                <ul className="space-y-1.5">
                  {bottleneck.suggestions.map((s, i) => (
                    <li key={i} className="text-sm flex gap-2 pl-2">
                      <span className="text-emerald-500 shrink-0">•</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {decompose && (
        <Card className="bg-primary/5 border-primary/30">
          <CardHeader>
            <div className="flex items-start justify-between gap-2">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <Target className="w-4 h-4 text-primary" />
                  {decompose.goal || "目標拆解結果"}
                </CardTitle>
                {decompose.totalEstimatedTime && (
                  <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                    <Clock className="w-3 h-3" /> 總預估時間：{decompose.totalEstimatedTime}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => setDecompose(null)}
                className="text-muted-foreground hover:text-foreground p-1 -mt-1 -mr-1 rounded transition-colors"
                title="關閉結果（繼續對話）"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {decompose.steps.map((s) => (
              <div
                key={s.stepNumber}
                className="border border-border bg-card rounded-lg p-4 space-y-2"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-7 h-7 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-medium">
                    {s.stepNumber}
                  </div>
                  <div className="flex-1 space-y-1">
                    <h4 className="text-sm font-semibold">{s.title}</h4>
                    {s.description && (
                      <p className="text-sm text-muted-foreground leading-relaxed">{s.description}</p>
                    )}
                    <div className="flex flex-wrap gap-3 text-xs text-muted-foreground pt-1">
                      {s.estimatedTime && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" /> {s.estimatedTime}
                        </span>
                      )}
                      {s.deliverable && (
                        <span className="flex items-center gap-1">
                          <Package className="w-3 h-3" /> {s.deliverable}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
