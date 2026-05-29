import json
import re
from datetime import date, timedelta
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..ai_client import (
    generate_text,
    generate_embedding,
    get_active_embedding_info,
    cosine_similarity,
)

router = APIRouter(prefix="/ai", tags=["ai"])


def _parse_json_loose(raw: str) -> dict:
    """Extract a JSON object from model output that may include prose, code fences, or trailing text."""
    text = raw.strip()
    # strip markdown code fences
    if text.startswith("```"):
        m = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
    # try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # fall back to first {...} block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        candidate = text[start : end + 1]
        return json.loads(candidate)
    raise ValueError(f"模型輸出不是有效 JSON：{text[:200]}")


class AnalyzeBottleneckBody(BaseModel):
    projectId: Optional[int] = None
    days: int = 30


class DecomposeGoalBody(BaseModel):
    goal: str
    context: Optional[str] = None


@router.post("/analyze-bottleneck")
def analyze_bottleneck(body: AnalyzeBottleneckBody):
    since = (date.today() - timedelta(days=body.days)).isoformat()

    with get_db() as conn:
        if body.projectId:
            entries = conn.execute(
                """
                SELECT e.date, e.content, e.mood, e.tags, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                WHERE e.project_id = ? AND e.date >= ?
                ORDER BY e.date ASC
                """,
                (body.projectId, since),
            ).fetchall()
        else:
            entries = conn.execute(
                """
                SELECT e.date, e.content, e.mood, e.tags, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                WHERE e.date >= ?
                ORDER BY e.date ASC
                """,
                (since,),
            ).fetchall()

    if not entries:
        return {
            "efficiency": {
                "trend": "stable",
                "firstDerivative": 0.0,
                "secondDerivative": 0.0,
                "score": 50.0,
            },
            "bottlenecks": ["日誌資料不足，無法進行分析"],
            "suggestions": ["請先累積至少 3 天的日誌記錄，再進行 AI 分析"],
            "summary": "資料不足，請繼續記錄日誌後再分析",
        }

    entries_text = "\n\n".join(
        [
            f"日期：{e['date']} | 專案：{e['project_name']} | 心情評分：{e['mood'] or '未填'}\n{e['content']}"
            for e in entries
        ]
    )

    moods = [e["mood"] for e in entries if e["mood"] is not None]
    mood_trend = 0.0
    mood_acceleration = 0.0
    if len(moods) >= 2:
        diffs = [moods[i + 1] - moods[i] for i in range(len(moods) - 1)]
        mood_trend = sum(diffs) / len(diffs)
        if len(diffs) >= 2:
            accel = [diffs[i + 1] - diffs[i] for i in range(len(diffs) - 1)]
            mood_acceleration = sum(accel) / len(accel)

    system_prompt = """你是一位專業的工作效率分析師，擅長透過日誌資料分析工作狀態。
請使用繁體中文回覆，格式嚴格按照 JSON 輸出。

分析框架：
- 一階偏微分（firstDerivative）：代表效率變化速率，正值表示提升，負值表示下降
- 二階偏微分（secondDerivative）：代表效率變化的加速度，正值表示加速改善，負值表示加速惡化
- 趨勢判斷：improving（改善中）/ declining（下降中）/ stable（穩定）
- 效率評分：0-100 分

請輸出以下 JSON 格式（不要有其他文字）：
{
  "efficiency": {
    "trend": "improving|declining|stable",
    "firstDerivative": <數值>,
    "secondDerivative": <數值>,
    "score": <0-100>
  },
  "bottlenecks": ["瓶頸1", "瓶頸2", "瓶頸3"],
  "suggestions": ["建議1", "建議2", "建議3"],
  "summary": "整體分析摘要（2-3 句話）"
}"""

    avg_mood = f"{sum(moods) / len(moods):.1f}" if moods else "無資料"
    prompt = f"""以下是過去 {body.days} 天的工作日誌：

{entries_text}

心情評分統計：
- 心情趨勢（一階微分）：{mood_trend:.2f}
- 心情加速度（二階微分）：{mood_acceleration:.2f}
- 平均心情：{avg_mood}

請根據以上資料進行深入分析，找出工作瓶頸並提供具體建議。"""

    try:
        raw = generate_text(prompt, system_prompt, json_mode=True)
        return _parse_json_loose(raw)
    except Exception as e:
        return {
            "efficiency": {
                "trend": "stable",
                "firstDerivative": round(mood_trend, 2),
                "secondDerivative": round(mood_acceleration, 2),
                "score": 60.0,
            },
            "bottlenecks": ["AI 分析暫時無法使用，請稍後再試"],
            "suggestions": ["小型本地模型（如 270M）可能無法穩定輸出 JSON，建議改用 7B 以上模型"],
            "summary": f"分析時發生錯誤：{str(e)[:100]}",
        }


@router.post("/decompose-goal")
def decompose_goal(body: DecomposeGoalBody):
    system_prompt = """你是一位專業的專案規劃師，擅長將大目標拆解成具體可執行的 SOP 步驟。
請使用繁體中文回覆，格式嚴格按照 JSON 輸出。

每個步驟需包含：
- stepNumber：步驟編號
- title：步驟標題（簡潔有力）
- description：詳細說明（具體可執行）
- estimatedTime：預估時間（如：30分鐘、2小時、3天）
- deliverable：可交付成果（具體的產出物）

請輸出以下 JSON 格式（不要有其他文字）：
{
  "goal": "<目標名稱>",
  "steps": [
    {
      "stepNumber": 1,
      "title": "步驟標題",
      "description": "詳細說明",
      "estimatedTime": "預估時間",
      "deliverable": "可交付成果"
    }
  ],
  "totalEstimatedTime": "總預估時間"
}"""

    context_text = f"\n背景資訊：{body.context}" if body.context else ""
    prompt = f"""請將以下大目標拆解成具體的 SOP 步驟：

目標：{body.goal}{context_text}

請產生 5-8 個具體可執行的步驟，每個步驟都要有明確的產出物。"""

    try:
        raw = generate_text(prompt, system_prompt, json_mode=True)
        return _parse_json_loose(raw)
    except Exception as e:
        return {
            "goal": body.goal,
            "steps": [
                {
                    "stepNumber": 1,
                    "title": "AI 分析暫時無法使用",
                    "description": f"錯誤：{str(e)[:200]}",
                    "estimatedTime": "未知",
                    "deliverable": "請稍後再試",
                }
            ],
            "totalEstimatedTime": "未知",
        }


# ── RAG: Retrospective search over historical journal entries ─────────────────


class RetrospectBody(BaseModel):
    query: str
    projectId: Optional[int] = None
    topK: int = 5


def _backfill_embeddings(conn, provider: str, model: str, limit: int = 50) -> int:
    """Generate embeddings for entries that don't have one yet (or have stale provider).

    Returns the number of entries backfilled.
    """
    rows = conn.execute(
        """
        SELECT id, content
        FROM entries
        WHERE embedding IS NULL
           OR embedding_provider IS NULL
           OR embedding_provider != ?
        ORDER BY date DESC, id DESC
        LIMIT ?
        """,
        (provider, limit),
    ).fetchall()
    count = 0
    for row in rows:
        try:
            vec, prov, mod = generate_embedding(row["content"])
            conn.execute(
                "UPDATE entries SET embedding = ?, embedding_provider = ?, embedding_model = ? WHERE id = ?",
                (json.dumps(vec), prov, mod, row["id"]),
            )
            count += 1
        except Exception:
            # Skip and continue — embedding service may be down for some entries
            continue
    return count


@router.post("/retrospect")
def retrospect(body: RetrospectBody):
    """RAG search: find related historical entries and synthesize an answer.

    Pipeline:
    1. Backfill embeddings for entries missing them (limited to 50 per call).
    2. Embed the query using the active provider.
    3. Compute cosine similarity against all entries' embeddings.
    4. Take top-K and ask the LLM to synthesize advice using them as context.
    """
    query = (body.query or "").strip()
    if not query:
        return {
            "synthesis": "請輸入問題後再進行回溯。",
            "related": [],
            "indexed": 0,
        }

    provider, model = get_active_embedding_info()

    with get_db() as conn:
        # Step 1: lazy backfill (best-effort, capped)
        try:
            _backfill_embeddings(conn, provider, model)
        except Exception:
            pass

        # Step 2: embed the query
        try:
            query_vec, _, _ = generate_embedding(query)
        except Exception as e:
            return {
                "synthesis": f"無法生成查詢向量：{str(e)[:200]}",
                "related": [],
                "indexed": 0,
            }

        # Step 3: fetch all entries with matching-provider embeddings
        if body.projectId:
            rows = conn.execute(
                """
                SELECT e.id, e.date, e.content, e.mood, e.embedding, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                WHERE e.embedding IS NOT NULL
                  AND e.embedding_provider = ?
                  AND e.project_id = ?
                """,
                (provider, body.projectId),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT e.id, e.date, e.content, e.mood, e.embedding, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                WHERE e.embedding IS NOT NULL
                  AND e.embedding_provider = ?
                """,
                (provider,),
            ).fetchall()

        indexed = len(rows)
        if indexed == 0:
            return {
                "synthesis": "目前還沒有任何已建立索引的日誌可供回溯。請先寫幾篇日誌，或在設定確認 AI 提供者已設定金鑰。",
                "related": [],
                "indexed": 0,
            }

        # Step 4: cosine similarity & top-K
        scored = []
        for r in rows:
            try:
                vec = json.loads(r["embedding"])
            except Exception:
                continue
            sim = cosine_similarity(query_vec, vec)
            scored.append((sim, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[: max(1, min(body.topK, 10))]

        if not top:
            return {
                "synthesis": "找不到相關的歷史日誌。",
                "related": [],
                "indexed": indexed,
            }

        # Step 5: ask LLM to synthesize
        context_blocks = []
        for sim, r in top:
            block = (
                f"[相似度 {sim:.2f}] 日期：{r['date']}"
                f" | 專案：{r['project_name']}"
                f" | 心情：{r['mood'] if r['mood'] is not None else '未填'}\n"
                f"{r['content']}"
            )
            context_blocks.append(block)
        context_text = "\n\n---\n\n".join(context_blocks)

        system_prompt = """你是一位陪伴使用者梳理思緒的智囊。
使用者問了你一個問題，系統從他過去的日誌找出最相關的幾篇給你參考。

請以繁體中文回答，並且：
1. 直接針對使用者的問題回答，給出具體、可行動的建議
2. 明確引用過去日誌中的具體事件或經驗（例如「你在 5/2 提到...」）
3. 點出「過去經驗如何幫助當下決策」的反思
4. 語氣自然親切，像在跟自己的內在對話，不要用條列式或制式格式
5. 控制在 4-6 段話以內"""

        user_prompt = f"""使用者的問題：
{query}

過去的相關日誌：
{context_text}

請給出綜合性的建議與反思。"""

        try:
            synthesis = generate_text(user_prompt, system_prompt)
        except Exception as e:
            synthesis = f"AI 生成回應失敗：{str(e)[:200]}\n\n以下是找到的相關日誌："

        return {
            "synthesis": synthesis,
            "related": [
                {
                    "id": r["id"],
                    "date": r["date"],
                    "content": r["content"],
                    "mood": r["mood"],
                    "projectName": r["project_name"],
                    "similarity": round(sim, 4),
                }
                for sim, r in top
            ],
            "indexed": indexed,
        }


# ── AI Chat: multi-mode conversational assistant ──────────────────────────────
# Modes:
#   "journal"    → user describes their day, AI drafts a journal entry
#   "bottleneck" → user describes work struggles, AI analyzes & suggests
#   "decompose"  → user describes a goal, AI breaks it into SOP steps


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ProjectRef(BaseModel):
    id: int
    name: str


class JournalChatBody(BaseModel):
    messages: list[ChatMessage]
    mode: str = "auto"  # auto = AI judges intent; or explicit journal/bottleneck/decompose
    projects: list[ProjectRef] = []
    projectId: Optional[int] = None
    days: int = 0  # 0 = use all entries (no date filter); >0 = limit to last N days


def _parse_time_range_zh(text: str) -> Optional[tuple[date, date, str]]:
    """Parse common Chinese / English time expressions in user message.

    Returns (start_date, end_date, label) or None.
    Order matters: more specific patterns must be checked before generic ones.
    """
    if not text:
        return None
    today = date.today()
    text_lower = text.lower()

    # ── 全部 / all entries ────────────────────────────────────────────────────
    if any(kw in text for kw in ["全部", "所有", "整體", "歷史所有", "全時間"]) or \
       any(kw in text_lower for kw in ["all entries", "all time", "entire history"]):
        return (date(2000, 1, 1), today, "全部歷史")

    # ── 今天 / 昨天 ───────────────────────────────────────────────────────────
    if "今天" in text or "today" in text_lower:
        return (today, today, "今天")
    if "昨天" in text or "yesterday" in text_lower:
        d = today - timedelta(days=1)
        return (d, d, "昨天")

    # ── 週相關（先 specific 後 generic）─────────────────────────────────────
    if any(kw in text for kw in ["上個禮拜", "上禮拜", "上週", "上周", "上星期"]) or "last week" in text_lower:
        this_monday = today - timedelta(days=today.weekday())
        last_monday = this_monday - timedelta(days=7)
        last_sunday = this_monday - timedelta(days=1)
        return (last_monday, last_sunday, "上週")
    if any(kw in text for kw in ["這個禮拜", "這禮拜", "本週", "這週", "本周", "這周", "本星期", "這星期"]) or "this week" in text_lower:
        monday = today - timedelta(days=today.weekday())
        return (monday, today, "這週")

    # ── 月相關 ───────────────────────────────────────────────────────────────
    if any(kw in text for kw in ["上個月", "上月"]) or "last month" in text_lower:
        first_of_month = date(today.year, today.month, 1)
        last_of_last_month = first_of_month - timedelta(days=1)
        first_of_last_month = date(last_of_last_month.year, last_of_last_month.month, 1)
        return (first_of_last_month, last_of_last_month, "上個月")
    if any(kw in text for kw in ["這個月", "本月", "這月"]) or "this month" in text_lower:
        return (date(today.year, today.month, 1), today, "這個月")

    # ── 年相關（先 specific 後 generic）─────────────────────────────────────
    if "去年" in text or "last year" in text_lower:
        return (date(today.year - 1, 1, 1), date(today.year - 1, 12, 31), "去年")
    if any(kw in text for kw in ["上半年"]):
        return (date(today.year, 1, 1), date(today.year, 6, 30), f"{today.year} 年上半年")
    if any(kw in text for kw in ["下半年"]):
        return (date(today.year, 7, 1), date(today.year, 12, 31), f"{today.year} 年下半年")
    if "半年" in text or "past 6 months" in text_lower:
        # 最近半年 / 半年內 ≈ past 6 months
        try:
            six_months_ago = date(today.year, today.month - 6, today.day) if today.month > 6 \
                else date(today.year - 1, today.month + 6, today.day)
        except ValueError:
            # 月末日子在前 6 個月不存在（例如 8/31 → 2/31）→ 用該月第一天
            six_months_ago = date(today.year, today.month, 1) - timedelta(days=180)
        return (six_months_ago, today, "最近半年")
    if "今年" in text or "this year" in text_lower:
        return (date(today.year, 1, 1), today, f"今年（{today.year}）")

    # ── N 天 / 週 / 月 ───────────────────────────────────────────────────────
    m = re.search(r"(?:最近|過去|近)\s*(\d+)\s*天", text)
    if m:
        n = int(m.group(1))
        return (today - timedelta(days=n - 1), today, f"最近 {n} 天")
    m = re.search(r"(?:最近|過去|近)\s*(\d+)\s*(?:週|周|禮拜)", text)
    if m:
        n = int(m.group(1))
        return (today - timedelta(days=n * 7 - 1), today, f"最近 {n} 週")
    m = re.search(r"(?:最近|過去|近)\s*(\d+)\s*(?:個月|月)", text)
    if m:
        n = int(m.group(1))
        # 約略 N 個月 ≈ N * 30 天，避免月份相減的邊界 bug
        return (today - timedelta(days=n * 30), today, f"最近 {n} 個月")
    m = re.search(r"past\s+(\d+)\s+days?", text_lower)
    if m:
        n = int(m.group(1))
        return (today - timedelta(days=n - 1), today, f"past {n} days")
    m = re.search(r"past\s+(\d+)\s+months?", text_lower)
    if m:
        n = int(m.group(1))
        return (today - timedelta(days=n * 30), today, f"past {n} months")

    return None


def _fetch_entries_by_date_range(
    start: date, end: date, project_id: Optional[int]
) -> str:
    """Fetch all entries between start and end date inclusive, formatted as context."""
    start_s, end_s = start.isoformat(), end.isoformat()
    with get_db() as conn:
        if project_id:
            rows = conn.execute(
                """
                SELECT e.date, e.title, e.content, e.mood, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                WHERE e.project_id = ? AND e.date >= ? AND e.date <= ?
                ORDER BY e.date ASC
                LIMIT 200
                """,
                (project_id, start_s, end_s),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT e.date, e.title, e.content, e.mood, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                WHERE e.date >= ? AND e.date <= ?
                ORDER BY e.date ASC
                LIMIT 200
                """,
                (start_s, end_s),
            ).fetchall()

    if not rows:
        return f"（{start_s} ~ {end_s} 期間沒有日誌資料）"

    mood_label = {
        1: "😩 遇到瓶頸",
        2: "🤔 邏輯卡關",
        3: "😐 推進中",
        4: "💡 靈光一閃",
        5: "💪 順利突破",
    }
    parts = []
    for r in rows:
        title = r["title"] or ""
        title_str = f" | {title}" if title else ""
        mood = mood_label.get(r["mood"], "—") if r["mood"] is not None else "—"
        snippet = (r["content"] or "")[:300]
        parts.append(
            f"[{r['date']} | {r['project_name']}{title_str} | 狀態 {mood}]\n{snippet}"
        )
    return "\n\n".join(parts)


def _fetch_relevant_entries_context(
    query: str,
    project_id: Optional[int],
    top_k: int = 20,
) -> str:
    """Use vector search (RAG) to find the most semantically relevant entries.

    Falls back to most-recent if:
    - Query is empty
    - Embedding service is unavailable (e.g., no API key, network down)
    - No entries have been indexed yet for the active provider
    """
    if not (query or "").strip():
        return _fetch_recent_entries_context(project_id, 0)

    provider, model = get_active_embedding_info()

    with get_db() as conn:
        # Lazily backfill any missing embeddings (best-effort, capped)
        try:
            _backfill_embeddings(conn, provider, model, limit=50)
        except Exception:
            pass

        # Embed the query
        try:
            query_vec, _, _ = generate_embedding(query)
        except Exception:
            return _fetch_recent_entries_context(project_id, 0)

        # Pull candidate entries with matching-provider embeddings
        if project_id:
            rows = conn.execute(
                """
                SELECT e.date, e.title, e.content, e.mood, e.embedding, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                WHERE e.embedding IS NOT NULL
                  AND e.embedding_provider = ?
                  AND e.project_id = ?
                ORDER BY e.date DESC
                LIMIT 2000
                """,
                (provider, project_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT e.date, e.title, e.content, e.mood, e.embedding, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                WHERE e.embedding IS NOT NULL
                  AND e.embedding_provider = ?
                ORDER BY e.date DESC
                LIMIT 2000
                """,
                (provider,),
            ).fetchall()

        if not rows:
            return _fetch_recent_entries_context(project_id, 0)

        # Cosine similarity ranking
        scored = []
        for r in rows:
            try:
                vec = json.loads(r["embedding"])
            except Exception:
                continue
            sim = cosine_similarity(query_vec, vec)
            scored.append((sim, r))
        if not scored:
            return _fetch_recent_entries_context(project_id, 0)

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[: max(1, min(top_k, 50))]

        mood_label = {
            1: "😩 遇到瓶頸",
            2: "🤔 邏輯卡關",
            3: "😐 推進中",
            4: "💡 靈光一閃",
            5: "💪 順利突破",
        }
        parts = []
        for sim, r in top:
            title = r["title"] or ""
            title_str = f" | {title}" if title else ""
            mood = mood_label.get(r["mood"], "—") if r["mood"] is not None else "—"
            snippet = (r["content"] or "")[:250]
            parts.append(
                f"[相似度 {sim:.2f} | {r['date']} | {r['project_name']}{title_str} | 狀態 {mood}]\n{snippet}"
            )
        return "\n\n".join(parts)


def _fetch_recent_entries_context(project_id: Optional[int], days: int) -> str:
    """Build a text context of journal entries for bottleneck analysis.

    Defaults to ALL entries (capped at 500 most recent to bound LLM context).
    The `days` parameter is kept for backwards compatibility but ignored
    unless > 0 and < 365 — in which case it acts as an upper date bound.
    """
    use_date_filter = 0 < days < 365
    since = (date.today() - timedelta(days=days)).isoformat() if use_date_filter else None
    with get_db() as conn:
        if project_id and use_date_filter:
            rows = conn.execute(
                """
                SELECT e.date, e.title, e.content, e.mood, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                WHERE e.project_id = ? AND e.date >= ?
                ORDER BY e.date DESC
                LIMIT 500
                """,
                (project_id, since),
            ).fetchall()
        elif project_id:
            rows = conn.execute(
                """
                SELECT e.date, e.title, e.content, e.mood, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                WHERE e.project_id = ?
                ORDER BY e.date DESC
                LIMIT 500
                """,
                (project_id,),
            ).fetchall()
        elif use_date_filter:
            rows = conn.execute(
                """
                SELECT e.date, e.title, e.content, e.mood, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                WHERE e.date >= ?
                ORDER BY e.date DESC
                LIMIT 500
                """,
                (since,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT e.date, e.title, e.content, e.mood, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                ORDER BY e.date DESC
                LIMIT 500
                """
            ).fetchall()
    if not rows:
        return "（資料庫中尚無任何日誌）"

    mood_label = {
        1: "😩 遇到瓶頸",
        2: "🤔 邏輯卡關",
        3: "😐 推進中",
        4: "💡 靈光一閃",
        5: "💪 順利突破",
    }
    parts = []
    for r in rows:
        title = r["title"] or ""
        title_str = f" | {title}" if title else ""
        mood = mood_label.get(r["mood"], "—") if r["mood"] is not None else "—"
        snippet = (r["content"] or "")[:250]
        parts.append(
            f"[{r['date']} | {r['project_name']}{title_str} | 狀態 {mood}]\n{snippet}"
        )
    return "\n\n".join(parts)


def _prompt_journal(projects: list[ProjectRef]) -> str:
    projects_text = (
        "\n".join(f"- ID {p.id}: {p.name}" for p in projects)
        if projects
        else "（目前沒有專案，suggestedProjectId 請填 null）"
    )
    return f"""你是「智囊」，一位陪伴使用者記錄日常的 AI 寫作助理。

工作流程：
1. 使用者會描述他今天做了什麼、感受如何、遇到什麼事
2. 如果資訊太簡略，以親切的語氣追問 1-2 個重點問題（例如：當時你的感受？有沒有什麼讓你印象深刻？）
3. 當收集到足夠細節後，整理成一篇結構化的日誌草稿
4. 對話來回不要超過 3-4 輪，太多輪反而讓人煩

可選的專案列表（讓日誌歸到哪個專案）：
{projects_text}

請以嚴格的 JSON 格式回覆（不要 markdown、不要其他文字），兩種格式之一：

【需要繼續對話時】：
{{
  "action": "ask",
  "message": "（你想問使用者的問題，繁體中文，1-2 個問題，自然親切）"
}}

【可以整理成日誌時】：
{{
  "action": "draft",
  "message": "（簡短說明，例如「我幫你整理好了，看看要不要再補充什麼」）",
  "draft": {{
    "title": "（一句話標題，10-20 字以內，繁體中文，能精準總結這篇日誌的重點）",
    "content": "（完整的日誌內容，用繁體中文，可以分段或條列。長度約 100-400 字。要保留使用者的口語感，不要寫得太正式。）",
    "mood": <1-5 整數，按以下狀態對應：1=😩 遇到瓶頸 / 2=🤔 邏輯卡關 / 3=😐 推進中 / 4=💡 靈光一閃 / 5=💪 順利突破>,
    "tags": ["（2-4 個關鍵字標籤，繁體中文，不要含 # 符號）"],
    "suggestedProjectId": <整數 ID 或 null>
  }}
}}

切換到 draft 的判斷：
- 使用者描述了「做了什麼」+「感受/結果/想法」其中至少 2 個面向
- 或使用者明確說「就這樣」「不用再問」「直接幫我整理」
- 或對話已 3 輪以上"""


def _prompt_bottleneck(entries_context: str) -> str:
    return f"""你是「智囊」，一位專業的工作效率分析師，擅長透過對話幫使用者梳理工作瓶頸。

工作流程：
1. 使用者會描述他現在卡住或挫折的事情
2. 你親切地追問 1-2 個重點細節（例如：具體哪一步卡住？多久了？以前有沒有類似經驗？）
3. 收集到足夠資訊後（通常 2-3 輪），輸出結構化的瓶頸分析
4. 系統用向量搜尋從使用者所有歷史日誌中找出**語意最相關**的幾篇給你參考（每篇前面有相似度分數，1.00 = 完全相關）。引用日誌中的具體事件能讓分析更有說服力

歷史日誌（依與當前問題的相似度排序）：
---
{entries_context}
---

請以嚴格 JSON 格式回覆（不要 markdown、不要其他文字），兩種格式之一：

【需要繼續對話時】：
{{
  "action": "ask",
  "message": "（你想問使用者的問題，繁體中文，1-2 個，自然親切）"
}}

【可以提供分析時】：
{{
  "action": "bottleneck",
  "message": "（簡短說明，例如「我幫你梳理了一下，看看有沒有共鳴」）",
  "result": {{
    "efficiency": {{
      "trend": "improving|declining|stable",
      "score": <0-100 整數>
    }},
    "bottlenecks": ["（具體瓶頸 1，引用日誌中的事件更好）", "瓶頸 2", "瓶頸 3"],
    "suggestions": ["（具體、可執行的建議 1）", "建議 2", "建議 3"],
    "summary": "（2-3 句話的整體分析）"
  }}
}}"""


def _prompt_auto(
    projects: list[ProjectRef],
    entries_context: str,
    range_label: str,
    start_date: str,
    end_date: str,
) -> str:
    """Unified prompt: AI infers intent and outputs the right action."""
    projects_text = (
        "\n".join(f"- ID {p.id}: {p.name}" for p in projects)
        if projects
        else "（目前沒有專案）"
    )
    return f"""你是「智囊」，一位多功能 AI 對話助理。可以做三件事：

1. **寫日誌** — 把使用者的口語描述整理成結構化日誌草稿
2. **分析瓶頸** — 根據使用者指定時間範圍內的「歷史日誌」找出該段時間出現的卡點與建議
3. **拆解目標** — 把大目標切成可執行的 SOP 步驟

請根據對話內容**自己判斷**使用者要什麼，輸出對應 JSON。

## 判斷規則

- 提到「今天我...」「做了什麼...」「整理一下今天」「記錄」等 → 用 **draft**（使用者描述自己的當下，AI 整理成日誌）
- 提到「分析瓶頸」「我這禮拜卡在哪」「過去 X 天為什麼沒進展」「最近的瓶頸」等 → 用 **bottleneck**（**不是使用者描述瓶頸給你聽，而是你從下方的歷史日誌中找出那段時間的瓶頸並給建議**）
- 提到「想完成 X」「目標」「怎麼開始」「拆解」「步驟」等 → 用 **decompose**
- 資訊不足或還沒辦法判斷 → 用 **ask**（請追問 1-2 個關鍵問題）
- 對話來回不超過 3-4 輪，盡早給出結果

## 輸出格式（嚴格 JSON，不要 markdown 或其他文字）

【追問】：
{{
  "action": "ask",
  "message": "（繁體中文的追問，1-2 個問題）"
}}

【日誌草稿】：
{{
  "action": "draft",
  "message": "（例如「我幫你整理好了！」）",
  "draft": {{
    "title": "（一句話標題，10-20 字）",
    "content": "（完整日誌內容，繁體中文，100-400 字，保留口語感）",
    "mood": <1-5 整數，1=😩 遇到瓶頸 / 2=🤔 邏輯卡關 / 3=😐 推進中 / 4=💡 靈光一閃 / 5=💪 順利突破>,
    "tags": ["標籤1", "標籤2"],
    "suggestedProjectId": <整數 ID 或 null>
  }}
}}

【瓶頸分析】（重要：從下方歷史日誌中**主動找出**那段時間的瓶頸，不要等使用者描述）：
{{
  "action": "bottleneck",
  "message": "（簡短說明，例如「分析了你 {range_label} 的日誌，看看這些卡點」）",
  "result": {{
    "efficiency": {{ "trend": "improving|declining|stable", "score": <0-100 整數> }},
    "bottlenecks": ["（從歷史日誌中觀察到的具體瓶頸，例如：「5/15、5/17 都提到 FPGA 資源分配卡住」）", "..."],
    "suggestions": ["（針對上述瓶頸的具體可執行建議）", "..."],
    "summary": "（2-3 句整體分析，描述這段時間的工作狀態走勢）"
  }}
}}

【目標拆解】：
{{
  "action": "decompose",
  "message": "（簡短說明）",
  "result": {{
    "goal": "<簡短目標描述>",
    "steps": [
      {{
        "stepNumber": 1,
        "title": "<步驟標題>",
        "description": "<詳細說明>",
        "estimatedTime": "<例：30分鐘、2小時、3天>",
        "deliverable": "<具體產出物>"
      }}
    ],
    "totalEstimatedTime": "<總預估時間>"
  }}
}}

## 可選的專案列表（寫日誌時 suggestedProjectId 用）

{projects_text}

## 歷史日誌 — 時間範圍：{range_label}（{start_date} ~ {end_date}）

**重要：當使用者要求分析瓶頸時，請從以下日誌中觀察 mood 分布、重複出現的關鍵字、卡住的事件，主動找出瓶頸並給建議。**

---
{entries_context}
---"""


def _prompt_decompose() -> str:
    return """你是「智囊」，一位協助使用者拆解大目標的專案規劃師。

工作流程：
1. 使用者會描述一個想達成的目標
2. 你親切地追問 1-2 個關鍵問題（時間限制？已有資源？已有的進度？卡點？）
3. 收集到足夠資訊後（通常 1-2 輪），輸出具體可執行的 SOP 步驟

請以嚴格 JSON 格式回覆（不要 markdown、不要其他文字），兩種格式之一：

【需要繼續對話時】：
{
  "action": "ask",
  "message": "（你想問使用者的問題，繁體中文，1-2 個，自然親切）"
}

【可以提供拆解時】：
{
  "action": "decompose",
  "message": "（簡短說明，例如「以你目前的條件，我會這樣拆」）",
  "result": {
    "goal": "<簡短目標描述>",
    "steps": [
      {
        "stepNumber": 1,
        "title": "<步驟標題，簡潔有力>",
        "description": "<詳細說明，具體可執行>",
        "estimatedTime": "<例：30分鐘、2小時、3天>",
        "deliverable": "<可交付成果，具體的產出物>"
      }
    ],
    "totalEstimatedTime": "<總預估時間>"
  }
}

步驟通常 5-8 個，太少不夠具體，太多會嚇到使用者。"""


@router.post("/journal-chat")
def journal_chat(body: JournalChatBody):
    """Multi-mode conversational assistant.

    Modes:
      - journal:    drafts a journal entry
      - bottleneck: analyzes work struggles based on recent entries
      - decompose:  breaks a goal into SOP steps
    """
    mode = body.mode if body.mode in ("auto", "journal", "bottleneck", "decompose") else "auto"

    if not body.messages:
        openings = {
            "auto":       "嗨 👋 我是智囊。跟我聊聊吧 — 你可以記今天的日誌、聊最近的瓶頸、或者一起拆解一個目標，我會根據你說的內容自動調整。",
            "journal":    "今天過得怎麼樣？跟我說說發生了什麼吧 😊",
            "bottleneck": "最近有什麼讓你卡住或挫折的事嗎？跟我聊聊，我會用向量搜尋從你所有日誌中找出最相關的幾篇，結合起來幫你梳理 🔍",
            "decompose":  "你想拆解什麼目標？告訴我大方向，我會幫你切成可執行的步驟 🎯",
        }
        return {"action": "ask", "message": openings[mode]}

    # Build mode-specific system prompt
    if mode == "auto":
        # Detect time range from latest user message (e.g. "這個禮拜", "最近 3 天").
        # If found, fetch entries in that range. Otherwise default to last 7 days.
        user_msgs = [m.content for m in body.messages if m.role == "user"]
        latest_user = user_msgs[-1] if user_msgs else ""

        time_range = _parse_time_range_zh(latest_user)
        if time_range:
            start, end, range_label = time_range
        else:
            end = date.today()
            start = end - timedelta(days=6)  # last 7 days inclusive
            range_label = "最近 7 天（預設）"

        entries_context = _fetch_entries_by_date_range(start, end, body.projectId)
        system_prompt = _prompt_auto(
            body.projects, entries_context, range_label, start.isoformat(), end.isoformat()
        )
    elif mode == "bottleneck":
        user_msgs = [m.content for m in body.messages if m.role == "user"]
        search_query = "\n".join(user_msgs[-2:]) if user_msgs else ""
        entries_context = _fetch_relevant_entries_context(
            search_query, body.projectId, top_k=20
        )
        system_prompt = _prompt_bottleneck(entries_context)
    elif mode == "decompose":
        system_prompt = _prompt_decompose()
    else:
        system_prompt = _prompt_journal(body.projects)

    # Build conversation text for the LLM
    chat_lines = []
    for m in body.messages:
        role_zh = "使用者" if m.role == "user" else "智囊"
        chat_lines.append(f"[{role_zh}]\n{m.content}")
    user_prompt = "\n\n".join(chat_lines) + "\n\n[智囊]\n（請輸出 JSON）"

    try:
        raw = generate_text(user_prompt, system_prompt, json_mode=True)
        result = _parse_json_loose(raw)
    except Exception as e:
        return {
            "action": "ask",
            "message": f"⚠️ AI 暫時無法回應：{str(e)[:150]}。要不要重試？",
        }

    action = result.get("action", "ask")

    # In auto mode, accept any of the 3 actions; in explicit modes, require matching action
    accept_draft = action == "draft" and mode in ("auto", "journal")
    accept_bottleneck = action == "bottleneck" and mode in ("auto", "bottleneck")
    accept_decompose = action == "decompose" and mode in ("auto", "decompose")

    if accept_draft:
        draft = result.get("draft") or {}
        return {
            "action": "draft",
            "message": result.get("message", "我幫你整理好了!"),
            "draft": {
                "title": str(draft.get("title", "") or "").strip()[:80],
                "content": str(draft.get("content", "")),
                "mood": int(draft.get("mood", 3)) if draft.get("mood") is not None else 3,
                "tags": list(draft.get("tags", [])),
                "suggestedProjectId": draft.get("suggestedProjectId"),
            },
        }

    if accept_bottleneck:
        r = result.get("result") or {}
        eff = r.get("efficiency") or {}
        try:
            score = float(eff.get("score", 50))
        except Exception:
            score = 50.0
        return {
            "action": "bottleneck",
            "message": result.get("message", "我幫你梳理了一下"),
            "result": {
                "efficiency": {
                    "trend": str(eff.get("trend", "stable")),
                    "score": max(0.0, min(100.0, score)),
                },
                "bottlenecks": [str(b) for b in (r.get("bottlenecks") or [])][:6],
                "suggestions": [str(s) for s in (r.get("suggestions") or [])][:6],
                "summary": str(r.get("summary", "")),
            },
        }

    if accept_decompose:
        r = result.get("result") or {}
        steps_raw = r.get("steps") or []
        steps = []
        for i, s in enumerate(steps_raw[:12], start=1):
            steps.append({
                "stepNumber": int(s.get("stepNumber", i)) if isinstance(s.get("stepNumber"), (int, float, str)) else i,
                "title": str(s.get("title", "")),
                "description": str(s.get("description", "")),
                "estimatedTime": str(s.get("estimatedTime", "")),
                "deliverable": str(s.get("deliverable", "")),
            })
        return {
            "action": "decompose",
            "message": result.get("message", "拆解結果"),
            "result": {
                "goal": str(r.get("goal", "")),
                "steps": steps,
                "totalEstimatedTime": str(r.get("totalEstimatedTime", "")),
            },
        }

    # Default: fall back to ask
    return {
        "action": "ask",
        "message": result.get("message", "可以多說一點嗎？"),
    }


@router.post("/embeddings/backfill")
def backfill_embeddings_endpoint(limit: int = 200):
    """Manually trigger embedding backfill. Useful after switching AI provider."""
    provider, model = get_active_embedding_info()
    with get_db() as conn:
        count = _backfill_embeddings(conn, provider, model, limit=limit)
        total = conn.execute("SELECT COUNT(*) as c FROM entries").fetchone()["c"]
        indexed = conn.execute(
            "SELECT COUNT(*) as c FROM entries WHERE embedding_provider = ?",
            (provider,),
        ).fetchone()["c"]
    return {
        "backfilled": count,
        "indexed": indexed,
        "total": total,
        "provider": provider,
        "model": model,
    }
