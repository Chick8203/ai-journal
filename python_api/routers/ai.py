import json
from datetime import date, timedelta
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..ai_client import generate_text

router = APIRouter(prefix="/ai", tags=["ai"])


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
        raw = generate_text(prompt, system_prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return data
    except Exception as e:
        return {
            "efficiency": {
                "trend": "stable",
                "firstDerivative": round(mood_trend, 2),
                "secondDerivative": round(mood_acceleration, 2),
                "score": 60.0,
            },
            "bottlenecks": ["AI 分析暫時無法使用，請稍後再試"],
            "suggestions": ["請確認 Gemini API 設定是否正確"],
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
        raw = generate_text(prompt, system_prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return data
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
