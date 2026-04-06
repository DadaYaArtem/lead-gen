import json
from typing import List, Dict, Any, Optional


def create_chat_system_prompt(
    lead: dict,
    retrieved_cases: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Build a system prompt for the per-lead chat session.

    The prompt embeds all available lead research so that the model always has
    full context about the person and company regardless of conversation length.

    Args:
        lead: Lead context dict (name, company, position, intent, analysis, …)
        retrieved_cases: Optional list of relevant case studies from the RAG engine.
            Each item has keys: id, title, content, score.
            When provided, a "Relevant Case Studies" section is appended so the
            model can reference real Interexy projects when answering.
    """
    name = lead.get('name', 'Unknown')
    company = lead.get('company', 'Unknown')
    position = lead.get('position', 'Unknown')
    location = lead.get('location', '')
    intent = lead.get('intent', 'unknown')
    intent_confidence = lead.get('intent_confidence', '')
    executive_summary = lead.get('executive_summary', '')
    analysis = lead.get('analysis', {})

    analysis_json = json.dumps(analysis, indent=2, ensure_ascii=False)

    cases_section = _build_cases_section(retrieved_cases)

    return f"""You are a B2B sales intelligence assistant for Interexy — a software development company specialising in mobile/web development, AI integration, and digital transformation.

You have been given detailed research about a specific lead. Help the sales team understand this person deeply and craft the best outreach strategy.

## Lead
- Name: {name}
- Company: {company}
- Position: {position}
- Location: {location}
- Detected intent: {intent} (confidence: {intent_confidence})

## Executive Summary
{executive_summary if executive_summary else 'Not available yet.'}

## Full Research Data
```json
{analysis_json}
```
{cases_section}
## Your responsibilities
- Answer any question about this lead using the research data above.
- Help craft personalised messages, subject lines, or talking points.
- Suggest objection-handling strategies specific to this person.
- Identify the strongest angle for initial or follow-up outreach.
- Highlight the most relevant pain points and business triggers.
- When case studies are provided, reference them specifically (by name, outcome, relevance).
- Be concrete and actionable — avoid generic sales advice.

When you speculate beyond the provided data, always say so explicitly.
Keep answers concise unless the user asks for detail."""


def _build_cases_section(cases: Optional[List[Dict[str, Any]]]) -> str:
    """Build the optional case studies section for the system prompt."""
    if not cases:
        return ""

    lines = ["\n## Relevant Case Studies from Interexy Portfolio"]
    lines.append(
        "These cases were automatically retrieved based on relevance to the current question. "
        "Use them to provide specific proof points and references.\n"
    )

    for i, case in enumerate(cases, 1):
        score_pct = int(case.get('score', 0) * 100)
        lines.append(f"### Case {i}: {case['title']} (relevance: {score_pct}%)")
        lines.append(case['content'])
        lines.append("")

    return "\n".join(lines) + "\n"
