import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import time

load_dotenv()

HEYREACH_API_KEY = os.getenv('HEYREACH_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
LINKEDIN_ACCOUNT_ID = os.getenv('LINKEDIN_ACCOUNT_ID')

print("=" * 100)
print("🔄 BATCH PROCESSING - Full Framework Analysis & Message Generation")
print("=" * 100)


def load_leads_from_file(filename='leads.txt'):
    """Загружает список LinkedIn URLs из файла"""
    
    print(f"\n📥 Загрузка лидов из файла: {filename}")
    
    if not os.path.exists(filename):
        print(f"❌ Файл {filename} не найден!")
        print(f"   Создайте файл {filename} со списком LinkedIn URLs (по одному на строку)")
        return []
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    urls = []
    for line in lines:
        line = line.strip()
        
        if not line or line.startswith('#'):
            continue
        
        if not line.startswith('http'):
            line = f"https://www.linkedin.com/in/{line}/"
        
        line = line.rstrip('/')
        urls.append(line)
    
    print(f"✅ Загружено {len(urls)} лидов")
    
    return urls


def get_conversation_by_linkedin(linkedin_url):
    """Получает conversation конкретного лида"""
    
    print(f"\n   📥 Поиск диалога: {linkedin_url}")
    
    url = "https://api.heyreach.io/api/public/inbox/GetConversationsV2"
    
    headers = {
        "X-API-KEY": HEYREACH_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "filters": {
            "linkedInAccountIds": [LINKEDIN_ACCOUNT_ID],
            "leadProfileUrl": linkedin_url,
            "seen": None
        },
        "offset": 0,
        "limit": 1
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"      ❌ Ошибка API: {response.status_code}")
            return None
        
        data = response.json()
        conversations = data.get('items', [])
        
        if not conversations:
            print(f"      ⚠️ Диалог не найден")
            return None
        
        conversation = conversations[0]
        correspondent = conversation.get('correspondentProfile', {})
        lead_name = f"{correspondent.get('firstName', '')} {correspondent.get('lastName', '')}".strip()
        
        print(f"      ✅ Найден: {lead_name}")
        
        return conversation
        
    except requests.exceptions.RequestException as e:
        print(f"      ❌ Ошибка: {e}")
        return None


def create_full_framework_prompt(conversation):
    """Создает ПОЛНЫЙ FULL FRAMEWORK промпт для глубокого анализа"""
    
    correspondent = conversation.get('correspondentProfile', {})
    
    lead_name = f"{correspondent.get('firstName', '')} {correspondent.get('lastName', '')}".strip()
    lead_company = correspondent.get('companyName', 'Unknown Company')
    lead_position = correspondent.get('position', 'Unknown Position')
    lead_location = correspondent.get('location', '')
    lead_linkedin = correspondent.get('profileUrl', '')
    lead_headline = correspondent.get('headline', '')
    
    messages = conversation.get('messages', [])
    conversation_history = []
    
    for msg in messages:
        sender = "You" if msg.get('sender') == 'ME' else lead_name
        created_at = msg.get('createdAt', '')
        body = msg.get('body', '[no text]')
        
        try:
            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_str = date_obj.strftime('%Y-%m-%d %H:%M')
        except:
            date_str = created_at
        
        conversation_history.append(f"[{date_str}] {sender}: {body}")
    
    history_text = "\n".join(conversation_history) if conversation_history else "No message history"
    
    last_message = conversation.get('lastMessageText', '')
    last_message_at = conversation.get('lastMessageAt', '')
    total_messages = conversation.get('totalMessages', 0)
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    # === ПОЛНЫЙ FULL FRAMEWORK PROMPT (БЕЗ СОКРАЩЕНИЙ) ===
    prompt = f"""You are an expert B2B sales researcher for Interexy, a premium software development company.

ABOUT INTEREXY:
- Company: American software development firm (Miami HQ)
- Services: Senior-level developers (top 2% of market), team augmentation, custom development
- Expertise: Healthcare, Fintech, Blockchain/Web3, AI/ML, Energy
- Team: 350+ senior engineers across US, Poland, Estonia, UAE
- Notable clients: RWE, E.ON (energy sector), healthcare & fintech companies
- Guarantee: 10-day engineer replacement, high-quality code standards

YOUR TASK:
Analyze this B2B lead using the RESEARCH FRAMEWORK below. Use web search extensively to gather current information. Return findings in structured JSON format.

=== LEAD INFORMATION ===
Name: {lead_name}
Company: {lead_company}
Position: {lead_position}
Location: {lead_location}
LinkedIn: {lead_linkedin}
Headline: {lead_headline}

=== CONVERSATION HISTORY ===
{history_text}

Last message: {last_message}
Date: {last_message_at}
Total messages: {total_messages}

=== RESEARCH FRAMEWORK ===

LEVEL 1: PERSONAL PROFILE ANALYSIS (LinkedIn)

1.1 CURRENT ROLE ANALYSIS
Use web search to find:
✓ Position: exact title
✓ Time in role: months/years
✓ Department: sales/product/tech/ops/etc
✓ Reports to: who (CEO/CTO/etc)
✓ Team size: if mentioned (10 direct reports = manager level)

WHAT THIS GIVES YOU:
- New role (<6 months) → "congrats on new role" opener, usually open to new tools
- Long in role (2+ years) → expert, ask for insights
- Head of/Director → strategic questions
- VP/C-level → high-level business impact questions

1.2 CAREER TRAJECTORY
Use web search to find:
✓ Previous companies: where they worked
✓ Industry switches: fintech → healthcare = interesting
✓ Role progression: engineer → manager → director
✓ Time at each role: job hopper vs. stable

WHAT THIS GIVES YOU:
- Industry switchers = ask "what's different between X and Y industry?"
- Rapid progression = ambitious, growth-focused
- Similar backgrounds = "I see you also worked at..."

1.3 ACTIVITY & SIGNALS
Use web search to find:
✓ Recent posts: what they post about
✓ #HIRING badge: hiring = potential need
✓ #OPEN_TO_WORK: job seeking = different approach
✓ Event speaking: conferences = thought leader
✓ Recent certifications: learning mode

WHAT THIS GIVES YOU:
- Hiring = "saw you're hiring for X, curious about..."
- Recent posts = conversation starter
- Speaking = "saw your talk at X conference"

LEVEL 2: COMPANY BASICS (LinkedIn Company Page + Web)

2.1 COMPANY BASICS
Use web search to find:
✓ Founded: year
✓ Size: employee count
✓ Locations: HQ + offices
✓ Industry: actual industry
✓ Stage: startup/growth/enterprise

WHAT THIS GIVES YOU:
- Startup (<50 people, <3 years) → growth pain points, scaling questions
- Scaleup (50-500, 3-7 years) → platform optimization, team expansion
- Enterprise (500+, 7+ years) → modernization, legacy system questions

2.2 RECENT COMPANY ACTIVITY
Use web search to find:
✓ Recent posts: hiring/product launches/awards
✓ Job openings: which roles they're hiring
✓ Team growth: compare employee count vs 3 months ago
✓ New locations: expansion signals

WHAT THIS GIVES YOU:
- 5+ open engineering roles = scaling tech team
- New office = expansion mode
- Awards/recognition = "congrats on X award" opener

LEVEL 3: DEEP RESEARCH (Web Search Required)

3.1 FUNDING & GROWTH
Search query: "{lead_company} funding round 2025 2026"
Find:
✓ Last funding: Series A/B/C, amount, date
✓ Total raised: $X million
✓ Investors: who backed them
✓ Valuation: if public
✓ Revenue: if mentioned in articles

WHAT THIS GIVES YOU:
- Recent funding (<6 months) → "congrats on Series B! As you scale with new capital, what's the biggest tech challenge?"
- No recent funding + growing → bootstrapped, cost-conscious
- Big name investors → "saw a16z backed you, interesting"

3.2 PRODUCT & TECH STACK
Search queries:
- "{lead_company} product launch 2025 2026"
- "{lead_company} tech stack"
- "{lead_company} platform technology"

Find:
✓ Main product: what they sell
✓ Recent launches: new features/products
✓ Tech mentioned: React/Python/blockchain/AI
✓ Integrations: Stripe/Salesforce/etc
✓ Platform type: SaaS/marketplace/infrastructure

WHAT THIS GIVES YOU:
- Recent launch = "saw you launched X, curious about adoption"
- Tech stack visible = technical questions
- Platform type = specific pain points (marketplace scaling, SaaS onboarding, etc)

3.3 NEWS & RECENT DEVELOPMENTS
Search query: "{lead_company} news 2025 2026"
Find:
✓ Partnerships announced: with who, when
✓ Acquisitions: bought/sold
✓ Product milestones: user count, revenue
✓ Industry awards: recognition
✓ Executive changes: new CEO/CTO
✓ Controversies: if any - be careful

WHAT THIS GIVES YOU:
- Partnership announcement = "saw the Stripe partnership, curious how..."
- Acquisition = "congrats on acquiring X, integration challenges?"
- Milestones = "1M users is impressive, what's next?"

3.4 COMPETITIVE LANDSCAPE
Search query: "{lead_company} competitors alternatives"
Find:
✓ Direct competitors: who they compete with
✓ Market position: leader/challenger/niche
✓ Differentiation: what makes them unique
✓ Market trends: industry growing/declining

WHAT THIS GIVES YOU:
- "How do you differentiate from [competitor]?"
- "Market seems crowded - what's your moat?"
- Shows you understand their space

3.5 REGULATORY & INDUSTRY CONTEXT
Search queries based on industry:
- Fintech: "CSRD MiCA regulations EU 2026"
- Healthcare: "HIPAA compliance digital health 2025 2026"
- Circular economy: "EPR extended producer responsibility EU 2025 2026"
- Crypto: "MiCA stablecoin regulations 2025 2026"
- Energy: "{lead_company} industry renewable energy transition 2025 2026"

Find:
✓ Recent regulations: what changed
✓ Compliance requirements: new mandates
✓ Industry trends: what's hot
✓ Market drivers: what's pushing change

WHAT THIS GIVES YOU:
- Timely, relevant questions
- Shows deep industry knowledge
- Opens compliance/tech discussion

LEVEL 4: PAIN POINT MAPPING

4.1 ROLE-SPECIFIC PAIN POINTS

Analyze based on position title:

HEAD OF DIGITAL/INNOVATION likely faces:
- Platform scaling challenges
- Legacy system integration
- Team capacity (build vs buy decisions)
- Innovation speed pressures
- Tech debt management

PRODUCT MANAGER likely faces:
- Feature velocity demands
- User feedback integration
- A/B testing infrastructure
- Technical feasibility assessments
- Cross-functional alignment issues

CEO/FOUNDER likely faces:
- Capital efficiency concerns
- Time to market pressures
- Team scaling challenges
- Product-market fit validation
- Go-to-market strategy

CTO/ENGINEERING LEAD likely faces:
- Technical debt accumulation
- Team productivity optimization
- Architecture decisions
- Hiring senior talent
- System reliability/uptime

4.2 STAGE-SPECIFIC PAIN POINTS

EARLY STAGE STARTUP (<2 years, Seed):
- MVP development speed
- Finding product-market fit
- Limited engineering resources
- Capital efficiency
- Rapid iteration needs

GROWTH STAGE (Series A/B, 2-5 years):
- Scaling infrastructure
- Team expansion (10x growth)
- Platform stability
- Feature velocity vs tech debt
- Customer success scaling

SCALE-UP (Series C+, 5+ years):
- Legacy modernization
- Enterprise features
- Compliance/security requirements
- Geographic expansion
- M&A integration

=== OUTPUT FORMAT ===

Return ONLY valid JSON with this EXACT structure:

{{
  "lead_profile": {{
    "current_role": {{
      "title": "exact position",
      "time_in_role": "X months/years",
      "department": "sales/product/tech/ops",
      "reports_to": "CEO/CTO/etc or unknown",
      "team_size": "number or unknown",
      "insight": "what this tells us about their priorities"
    }},
    "career_trajectory": {{
      "previous_companies": ["Company 1", "Company 2"],
      "industry_switches": "any notable industry changes",
      "progression": "engineer->manager->director pattern",
      "insight": "what this tells us about their ambition/focus"
    }},
    "activity_signals": {{
      "hiring": true,
      "recent_posts_topics": ["topic1", "topic2"],
      "speaking_events": ["event1 if any"],
      "certifications": ["recent cert if any"],
      "insight": "best conversation hooks from activity"
    }}
  }},
  
  "company_basics": {{
    "founded": "year",
    "size": "employee count",
    "locations": ["location1", "location2"],
    "industry": "actual industry",
    "stage": "startup/growth/enterprise",
    "stage_insight": "what pain points this stage typically has"
  }},
  
  "company_activity": {{
    "recent_hiring": {{
      "open_roles_count": 0,
      "key_roles": ["role1", "role2"],
      "insight": "what this hiring pattern suggests"
    }},
    "team_growth": "growing/stable/shrinking",
    "expansion": ["new office location if any"],
    "awards": ["recent award if any"]
  }},
  
  "deep_research": {{
    "funding": {{
      "last_round": "Series X, $Y million, date",
      "total_raised": "$X million",
      "investors": ["investor1", "investor2"],
      "funding_insight": "what recent funding means for outreach"
    }},
    "product": {{
      "main_product": "what they sell",
      "recent_launches": [
        {{
          "name": "feature/product name",
          "date": "YYYY-MM-DD",
          "description": "brief description"
        }}
      ],
      "tech_stack": ["React", "Python", "AWS"],
      "platform_type": "SaaS/marketplace/infrastructure",
      "product_insight": "technical conversation hooks"
    }},
    "news": [
      {{
        "date": "YYYY-MM-DD",
        "headline": "headline",
        "summary": "brief summary",
        "source": "source URL",
        "outreach_hook": "how to use this in conversation"
      }}
    ],
    "competitive_landscape": {{
      "competitors": ["competitor1", "competitor2"],
      "market_position": "leader/challenger/niche",
      "differentiation": "what makes them unique",
      "market_trend": "growing/stable/declining"
    }},
    "regulatory_context": {{
      "recent_regulations": [
        {{
          "regulation": "regulation name",
          "impact": "how it affects company",
          "date": "when it takes effect"
        }}
      ],
      "compliance_requirements": ["requirement1"],
      "industry_trend": "what's driving change in industry"
    }}
  }},
  
  "pain_point_analysis": {{
    "role_specific_pain_points": [
      "pain point 1 based on their role",
      "pain point 2",
      "pain point 3"
    ],
    "stage_specific_pain_points": [
      "pain point 1 based on company stage",
      "pain point 2",
      "pain point 3"
    ],
    "evidence_from_research": [
      "evidence 1 from news/hiring/etc",
      "evidence 2"
    ]
  }},
  
  "conversation_analysis": {{
    "conversation_stage": "initial_response/engaged/qualification/negotiation",
    "messages_exchanged": 0,
    "lead_responsiveness": "high/medium/low",
    "interest_signals": ["signal1 from messages", "signal2"],
    "objections_raised": ["objection1 if any"],
    "questions_asked": ["question1 if any"]
  }},
  
  "qualification": {{
    "status": "qualified/partially_qualified/not_qualified/too_early",
    "fit_score": 5,
    "reasoning": "why this qualification status",
    "budget_indicator": "high/medium/low/unknown",
    "authority_level": "decision_maker/influencer/user/unknown",
    "need_urgency": "high/medium/low/none_detected"
  }},
  
  "recommended_action": {{
    "next_step": "specific action with timeframe",
    "message_angle": "which angle to use in next message",
    "personalization_hooks": [
      "hook 1 with context why it works",
      "hook 2 with context",
      "hook 3 with context"
    ],
    "questions_to_ask": [
      "question 1 based on research",
      "question 2",
      "question 3"
    ],
    "timing": "when to reach out (now/wait X days/specific trigger)",
    "priority": "high/medium/low"
  }},
  
  "interexy_value_props": {{
    "most_relevant": [
      "value prop 1 based on their pain points",
      "value prop 2",
      "value prop 3"
    ],
    "case_studies_to_mention": [
      "RWE/E.ON energy sector work if relevant",
      "Other relevant case study"
    ],
    "technical_expertise_highlight": "which tech expertise to emphasize"
  }},
  
  "executive_summary": "2-3 sentence summary of lead quality, key insights, and recommended approach"
}}

IMPORTANT INSTRUCTIONS:
1. Use web search extensively - search for company news, funding, product launches, regulatory context
2. Find REAL information with REAL sources and dates
3. If information not found, say "not found" - don't invent
4. Focus on RECENT information (last 12 months prioritized)
5. Provide specific, actionable insights - not generic
6. Match pain points to REAL evidence from research
7. Return ONLY valid JSON, no markdown blocks, no extra text
8. Today's date for reference: {today_date}"""
    
    return prompt, lead_name, lead_company


def analyze_with_openai(prompt, lead_name):
    """Анализирует через OpenAI с web search"""
    
    print(f"      🤖 ANALYSIS через OpenAI (с web search)...")
    
    url = "https://api.openai.com/v1/responses"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o",
        "tools": [{"type": "web_search"}],  # ← WEB SEARCH ВКЛЮЧЕН
        "input": prompt
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=180)
        
        if response.status_code != 200:
            print(f"      ❌ OpenAI error: {response.status_code}")
            return None
        
        data = response.json()
        
        # Извлекаем текст
        output_array = data.get('output', [])
        output_text = ""
        
        for item in output_array:
            if item.get('type') == 'message':
                content_array = item.get('content', [])
                for content_item in content_array:
                    if content_item.get('type') == 'output_text':
                        output_text = content_item.get('text', '')
                        break
                if output_text:
                    break
        
        if not output_text:
            print(f"      ❌ No output_text")
            return None
        
        # Парсим JSON
        output_text = output_text.replace('```json', '').replace('```', '').strip()
        json_start = output_text.find('{')
        json_end = output_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            output_text = output_text[json_start:json_end]
        
        analysis = json.loads(output_text)
        print(f"      ✅ Analysis готов")
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"      ❌ JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return None


def generate_messages_prompt(analysis, metadata):
    """Создает ПОЛНЫЙ промпт для генерации сообщений"""
    
    lead_name = metadata.get('lead_name', 'Unknown')
    lead_company = metadata.get('lead_company', 'Unknown')
    lead_position = metadata.get('lead_position', 'Unknown')
    
    qual = analysis.get('qualification', {})
    company = analysis.get('company_basics', {})
    pain_points = analysis.get('pain_point_analysis', {})
    deep_research = analysis.get('deep_research', {})
    recommended = analysis.get('recommended_action', {})
    value_props = analysis.get('interexy_value_props', {})
    
    # === ПОЛНЫЙ MESSAGE GENERATION PROMPT (БЕЗ СОКРАЩЕНИЙ) ===
    prompt = f"""You are an expert B2B sales copywriter for Interexy (software development company).

CONTEXT:
We've analyzed this lead and now need to generate follow-up messages after they responded "Thank you" to a congratulations message (birthday/new role/etc).

LEAD INFORMATION:
Name: {lead_name}
Company: {lead_company}
Position: {lead_position}

ANALYSIS SUMMARY:
Qualification Status: {qual.get('status', 'N/A')}
Fit Score: {qual.get('fit_score', 0)}/10
Company Stage: {company.get('stage', 'N/A')}
Company Size: {company.get('size', 'N/A')}

PAIN POINTS IDENTIFIED:
Role-Specific:
{chr(10).join(f"- {p}" for p in pain_points.get('role_specific_pain_points', []))}

Stage-Specific:
{chr(10).join(f"- {p}" for p in pain_points.get('stage_specific_pain_points', []))}

RECENT NEWS/CONTEXT:
{json.dumps(deep_research.get('news', [])[:2], indent=2)}

FUNDING INFO:
{json.dumps(deep_research.get('funding', {}), indent=2)}

RECOMMENDED APPROACH:
Next Step: {recommended.get('next_step', 'N/A')}
Message Angle: {recommended.get('message_angle', 'N/A')}

PERSONALIZATION HOOKS:
{chr(10).join(f"- {hook}" for hook in recommended.get('personalization_hooks', []))}

INTEREXY VALUE PROPS TO EMPHASIZE:
{chr(10).join(f"- {vp}" for vp in value_props.get('most_relevant', []))}

---

TASK:
Generate 10-15 follow-up message variants that naturally transition from "Thank you" → Business conversation.

SUCCESSFUL PATTERNS FROM EXAMPLES:

PATTERN 1 - SYNERGY APPROACH:
"My pleasure, [Name]!
Saw you're [doing X]. We work with [similar companies] who need [Y] - could be synergy there?"

PATTERN 2 - CHALLENGE QUESTION:
"My pleasure, [Name]!
Quick question - with your new [role/scope], are you looking to [expand/build/scale] [X] this year?"

PATTERN 3 - STRATEGIC INSIGHT:
"My pleasure, [Name]!
As you [scale/launch/expand], what's been the biggest [challenge/bottleneck] with [specific area]?"

PATTERN 4 - SOFT FOLLOW-UP:
"My pleasure, [Name]!
Not looking to pitch anything - just curious: what's the biggest [tech/product/team] challenge for [Company] right now?"

PATTERN 5 - INDUSTRY TREND:
"My pleasure, [Name]!
Are you seeing [specific trend] accelerate in [industry], or still early days?"

PATTERN 6 - DIRECT VALUE PROP:
"My pleasure, [Name]!
We work with [industry] companies scaling [specific challenge]. Worth a quick chat?"

GENERATE 10-15 VARIANTS covering these message types:

1. **Synergy-based** (2-3 variants)
   - Focus on overlap between what they do and what we offer
   
2. **Question-based** (3-4 variants)
   - Strategic questions about challenges, priorities, trends
   
3. **Insight-based** (2-3 variants)
   - Show understanding of their situation, ask about specific pain points
   
4. **Soft touch** (2-3 variants)
   - "Not selling, just curious" approach
   
5. **Direct value prop** (2-3 variants)
   - Clear about what we do and how we help

REQUIREMENTS:
- Keep messages SHORT (2-3 sentences max)
- Natural, conversational tone
- Start with "My pleasure, [FirstName]!" or "Glad to hear, [FirstName]!"
- Use personalization hooks from analysis
- Reference REAL information (news, funding, role, challenges)
- NO generic statements
- Each variant should feel different

OUTPUT FORMAT:
Return ONLY valid JSON:

{{
  "messages": [
    {{
      "id": 1,
      "type": "synergy",
      "message": "full message text here",
      "rationale": "why this works for this lead",
      "best_for": "what situation/response triggers this",
      "follow_up_ready": true
    }},
    ...
  ],
  "recommended_top_3": [1, 5, 8],
  "notes": "overall strategy notes for this lead"
}}

IMPORTANT:
- Use REAL data from analysis (company name, position, news, funding)
- Match message sophistication to lead's seniority
- Reference specific context (recent funding, new role, company stage)
- Return ONLY JSON, no markdown blocks"""
    
    return prompt


def generate_messages(prompt):
    """Генерирует сообщения через OpenAI БЕЗ web search"""
    
    print(f"      💬 MESSAGE GENERATION через OpenAI (без web search)...")
    
    url = "https://api.openai.com/v1/responses"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o",
        "tools": [],  # ← БЕЗ WEB SEARCH
        "input": prompt
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        
        if response.status_code != 200:
            print(f"      ❌ OpenAI error: {response.status_code}")
            return None
        
        data = response.json()
        
        # Извлекаем текст
        output_array = data.get('output', [])
        output_text = ""
        
        for item in output_array:
            if item.get('type') == 'message':
                content_array = item.get('content', [])
                for content_item in content_array:
                    if content_item.get('type') == 'output_text':
                        output_text = content_item.get('text', '')
                        break
                if output_text:
                    break
        
        if not output_text:
            return None
        
        # Парсим JSON
        output_text = output_text.replace('```json', '').replace('```', '').strip()
        json_start = output_text.find('{')
        json_end = output_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            output_text = output_text[json_start:json_end]
        
        messages_data = json.loads(output_text)
        print(f"      ✅ Messages готовы ({len(messages_data.get('messages', []))} вариантов)")
        return messages_data
        
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return None


def save_batch_results(results):
    """Сохраняет результаты batch обработки с ВСЕМИ сообщениями"""
    
    batch_dir = "batch_results"
    if not os.path.exists(batch_dir):
        os.makedirs(batch_dir)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # === 1. Сохраняем полный JSON ===
    json_filename = f"{batch_dir}/batch_{timestamp}.json"
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Full JSON: {json_filename}")
    
    # === 2. Создаем читаемый summary с ВСЕМИ вариантами сообщений ===
    txt_filename = f"{batch_dir}/batch_{timestamp}_summary.txt"
    
    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("BATCH PROCESSING RESULTS - FULL FRAMEWORK\n")
        f.write("=" * 100 + "\n\n")
        
        f.write(f"Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total leads: {results['total_leads']}\n")
        f.write(f"Successful: {results['successful']}\n")
        f.write(f"Failed: {results['failed']}\n")
        f.write(f"Total cost: ~${results['estimated_cost']:.2f}\n\n")
        
        # === УСПЕШНЫЕ ЛИДЫ ===
        f.write("=" * 100 + "\n")
        f.write("SUCCESSFUL LEADS - DETAILED REPORTS\n")
        f.write("=" * 100 + "\n\n")
        
        for lead in results['leads']:
            if lead['status'] == 'success':
                f.write("\n" + "=" * 100 + "\n")
                f.write(f"LEAD: {lead['lead_name']} @ {lead['lead_company']}\n")
                f.write("=" * 100 + "\n\n")
                
                f.write(f"LinkedIn: {lead['linkedin_url']}\n")
                f.write(f"Position: {lead.get('lead_position', 'N/A')}\n")
                f.write(f"Qualification: {lead.get('qualification', 'N/A')}\n")
                f.write(f"Fit Score: {lead.get('fit_score', 0)}/10\n\n")
                
                f.write("-" * 100 + "\n")
                f.write("EXECUTIVE SUMMARY\n")
                f.write("-" * 100 + "\n")
                f.write(f"{lead.get('executive_summary', 'N/A')}\n\n")
                
                # === ВСЕ ВАРИАНТЫ СООБЩЕНИЙ ===
                messages_data = lead.get('messages_data', {})
                messages = messages_data.get('messages', [])
                recommended = messages_data.get('recommended_top_3', [])
                
                if messages:
                    f.write("-" * 100 + "\n")
                    f.write(f"FOLLOW-UP MESSAGES ({len(messages)} variants)\n")
                    f.write("-" * 100 + "\n\n")
                    
                    # Top 3 сначала
                    if recommended:
                        f.write("⭐ TOP 3 RECOMMENDED:\n\n")
                        for msg_id in recommended:
                            for msg in messages:
                                if msg.get('id') == msg_id:
                                    f.write(f"#{msg_id} [{msg.get('type', '').upper()}]\n")
                                    f.write(f"{msg.get('message', '')}\n")
                                    f.write(f"💡 {msg.get('rationale', '')}\n\n")
                        f.write("\n")
                    
                    # Все варианты по категориям
                    types = {}
                    for msg in messages:
                        msg_type = msg.get('type', 'other')
                        if msg_type not in types:
                            types[msg_type] = []
                        types[msg_type].append(msg)
                    
                    f.write("ALL VARIANTS BY TYPE:\n\n")
                    
                    for msg_type, msgs in sorted(types.items()):
                        f.write(f"--- {msg_type.upper()} ({len(msgs)} variants) ---\n\n")
                        
                        for msg in msgs:
                            f.write(f"#{msg.get('id', '?')}:\n")
                            f.write(f"{msg.get('message', '')}\n")
                            f.write(f"Rationale: {msg.get('rationale', '')}\n")
                            f.write(f"Best for: {msg.get('best_for', '')}\n")
                            f.write(f"Follow-up ready: {'Yes' if msg.get('follow_up_ready') else 'No'}\n\n")
                    
                    # Strategy notes
                    notes = messages_data.get('notes', '')
                    if notes:
                        f.write("-" * 100 + "\n")
                        f.write("STRATEGY NOTES:\n")
                        f.write(f"{notes}\n\n")
                
                f.write("\n")
        
        # === FAILED LEADS ===
        if results['failed'] > 0:
            f.write("\n" + "=" * 100 + "\n")
            f.write("FAILED LEADS\n")
            f.write("=" * 100 + "\n\n")
            
            for lead in results['leads']:
                if lead['status'] == 'failed':
                    f.write(f"❌ {lead['linkedin_url']}\n")
                    f.write(f"   Reason: {lead.get('error', 'Unknown error')}\n\n")
        
        f.write("=" * 100 + "\n")
        f.write("END OF BATCH REPORT\n")
        f.write("=" * 100 + "\n")
    
    print(f"💾 Summary TXT: {txt_filename}")
    
    return json_filename, txt_filename


def process_single_lead(linkedin_url):
    """Обрабатывает одного лида: HeyReach → Analysis → Messages"""
    
    result = {
        'linkedin_url': linkedin_url,
        'status': 'failed',
        'lead_name': None,
        'lead_company': None,
        'lead_position': None,
        'error': None
    }
    
    # === ШАГ 1: HeyReach - Получаем conversation ===
    conversation = get_conversation_by_linkedin(linkedin_url)
    
    if not conversation:
        result['error'] = 'Conversation not found in HeyReach'
        return result
    
    correspondent = conversation.get('correspondentProfile', {})
    lead_name = f"{correspondent.get('firstName', '')} {correspondent.get('lastName', '')}".strip()
    lead_company = correspondent.get('companyName', 'Unknown')
    lead_position = correspondent.get('position', 'Unknown')
    
    result['lead_name'] = lead_name
    result['lead_company'] = lead_company
    result['lead_position'] = lead_position
    
    # === ШАГ 2: GPT Analysis с web search ===
    prompt, _, _ = create_full_framework_prompt(conversation)
    analysis = analyze_with_openai(prompt, lead_name)
    
    if not analysis:
        result['error'] = 'Analysis failed'
        return result
    
    result['analysis'] = analysis
    result['qualification'] = analysis.get('qualification', {}).get('status', 'N/A')
    result['fit_score'] = analysis.get('qualification', {}).get('fit_score', 0)
    result['executive_summary'] = analysis.get('executive_summary', '')
    
    # === ШАГ 3: GPT Messages БЕЗ web search (использует результат analysis) ===
    metadata = {
        'lead_name': lead_name,
        'lead_company': lead_company,
        'lead_position': lead_position
    }
    
    msg_prompt = generate_messages_prompt(analysis, metadata)
    messages_data = generate_messages(msg_prompt)
    
    if not messages_data:
        result['error'] = 'Message generation failed'
        return result
    
    result['messages_data'] = messages_data
    result['status'] = 'success'
    
    return result


# === MAIN FLOW ===

print("\n" + "=" * 100)
print("STEP 1: Загрузка списка лидов")
print("=" * 100)

linkedin_urls = load_leads_from_file('leads.txt')

if not linkedin_urls:
    print("\n❌ Нет лидов для обработки")
    exit(1)

print("\n" + "=" * 100)
print(f"STEP 2: Обработка {len(linkedin_urls)} лидов")
print("=" * 100)
print("⏳ Примерно 2-3 минуты на лид")
print("   (HeyReach → Analysis с web search → Messages)")
print()

results = {
    'processed_at': datetime.now().isoformat(),
    'total_leads': len(linkedin_urls),
    'successful': 0,
    'failed': 0,
    'estimated_cost': 0,
    'leads': []
}

start_time = time.time()

for idx, linkedin_url in enumerate(linkedin_urls, 1):
    print(f"\n{'='*100}")
    print(f"[{idx}/{len(linkedin_urls)}] Processing: {linkedin_url}")
    print(f"{'='*100}")
    
    lead_result = process_single_lead(linkedin_url)
    results['leads'].append(lead_result)
    
    if lead_result['status'] == 'success':
        results['successful'] += 1
        results['estimated_cost'] += 0.10  # ~$0.10 per lead (full framework)
        print(f"      ✅ SUCCESS: {lead_result['lead_name']} (Fit: {lead_result['fit_score']}/10)")
    else:
        results['failed'] += 1
        print(f"      ❌ FAILED: {lead_result.get('error', 'Unknown')}")
    
    # Rate limiting
    if idx < len(linkedin_urls):
        print(f"\n      ⏸️  Пауза 5 секунд...")
        time.sleep(5)

elapsed_time = time.time() - start_time

print("\n" + "=" * 100)
print("STEP 3: Сохранение результатов")
print("=" * 100)

json_file, txt_file = save_batch_results(results)

print("\n" + "=" * 100)
print("✅ BATCH PROCESSING ЗАВЕРШЕН!")
print("=" * 100)

print(f"\n📊 СТАТИСТИКА:")
print(f"   Всего лидов: {results['total_leads']}")
print(f"   Успешно: {results['successful']} ✅")
print(f"   Не удалось: {results['failed']} ❌")
print(f"   Время: {int(elapsed_time/60)} мин {int(elapsed_time%60)} сек")
print(f"   Примерная стоимость: ${results['estimated_cost']:.2f}")

if results['successful'] > 0:
    print(f"\n📁 РЕЗУЛЬТАТЫ:")
    print(f"   • JSON (полный): {json_file}")
    print(f"   • TXT (с ВСЕМИ вариантами сообщений): {txt_file}")
    
    print(f"\n🎯 TOP QUALIFIED LEADS:")
    qualified = [l for l in results['leads'] if l['status'] == 'success' and l.get('fit_score', 0) >= 7]
    qualified.sort(key=lambda x: x.get('fit_score', 0), reverse=True)
    
    for lead in qualified[:5]:
        print(f"   • {lead['lead_name']} @ {lead['lead_company']} (Fit: {lead['fit_score']}/10)")
        # Показываем топ сообщение
        messages_data = lead.get('messages_data', {})
        recommended = messages_data.get('recommended_top_3', [])
        if recommended:
            top_msg_id = recommended[0]
            for msg in messages_data.get('messages', []):
                if msg.get('id') == top_msg_id:
                    print(f"     Top message: {msg.get('message', '')[:80]}...")
                    break

print("\n" + "=" * 100)