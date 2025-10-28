from google import genai

PROMPT_TEMPLATE = """You are a wildfire risk analyst. I will provide binned regions (lat/lon on a {grid_deg}° grid) with recent and prior counts of fire discoveries.

Task:
1) Select {min_k}–{max_k} regions most likely to have near-term fire discovery, using recent counts, prior counts, total history, and trend_ratio.
2) Output a brief plain-text list, highest-risk first. Each line must include:
   - lat_bin, lon_bin
   - a short reason (e.g., "recent spike", "sustained activity", "high baseline")
3) Keep the entire output under 120 words. No JSON, no extra commentary.

Data (JSON):
{context_json}
"""

def ask_gemini(api_key: str,
               context_json: str,
               grid_deg: float,
               out_min: int = 5,
               out_max: int = 10,
               model: str = "gemini-2.5-flash") -> str:
    client = genai.Client(api_key=api_key)
    prompt = PROMPT_TEMPLATE.format(
        grid_deg=grid_deg,
        min_k=out_min,
        max_k=out_max,
        context_json=context_json
    )
    resp = client.models.generate_content(
        model=model,
        contents=prompt
    )
    return getattr(resp, "text", "").strip()
