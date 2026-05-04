import { useState } from "react";
import { 
  useAnalyzeBottleneck, 
  useDecomposeGoal,
  useListProjects 
} from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  BrainCircuit, TrendingUp, TrendingDown, Minus, 
  AlertTriangle, Lightbulb, Target, Clock, ListChecks 
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function AIAnalysis() {
  const { data: projects } = useListProjects();
  
  const analyzeBottleneck = useAnalyzeBottleneck();
  const decomposeGoal = useDecomposeGoal();

  // Bottleneck State
  const [analyzeProjectId, setAnalyzeProjectId] = useState<string>("all");
  const [analyzeDays, setAnalyzeDays] = useState<string>("30");

  // Goal State
  const [goalText, setGoalText] = useState("");
  const [goalContext, setGoalContext] = useState("");

  const handleAnalyze = () => {
    analyzeBottleneck.mutate({
      data: {
        projectId: analyzeProjectId === "all" ? null : parseInt(analyzeProjectId),
        days: parseInt(analyzeDays)
      }
    });
  };

  const handleDecompose = () => {
    if (!goalText.trim()) return;
    decomposeGoal.mutate({
      data: {
        goal: goalText,
        context: goalContext.trim() || null
      }
    });
  };

  const renderTrendIcon = (trend: string) => {
    switch (trend) {
      case "improving": return <TrendingUp className="w-5 h-5 text-green-600" />;
      case "declining": return <TrendingDown className="w-5 h-5 text-red-600" />;
      default: return <Minus className="w-5 h-5 text-gray-500" />;
    }
  };

  const renderTrendLabel = (trend: string) => {
    switch (trend) {
      case "improving": return "持續提升";
      case "declining": return "逐漸下滑";
      default: return "穩定持平";
    }
  };

  const formatDerivative = (val: number) => {
    const sign = val > 0 ? "+" : "";
    return `${sign}${val.toFixed(2)}`;
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
      <header>
        <h1 className="text-3xl font-serif font-bold text-foreground mb-2 flex items-center gap-3">
          <BrainCircuit className="w-8 h-8 text-primary" />
          AI 智囊分析
        </h1>
        <p className="text-muted-foreground">透過模式識別尋找瓶頸，或將複雜目標拆解為可執行的步驟。</p>
      </header>

      <Tabs defaultValue="bottleneck" className="w-full">
        <TabsList className="grid w-full grid-cols-2 max-w-[400px]">
          <TabsTrigger value="bottleneck">分析瓶頸</TabsTrigger>
          <TabsTrigger value="goal">目標拆解</TabsTrigger>
        </TabsList>

        <TabsContent value="bottleneck" className="mt-6 space-y-6">
          <Card className="border-border shadow-sm">
            <CardHeader className="pb-4 bg-sidebar/30 border-b border-border">
              <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div className="space-y-4 flex-1">
                  <CardTitle className="text-lg">配置分析範圍</CardTitle>
                  <div className="flex gap-4">
                    <div className="space-y-1.5 flex-1 max-w-[200px]">
                      <Label className="text-xs">分析專案</Label>
                      <Select value={analyzeProjectId} onValueChange={setAnalyzeProjectId}>
                        <SelectTrigger className="bg-card">
                          <SelectValue placeholder="選擇專案" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">所有專案</SelectItem>
                          {projects?.map(p => (
                            <SelectItem key={p.id} value={p.id.toString()}>{p.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5 flex-1 max-w-[150px]">
                      <Label className="text-xs">時間範圍</Label>
                      <Select value={analyzeDays} onValueChange={setAnalyzeDays}>
                        <SelectTrigger className="bg-card">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="7">最近 7 天</SelectItem>
                          <SelectItem value="14">最近 14 天</SelectItem>
                          <SelectItem value="30">最近 30 天</SelectItem>
                          <SelectItem value="90">最近 90 天</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
                <Button 
                  onClick={handleAnalyze} 
                  disabled={analyzeBottleneck.isPending}
                  className="w-full md:w-auto"
                >
                  {analyzeBottleneck.isPending ? "AI 運算中..." : "開始分析瓶頸"}
                </Button>
              </div>
            </CardHeader>
            
            {analyzeBottleneck.isPending ? (
              <CardContent className="p-6 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-24 w-full" />)}
                </div>
                <div className="space-y-3">
                  <Skeleton className="h-6 w-32" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-5/6" />
                  <Skeleton className="h-4 w-full" />
                </div>
              </CardContent>
            ) : analyzeBottleneck.data ? (
              <CardContent className="p-6 space-y-8 animate-in fade-in duration-500">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 rounded-lg bg-secondary/50 border border-border/50 flex flex-col gap-1">
                    <span className="text-xs font-medium text-muted-foreground">效率趨勢</span>
                    <div className="flex items-center gap-2 mt-1">
                      {renderTrendIcon(analyzeBottleneck.data.efficiency.trend)}
                      <span className="font-semibold text-lg">
                        {renderTrendLabel(analyzeBottleneck.data.efficiency.trend)}
                      </span>
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-secondary/50 border border-border/50 flex flex-col gap-1">
                    <span className="text-xs font-medium text-muted-foreground">產出變化率 (一階)</span>
                    <span className={cn(
                      "font-semibold text-xl mt-1",
                      analyzeBottleneck.data.efficiency.firstDerivative > 0 ? "text-green-600" : 
                      analyzeBottleneck.data.efficiency.firstDerivative < 0 ? "text-red-600" : ""
                    )}>
                      {formatDerivative(analyzeBottleneck.data.efficiency.firstDerivative)}
                    </span>
                  </div>
                  <div className="p-4 rounded-lg bg-secondary/50 border border-border/50 flex flex-col gap-1">
                    <span className="text-xs font-medium text-muted-foreground">變化加速度 (二階)</span>
                    <span className={cn(
                      "font-semibold text-xl mt-1",
                      analyzeBottleneck.data.efficiency.secondDerivative > 0 ? "text-green-600" : 
                      analyzeBottleneck.data.efficiency.secondDerivative < 0 ? "text-red-600" : ""
                    )}>
                      {formatDerivative(analyzeBottleneck.data.efficiency.secondDerivative)}
                    </span>
                  </div>
                  <div className="p-4 rounded-lg bg-secondary/50 border border-border/50 flex flex-col gap-1">
                    <span className="text-xs font-medium text-muted-foreground">整體狀態分數</span>
                    <span className="font-semibold text-xl mt-1 text-primary">
                      {analyzeBottleneck.data.efficiency.score}/100
                    </span>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-serif font-semibold mb-3 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-500" />
                    偵測到的瓶頸
                  </h3>
                  <ul className="space-y-2">
                    {analyzeBottleneck.data.bottlenecks.map((b, i) => (
                      <li key={i} className="flex items-start gap-3 p-3 bg-amber-50/50 dark:bg-amber-950/20 text-amber-900 dark:text-amber-200 rounded-md border border-amber-200/50 dark:border-amber-900/50 text-sm">
                        <span className="mt-0.5">•</span>
                        <span className="leading-relaxed">{b}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h3 className="text-lg font-serif font-semibold mb-3 flex items-center gap-2">
                    <Lightbulb className="w-5 h-5 text-primary" />
                    改善建議
                  </h3>
                  <ul className="space-y-2">
                    {analyzeBottleneck.data.suggestions.map((s, i) => (
                      <li key={i} className="flex items-start gap-3 p-3 bg-secondary/50 rounded-md text-sm">
                        <span className="mt-0.5 text-primary">•</span>
                        <span className="leading-relaxed">{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="p-4 bg-muted rounded-lg text-sm leading-relaxed border border-border">
                  <span className="font-semibold block mb-1">AI 總結：</span>
                  {analyzeBottleneck.data.summary}
                </div>
              </CardContent>
            ) : (
              <CardContent className="p-12 text-center text-muted-foreground flex flex-col items-center justify-center">
                <BrainCircuit className="w-12 h-12 mb-4 opacity-20" />
                <p>配置條件後點擊「開始分析瓶頸」以獲取 AI 洞察報告</p>
              </CardContent>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="goal" className="mt-6 space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-2 space-y-4">
              <Card className="border-border shadow-sm">
                <CardHeader className="pb-4 bg-sidebar/30 border-b border-border">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Target className="w-5 h-5" /> 
                    輸入巨大目標
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 space-y-4">
                  <div className="space-y-2">
                    <Label>你想完成什麼大目標？</Label>
                    <Textarea 
                      value={goalText}
                      onChange={(e) => setGoalText(e.target.value)}
                      placeholder="例如：建立一個新的個人部落格系統，包含文章管理和會員訂閱功能..."
                      className="min-h-[120px] resize-y bg-card"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>補充背景資訊 (可選)</Label>
                    <Textarea 
                      value={goalContext}
                      onChange={(e) => setGoalContext(e.target.value)}
                      placeholder="你的技術棧、限制條件、或者任何相關的上下文..."
                      className="min-h-[80px] resize-y bg-card"
                    />
                  </div>
                  <Button 
                    className="w-full" 
                    onClick={handleDecompose}
                    disabled={decomposeGoal.isPending || !goalText.trim()}
                  >
                    {decomposeGoal.isPending ? "AI 拆解中..." : "開始拆解目標"}
                  </Button>
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-3">
              <Card className="border-border shadow-sm h-full">
                {decomposeGoal.isPending ? (
                  <CardContent className="p-8 flex flex-col items-center justify-center h-full min-h-[400px] space-y-6">
                    <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center animate-pulse">
                      <BrainCircuit className="w-8 h-8 text-primary" />
                    </div>
                    <div className="space-y-2 w-full max-w-sm">
                      <Skeleton className="h-4 w-full" />
                      <Skeleton className="h-4 w-5/6 mx-auto" />
                    </div>
                    <p className="text-sm text-muted-foreground animate-pulse">正在構思執行步驟...</p>
                  </CardContent>
                ) : decomposeGoal.data ? (
                  <>
                    <CardHeader className="pb-4 border-b border-border bg-sidebar/30">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg">拆解結果：{decomposeGoal.data.goal}</CardTitle>
                        <div className="flex items-center gap-2 text-sm font-medium bg-primary/10 text-primary px-3 py-1 rounded-full">
                          <Clock className="w-4 h-4" />
                          總預估時間: {decomposeGoal.data.totalEstimatedTime}
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="divide-y divide-border">
                        {decomposeGoal.data.steps.map((step) => (
                          <div key={step.stepNumber} className="p-6 hover:bg-secondary/20 transition-colors flex gap-4">
                            <div className="flex-shrink-0 mt-1">
                              <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-sm">
                                {step.stepNumber}
                              </div>
                            </div>
                            <div className="flex-1 space-y-2">
                              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                <h4 className="font-bold text-base">{step.title}</h4>
                                <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5 px-2 py-0.5 bg-secondary rounded-sm w-fit">
                                  <Clock className="w-3 h-3" />
                                  {step.estimatedTime}
                                </span>
                              </div>
                              <p className="text-sm text-foreground/80 leading-relaxed">
                                {step.description}
                              </p>
                              <div className="flex items-start gap-2 mt-3 p-3 bg-muted/50 rounded border border-border/50 text-sm">
                                <ListChecks className="w-4 h-4 mt-0.5 text-primary flex-shrink-0" />
                                <div>
                                  <span className="font-semibold block mb-0.5 text-xs text-muted-foreground">產出物 / 驗收標準：</span>
                                  {step.deliverable}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </>
                ) : (
                  <CardContent className="p-12 text-center text-muted-foreground flex flex-col items-center justify-center h-full min-h-[400px]">
                    <Target className="w-12 h-12 mb-4 opacity-20" />
                    <p>輸入您的目標，AI 將為您規劃清晰的執行步驟 (SOP)</p>
                  </CardContent>
                )}
              </Card>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
