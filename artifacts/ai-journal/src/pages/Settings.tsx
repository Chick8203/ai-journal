import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useToast } from "@/hooks/use-toast";
import { KeyRound, Bot, Cpu, CheckCircle2, CircleDot } from "lucide-react";
import { cn } from "@/lib/utils";

interface AISettingsData {
  ai_provider: string;
  gemini_api_key_set: boolean;
  openai_api_key_set: boolean;
  gemini_api_key_preview: string | null;
  openai_api_key_preview: string | null;
}

export default function Settings() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [provider, setProvider] = useState("replit");
  const [geminiKey, setGeminiKey] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [serverData, setServerData] = useState<AISettingsData | null>(null);

  useEffect(() => {
    fetch("/api/settings/ai")
      .then((r) => r.json())
      .then((data: AISettingsData) => {
        setServerData(data);
        setProvider(data.ai_provider);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const body: Record<string, string | null> = { ai_provider: provider };
      if (geminiKey.trim()) body.gemini_api_key = geminiKey.trim();
      else if (geminiKey === "") body.gemini_api_key = null;
      if (openaiKey.trim()) body.openai_api_key = openaiKey.trim();
      else if (openaiKey === "") body.openai_api_key = null;

      const res = await fetch("/api/settings/ai", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Failed to save");
      const updated: AISettingsData = await res.json();
      setServerData(updated);
      setGeminiKey("");
      setOpenaiKey("");
      toast({ title: "設定已儲存", description: "AI 提供者設定更新成功" });
    } catch {
      toast({ title: "儲存失敗", description: "請稍後再試", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const clearKey = async (keyName: "gemini_api_key" | "openai_api_key") => {
    setSaving(true);
    try {
      await fetch("/api/settings/ai", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ai_provider: provider, [keyName]: "" }),
      });
      const res = await fetch("/api/settings/ai");
      const updated: AISettingsData = await res.json();
      setServerData(updated);
      toast({ title: "金鑰已清除" });
    } catch {
      toast({ title: "操作失敗", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
        載入中...
      </div>
    );
  }

  const providers = [
    {
      id: "replit",
      label: "Replit 內建 Gemini",
      description: "使用 Replit AI 代理，無需自備金鑰，費用計入 Replit 點數",
      icon: <Cpu className="w-5 h-5" />,
    },
    {
      id: "gemini",
      label: "Google Gemini（自備金鑰）",
      description: "使用你自己的 Google AI Studio API 金鑰",
      icon: <Bot className="w-5 h-5" />,
    },
    {
      id: "openai",
      label: "OpenAI ChatGPT（自備金鑰）",
      description: "使用你自己的 OpenAI API 金鑰，模型為 gpt-4o-mini",
      icon: <KeyRound className="w-5 h-5" />,
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-serif font-bold">設定</h2>
        <p className="text-muted-foreground mt-1 text-sm">管理 AI 分析功能的提供者與 API 金鑰</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">AI 提供者</CardTitle>
          <CardDescription>選擇 AI 分析功能要使用的服務</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <RadioGroup value={provider} onValueChange={setProvider} className="space-y-3">
            {providers.map((p) => (
              <label
                key={p.id}
                className={cn(
                  "flex items-start gap-4 p-4 rounded-lg border cursor-pointer transition-colors",
                  provider === p.id
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-muted-foreground/40"
                )}
              >
                <RadioGroupItem value={p.id} className="mt-0.5" />
                <div className="flex items-start gap-3 flex-1">
                  <span className="text-muted-foreground mt-0.5">{p.icon}</span>
                  <div>
                    <div className="font-medium text-sm">{p.label}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{p.description}</div>
                  </div>
                </div>
              </label>
            ))}
          </RadioGroup>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">API 金鑰</CardTitle>
          <CardDescription>
            金鑰儲存在本地資料庫，不會對外傳送。留白表示不變更現有金鑰。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="gemini-key">Google Gemini API 金鑰</Label>
              {serverData?.gemini_api_key_set && (
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1 text-xs text-green-600">
                    <CheckCircle2 className="w-3 h-3" /> 已設定
                  </span>
                  <button
                    onClick={() => clearKey("gemini_api_key")}
                    className="text-xs text-destructive hover:underline"
                  >
                    清除
                  </button>
                </div>
              )}
            </div>
            {serverData?.gemini_api_key_preview && (
              <p className="text-xs text-muted-foreground font-mono bg-muted px-2 py-1 rounded">
                {serverData.gemini_api_key_preview}
              </p>
            )}
            <Input
              id="gemini-key"
              type="password"
              placeholder={
                serverData?.gemini_api_key_set
                  ? "輸入新金鑰以替換現有金鑰"
                  : "AIza..."
              }
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              取得金鑰：
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noopener noreferrer"
                className="underline ml-1"
              >
                Google AI Studio
              </a>
            </p>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="openai-key">OpenAI API 金鑰</Label>
              {serverData?.openai_api_key_set && (
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1 text-xs text-green-600">
                    <CheckCircle2 className="w-3 h-3" /> 已設定
                  </span>
                  <button
                    onClick={() => clearKey("openai_api_key")}
                    className="text-xs text-destructive hover:underline"
                  >
                    清除
                  </button>
                </div>
              )}
            </div>
            {serverData?.openai_api_key_preview && (
              <p className="text-xs text-muted-foreground font-mono bg-muted px-2 py-1 rounded">
                {serverData.openai_api_key_preview}
              </p>
            )}
            <Input
              id="openai-key"
              type="password"
              placeholder={
                serverData?.openai_api_key_set
                  ? "輸入新金鑰以替換現有金鑰"
                  : "sk-..."
              }
              value={openaiKey}
              onChange={(e) => setOpenaiKey(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              取得金鑰：
              <a
                href="https://platform.openai.com/api-keys"
                target="_blank"
                rel="noopener noreferrer"
                className="underline ml-1"
              >
                OpenAI Platform
              </a>
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? "儲存中..." : "儲存設定"}
        </Button>
      </div>
    </div>
  );
}
