import os
import json
import logging
import httpx
from pathlib import Path
from dotenv import load_dotenv
from json_repair import repair_json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

logger = logging.getLogger(__name__)

INTENT_TYPES = [
    "interested",
    "catchup_thanks",
    "soft_objection",
    "hard_rejection",
    "question",
    "redirect",
    "ooo",
    "hiring",
    "competitor",
    "neutral",
]

# Keyword fallback patterns
_FALLBACK_KEYWORDS = {
    "interested": ["tell me more", "what services", "sounds interesting", "send me details", "love to learn", "would love"],
    "catchup_thanks": ["thank you", "thanks", "appreciate", "cheers", "kind of you", "glad", "pleasure"],
    "soft_objection": ["no thanks", "not for us", "thanks but", "not right now", "we're good", "maybe later", "happy with", "not at the moment", "currently covered", "not interested", "not looking", "already have", "covered for now"],
    "hard_rejection": ["don't contact", "remove me from", "unsubscribe", "stop messaging", "stop contacting", "please remove", "never contact", "report as spam", "this is spam"],
    "question": ["what exactly", "where are", "how does", "can you explain", "what is"],
    "redirect": ["talk to", "speak with", "email me at", "you should contact", "reach out to"],
    "ooo": ["out of office", "on vacation", "annual leave", "maternity leave", "will be back", "auto-reply", "automatic reply"],
    "hiring": ["looking for", "we're hiring", "open position", "job opening", "recruit"],
    "competitor": ["we do software", "in-house team", "our developers", "we build", "internal team"],
}


def _extract_openai_text(data: dict) -> str:
    """Extract output text from OpenAI Responses API response"""
    output_array = data.get('output', [])
    for item in output_array:
        if item.get('type') == 'message':
            for content_item in item.get('content', []):
                if content_item.get('type') == 'output_text':
                    return content_item.get('text', '')
    return ''


def _parse_json_from_text(text: str) -> dict:
    """Parse JSON from OpenAI response text, handling markdown wrappers and malformed JSON"""
    text = text.replace('```json', '').replace('```', '').strip()
    json_start = text.find('{')
    json_end = text.rfind('}') + 1
    if json_start != -1 and json_end > json_start:
        text = text[json_start:json_end]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = repair_json(text, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
        raise ValueError("Could not parse JSON even after repair")


def _has_correspondent_in_last_5(conversation: dict) -> bool:
    """Check if any of the last 5 messages is from CORRESPONDENT (not ME)"""
    messages = conversation.get('messages', [])
    recent = messages[-5:] if len(messages) > 5 else messages
    return any(msg.get('sender') != 'ME' for msg in recent)


def _keyword_fallback_intent(last_text: str, last_sender: str = "CORRESPONDENT") -> str:
    """Determine intent via keyword matching as fallback.
    Only uses the text if it was sent by CORRESPONDENT; returns 'neutral' for ME-authored text."""
    if last_sender == "ME":
        return "neutral"
    text_lower = (last_text or '').lower()
    for intent, keywords in _FALLBACK_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return intent
    return "neutral"


async def classify_conversations(conversations: list) -> list:
    """
    Classify LinkedIn conversations by intent type using gpt-4o-mini.

    Only processes conversations where at least one of the last 5 messages
    is from CORRESPONDENT (not ME).

    Returns list of dicts: {index, intent, confidence, reasoning}
    """
    if not conversations:
        return []

    # Filter to conversations that have CORRESPONDENT messages in last 5
    candidates = []
    for idx, conv in enumerate(conversations):
        if _has_correspondent_in_last_5(conv):
            profile = conv.get('correspondentProfile', {})
            messages = conv.get('messages', [])
            recent_msgs = messages[-5:] if len(messages) > 5 else messages

            msg_history = []
            for msg in recent_msgs:
                sender = "ME" if msg.get('sender') == 'ME' else "CORRESPONDENT"
                body = (msg.get('body', '') or '')[:300]
                msg_history.append(f"{sender}: {body}")

            candidates.append({
                "index": idx,
                "name": f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
                "company": profile.get('companyName', ''),
                "position": profile.get('position', ''),
                "last_message": (conv.get('lastMessageText', '') or '')[:300],
                "last_sender": conv.get('lastMessageSender', ''),
                "recent_messages": msg_history,
            })

    if not candidates:
        return []

    prompt = f"""You are a B2B sales assistant classifying LinkedIn conversation intent types.
You work for Interexy — a software development / staff augmentation company.
Classify what the CORRESPONDENT (the lead) is communicating in their most recent reply.

=== INTENT DEFINITIONS ===

interested
  The lead shows genuine curiosity or openness to learning more.
  Examples: "Tell me more", "What services do you offer?", "Sounds interesting, send me details",
            "How does it work?", "What's your pricing?", "Can we schedule a call?"
  Key signal: forward motion — they want MORE information or a next step.

catchup_thanks
  The lead is responding positively but without business intent — a social reply.
  Examples: "Thanks!", "Appreciate it!", "Kind of you to reach out", "Good to hear from you",
            "Hope you're well too", "Thanks for thinking of me"
  Key signal: warm but non-committal, replying to a congrats/catch-up opener.

soft_objection  ← MOST COMMONLY CONFUSED
  The lead politely declines but leaves the door open. NO aggression, NO demand to stop contacting.
  Examples: "No thanks", "Thanks but no thanks", "Not for us right now", "We're good at the moment",
            "Not interested at this time", "Maybe later", "We're covered", "Happy with our current setup",
            "Not the right time", "We already have someone for this", "Thanks, but we're not looking"
  Key signal: polite refusal WITHOUT asking to be removed. The relationship is not damaged.
  ⚠️ DO NOT confuse with hard_rejection — "no thanks" is SOFT, not hard.

hard_rejection
  The lead explicitly demands to stop contact or is hostile/aggressive.
  Examples: "Please remove me from your list", "Don't contact me again", "Stop messaging me",
            "Unsubscribe", "This is spam", "I've asked you not to contact me", "Report as spam"
  Key signal: explicit demand to stop, hostility, or threat. The relationship is over.
  ⚠️ "No thanks" alone is NEVER a hard_rejection — it's a soft_objection.

question
  The lead asks a specific question about Interexy, its services, process, or team.
  Examples: "What exactly does Interexy do?", "Where are your developers based?",
            "What tech stack do you specialize in?", "How many engineers do you have?"

redirect
  The lead points to a different person or channel.
  Examples: "You should talk to our CTO", "Email me at john@company.com",
            "Reach out to our head of engineering", "This isn't my area, try [name]"

ooo
  Automated out-of-office or vacation reply.
  Examples: "I'm out of the office until...", "Auto-reply: I'm on leave", "I'll be back on..."
  Key signal: automated message or explicit absence notice.

hiring
  The lead indicates they are looking to hire or have open roles.
  Examples: "We're actually hiring React developers", "We have open positions",
            "We're looking for senior engineers ourselves"

competitor
  The lead reveals they are in the same or adjacent business (software dev / staffing).
  Examples: "We do software development ourselves", "We have an in-house team of 50 engineers",
            "We're a dev shop too", "Our company builds custom software"

neutral
  Short, ambiguous, or social reply that doesn't fit any category above.
  Examples: "Ok", "Sure", "Hmm", "👍", "Got it", "I see"

=== CLASSIFICATION RULES ===
1. Focus ONLY on what the CORRESPONDENT wrote — ignore ME's messages.
2. "No thanks" / "Not interested" / "Thanks but not for us" = soft_objection, NOT hard_rejection.
3. Only use hard_rejection if the lead explicitly demands to stop being contacted.
4. If the last message is from ME (not CORRESPONDENT), classify based on the full conversation context.
5. When unsure between two intents, pick the one with lower business risk (e.g. soft_objection over hard_rejection).

=== CONVERSATIONS TO CLASSIFY ===
{json.dumps(candidates, indent=2)}

Return ONLY valid JSON:
{{
  "classifications": [
    {{
      "index": 0,
      "intent": "one of the 10 intent types",
      "confidence": "high/medium/low",
      "reasoning": "1-2 sentences: which signal led to this classification"
    }}
  ]
}}"""

    try:
        url = "https://api.openai.com/v1/responses"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "tools": [],
            "input": prompt,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text[:500]}")

        data = response.json()
        output_text = _extract_openai_text(data)
        if not output_text:
            raise Exception("No output_text in OpenAI response")

        result = _parse_json_from_text(output_text)
        classifications = result.get('classifications', [])

        # Validate intent values, fall back to keyword matching if invalid
        valid_intents = set(INTENT_TYPES)
        classified_indices = {item.get('index') for item in classifications}

        # Ensure one output per candidate — fill in any missing entries
        for candidate in candidates:
            idx = candidate['index']
            if idx not in classified_indices:
                last_text = conversations[idx].get('lastMessageText', '')
                last_sender = conversations[idx].get('lastMessageSender', 'CORRESPONDENT')
                classifications.append({
                    "index": idx,
                    "intent": _keyword_fallback_intent(last_text, last_sender),
                    "confidence": "low",
                    "reasoning": "Missing from LLM output — keyword fallback applied",
                })

        for item in classifications:
            if item.get('intent') not in valid_intents:
                idx = item.get('index', -1)
                if 0 <= idx < len(conversations):
                    last_text = conversations[idx].get('lastMessageText', '')
                    last_sender = conversations[idx].get('lastMessageSender', 'CORRESPONDENT')
                    item['intent'] = _keyword_fallback_intent(last_text, last_sender)
                    item['confidence'] = 'low'

        return classifications

    except Exception as e:
        logger.error(f"Classification error, using keyword fallback: {e}")
        # Keyword fallback for all candidates
        results = []
        for candidate in candidates:
            idx = candidate['index']
            last_text = conversations[idx].get('lastMessageText', '')
            last_sender = conversations[idx].get('lastMessageSender', 'CORRESPONDENT')
            intent = _keyword_fallback_intent(last_text, last_sender)
            results.append({
                "index": idx,
                "intent": intent,
                "confidence": "low",
                "reasoning": f"Keyword fallback (API error: {str(e)[:100]})",
            })
        return results
