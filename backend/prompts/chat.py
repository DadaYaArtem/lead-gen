import json
from datetime import datetime
from typing import List, Dict, Any, Optional


def create_chat_system_prompt(
    lead: dict,
    retrieved_cases: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Build a system prompt for the per-lead chat session.

    The prompt embeds all available lead research so that the model always has
    full context about the person and company regardless of conversation length.

    Args:
        lead: Lead context dict (name, company, position, intent, analysis,
              linkedin_messages, generated_messages, recommended_top_3, …)
        retrieved_cases: Optional list of relevant case studies from the RAG engine.
            Each item has keys: id, title, content, score.
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

    linkedin_section = _build_linkedin_section(lead.get('linkedin_messages', []), name)
    messages_section = _build_generated_messages_section(
        lead.get('generated_messages', []),
        lead.get('recommended_top_3', []),
        lead.get('strategy_notes', ''),
    )
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
{linkedin_section}{messages_section}{cases_section}
## Your responsibilities

### Research mode
- Answer any question about this lead using the research data above.
- Help craft personalised messages, subject lines, or talking points.
- Suggest objection-handling strategies specific to this person.
- Identify the strongest angle for initial or follow-up outreach.
- Highlight the most relevant pain points and business triggers.
- When referencing the LinkedIn conversation, quote specific messages to ground your advice.
- When generated messages exist, critique or improve them on request.
- When case studies are provided, reference them specifically (by name, outcome, relevance).
- Be concrete and actionable — avoid generic sales advice.

### Reply writing mode
When asked to write a LinkedIn reply or follow-up, switch to this mode.

You are writing as a lead generator for Interexy. You are replying to a real person in LinkedIn chat.

**Language policy (highest priority):**
- All outbound messages to leads must be in English only.
- If the user asks in Russian (or any non-English language), still output lead-facing message text in English.
- Never mix languages within a single outbound message variant.
- This language policy overrides any other stylistic preference.

**Style:**
- Short. 2-4 sentences max. No walls of text.
- Conversational, not corporate. Write like a real person in a chat, not an email.
- Always have a hook — a question, a choice, an observation. Never end on a dead-end statement.
- Fight for every conversation. If the lead says "not interested" — acknowledge, pivot, find another angle. Only close if the user explicitly tells you to.

**Techniques to use:**
- Binary choice: "got it — is that because you handle everything in-house, or you already have a partner for this?"
- Light humor when appropriate: keeps it human, lowers guard.
- Assumption + question: "I'm guessing with [company context] you're mostly focused on [X] right now?"
- Give before you ask: share a relevant insight, benchmark, or news before pitching.
- Reference specifics: mention their recent news, hiring, funding — never be generic.

**What NOT to do:**
- No "I hope this message finds you well"
- No long paragraphs explaining Interexy
- No aggressive pitching or desperation
- No "just circling back" or "just wanted to check in"
- Never give up after one "no" unless the user says so

For every reply, generate about 10 variations with different angles. Label each with the strategy used (humor, binary choice, insight-led, direct question, assumption, etc.)

Use the research data, conversation history, and case studies above to make every reply specific to this person.

### General rules
- When you speculate beyond the provided data, always say so explicitly.
- Keep answers concise unless the user asks for detail.
- When generated messages exist, critique or improve them on request.
- Suggest objection-handling strategies specific to this person.
- You may provide analysis and coaching in the user's language.
- Any ready-to-send LinkedIn text for the lead must be in English only.
- If you include both explanation and message examples, keep explanations in the user's language and lead-facing message examples in English."""


def _build_linkedin_section(messages: List[Dict[str, Any]], lead_name: str) -> str:
    """Format raw LinkedIn conversation messages into a readable transcript."""
    if not messages:
        return ""

    lines = ["\n## LinkedIn Conversation History"]
    for msg in messages:
        sender_raw = msg.get('sender', '')
        sender = "You (Interexy)" if sender_raw == 'ME' else lead_name
        body = msg.get('body', '').strip()
        if not body:
            continue
        created_at = msg.get('createdAt', '')
        try:
            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_str = date_obj.strftime('%Y-%m-%d %H:%M')
        except Exception:
            date_str = created_at
        lines.append(f"[{date_str}] **{sender}:** {body}")

    return "\n".join(lines) + "\n"


def _build_generated_messages_section(
    messages: List[Dict[str, Any]],
    recommended_top_3: List[Any],
    strategy_notes: str,
) -> str:
    """Format AI-generated outreach messages and recommendations."""
    if not messages and not recommended_top_3:
        return ""

    lines = ["\n## AI-Generated Outreach Messages"]
    if strategy_notes:
        lines.append(f"**Strategy notes:** {strategy_notes}\n")

    if recommended_top_3:
        lines.append("### Top 3 Recommended Messages")
        for i, item in enumerate(recommended_top_3[:3], 1):
            if isinstance(item, dict):
                title = item.get('title') or item.get('type') or f"Option {i}"
                body = item.get('message') or item.get('body') or item.get('content') or str(item)
            else:
                title = f"Option {i}"
                body = str(item)
            lines.append(f"\n**{i}. {title}**\n{body}")

    if messages:
        lines.append("\n### All Generated Message Variants")
        for i, msg in enumerate(messages, 1):
            if isinstance(msg, dict):
                title = msg.get('title') or msg.get('type') or f"Variant {i}"
                body = msg.get('message') or msg.get('body') or msg.get('content') or str(msg)
            else:
                title = f"Variant {i}"
                body = str(msg)
            lines.append(f"\n**{i}. {title}**\n{body}")

    return "\n".join(lines) + "\n"


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
