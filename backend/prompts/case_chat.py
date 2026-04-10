from typing import List, Dict, Any, Optional


def create_case_chat_system_prompt(
    retrieved_cases: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Build a system prompt for the standalone case portfolio chat.

    This prompt is used when there is no specific lead context — the user is
    querying Interexy's case library in general (e.g., "what healthcare cases
    do we have?", "show me IoT projects").

    Args:
        retrieved_cases: List of relevant case studies from the RAG engine.
            Each item has keys: id, title, content, score.
            When empty or None, the model is told no matching cases were found.
    """
    cases_section = _build_cases_section(retrieved_cases)

    return f"""You are Interexy's internal Case Portfolio Assistant — a tool for the sales and business development team.

Interexy is a software development company specialising in mobile/web development, AI integration, and digital transformation for B2B clients.

Your job is to help sales reps quickly find, understand, and use Interexy's past project experience when preparing for outreach or calls.

{cases_section}## Your responsibilities
- Answer questions about Interexy's case portfolio based on the retrieved cases above.
- Help identify which cases are most relevant for a given industry, technology, or client profile.
- Summarise case outcomes, tech stacks, and key achievements concisely.
- Suggest how to reference a specific case in a sales message or call prep.
- If no cases were retrieved, say so clearly and suggest how the user might rephrase their query.
- You may use web search to supplement your knowledge about industries, technologies, or market trends mentioned in cases.

## Guidelines
- Be specific — mention actual case names, outcomes, and technologies.
- If asked about something not in the retrieved cases, say "I didn't find a matching case for that — try asking about [related topic]."
- Keep answers concise unless the user asks for full details.
- Do not invent case details that are not present in the provided content."""


def _build_cases_section(cases: Optional[List[Dict[str, Any]]]) -> str:
    """Format the retrieved cases into a readable section for the system prompt."""
    if not cases:
        return "## Retrieved Cases\nNo cases matched your query. Please try rephrasing or broadening your search.\n\n"

    lines = ["## Retrieved Cases from Interexy Portfolio"]
    lines.append(
        f"{len(cases)} case(s) were retrieved based on your query. Use these as your primary source.\n"
    )

    for i, case in enumerate(cases, 1):
        score_pct = int(case.get("score", 0) * 100)
        lines.append(f"### {i}. {case['title']} (relevance: {score_pct}%)")
        lines.append(case["content"])
        lines.append("")

    return "\n".join(lines) + "\n\n"
