import { useState } from "react";
import {
  useListEntries,
  useCreateEntry,
  useUpdateEntry,
  useDeleteEntry,
  useListProjects,
  CreateEntryBodyTemplate,
  Tag,
} from "@workspace/api-client-react";
import { useToast } from "@/hooks/use-toast";
import { format } from "date-fns";
import {
  Plus, Calendar as CalendarIcon, Tag as TagIcon, Trash2,
  AlignLeft, Edit3, Briefcase, Code, FileText,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { TagSelector } from "@/components/TagSelector";

function hexToRgba(hex: string, alpha: number): string {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  if (isNaN(r) || isNaN(g) || isNaN(b)) return `rgba(100,100,100,${alpha})`;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

const TEMPLATES = {
  engineering: `【今日目標】

【完成事項】
-

【遇到瓶頸】

【明日計畫】`,
  office: `【今日重點】

【心得筆記】
-

【行動項目】`,
  freeform: "",
};

export default function Journal() {
  const { toast } = useToast();
  const { data: entries, isLoading: isLoadingEntries, refetch: refetchEntries } = useListEntries();
  const { data: projects, isLoading: isLoadingProjects } = useListProjects();

  const createEntry = useCreateEntry();
  const updateEntry = useUpdateEntry();
  const deleteEntry = useDeleteEntry();

  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const [date, setDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [projectId, setProjectId] = useState<string>("");
  const [template, setTemplate] = useState<CreateEntryBodyTemplate>(CreateEntryBodyTemplate.freeform);
  const [content, setContent] = useState("");
  const [mood, setMood] = useState<string>("");
  const [selectedTags, setSelectedTags] = useState<Tag[]>([]);

  const handleOpenCreate = () => {
    setEditingId(null);
    setDate(format(new Date(), "yyyy-MM-dd"));
    setProjectId(projects?.[0]?.id.toString() || "");
    setTemplate(CreateEntryBodyTemplate.freeform);
    setContent("");
    setMood("");
    setSelectedTags([]);
    setIsSheetOpen(true);
  };

  const handleOpenEdit = (entry: any) => {
    setEditingId(entry.id);
    setDate(format(new Date(entry.date), "yyyy-MM-dd"));
    setProjectId(entry.projectId.toString());
    setTemplate(entry.template as CreateEntryBodyTemplate);
    setContent(entry.content);
    setMood(entry.mood?.toString() || "");
    setSelectedTags(entry.tags ?? []);
    setIsSheetOpen(true);
  };

  const handleTemplateChange = (val: CreateEntryBodyTemplate) => {
    setTemplate(val);
    if (!content.trim() || Object.values(TEMPLATES).some((t) => t.trim() === content.trim())) {
      setContent(TEMPLATES[val]);
    }
  };

  const handleSave = async () => {
    if (!projectId) {
      toast({ title: "請選擇專案", variant: "destructive" });
      return;
    }
    if (!content.trim()) {
      toast({ title: "日誌內容不能為空", variant: "destructive" });
      return;
    }

    const tagNames = selectedTags.map((t) => t.name);
    const moodNum = mood ? parseInt(mood) : null;

    try {
      if (editingId) {
        await updateEntry.mutateAsync({
          entryId: editingId,
          data: { content, mood: moodNum, tags: tagNames },
        });
        toast({ title: "日誌已更新" });
      } else {
        await createEntry.mutateAsync({
          data: {
            date,
            projectId: parseInt(projectId),
            template,
            content,
            mood: moodNum,
            tags: tagNames,
          },
        });
        toast({ title: "日誌已建立" });
      }
      setIsSheetOpen(false);
      refetchEntries();
    } catch {
      toast({ title: "儲存失敗", variant: "destructive" });
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("確定要刪除這篇日誌嗎？")) {
      try {
        await deleteEntry.mutateAsync({ entryId: id });
        toast({ title: "日誌已刪除" });
        refetchEntries();
      } catch {
        toast({ title: "刪除失敗", variant: "destructive" });
      }
    }
  };

  const getTemplateIcon = (tpl: string) => {
    switch (tpl) {
      case "engineering": return <Code className="w-3 h-3" />;
      case "office": return <Briefcase className="w-3 h-3" />;
      default: return <FileText className="w-3 h-3" />;
    }
  };

  return (
    <div className="space-y-6 h-full flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <header>
          <h1 className="text-3xl font-serif font-bold text-foreground mb-2">日誌</h1>
          <p className="text-muted-foreground">記錄您的工作軌跡、瓶頸與心得。</p>
        </header>
        <Button onClick={handleOpenCreate} className="flex items-center gap-2">
          <Plus className="w-4 h-4" /> 新增日誌
        </Button>
      </div>

      <div className="flex-1 min-h-0 relative">
        {isLoadingEntries ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        ) : entries?.length === 0 ? (
          <div className="text-center py-20 border rounded-lg border-dashed bg-card/50">
            <AlignLeft className="h-12 w-12 mx-auto text-muted-foreground mb-4 opacity-50" />
            <h3 className="text-lg font-medium text-foreground mb-1">尚未記錄任何日誌</h3>
            <p className="text-muted-foreground mb-4">開始記錄您的第一天工作心得吧。</p>
            <Button onClick={handleOpenCreate}>開始撰寫</Button>
          </div>
        ) : (
          <div className="space-y-4 pb-20">
            {entries?.map((entry) => (
              <Card
                key={entry.id}
                className="cursor-pointer hover-elevate transition-all border-border shadow-sm group"
                onClick={() => handleOpenEdit(entry)}
              >
                <CardHeader className="p-5 pb-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="secondary" className="font-normal flex items-center gap-1.5">
                          {getTemplateIcon(entry.template)}
                          {entry.projectName}
                        </Badge>
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <CalendarIcon className="w-3 h-3" />
                          {format(new Date(entry.date), "yyyy-MM-dd")}
                        </span>
                      </div>
                      <CardTitle className="text-base line-clamp-1 mt-2">
                        {entry.content.split("\n")[0].replace(/^[#*-]\s+|【.*?】\s*/, "") || "無標題"}
                      </CardTitle>
                    </div>
                    <div className="flex items-center gap-2">
                      {entry.mood && (
                        <div className="text-xs font-medium px-2 py-1 bg-primary/10 text-primary rounded-md">
                          心情: {entry.mood}/5
                        </div>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive hover:bg-destructive/10 h-8 w-8"
                        onClick={(e) => handleDelete(entry.id, e)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-5 pt-0">
                  <p className="text-sm text-muted-foreground line-clamp-2 mb-3 whitespace-pre-wrap font-sans">
                    {entry.content}
                  </p>
                  {entry.tags && entry.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {entry.tags.map((tag) => (
                        <span
                          key={tag.id}
                          className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full"
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
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent className="sm:max-w-xl w-full flex flex-col p-0 border-l">
          <SheetHeader className="p-6 border-b border-border bg-sidebar/50">
            <SheetTitle className="font-serif text-2xl">
              {editingId ? "編輯日誌" : "撰寫日誌"}
            </SheetTitle>
            <SheetDescription>專注記錄當下的工作脈絡與心得。</SheetDescription>
          </SheetHeader>

          <ScrollArea className="flex-1 p-6">
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>日期</Label>
                  <Input
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    disabled={!!editingId}
                    className="bg-card"
                  />
                </div>
                <div className="space-y-2">
                  <Label>專案</Label>
                  <Select value={projectId} onValueChange={setProjectId} disabled={!!editingId || isLoadingProjects}>
                    <SelectTrigger className="bg-card">
                      <SelectValue placeholder="選擇專案" />
                    </SelectTrigger>
                    <SelectContent>
                      {projects?.map((p) => (
                        <SelectItem key={p.id} value={p.id.toString()}>{p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {!editingId && (
                <div className="space-y-2">
                  <Label>版型範本</Label>
                  <Select value={template} onValueChange={(v) => handleTemplateChange(v as CreateEntryBodyTemplate)}>
                    <SelectTrigger className="bg-card">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="freeform">自由格式</SelectItem>
                      <SelectItem value="engineering">工程開發</SelectItem>
                      <SelectItem value="office">一般辦公</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>內容</Label>
                  <Button variant="ghost" size="sm" className="h-6 text-xs px-2" onClick={() => setContent("")}>
                    清空
                  </Button>
                </div>
                <Textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="在此記錄..."
                  className="min-h-[300px] font-sans leading-relaxed resize-y bg-card"
                />
              </div>

              <div className="space-y-2">
                <Label>心情評分 (可選)</Label>
                <ToggleGroup
                  type="single"
                  value={mood}
                  onValueChange={(v) => setMood(v)}
                  className="justify-start"
                >
                  {["1", "2", "3", "4", "5"].map((v) => (
                    <ToggleGroupItem
                      key={v}
                      value={v}
                      aria-label={v}
                      className="w-10 h-10 rounded-full data-[state=on]:bg-primary data-[state=on]:text-primary-foreground"
                    >
                      {v}
                    </ToggleGroupItem>
                  ))}
                </ToggleGroup>
              </div>

              <div className="space-y-2">
                <Label className="flex items-center gap-1.5">
                  <TagIcon className="w-3.5 h-3.5" />
                  標籤
                </Label>
                <TagSelector selectedTags={selectedTags} onChange={setSelectedTags} />
              </div>
            </div>
          </ScrollArea>

          <SheetFooter className="p-6 border-t border-border bg-sidebar/50 mt-auto">
            <Button variant="outline" onClick={() => setIsSheetOpen(false)}>取消</Button>
            <Button onClick={handleSave} disabled={createEntry.isPending || updateEntry.isPending}>
              {createEntry.isPending || updateEntry.isPending ? "儲存中..." : "儲存日誌"}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  );
}
