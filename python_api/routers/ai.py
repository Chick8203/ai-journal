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
