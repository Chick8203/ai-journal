import { useState, useEffect, useRef, useCallback } from "react";
import { X, Tag as TagIcon, Loader2, Trash2 } from "lucide-react";
import { Tag } from "@workspace/api-client-react";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";

function hexToRgba(hex: string, alpha: number): string {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  if (isNaN(r) || isNaN(g) || isNaN(b)) return `rgba(100,100,100,${alpha})`;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

interface TagSelectorProps {
  selectedTags: Tag[];
  onChange: (tags: Tag[]) => void;
  placeholder?: string;
}

export function TagSelector({ selectedTags, onChange, placeholder = "搜尋或建立標籤..." }: TagSelectorProps) {
  const [query, setQuery] = useState("");
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [highlightIndex, setHighlightIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLUListElement>(null);

  const fetchTags = useCallback((search: string) => {
    const url = search.trim()
      ? `/api/tags?search=${encodeURIComponent(search)}`
      : "/api/tags";
    apiFetch<Tag[]>(url)
      .then((data) => setAllTags(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchTags(query);
  }, [query, fetchTags]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setQuery("");
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const selectedIds = new Set(selectedTags.map((t) => t.id));
  const filteredTags = allTags.filter((t) => !selectedIds.has(t.id));
  const exactMatch = allTags.some(
    (t) => t.name.toLowerCase() === query.trim().toLowerCase()
  );
  const showCreate = query.trim().length > 0 && !exactMatch;

  const dropdownItems = [...filteredTags, ...(showCreate ? [null] : [])];

  useEffect(() => {
    setHighlightIndex(0);
  }, [query]);

  const addTag = (tag: Tag) => {
    onChange([...selectedTags, tag]);
    setQuery("");
    setHighlightIndex(0);
    inputRef.current?.focus();
  };

  const removeTag = (tagId: number) => {
    onChange(selectedTags.filter((t) => t.id !== tagId));
  };

  const deleteTagFromSystem = async (tag: Tag, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    if (!confirm(`確定要永久刪除標籤「${tag.name}」嗎？這將從所有日誌中移除此標籤。`)) return;
    setDeletingId(tag.id);
    try {
      await apiFetch(`/api/tags/${tag.id}`, { method: "DELETE" });
      onChange(selectedTags.filter((t) => t.id !== tag.id));
      fetchTags(query);
    } catch {
    } finally {
      setDeletingId(null);
    }
  };

  const createTag = async () => {
    const name = query.trim();
    if (!name || isCreating) return;
    setIsCreating(true);
    try {
      const tag = await apiFetch<Tag>("/api/tags", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      addTag(tag);
      fetchTags("");
    } catch {
    } finally {
      setIsCreating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIndex((i) => Math.min(i + 1, dropdownItems.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const item = dropdownItems[highlightIndex];
      if (item === null) {
        createTag();
      } else if (item) {
        addTag(item);
      }
    } else if (e.key === "Backspace" && !query && selectedTags.length > 0) {
      removeTag(selectedTags[selectedTags.length - 1].id);
    } else if (e.key === "Escape") {
      setIsOpen(false);
      setQuery("");
    }
  };

  const showDropdown = isOpen && dropdownItems.length > 0;

  return (
    <div ref={containerRef} className="relative">
      <div
        className={cn(
          "min-h-10 flex flex-wrap gap-1.5 items-center px-3 py-2 rounded-md border bg-card cursor-text transition-colors",
          isOpen ? "border-ring ring-1 ring-ring" : "border-input"
        )}
        onClick={() => {
          setIsOpen(true);
          inputRef.current?.focus();
        }}
      >
        {selectedTags.map((tag) => (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full select-none flex-shrink-0"
            style={{
              backgroundColor: hexToRgba(tag.color, 0.15),
              color: tag.color,
              border: `1px solid ${hexToRgba(tag.color, 0.35)}`,
            }}
          >
            {tag.name}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                removeTag(tag.id);
              }}
              className="hover:opacity-60 transition-opacity ml-0.5 flex-shrink-0"
            >
              <X className="w-2.5 h-2.5" />
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          className="flex-1 min-w-[100px] bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          placeholder={selectedTags.length === 0 ? placeholder : ""}
        />
      </div>

      {showDropdown && (
        <div className="absolute z-50 mt-1 w-full bg-popover border border-border rounded-md shadow-lg overflow-hidden">
          <ul ref={dropdownRef} className="max-h-52 overflow-y-auto py-1">
            {filteredTags.map((tag, idx) => (
              <li
                key={tag.id}
                onMouseDown={(e) => {
                  e.preventDefault();
                  addTag(tag);
                }}
                onMouseEnter={() => setHighlightIndex(idx)}
                className={cn(
                  "flex items-center gap-2.5 px-3 py-2 cursor-pointer text-sm transition-colors group/item",
                  highlightIndex === idx ? "bg-accent" : "hover:bg-accent/50"
                )}
              >
                <span
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: tag.color }}
                />
                <span className="flex-1">{tag.name}</span>
                <button
                  type="button"
                  onMouseDown={(e) => deleteTagFromSystem(tag, e)}
                  disabled={deletingId === tag.id}
                  className="opacity-0 group-hover/item:opacity-100 transition-opacity p-0.5 rounded hover:bg-destructive/10 hover:text-destructive text-muted-foreground flex-shrink-0"
                  title={`刪除標籤「${tag.name}」`}
                >
                  {deletingId === tag.id ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Trash2 className="w-3 h-3" />
                  )}
                </button>
              </li>
            ))}
            {showCreate && (
              <li
                onMouseDown={(e) => {
                  e.preventDefault();
                  createTag();
                }}
                onMouseEnter={() => setHighlightIndex(filteredTags.length)}
                className={cn(
                  "flex items-center gap-2.5 px-3 py-2 cursor-pointer text-sm transition-colors",
                  highlightIndex === filteredTags.length
                    ? "bg-accent"
                    : "hover:bg-accent/50"
                )}
              >
                {isCreating ? (
                  <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
                ) : (
                  <TagIcon className="w-3 h-3 text-primary flex-shrink-0" />
                )}
                <span className="text-primary">
                  建立新標籤「<strong>{query.trim()}</strong>」
                </span>
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
