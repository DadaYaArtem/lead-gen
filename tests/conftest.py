"""
Shared pytest configuration: adds backend/ to sys.path and provides
sample conversation fixtures that simulate HeyReach API responses.
"""
import sys
from pathlib import Path
import pytest

# Make backend/ importable from the tests/ directory
BACKEND_DIR = Path(__file__).parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------------------------
# Sample conversation builder helpers
# ---------------------------------------------------------------------------

def make_message(sender: str, body: str, created_at: str = "2024-03-01T10:00:00Z") -> dict:
    return {"sender": sender, "body": body, "createdAt": created_at}


def make_conversation(
    first_name: str,
    last_name: str,
    company: str,
    position: str,
    messages: list,
    last_sender: str = None,
    last_text: str = None,
    location: str = "New York, US",
    profile_url: str = "https://linkedin.com/in/test",
    headline: str = "",
) -> dict:
    last_msg = messages[-1] if messages else {}
    return {
        "correspondentProfile": {
            "firstName": first_name,
            "lastName": last_name,
            "companyName": company,
            "position": position,
            "location": location,
            "profileUrl": profile_url,
            "headline": headline,
        },
        "messages": messages,
        "lastMessageSender": last_sender or last_msg.get("sender", ""),
        "lastMessageText": last_text or last_msg.get("body", ""),
        "lastMessageAt": "2024-03-01T11:00:00Z",
        "totalMessages": len(messages),
    }


# ---------------------------------------------------------------------------
# Fixture conversations
# ---------------------------------------------------------------------------

@pytest.fixture
def conv_catchup_thanks():
    """Lead replied 'Thanks!' to a congratulations — classic catchup_thanks."""
    msgs = [
        make_message("ME", "Hey Sarah, congrats on your new role as VP of Product!"),
        make_message("CORRESPONDENT", "Thanks! Really appreciate it."),
    ]
    return make_conversation("Sarah", "Johnson", "FinTech Inc", "VP of Product", msgs,
                             headline="VP of Product @ FinTech Inc | Building great products")


@pytest.fixture
def conv_interested():
    """Lead expressed interest in services."""
    msgs = [
        make_message("ME", "Hi Tom, I noticed you're scaling your engineering team."),
        make_message("CORRESPONDENT", "Sounds interesting! Tell me more about what you offer."),
    ]
    return make_conversation("Tom", "Williams", "GrowthCo", "CTO", msgs)


@pytest.fixture
def conv_soft_objection():
    """Lead politely declined."""
    msgs = [
        make_message("ME", "Hi Mark, wanted to reach out about staff augmentation."),
        make_message("CORRESPONDENT", "Thanks for reaching out, but we're good for now. Maybe later."),
    ]
    return make_conversation("Mark", "Davis", "StableCorp", "Engineering Manager", msgs)


@pytest.fixture
def conv_hard_rejection():
    """Lead firmly refused contact."""
    msgs = [
        make_message("ME", "Hi Alex, I'd love to discuss..."),
        make_message("CORRESPONDENT", "Please don't contact me again. Remove me from your list."),
    ]
    return make_conversation("Alex", "Brown", "BigCorp", "Director of IT", msgs)


@pytest.fixture
def conv_ooo():
    """Out-of-office auto-reply."""
    msgs = [
        make_message("ME", "Hi Lisa, hope you're doing well!"),
        make_message("CORRESPONDENT", "I'm out of office until April 15th. Will reply upon my return."),
    ]
    return make_conversation("Lisa", "Chen", "GlobalCo", "Head of Engineering", msgs)


@pytest.fixture
def conv_hiring():
    """Lead is looking for developers."""
    msgs = [
        make_message("ME", "Hi James, saw you're expanding your tech team."),
        make_message("CORRESPONDENT", "Yes! We're actually looking for senior React developers."),
    ]
    return make_conversation("James", "Taylor", "StartupXYZ", "CEO", msgs)


@pytest.fixture
def conv_question():
    """Lead asks a question about the company."""
    msgs = [
        make_message("ME", "Hi Emma, we work with companies like yours on tech challenges."),
        make_message("CORRESPONDENT", "Interesting — what exactly does Interexy do?"),
    ]
    return make_conversation("Emma", "Wilson", "MediaCo", "Product Manager", msgs)


@pytest.fixture
def conv_redirect():
    """Lead redirects to another person."""
    msgs = [
        make_message("ME", "Hi Robert, wanted to connect about your tech needs."),
        make_message("CORRESPONDENT", "You should talk to our CTO, Mike. Email him at mike@company.com"),
    ]
    return make_conversation("Robert", "Miller", "EnterpriseX", "COO", msgs)


@pytest.fixture
def conv_competitor():
    """Lead is a software development company themselves."""
    msgs = [
        make_message("ME", "Hi David, curious about your development setup."),
        make_message("CORRESPONDENT", "We do software development ourselves — we have an in-house team of 80 engineers."),
    ]
    return make_conversation("David", "Anderson", "DevShop", "CEO", msgs)


@pytest.fixture
def conv_no_correspondent_reply():
    """All recent messages are from ME — no CORRESPONDENT reply in last 5.
    6 messages total so that messages[-5:] excludes the old CORRESPONDENT message."""
    msgs = [
        make_message("CORRESPONDENT", "Hi, thanks for connecting.", "2024-01-01T10:00:00Z"),
        make_message("ME", "Hi! Great to connect.", "2024-01-02T10:00:00Z"),
        make_message("ME", "Just following up...", "2024-02-01T10:00:00Z"),
        make_message("ME", "Still hoping to chat.", "2024-02-15T10:00:00Z"),
        make_message("ME", "Another follow-up.", "2024-02-20T10:00:00Z"),
        make_message("ME", "One last touch...", "2024-03-01T10:00:00Z"),
    ]
    return make_conversation("Chris", "Evans", "SilentCo", "Head of Product", msgs)


@pytest.fixture
def conv_neutral():
    """Short ambiguous reply."""
    msgs = [
        make_message("ME", "Hi Karen, hope you're well!"),
        make_message("CORRESPONDENT", "Ok"),
    ]
    return make_conversation("Karen", "Lee", "AmbiguousCo", "Manager", msgs)


@pytest.fixture
def all_sample_conversations(
    conv_catchup_thanks, conv_interested, conv_soft_objection,
    conv_hard_rejection, conv_ooo, conv_hiring,
    conv_no_correspondent_reply, conv_question
):
    """A list of varied conversations for bulk testing."""
    return [
        conv_catchup_thanks,
        conv_interested,
        conv_soft_objection,
        conv_hard_rejection,
        conv_ooo,
        conv_hiring,
        conv_no_correspondent_reply,
        conv_question,
    ]


@pytest.fixture
def minimal_analysis() -> dict:
    """Minimal analysis dict that satisfies all prompt functions."""
    return {
        "lead_profile": {
            "current_role": {"title": "CTO", "time_in_role": "1 year", "insight": "Technical leader"}
        },
        "company_basics": {"stage": "growth", "size": "50-200", "industry": "SaaS"},
        "pain_point_analysis": {
            "role_specific_pain_points": ["Scaling engineering team", "Managing tech debt"],
            "stage_specific_pain_points": ["Platform stability", "Hiring senior talent"],
            "evidence_from_research": ["Open engineering positions", "Recent product launch"],
        },
        "deep_research": {
            "funding": {"last_round": "Series B, $20M", "total_raised": "$30M", "investors": ["a16z"]},
            "news": [{"date": "2024-02-01", "headline": "TechCorp raises Series B", "summary": "...", "source": "TechCrunch", "outreach_hook": "Use funding news"}],
        },
        "vendor_approach_inference": {
            "current_solution_hypothesis": "likely_hybrid",
            "confidence": "medium",
            "evidence": ["Medium team size", "Some open engineering roles"],
            "build_vs_buy_philosophy": {"assessment": "hybrid-approach", "reasoning": "...", "implications": "..."},
        },
        "timing_triggers_analysis": {
            "active_triggers": [{"trigger": "Recent funding", "timeframe": "0-3 months", "urgency": "high", "how_it_creates_need": "Scaling pressure"}],
            "upcoming_triggers": [],
            "vendor_evaluation_pattern": {"likely_pattern": "triggered", "decision_maker": "CTO", "typical_timeline": "4-8 weeks", "criteria": ["quality", "speed"]},
            "urgency_assessment": {"urgency_level": "medium", "primary_driver": "Growth", "timing_recommendation": "reach out now"},
        },
        "conversation_analysis": {
            "conversation_stage": "initial_response",
            "messages_exchanged": 2,
            "lead_responsiveness": "medium",
            "interest_signals": [],
            "objections_raised": [],
            "questions_asked": [],
            "rejection_analysis": {
                "rejection_type": "not_applicable",
                "confidence": "high",
                "evidence": "Positive thanks reply",
                "recommended_approach": "continue",
            },
        },
        "qualification": {
            "status": "qualified",
            "fit_score": 7,
            "reasoning": "Good fit for team augmentation",
            "budget_indicator": "medium",
            "authority_level": "decision_maker",
            "need_urgency": "medium",
            "vendor_readiness": "maybe_soon",
        },
        "recommended_action": {
            "next_step": "Send follow-up message",
            "message_angle": "Team growth",
            "personalization_hooks": ["Recent Series B funding", "Hiring engineers"],
            "questions_to_ask": ["What's your biggest scaling challenge?"],
            "timing": "now",
            "priority": "high",
        },
        "interexy_value_props": {
            "most_relevant": ["Senior engineers in 2 weeks", "10-day replacement guarantee"],
            "case_studies_to_mention": ["RWE energy sector"],
            "technical_expertise_highlight": "React, Node.js, cloud",
            "differentiation_angle": "Top 2% engineers vs typical agencies",
        },
        "executive_summary": "Strong qualified lead — CTO at a Series B company actively scaling their engineering team.",
    }
