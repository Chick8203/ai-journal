import { useState } from "react";
import { 
  useListProjects, 
  useCreateProject, 
  useDeleteProject,
  CreateProjectBodyCategory 
} from "@workspace/api-client-react";
import { useToast } from "@/hooks/use-toast";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { FolderKanban, Trash2, Code, Briefcase, Layout } from "lucide-react";
import { format } from "date-fns";

export default function Projects() {
  const { toast } = useToast();
  const { data: projects, isLoading, refetch } = useListProjects();
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newProject, setNewProject] = useState({
    name: "",
    description: "",
    category: CreateProjectBodyCategory.engineering as CreateProjectBodyCategory
  });

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
    } catch (error) {
      toast({ title: "建立失敗", variant: "destructive" });
    }
  };

  const handleDelete = async (id: number) => {
    if (confirm("確定要刪除此專案嗎？")) {
      try {
        await deleteProject.mutateAsync({ projectId: id });
        toast({ title: "專案已刪除" });
        refetch();
      } catch (error) {
        toast({ title: "刪除失敗", variant: "destructive" });
      }
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

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
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
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>專案名稱</Label>
                <Input 
                  value={newProject.name} 
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  placeholder="例如：重構核心系統"
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
                />
              </div>
              <Button className="w-full" onClick={handleCreate} disabled={createProject.isPending}>
                {createProject.isPending ? "建立中..." : "建立專案"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : projects?.length === 0 ? (
        <div className="text-center py-16 border rounded-lg border-dashed">
          <FolderKanban className="h-12 w-12 mx-auto text-muted-foreground mb-4 opacity-50" />
          <h3 className="text-lg font-medium text-foreground mb-1">尚無專案</h3>
          <p className="text-muted-foreground mb-4">建立您的第一個專案開始記錄日誌。</p>
          <Button variant="outline" onClick={() => setIsDialogOpen(true)}>新增專案</Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects?.map((project) => (
            <Card key={project.id} className="hover-elevate transition-all border-border shadow-sm group">
              <CardHeader className="pb-2 flex flex-row items-start justify-between">
                <div>
                  <CardTitle className="text-lg mb-1">{project.name}</CardTitle>
                  <CardDescription className="flex items-center gap-2">
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-sm bg-secondary text-xs">
                      {getCategoryIcon(project.category)}
                      {getCategoryLabel(project.category)}
                    </span>
                    <span>•</span>
                    <span>{project.entryCount} 篇日誌</span>
                  </CardDescription>
                </div>
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                  onClick={() => handleDelete(project.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
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
    </div>
  );
}
