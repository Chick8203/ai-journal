import { useGetEntriesSummary } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Link } from "wouter";
import { Book, FolderKanban, TrendingUp, Calendar, AlertCircle } from "lucide-react";
import { format } from "date-fns";

export default function Dashboard() {
  const { data: summary, isLoading, isError } = useGetEntriesSummary();

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div>
          <Skeleton className="h-10 w-48 mb-2" />
          <Skeleton className="h-5 w-64" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <AlertCircle className="h-12 w-12 mb-4 text-destructive" />
        <p>無法載入總覽資料</p>
      </div>
    );
  }

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header>
        <h1 className="text-3xl font-serif font-bold text-foreground mb-2">早安，今日的工作狀況如何？</h1>
        <p className="text-muted-foreground">這是您的工作日誌總覽，隨時掌握進度與模式。</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-none shadow-sm bg-card hover-elevate transition-all">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Book className="h-4 w-4" />
              總日誌數
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold font-serif">{summary?.totalEntries || 0}</div>
          </CardContent>
        </Card>

        <Card className="border-none shadow-sm bg-card hover-elevate transition-all">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              連續紀錄天數
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold font-serif text-primary">{summary?.streak || 0}</div>
          </CardContent>
        </Card>

        <Card className="border-none shadow-sm bg-card hover-elevate transition-all">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <FolderKanban className="h-4 w-4" />
              專案總數
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold font-serif">{summary?.totalProjects || 0}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-serif font-semibold">最近的日誌</h2>
            <Link href="/journal" className="text-sm text-primary hover:underline">
              撰寫新日誌
            </Link>
          </div>
          
          <div className="space-y-4">
            {summary?.recentEntries && summary.recentEntries.length > 0 ? (
              summary.recentEntries.map((entry) => (
                <Card key={entry.id} className="border-border shadow-none">
                  <CardHeader className="p-4 pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">{entry.projectName}</CardTitle>
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {format(new Date(entry.date), "yyyy-MM-dd")}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="p-4 pt-2">
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {entry.content || "無內容"}
                    </p>
                  </CardContent>
                </Card>
              ))
            ) : (
              <div className="text-center py-8 border rounded-lg border-dashed">
                <p className="text-muted-foreground">尚無日誌記錄</p>
                <Link href="/journal" className="mt-4 inline-block">
                  <Button variant="outline" size="sm">開始第一篇</Button>
                </Link>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <h2 className="text-xl font-serif font-semibold">專案投入分佈</h2>
          <Card className="border-border shadow-none">
            <CardContent className="p-6">
              {summary?.entriesByProject && summary.entriesByProject.length > 0 ? (
                <div className="space-y-4">
                  {summary.entriesByProject.map((project) => (
                    <div key={project.projectId} className="flex items-center justify-between">
                      <span className="text-sm font-medium">{project.projectName}</span>
                      <div className="flex items-center gap-3">
                        <div className="h-2 w-32 bg-secondary rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-primary" 
                            style={{ 
                              width: `${Math.min(100, (project.count / (summary.totalEntries || 1)) * 100)}%` 
                            }} 
                          />
                        </div>
                        <span className="text-sm text-muted-foreground w-8 text-right">
                          {project.count}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  尚無專案資料
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
