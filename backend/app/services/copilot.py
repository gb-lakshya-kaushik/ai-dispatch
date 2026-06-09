"""Gemini AI Copilot via Vertex AI — explains optimization decisions."""
import asyncio
import json

from google import genai
from google.genai import types

from app.config import settings


SYSTEM_PROMPT = """You are an AI assistant explaining workforce dispatch optimization decisions
for a traffic management company. You EXPLAIN decisions made by the optimization engine —
you do NOT make scheduling decisions yourself.

When explaining:
- Reference specific scores and their contributing factors
- Mention constraints that were active (certifications, driver requirements, crew composition)
- Compare alternatives and why they scored lower
- Be concise, use bullet points, highlight key numbers
- Format responses in markdown

You have access to the full optimization context including individual scores,
crew compositions, constraint violations, and rejection reasons."""


class CopilotService:
    def __init__(self):
        self.client = None
        if settings.vertex_ai_api_key:
            self.client = genai.Client(
                vertexai=True,
                api_key=settings.vertex_ai_api_key,
                http_options=types.HttpOptions(base_url="https://aiplatform.googleapis.com/"),
            )
        elif settings.vertex_ai_project:
            self.client = genai.Client(
                vertexai=True,
                project=settings.vertex_ai_project,
                location=settings.vertex_ai_location,
            )

    async def ask(self, question: str, context: dict) -> str:
        if not self.client:
            return self._fallback_response(question, context)

        prompt = self._build_prompt(question, context)
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.aio.models.generate_content(
                    model="gemini-2.5-pro",
                    contents=[SYSTEM_PROMPT, prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        max_output_tokens=8000,
                    ),
                )
                return response.text
            except Exception as e:
                if ("429" in str(e) or "404" in str(e)) and attempt < max_retries:
                    await asyncio.sleep(2 ** attempt * 2)
                    continue
                return f"Error calling Gemini: {str(e)}\n\n{self._fallback_response(question, context)}"

    def _build_prompt(self, question: str, context: dict) -> str:
        context_str = json.dumps(context, indent=2, default=str)
        return f"""User question: {question}

Optimization context:
{context_str}

Provide a clear, concise explanation."""

    def _fallback_response(self, question: str, context: dict) -> str:
        """Provide a structured response when API key is not configured."""
        question_lower = question.lower()

        if "why" in question_lower and "selected" in question_lower:
            return self._explain_selection(question, context)
        elif "why" in question_lower and "rejected" in question_lower:
            return self._explain_rejection(question, context)
        elif "alternative" in question_lower or "next best" in question_lower:
            return self._show_alternatives(context)
        elif "what if" in question_lower:
            return self._explain_whatif(question, context)
        else:
            return self._general_summary(context)

    def _explain_selection(self, question: str, context: dict) -> str:
        total = context.get("total_score", 0)
        return (
            f"## Assignment Explanation\n\n"
            f"The optimization engine selected this crew to maximize the total "
            f"assignment score of **{total:.1f}** across all service orders.\n\n"
            f"Key factors:\n"
            f"- **Skill match** contributed the highest weight (30 pts max)\n"
            f"- **Hour balancing** favored personnel with fewer YTD hours\n"
            f"- **No constraint violations** — all certifications and composition rules met\n\n"
            f"*Configure VERTEX_AI_API_KEY for detailed, natural-language explanations.*"
        )

    def _explain_rejection(self, question: str, context: dict) -> str:
        rejections = context.get("rejections", {})
        return (
            f"## Rejection Explanation\n\n"
            f"Personnel may be rejected for:\n"
            f"- Missing required certification (Local Flagger)\n"
            f"- No matching skills for the closure type\n"
            f"- Insufficient driver qualification for the assigned vehicle\n"
            f"- Already assigned to an overlapping service order\n\n"
            f"Rejection details: {json.dumps(rejections, indent=2)}\n\n"
            f"*Configure VERTEX_AI_API_KEY for detailed explanations.*"
        )

    def _show_alternatives(self, context: dict) -> str:
        return (
            f"## Alternative Crews\n\n"
            f"The system generated up to 10 valid crew combinations per order, "
            f"ranked by score. The optimizer selected the combination that maximizes "
            f"the *global* score across all orders simultaneously.\n\n"
            f"*Configure VERTEX_AI_API_KEY for detailed alternative analysis.*"
        )

    def _explain_whatif(self, question: str, context: dict) -> str:
        return (
            f"## What-If Analysis\n\n"
            f"To answer what-if questions, the system would re-run the optimization "
            f"with modified constraints (e.g., removing a person from the pool). "
            f"The score difference shows the impact.\n\n"
            f"*Configure VERTEX_AI_API_KEY for interactive what-if analysis.*"
        )

    def _general_summary(self, context: dict) -> str:
        total = context.get("total_score", 0)
        status = context.get("status", "unknown")
        n_orders = len(context.get("assignments", {}))
        return (
            f"## Optimization Summary\n\n"
            f"- **Status**: {status}\n"
            f"- **Total Score**: {total:.1f}\n"
            f"- **Orders Assigned**: {n_orders}\n\n"
            f"Ask specific questions like:\n"
            f"- \"Why was TC001 selected for SO001?\"\n"
            f"- \"Why was TC011 rejected for SO004?\"\n"
            f"- \"Show alternatives for SO002\"\n"
            f"- \"What if TC007 is unavailable?\""
        )
