"""
Unit tests for backend/prompts/

Tests are pure (no external API calls):
- create_analysis_prompt — verifies lead info, new Level 4.3/4.4 sections, no no_thanks_response_strategy
- create_catchup_messages_prompt — verifies content and JSON output template
- create_no_thanks_messages_prompt — verifies content and message types
"""
import pytest
from prompts.base_research import create_analysis_prompt
from prompts.catchup import create_catchup_messages_prompt
from prompts.no_thanks import create_no_thanks_messages_prompt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_conv_dict(first="John", last="Smith", company="TechCorp",
                   position="CTO", location="NY", url="https://linkedin.com/in/test",
                   headline="CTO @ TechCorp", messages=None):
    if messages is None:
        messages = [
            {"sender": "ME", "body": "Congrats on the new role!", "createdAt": "2024-01-01T10:00:00Z"},
            {"sender": "CORRESPONDENT", "body": "Thanks!", "createdAt": "2024-01-01T11:00:00Z"},
        ]
    return {
        "correspondentProfile": {
            "firstName": first, "lastName": last, "companyName": company,
            "position": position, "location": location,
            "profileUrl": url, "headline": headline,
        },
        "messages": messages,
        "lastMessageSender": "CORRESPONDENT",
        "lastMessageText": messages[-1]["body"] if messages else "",
    }


# ---------------------------------------------------------------------------
# create_analysis_prompt
# ---------------------------------------------------------------------------

class TestCreateAnalysisPrompt:
    def test_returns_non_empty_string(self):
        prompt = create_analysis_prompt(make_conv_dict())
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_contains_lead_name(self):
        prompt = create_analysis_prompt(make_conv_dict(first="Alice", last="Walker"))
        assert "Alice Walker" in prompt

    def test_contains_company_name(self):
        prompt = create_analysis_prompt(make_conv_dict(company="FinTech Unicorn"))
        assert "FinTech Unicorn" in prompt

    def test_contains_position(self):
        prompt = create_analysis_prompt(make_conv_dict(position="Head of Product"))
        assert "Head of Product" in prompt

    def test_contains_location(self):
        prompt = create_analysis_prompt(make_conv_dict(location="San Francisco, CA"))
        assert "San Francisco, CA" in prompt

    def test_contains_conversation_history(self):
        msgs = [
            {"sender": "ME", "body": "Congrats on the new role!", "createdAt": "2024-01-01T10:00:00Z"},
            {"sender": "CORRESPONDENT", "body": "Really appreciate it!", "createdAt": "2024-01-01T11:00:00Z"},
        ]
        prompt = create_analysis_prompt(make_conv_dict(messages=msgs))
        assert "Really appreciate it!" in prompt

    def test_contains_interexy_description(self):
        prompt = create_analysis_prompt(make_conv_dict())
        assert "Interexy" in prompt
        assert "Miami" in prompt

    def test_contains_vendor_approach_section(self):
        """Level 4.3 VENDOR APPROACH INFERENCE should be present."""
        prompt = create_analysis_prompt(make_conv_dict())
        assert "VENDOR APPROACH" in prompt.upper() or "vendor_approach_inference" in prompt

    def test_contains_timing_triggers_section(self):
        """Level 4.4 TIMING TRIGGERS should be present."""
        prompt = create_analysis_prompt(make_conv_dict())
        assert "TIMING TRIGGER" in prompt.upper() or "timing_triggers_analysis" in prompt

    def test_does_not_contain_no_thanks_response_strategy(self):
        """no_thanks_response_strategy is specific to the message generation step, not research."""
        prompt = create_analysis_prompt(make_conv_dict())
        assert "no_thanks_response_strategy" not in prompt

    def test_output_format_contains_vendor_approach_inference_key(self):
        prompt = create_analysis_prompt(make_conv_dict())
        assert "vendor_approach_inference" in prompt

    def test_output_format_contains_timing_triggers_analysis_key(self):
        prompt = create_analysis_prompt(make_conv_dict())
        assert "timing_triggers_analysis" in prompt

    def test_output_format_contains_rejection_analysis_key(self):
        prompt = create_analysis_prompt(make_conv_dict())
        assert "rejection_analysis" in prompt

    def test_output_format_contains_vendor_readiness_key(self):
        prompt = create_analysis_prompt(make_conv_dict())
        assert "vendor_readiness" in prompt

    def test_output_format_contains_executive_summary_key(self):
        prompt = create_analysis_prompt(make_conv_dict())
        assert "executive_summary" in prompt

    def test_contains_today_date(self):
        """Prompt should include a real date string (not a placeholder)."""
        from datetime import datetime
        today = datetime.utcnow().strftime('%Y-%m-%d')
        prompt = create_analysis_prompt(make_conv_dict())
        assert today in prompt

    def test_empty_messages_does_not_crash(self):
        prompt = create_analysis_prompt(make_conv_dict(messages=[]))
        assert "No message history" in prompt

    def test_fixture_conversation(self, conv_catchup_thanks):
        prompt = create_analysis_prompt(conv_catchup_thanks)
        assert "Sarah" in prompt
        assert "FinTech Inc" in prompt


# ---------------------------------------------------------------------------
# create_catchup_messages_prompt
# ---------------------------------------------------------------------------

class TestCreateCatchupMessagesPrompt:
    def test_returns_non_empty_string(self, minimal_analysis):
        prompt = create_catchup_messages_prompt(minimal_analysis, "John Smith", "TechCorp", "CTO")
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_contains_lead_name(self, minimal_analysis):
        prompt = create_catchup_messages_prompt(minimal_analysis, "Alice Walker", "FinCo", "VP")
        assert "Alice Walker" in prompt

    def test_uses_first_name_in_opening(self, minimal_analysis):
        """The prompt instructs starting with 'My pleasure, [FirstName]!'"""
        prompt = create_catchup_messages_prompt(minimal_analysis, "Thomas Edison", "LightBulb Inc", "CEO")
        assert "Thomas" in prompt

    def test_contains_company_name(self, minimal_analysis):
        prompt = create_catchup_messages_prompt(minimal_analysis, "John Smith", "UniqueCompanyXYZ", "CTO")
        assert "UniqueCompanyXYZ" in prompt

    def test_contains_json_output_template(self, minimal_analysis):
        prompt = create_catchup_messages_prompt(minimal_analysis, "John Smith", "TechCorp", "CTO")
        assert "recommended_top_3" in prompt
        assert '"messages"' in prompt

    def test_contains_message_categories(self, minimal_analysis):
        prompt = create_catchup_messages_prompt(minimal_analysis, "John Smith", "TechCorp", "CTO")
        assert "Synergy" in prompt or "synergy" in prompt
        assert "Question" in prompt or "question" in prompt

    def test_includes_pain_points_from_analysis(self, minimal_analysis):
        prompt = create_catchup_messages_prompt(minimal_analysis, "John Smith", "TechCorp", "CTO")
        assert "Scaling engineering team" in prompt

    def test_includes_fit_score(self, minimal_analysis):
        prompt = create_catchup_messages_prompt(minimal_analysis, "John Smith", "TechCorp", "CTO")
        assert "7" in prompt  # fit_score from minimal_analysis

    def test_accepts_optional_intent_param(self, minimal_analysis):
        """Should not raise when intent is passed."""
        prompt = create_catchup_messages_prompt(
            minimal_analysis, "John Smith", "TechCorp", "CTO", intent="interested"
        )
        assert isinstance(prompt, str)

    def test_empty_analysis_does_not_crash(self):
        prompt = create_catchup_messages_prompt({}, "John Smith", "TechCorp", "CTO")
        assert isinstance(prompt, str)


# ---------------------------------------------------------------------------
# create_no_thanks_messages_prompt
# ---------------------------------------------------------------------------

class TestCreateNoThanksMessagesPrompt:
    def test_returns_non_empty_string(self, minimal_analysis):
        prompt = create_no_thanks_messages_prompt(minimal_analysis, "Mark Davis", "SomeCo", "Director")
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_contains_lead_name(self, minimal_analysis):
        prompt = create_no_thanks_messages_prompt(minimal_analysis, "Karen Smith", "TestCo", "Manager")
        assert "Karen Smith" in prompt

    def test_uses_first_name(self, minimal_analysis):
        prompt = create_no_thanks_messages_prompt(minimal_analysis, "Thomas Clark", "BigCorp", "CTO")
        assert "Thomas" in prompt

    def test_contains_assumption_questions_type(self, minimal_analysis):
        prompt = create_no_thanks_messages_prompt(minimal_analysis, "Mark Davis", "SomeCo", "Director")
        assert "assumption" in prompt.lower() or "ASSUMPTION" in prompt

    def test_contains_clarification_type(self, minimal_analysis):
        prompt = create_no_thanks_messages_prompt(minimal_analysis, "Mark Davis", "SomeCo", "Director")
        assert "clarification" in prompt.lower() or "CLARIFICATION" in prompt

    def test_contains_future_focused_type(self, minimal_analysis):
        prompt = create_no_thanks_messages_prompt(minimal_analysis, "Mark Davis", "SomeCo", "Director")
        assert "future" in prompt.lower() or "timing" in prompt.lower()

    def test_contains_benchmark_type(self, minimal_analysis):
        prompt = create_no_thanks_messages_prompt(minimal_analysis, "Mark Davis", "SomeCo", "Director")
        assert "benchmark" in prompt.lower()

    def test_contains_alternative_angle_type(self, minimal_analysis):
        prompt = create_no_thanks_messages_prompt(minimal_analysis, "Mark Davis", "SomeCo", "Director")
        assert "alternative" in prompt.lower()

    def test_contains_json_output_template(self, minimal_analysis):
        prompt = create_no_thanks_messages_prompt(minimal_analysis, "Mark Davis", "SomeCo", "Director")
        assert "recommended_top_3" in prompt
        assert '"messages"' in prompt
        assert '"notes"' in prompt

    def test_includes_vendor_approach_data(self, minimal_analysis):
        prompt = create_no_thanks_messages_prompt(minimal_analysis, "Mark Davis", "SomeCo", "Director")
        assert "likely_hybrid" in prompt or "hybrid" in prompt.lower()

    def test_includes_timing_triggers_data(self, minimal_analysis):
        prompt = create_no_thanks_messages_prompt(minimal_analysis, "Mark Davis", "SomeCo", "Director")
        assert "Recent funding" in prompt or "triggered" in prompt

    def test_empty_analysis_does_not_crash(self):
        prompt = create_no_thanks_messages_prompt({}, "Mark Davis", "SomeCo", "Director")
        assert isinstance(prompt, str)

    def test_fixture_soft_objection(self, conv_soft_objection, minimal_analysis):
        """Smoke test: generate prompt for a soft_objection lead."""
        profile = conv_soft_objection["correspondentProfile"]
        prompt = create_no_thanks_messages_prompt(
            minimal_analysis,
            f"{profile['firstName']} {profile['lastName']}",
            profile["companyName"],
            profile["position"],
        )
        assert "Mark" in prompt
        assert isinstance(prompt, str)


# ---------------------------------------------------------------------------
# Cross-prompt: routing by intent should select different prompts
# ---------------------------------------------------------------------------

class TestPromptRoutingByIntent:
    """Simulates the pipeline's intent-based prompt selection logic."""

    def _select_prompt(self, intent: str, analysis: dict, lead_name: str,
                       lead_company: str, lead_position: str) -> str:
        if intent == "soft_objection":
            return create_no_thanks_messages_prompt(analysis, lead_name, lead_company, lead_position)
        else:
            return create_catchup_messages_prompt(analysis, lead_name, lead_company, lead_position, intent)

    def test_soft_objection_uses_no_thanks_prompt(self, minimal_analysis):
        prompt = self._select_prompt("soft_objection", minimal_analysis, "Mark", "Co", "Dir")
        assert "assumption" in prompt.lower() or "fair enough" in prompt.lower() or "no thanks" in prompt.lower()

    def test_catchup_thanks_uses_catchup_prompt(self, minimal_analysis):
        prompt = self._select_prompt("catchup_thanks", minimal_analysis, "John", "Co", "CTO")
        assert "Thank you" in prompt or "thank you" in prompt.lower() or "Synergy" in prompt

    def test_interested_uses_catchup_prompt(self, minimal_analysis):
        prompt = self._select_prompt("interested", minimal_analysis, "Anna", "Co", "PM")
        assert isinstance(prompt, str) and len(prompt) > 0

    def test_hard_rejection_uses_catchup_prompt_as_default(self, minimal_analysis):
        prompt = self._select_prompt("hard_rejection", minimal_analysis, "Bob", "Co", "VP")
        assert isinstance(prompt, str) and len(prompt) > 0

    def test_soft_objection_and_catchup_produce_different_prompts(self, minimal_analysis):
        no_thanks = self._select_prompt("soft_objection", minimal_analysis, "Lee", "Co", "CEO")
        catchup = self._select_prompt("catchup_thanks", minimal_analysis, "Lee", "Co", "CEO")
        assert no_thanks != catchup
