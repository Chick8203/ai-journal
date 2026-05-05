import { useState } from "react";
import {
  useListProjects,
  useCreateProject,
  useDeleteProject,
  useUpdateProjectStatus,
  useGetProjectEntries,
  CreateProjectBodyCategory,
  ListProjectsStatus,
  UpdateProjectBodyStatus,
  type Project,
  type Entry,
} from "@workspace/api-client-react";
import { useToast } from "@/hooks/use-toast";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import {
  FolderKanban, Trash2, Code, Briefcase, Layout,
  CheckCircle2, Archive, RotateCcw, AlignLeft, CalendarIcon,
  ChevronRight, X,
} from "lucide-react";
import { format } from "date-fns";

function hexToRgba(hex: string, alpha: number): string {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  if (isNaN(r) || isNaN(g) || isNaN(b)) return `rgba(100,100,100,${alpha})`;
  return `rgba(${r},${g},${b},${alpha})`;
}

const STATUS_TABS = [
  { value: ListProjectsStatus.active, label: "進行中" },
  { value: ListProjectsStatus.completed, label: "已完工" },
  { value: ListProjectsStatus.archived, label: "已封存" },
] as const;

function EntryDetailDialog({
  entry,
  onClose,
}: {
  entry: Entry;
  onClose: () => void;
}) {
  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] flex flex-col p-0 gap-0">
        <DialogHeader className="p-6 border-b border-border shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <CalendarIcon className="w-3 h-3" />
                {format(new Date(entry.date), "yyyy-MM-dd")}
              </span>
              {entry.mood && (
                <span className="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded-md font-medium">
                  心情 {entry.mood}/5
                </span>
              )}
              <span className="text-xs px-2 py-0.5 bg-secondary rounded-md text-muted-foreground">
                {entry.template === "engineering" ? "工程開發" : entry.template === "office" ? "一般辦公" : "自由格式"}
              </span>
            </div>
          </div>
          <DialogTitle className="sr-only">日誌詳情</DialogTitle>
          <DialogDescription className="sr-only">完整日誌內容</DialogDescription>
        </DialogHeader>
        <ScrollArea className="flex-1 p-6">
          <pre className="text-sm text-foreground whitespace-pre-wrap leading-relaxed font-sans">
            {entry.content}
          </pre>
          {entry.tags && entry.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-6 pt-4 border-t border-border">
              {entry.tags.map((tag) => (
                <span
                  key={tag.id}
                  className="inline-flex items-center text-[11px] font-medium px-2 py-0.5 rounded-full"
                  style={{
                    backgroundColor: hexToRgba(tag.color, 0.15),
                    color: tag.color,
                    border: `1px solid ${hexToRgba(tag.color, 0.35)}`,
                  }}
                >
                  {tag.name}
                </span>
              ))}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}

function ProjectEntriesSheet({
  project,
  open,
  onClose,
}: {
  project: Project;
  open: boolean;
  onClose: () => void;
}) {
  const [selectedEntry, setSelectedEntry] = useState<Entry | null>(null);
  const { data: entries, isLoading } = useGetProjectEntries(
    project.id,
    { query: { enabled: open } }
  );

  return (
    <>
      <Sheet open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
        <SheetContent className="sm:max-w-2xl w-full flex flex-col p-0 border-l">
          <SheetHeader className="p-6 border-b border-border bg-sidebar/50">
            <SheetTitle className="font-serif text-2xl">{project.name}</SheetTitle>
            <SheetDescription>
              {project.description || "無描述"} · 共 {project.entryCount} 篇日誌
            </SheetDescription>
          </SheetHeader>
          <ScrollArea className="flex-1 p-6">
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => <Skeleton key={i} className="h-24 w-full" />)}
              </div>
            ) : !entries?.length ? (
              <div className="text-center py-20 border rounded-lg border-dashed">
                <AlignLeft className="h-10 w-10 mx-auto text-muted-foreground mb-3 opacity-40" />
                <p className="text-muted-foreground">此專案尚無日誌記錄。</p>
              </div>
            ) : (
              <div className="space-y-3">
                {entries.map((entry) => (
                  <div
                    key={entry.id}
                    onClick={() => setSelectedEntry(entry)}
                    className="border rounded-lg p-4 bg-card hover:border-primary/40 hover:bg-accent/30 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <CalendarIcon className="w-3 h-3" />
                          {format(new Date(entry.date), "yyyy-MM-dd")}
                        </span>
                        {entry.mood && (
                          <span className="text-xs px-1.5 py-0.5 bg-primary/10 text-primary rounded">
                            心情 {entry.mood}/5
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                        點擊閱讀全文 <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>
                    <p className="text-sm text-foreground line-clamp-3 whitespace-pre-wrap leading-relaxed">
                      {entry.content}
                    </p>
                    {entry.tags && entry.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {entry.tags.map((tag) => (
                          <span
                            key={tag.id}
                            className="inline-flex items-center text-[11px] font-medium px-2 py-0.5 rounded-full"
                            style={{
                              backgroundColor: hexToRgba(tag.color, 0.15),
                              color: tag.color,
                              border: `1px solid ${hexToRgba(tag.color, 0.35)}`,
                            }}
                          >
                            {tag.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {selectedEntry && (
        <EntryDetailDialog
          entry={selectedEntry}
          onClose={() => setSelectedEntry(null)}
        />
      )}
    </>
  );
}

export default function Projects() {
  const { toast } = useToast();
  const [statusFilter, setStatusFilter] = useState<ListProjectsStatus>(ListProjectsStatus.active);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newProject, setNewProject] = useState({
    name: "",
    description: "",
    category: CreateProjectBodyCategory.engineering as CreateProjectBodyCategory,
  });

  const { data: projects, isLoading, refetch } = useListProjects({ status: statusFilter });
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();
  const updateStatus = useUpdateProjectStatus();

  const handleCreate = async () => {
    if (!newProject.name) {
      toast({ title: "請填寫專案名稱", variant: "destructive" });
      return;
    }
    try {
      await createProject.mutateAsync({ data: newProject });
      toast({ title: "專案建立成功" });
      setIsDialogOpen(false);
      setNewProject({ name: "", description: "", category: CreateProjectBodyCategory.engineering });
      refetch();
    } catch {
      toast({ title: "建立失敗", variant: "destructive" });
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("確定要刪除此專案嗎？這將同時刪除所有相關日誌。")) {
      try {
        await deleteProject.mutateAsync({ projectId: id });
        toast({ title: "專案已刪除" });
        refetch();
      } catch {
        toast({ title: "刪除失敗", variant: "destructive" });
      }
    }
  };

  const handleStatusChange = async (
    id: number,
    status: UpdateProjectBodyStatus,
    e: React.MouseEvent
  ) => {
    e.stopPropagation();
    try {
      await updateStatus.mutateAsync({ projectId: id, data: { status } });
      const messages: Record<UpdateProjectBodyStatus, string> = {
        completed: "專案已標記為完工 ✓",
        archived: "專案已封存",
        active: "專案已恢復進行中",
      };
      toast({ title: messages[status] });
      refetch();
    } catch {
      toast({ title: "操作失敗", variant: "destructive" });
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "engineering": return <Code className="h-4 w-4" />;
      case "office": return <Briefcase className="h-4 w-4" />;
      default: return <Layout className="h-4 w-4" />;
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case "engineering": return "工程開發";
      case "office": return "一般辦公";
      default: return "一般";
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <Badge variant="secondary" className="bg-emerald-500/15 text-emerald-600 border-emerald-500/30 text-xs">已完工</Badge>;
      case "archived":
        return <Badge variant="secondary" className="bg-muted text-muted-foreground text-xs">已封存</Badge>;
      default:
        return <Badge variant="secondary" className="bg-blue-500/15 text-blue-600 border-blue-500/30 text-xs">進行中</Badge>;
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <header>
          <h1 className="text-3xl font-serif font-bold text-foreground mb-2">專案列表</h1>
          <p className="text-muted-foreground">管理您的工作專案與領域。</p>
        </header>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button>新增專案</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>新增專案</DialogTitle>
              <DialogDescription>建立一個新的工作專案來分類您的日誌。</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>專案名稱</Label>
                <Input
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  placeholder="例如：重構核心系統"
                  onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                />
              </div>
              <div className="space-y-2">
                <Label>分類</Label>
                <Select
                  value={newProject.category}
                  onValueChange={(v) => setNewProject({ ...newProject, category: v as CreateProjectBodyCategory })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="engineering">工程開發</SelectItem>
                    <SelectItem value="office">一般辦公</SelectItem>
                    <SelectItem value="general">一般</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>描述 (選填)</Label>
                <Input
                  value={newProject.description || ""}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  placeholder="專案目標或說明…"
                />
              </div>
              <Button className="w-full" onClick={handleCreate} disabled={createProject.isPending}>
                {createProject.isPending ? "建立中..." : "建立專案"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Status Filter Tabs */}
      <div className="flex items-center gap-1 border-b border-border pb-0">
        {STATUS_TABS.map((tab) => (
          <button
            key={String(tab.value)}
            onClick={() => setStatusFilter(tab.value)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
              statusFilter === tab.value
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Project Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : projects?.length === 0 ? (
        <div className="text-center py-16 border rounded-lg border-dashed">
          <FolderKanban className="h-12 w-12 mx-auto text-muted-foreground mb-4 opacity-50" />
          <h3 className="text-lg font-medium text-foreground mb-1">此分類尚無專案</h3>
          <p className="text-muted-foreground mb-4">
            {statusFilter === ListProjectsStatus.archived
              ? "沒有已封存的專案。"
              : statusFilter === ListProjectsStatus.completed
              ? "沒有已完工的專案。"
              : "建立您的第一個專案開始記錄日誌。"}
          </p>
          {!statusFilter && (
            <Button variant="outline" onClick={() => setIsDialogOpen(true)}>新增專案</Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects?.map((project) => (
            <Card
              key={project.id}
              className="hover-elevate transition-all border-border shadow-sm group cursor-pointer"
              onClick={() => setSelectedProject(project)}
            >
              <CardHeader className="pb-2 flex flex-row items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    {getStatusBadge(project.status)}
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-sm bg-secondary text-xs text-muted-foreground">
                      {getCategoryIcon(project.category)}
                      {getCategoryLabel(project.category)}
                    </span>
                  </div>
                  <CardTitle className="text-lg flex items-center gap-1.5 group/title">
                    <span className="truncate">{project.name}</span>
                    <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover/title:opacity-100 transition-opacity shrink-0" />
                  </CardTitle>
                  <CardDescription className="mt-0.5">
                    {project.entryCount} 篇日誌
                    {project.status === "completed" && project.completedAt && (
                      <span> · 完工於 {format(new Date(project.completedAt), "yyyy-MM-dd")}</span>
                    )}
                  </CardDescription>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  {project.status === "active" && (
                    <>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-emerald-600 hover:bg-emerald-500/10"
                        title="標記完工"
                        onClick={(e) => handleStatusChange(project.id, UpdateProjectBodyStatus.completed, e)}
                      >
                        <CheckCircle2 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-amber-600 hover:bg-amber-500/10"
                        title="封存專案"
                        onClick={(e) => handleStatusChange(project.id, UpdateProjectBodyStatus.archived, e)}
                      >
                        <Archive className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                  {project.status === "completed" && (
                    <>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-blue-600 hover:bg-blue-500/10"
                        title="恢復進行中"
                        onClick={(e) => handleStatusChange(project.id, UpdateProjectBodyStatus.active, e)}
                      >
                        <RotateCcw className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-amber-600 hover:bg-amber-500/10"
                        title="封存專案"
                        onClick={(e) => handleStatusChange(project.id, UpdateProjectBodyStatus.archived, e)}
                      >
                        <Archive className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                  {project.status === "archived" && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-blue-600 hover:bg-blue-500/10"
                      title="恢復進行中"
                      onClick={(e) => handleStatusChange(project.id, UpdateProjectBodyStatus.active, e)}
                    >
                      <RotateCcw className="h-4 w-4" />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    title="刪除專案"
                    onClick={(e) => handleDelete(project.id, e)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>

              <CardContent>
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {project.description || "無描述"}
                </p>
                <div className="mt-4 text-xs text-muted-foreground">
                  建立於 {format(new Date(project.createdAt), "yyyy-MM-dd")}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Project Detail Sheet */}
      {selectedProject && (
        <ProjectEntriesSheet
          project={selectedProject}
          open={!!selectedProject}
          onClose={() => setSelectedProject(null)}
        />
      )}
    </div>
  );
}
