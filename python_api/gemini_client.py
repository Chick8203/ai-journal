import os
from google import genai
from google.genai import types as genai_types

_client = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("AI_INTEGRATIONS_GEMINI_API_KEY", "dummy")
        base_url = os.environ.get("AI_INTEGRATIONS_GEMINI_BASE_URL")

        http_options = None
        if base_url:
            http_options = genai_types.HttpOptions(base_url=base_url)

        _client = genai.Client(api_key=api_key, http_options=http_options)
    return _client


def generate_text(prompt: str, system: str | None = None) -> str:
    client = get_client()
    contents = []
    if system:
        contents.append(
            genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=f"[System Instructions]\n{system}\n\n[User Request]\n{prompt}")]
            )
        )
    else:
        contents.append(
            genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=prompt)]
            )
        )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=genai_types.GenerateContentConfig(
            max_output_tokens=8192,
        ),
    )
    return response.text or ""
