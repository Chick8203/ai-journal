import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Sparkles, Loader2, Calendar, Heart, FolderKanban, Database, RefreshCcw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiFetch } from "@/lib/api";
import { format } from "date-fns";

interface RelatedEntry {
  id: number;
  date: string;
  content: string;
  mood: number | null;
  projectName: string;
  similarity: number;
}

interface RetrospectResponse {
  synthesis: string;
  related: RelatedEntry[];
  indexed: number;
}

interface BackfillResponse {
  backfilled: number;
  indexed: number;
  total: number;
  provider: string;
  model: string;
}

const EXAMPLE_QUERIES = [
  "我之前是怎麼解決資料類別不平衡的問題的？",
  "上次卡關時我用了什麼方法突破？",
  "我最近一直在思考的是什麼？",
  "回顧一下我這個月的成長",
];

export default function Retrospect() {
  const { toast } = useToast();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [backfilling, setBackfilling] = useState(false);
  const [result, setResult] = useState<RetrospectResponse | null>(null);

  const handleSearch = async () => {
    const q = query.trim();
    if (!q || loading) return;
    setLoading(true);
    setResult(null);
    try {
      const data = await apiFetch<RetrospectResponse>("/api/ai/retrospect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, topK: 5 }),
      });
      setResult(data);
    } catch {
      toast({ title: "回溯失敗", description: "請稍後再試或確認 AI 設定", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const handleBackfill = async () => {
    setBackfilling(true);
    try {
      const data = await apiFetch<BackfillResponse>("/api/ai/embeddings/backfill?limit=500", {
        method: "POST",
      });
      toast({
        title: "索引更新完成",
        description: `本次新建 ${data.backfilled} 篇，共 ${data.indexed}/${data.total} 篇已索引（${data.provider}）`,
      });
    } catch {
      toast({ title: "索引失敗", variant: "destructive" });
    } finally {
      setBackfilling(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary" />
            跨時空對話
          </h2>
          <p className="text-muted-foreground mt-1 text-sm">
            問一個問題，讓 AI 從你過去的日誌中找出相關記憶並給出綜合建議。
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleBackfill}
          disabled={backfilling}
          className="shrink-0"
          title="為所有尚未建立索引的日誌生成向量（切換 AI 提供者後需重新索引）"
        >
          {backfilling ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
          ) : (
            <RefreshCcw className="w-3.5 h-3.5 mr-1.5" />
          )}
          重建索引
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">提出問題</CardTitle>
          <CardDescription>
            像跟自己對話一樣描述你想問的事情，AI 會找出 5 篇最相關的歷史日誌。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="例如：我之前在做專案時，是怎麼安排優先順序的？"
            rows={3}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                handleSearch();
              }
            }}
          />

          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUERIES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => setQuery(ex)}
                className="text-xs px-2.5 py-1 rounded-full border border-border text-muted-foreground hover:text-foreground hover:border-muted-foreground/40 transition-colors"
              >
                {ex}
              </button>
            ))}
          </div>

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">提示：Ctrl/⌘ + Enter 快速送出</p>
            <Button onClick={handleSearch} disabled={loading || !query.trim()}>
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                  回溯中...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-1.5" />
                  啟動回溯
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {result && (
        <>
          <Card className="bg-primary/5 border-primary/20">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-primary" />
                AI 綜合建議
              </CardTitle>
              <CardDescription className="flex items-center gap-1 text-xs">
                <Database className="w-3 h-3" />
                已從 {result.indexed} 篇已索引日誌中找出 {result.related.length} 篇相關內容
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="prose prose-sm max-w-none text-foreground whitespace-pre-wrap leading-relaxed">
                {result.synthesis}
              </div>
            </CardContent>
          </Card>

          {result.related.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-muted-foreground">相關歷史日誌</h3>
              {result.related.map((entry) => (
                <Card key={entry.id} className="hover:border-primary/40 transition-colors">
                  <CardContent className="pt-5 pb-4 space-y-2">
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {format(new Date(entry.date), "yyyy-MM-dd")}
                      </span>
                      <span className="flex items-center gap-1">
                        <FolderKanban className="w-3 h-3" />
                        {entry.projectName}
                      </span>
                      {entry.mood !== null && (
                        <span className="flex items-center gap-1">
                          <Heart className="w-3 h-3" />
                          {entry.mood}/5
                        </span>
                      )}
                      <span className="ml-auto px-2 py-0.5 rounded-full bg-primary/10 text-primary font-mono">
                        相似度 {(entry.similarity * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-sm text-foreground/90 whitespace-pre-wrap line-clamp-4">
                      {entry.content}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {!result && !loading && (
        <div className="text-center py-16 text-muted-foreground text-sm">
          <Sparkles className="w-10 h-10 mx-auto opacity-30 mb-3" />
          <p>輸入問題後，AI 會從你所有日誌中找出最相關的記憶。</p>
          <p className="text-xs mt-2">
            第一次使用時會自動為現有日誌建立向量索引（可能需要幾秒鐘）。
          </p>
        </div>
      )}
    </div>
  );
}
