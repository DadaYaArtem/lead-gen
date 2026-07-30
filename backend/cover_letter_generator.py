# cover_letter_generator.py
import os
import asyncio
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
import sys
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import rag

# Загрузка переменных окружения (локально из .env, на Railway — системные env vars)
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

MAX_HOURS_PER_WEEKS = 40
MIN_DURATION_MONTHS = 2

# ----------------------------------------------------------------------
# 1. Профили пользователей (полные данные)
# ----------------------------------------------------------------------
user_profiles = [
    {
        "name": "Tilek Chubakov",
        "position": "Senior AI/ML Engineer, AI Agents, LLM, MLOps, Lead Data Engineer",
        "skills": [
            "ETL/ELT pipelines with dbt and scalable data warehousing",
            "Data lake and lakehouse architectures for analytics and ML",
            "High-performance data systems optimized for cost and latency",
            "AWS, Google Cloud, and Microsoft Azure infrastructure",
            "Docker and Kubernetes for scalable deployments",
            "CI/CD pipelines with GitHub Actions and GitLab CI/CD",
            "Event-driven systems with Kinesis, Event Hubs, and RabbitMQ",
            "Docker, AWS, RAG, LangChain, LLM fine-tuning",
            "Hugging Face Transformers",
            "Prompt engineering, tool usage, and context-aware pipelines",
            "Autonomous workflows integrating APIs, databases, and enterprise systems",
            "Real-time decision systems replacing manual operations",
            "End-to-end ML pipelines with MLflow and Kubeflow",
            "Time-series forecasting with Prophet and ARIMA",
            "Gradient boosting using XGBoost, LightGBM, and CatBoost",
            "Deep learning with PyTorch and TensorFlow on GPU infrastructure",
            "Supervised and unsupervised learning for anomaly detection, fraud detection, and risk modeling",
            "Named entity recognition, classification, and semantic search",
            "Knowledge retrieval systems and question-answering pipelines",
            "Contract analysis, invoice automation, and compliance validation",
            "Multilingual NLP and morphologically rich language processing",
            "Batch and streaming pipelines using Apache Spark, Apache Kafka, and Apache Airflow",
            "Cloud-native architectures with BigQuery, Dataflow, Pub/Sub, and Snowflake",
            "Hadoop, Hive, Spark (Databricks), Kafka (Confluent), Airflow, DataFlow, Pub/Sub, Kinesis, RabbitMQ, Event Hubs, NiFi, Stitch, Great Expectations",
            "Apache Superset, Tableau, Looker, Power BI",
            "Python, C#, Scala, Java, R, JavaScript, VB.NET, C/C++, shell scripting",
            "sci-kit learn, PyTorch, TensorFlow, Kubeflow, MLflow",
            "Snowflake, MySQL, PostgreSQL, MS SQL Server, MongoDB, Cassandra, HBase, Oracle, Redis, Amazon Redshift",
            "AWS (EC2, S3, RDS, Lambda, Redshift, Glue, Kinesis)",
            "Azure (Function Apps, Event Hubs, Data Explorer, Storage)",
            "GCP (Cloud Functions, Pub/Sub, BigQuery, Cloud Run)",
            "HTML/CSS, React, Node.js, Flask, Express, FastAPI",
            "Docker, Kubernetes, Terraform",
            "Git, GitLab CI/CD, GitHub Actions, dbt, Fivetran, CircleCI, SSIS, CDK"
        ],
        "min_salary_per_hour_usd": 50,
        "priority_cases": [
            "Scale AI", "Arcade", "Deverus", "Generative AI Marketplace",
            "AI Identity Verification", "CryptoPay", "LLM Chatbot & RAG System",
            "AI Document Processing", "FinTech Payment System"
        ],
        "portfolio_link": "https://github.com/tilekchubakov"
    },
    {
        "name": "Victoria",
        "position": "Senior Full-Stack Developer, React, Node.js, Scalable SaaS",
        "skills": [
            "Full-stack development with React and Node.js for scalable web applications",
            "Frontend engineering with React, Next.js, TypeScript, Redux, Tailwind CSS",
            "Backend development using Node.js and Express.js for REST API architecture",
            "SaaS platform development with multi-tenant systems and cloud infrastructure",
            "Database design with PostgreSQL and MongoDB, including performance optimization",
            "API integrations, authentication, and secure data handling",
            "Cloud deployment with AWS, Docker, and CI/CD pipelines",
            "Cross-platform development using Flutter and React Native"
        ],
        "min_salary_per_hour_usd": 40,
        "min_salary_agency_usd": 35,
        "priority_cases": [
            "Deverus", "Compassly", "Arcade", "Solstice",
            "FlexCare", "Classful", "Garantme",
            "NFT Ticketing", "Flink", "A Little Dose of Happy"
        ]
    },
    {
        "name": "Vicode Solutions",
        "position": "Full-Cycle Software Development Agency, React, Node.js, Scalable SaaS, 350+ developers",
        "skills": [
            "Responsive, high-performance interfaces using React, Next.js, TypeScript, Redux, and Tailwind CSS - clean architecture, intuitive UX, and optimized performance",
            "Robust server-side systems with Node.js and Express.js, secure RESTful APIs, and scalable infrastructures powered by PostgreSQL and MongoDB",
            "Authentication systems, third-party service integrations, and cloud deployment with CI/CD pipelines",
            "Full-stack SaaS application development",
            "React & Next.js frontend architecture",
            "Node.js backend systems and REST API design",
            "Database modeling with PostgreSQL and MongoDB",
            "Multi-tenant platforms and subscription-based products",
            "Payment integrations and secure authentication",
            "Cloud infrastructure and DevOps workflows"
        ],
        "min_salary_per_hour_usd": 35,
        "priority_cases": [
            "Deverus", "Compassly", "Arcade", "Solstice",
            "FlexCare", "Classful", "Garantme",
            "NFT Ticketing", "Flink", "A Little Dose of Happy"
        ],
        "portfolio_link": "vicode.solutions/portfolio"
    },
]

# ----------------------------------------------------------------------
# 3. Базовые правила отбора работы
# ----------------------------------------------------------------------
selection_rules = {
    "min_duration_months": 2,
    "preferred_work_hours_per_week": 30,
    "red_flags": """No job details, too niche stack (GHL-only, OpenClaw-only, n8n-only),
                 geo restrictions that exclude the profile, screen-recorded assessments,
                 Loom mandatory with no alternative."""
}

# ----------------------------------------------------------------------
# 4. Правила составления письма
# ----------------------------------------------------------------------
cover_letter_rules = """
Structure: each case contains project name, client URL or Upwork portfolio link, tech stack (technologies used), industry or niche, role description (what was built), key results with metrics, and a priority flag.

Case 1 (required) must come from the Upwork portfolio. Pick the most relevant Upwork case by stack, niche, and problem type.

Case 2 (best match) is the single most relevant case from the combined pool: Upwork portfolio plus full Interexy case database. There is no hierarchy between the two sources; relevance wins. The system uses the full internal case database to determine best fit.

Case Matching Logic
Match by stack keywords from the job's mandatory skills section. Match by industry or niche. Match by problem type (real-time systems, payments, AI integration, healthcare, etc.). Case 1 is always from the Upwork portfolio. Case 2 is the best-matching case from either the Upwork portfolio or the full Interexy case database, whichever is more relevant. Maximum 2 cases per letter. Never use the same case in both Tilek and Victoria letters for the same job.

Output Block 3: two selected cases with a one-line explanation of why each was chosen.

Keyword Integration Rules
Source: mandatory skills section of the job posting. Naturally weave three to five mandatory skill keywords into the cover letter body. Never list them. Always embed them in the context of case descriptions or the closing statement.

Example: mandatory skills: React, Node.js, Supabase, TypeScript → "Built a production-grade React and Node.js platform with TypeScript throughout and Supabase as the real-time data layer."

Cover Letter Generation Pipeline

Step 0 — Job Analysis (mandatory, executed before all other steps)

Extract the following data from the job description (as a JSON object; do not include it in the final output, but use it for subsequent steps):

- `required_skills` (array of strings) – all skills from the "Mandatory skills" section and those mentioned in the text.
- `core_technical_terms` (array of strings) – specialized terms: "ontology", "knowledge graph", "RAG", "compliance enforcement", "multi-agent", etc.
- `business_pain_points` (array of strings) – specific client problems (e.g., "existing tools don't scale", "lack of automation", "compliance risks").
- `screening_questions` (array of objects with fields `question` and `type`) – all questions the client explicitly or implicitly asks. For example, "Walk us through one part you find interesting", "What would you do your first week".
- `special_instructions` (object) – flags: `loom_required: true/false`, `nda_required: true/false`, `test_task: "paid"/"unpaid"/none`.
- `urgency` (string) – "immediate", "with_days", "none".
- `budget` (object) – `min`, `max`, `type` ("hourly"/"fixed").
- `weekly_hours` (number) – the number of hours per week required (if specified).

This data is used in steps 3–7 to generate a personalized, targeted response.

Step 1 - Job Evaluation: assess duration, hours, budget, stack fit, red flags. Output PASS or SKIP with reasoning. Stop if SKIP.

Step 2 - Profile Selection: determine Tilek / Victoria / Vicode Solutions / both. If both, run the pipeline twice independently.

Dual-profile rule (when both Tilek and Victoria letters are generated): cases must be completely different; no case can appear in both letters. Letter texts must be meaningfully distinct in hook, framing, and angle - not paraphrases of each other. Screening question answers must also differ; each answer written from the respective profile's perspective with different cases and different language.

Step 3 - Hook Generation: generate two or three hook options for the user to choose from, or auto-select the strongest one.

Hook Rules: never start with "Most...". Use conversational openers only: "Let me be honest...", "From what I see...", "To be honest...", "Let me be direct...". The hook must address a specific technical risk or business pain visible in the job description. One or two sentences maximum. No generic compliments to the client.

Step 4 - Case Selection: pull the two most relevant Priority 1 cases. Format per case: name plus link (if available) plus one or two lines on what was built and with which stack, plus a key result with metric.

Step 5 - Closing Statement: one or two sentences containing years of experience, core stack match to job requirements, availability (40 hours/week), and hourly rate (omit if fixed price).

Immediate start rule: if the job posting indicates the client wants to start immediately, within a few days, or urgently, include in the closing statement that the selected profile is available to start immediately.

Step 6 - CTA and Signature: CTA is always "Let's talk." Signature formats: for a solo profile (Tilek or Victoria) use "Best, [Name]". For the agency angle (Vicode Solutions) use "Best, [Name], Vicode Solutions / vicode.solutions/portfolio". For Tilek on technical roles, add "https://github.com/tilekchubakov" on a separate line.

Step 7 - Screening Questions (if present): detect if the job posting contains a screening questions block (for example, "You will be asked to answer the following questions" or similar). If yes, generate answers as a separate output block; never mix them into the letter body.

Format per answer: use a numbered list matching the job's question order. For "Describe recent experience" or any request to describe a case or project, answer in full detail: project name plus link, what the product does, the client's pain point, the solution built, tech stack, role on the project, and measurable results. Never give a brief or summary answer to this type of question. For technical questions, give a precise technical answer. For "Do you have certifications?" use a standard answer referencing production experience. Include GitHub or portfolio links where relevant. When both Tilek and Victoria answers are generated, each must use different cases and different language.

Cover Letter Structure

Block 1 Hook: one or two sentences, conversational, addresses a specific pain or risk from the job description.
Block 2 Bridge: one sentence connecting the hook to the solution being offered.
Block 3 Case 1: name and link on the same line, followed by one or two lines describing what was built, stack used, and a key result with metric.
Block 4 Case 2: same format as Case 1.
Block 5 Closing: years of experience plus stack match plus availability plus rate if hourly, plus "available to start immediately" if the job is urgent.
Block 6 CTA: "Let's talk."
Block 7 Signature: "Best, [Name]" plus optional portfolio/GitHub line.

Formatting Rules
Use hyphen-minus ( - ) only, never em dash ( — ) or en dash ( – ). No bold text inside the letter. No bullet points inside the letter. No headers inside the letter. Use plain paragraphs only. The case name and link appear on the same line, for example: Classful - https://classful.com. Letter length is 150-200 words maximum. Screening answers are always a separate block, never inside the letter. If the job posting contains specific instructions (answer questions, provide a timeline, include something particular), always follow them without exception. Missing a stated requirement is an automatic disqualifier.

Edge Cases
If the client name is known, open the letter with the client name. If the client name is unknown, use no greeting or just "Hi there". If a Loom is mandatory, write that a Loom will be sent upon response. If an NDA is required, acknowledge willingness to sign in the closing. If "Agency preferred" is stated, use the Vicode Solutions angle. For a fixed price job, do not mention a rate anywhere in the letter. For an hourly job, include the rate in the closing statement. If a screen-recorded assessment is required, flag it to the user and ask whether to proceed. If both AI and fullstack are required, generate two letters independently. If the job requires a test task or assessment, state in the letter that test tasks are completed on a paid basis only, and that the terms can be discussed separately; never agree to unpaid test tasks. If an urgent start or start within days is required, include in the closing that the profile is available to start immediately.
"""

# ----------------------------------------------------------------------
# 5. Шаблон письма-отклика (few-shot examples + правила)
# ----------------------------------------------------------------------
letter_template = """
Example 1 (Good — specific, with metrics and stack):

[Block 1 Hook]
From what I see - this is less about building a shoe store and more about building a conversion machine that happens to sell shoes.

[Block 2 Bridge]
Performance, SEO, and clean architecture from day one - that's where I focus.

[Block 3 Case 1]
Arcade - https://arcade.ai
AI-powered marketplace handling thousands of concurrent requests. Built scalable backend infrastructure and React frontend optimized for high-load, real-time user interactions.

[Block 4 Case 2]
Classful - https://classful.com
EdTech SaaS, 1M+ MAU. Stripe integration, PostgreSQL optimization, page load speed improved by 55%. Conversion rate up 30%.

[Block 5 Closing]
15+ years building scalable backend systems. I'll make sure your store is fast, clean, and ready to grow. Available 40 hrs/week.

[Block 6 CTA]
Let's talk.

[Block 7 Signature]
Best,
Tilek


Example 2 (Good — addresses specific pain, includes technical answer, fixed‑price mention):

[Block 1 Hook]
Hi Jason,
This is a backend ownership problem - multi-tenant data isolation, HIPAA-compliant infrastructure, and a clean API layer a real clinic can trust from day one. The frontend is done; the hard part is everything underneath it.

[Block 2 Bridge]
I work as a senior full-stack engineer owning Node.js + Fastify backends and React frontends end to end - PostgreSQL schema design, REST API boundaries, auth systems, and production delivery. I'm fluent in TypeScript, work with Prisma and Supabase regularly, and handle Redis-backed async infrastructure as a standard part of the stack.

[Block 3 Case 1]
On Renegade Health - https://renegade.health/ - a HIPAA-regulated telemedicine platform, I led compliance audit preparation: PHI access controls, audit logging, and architectural sign-off. Stack: Node.js, TypeScript, PostgreSQL, GCP.

[Block 4 Case 2]
On Deverus - https://www.deverus.com/ - a regulated multi-tenant SaaS, I worked on backend redesign and integrated a blockchain-based digital wallet for sensitive document verification - another environment where data isolation wasn't optional.

[Block 5 Closing]
For RLS in PostgreSQL: I set a session-level clinic_id variable per connection and enforce Supabase RLS policies that filter all PHI reads and writes against it - combined with Prisma middleware injecting tenant context before every query.

Available immediately, 40 hrs/week, open to fixed-price per phase or hourly.

[Block 6 CTA]
Let's jump on a short call to walk through the spec and scope Phase 1.

[Block 7 Signature]
Best,
Viktoryia


Example 3 (Good — risk‑aware, DevOps‑heavy, one case only, but strong metrics):

[Block 1 Hook]
❗You are not considering the significant technical risk which can cost you $150k according to my experience when React + Python systems are scaled on AWS without proper Terraform, API boundaries, and cloud cost control.

[Block 2 Bridge]
I build full stack platforms using React for complex admin UIs, Python for backend services, AWS Lambda for scalable workloads, GraphQL for stable data contracts, and Terraform for fully reproducible infrastructure, with production-grade DevOps from day one.

[Block 3 Case 1]
On Deverus, a large-scale background screening platform, the business faced onboarding drop-offs and scaling limits due to legacy architecture, so I rebuilt core flows with React frontend, Python services on AWS, API-first design, and cloud automation, resulting in a 74% reduction in drop-off and support for millions of checks monthly.
Link: https://www.deverus.com/ 

[Block 4 Case 2]
(Second case missing – structure allows one case, but two are preferred)

[Block 5 Closing]
Working with me means you get a senior full stack engineer who designs systems to survive real traffic, audits, and growth, not just pass initial QA.
I proactively eliminate AWS cost leaks, GraphQL overfetching, and infra drift that usually appear after launch and quietly burn budgets.

My clients get predictable delivery, clean handover, and architectures that new engineers can safely extend without rewrites.

[Block 6 CTA]
Reply to this proposal to have a chat ASAP.

[Block 7 Signature]
Best,
Tilek


Example 4 (BAD — generic, no personalisation, missing answers to job questions, weak cases):

[Block 1 Hook]
Let me be honest, building a responsive and performant web application from scratch requires not just technical skills but also a deep understanding of user needs and AI integration.

[Block 2 Bridge]
I focus on creating solutions that are both user-friendly and technically sound.

[Block 3 Case 1]
Stauffer (Estimating app) - https://stauffer.com
Developed an internal web application for estimating landscape projects using JS/TS, React, and Node.js, optimizing calculations and improving efficiency by 40%.

[Block 4 Case 2]
MyGenMe (ChatBot) - https://mygenme.com
Built a conversational chatbot using Node.js for the backend and React Native for the frontend, enhancing user engagement through AI integration.

[Block 5 Closing]
With over 5 years of experience in full-stack development, I specialize in React and Node.js, and I am available to start immediately, working 40 hours per week.

[Block 6 CTA]
Let's talk.

[Block 7 Signature]
Best,
Victoria

Why this is weak:
- Hook: does not target a specific pain from the job description (no mention of greenfield, LLM integration risk, or DevOps).
- Bridge: generic declaration (“user-friendly and technically sound”) – no method, no tools.
- Cases: Stauffer is irrelevant to AI/DevOps; MyGenMe lacks metrics and specific AI details (e.g., which LLM, embeddings, scale).
- Closing: missing rate (hourly job) and excludes AI/DevOps skills.
- No answers to mandatory screening questions (the job had three questions).


Example 5 (GOOD — personalised, addresses specific job requirements, includes answers to questions):

[Block 1 Hook]
Let me be honest - building a greenfield product with LLMs from scratch is already risky. Adding a responsive frontend without a solid CI/CD pipeline is how AI budgets get burned.

[Block 2 Bridge]
That's why I start every AI project with Docker Compose for local dev, GitHub Actions for CI/CD, and Terraform for AWS. The same stack keeps your RAG pipeline and React frontend in sync without cost surprises.

[Block 3 Case 1]
MyGenMe - https://mygenme.com
Built a conversational chatbot with RAG over product docs using GPT-4, Pinecone vector DB, and Node.js. Deployed on AWS Lambda with API Gateway, handling 10k daily requests at <2s p95 latency.

[Block 4 Case 2]
Arcade - https://arcade.ai
AI-powered marketplace with thousands of concurrent users. Built scalable backend (Node.js + Redis) and React frontend, set up GitHub Actions CI/CD and Docker deployment on AWS ECS.

[Block 5 Closing]
10+ years full-stack, 5+ LLM integrations. React, Node.js, Python, Docker, AWS CDK. Available 40 hrs/week, rate $35/hr. I can start immediately.

[Block 6 CTA]
Let's jump on a short call to walk through your spec.

[Block 7 Signature]
Best,
Tilek
https://github.com/tilekchubakov

[Answers to your questions]
1. I'm strongest in AI integration (LLM APIs, embeddings, RAG) and DevOps (CI/CD, Docker, Terraform). I also do full-stack React/Node.js.
2. MyGenMe chatbot (above): built the entire pipeline from prompt design to production deployment on AWS Lambda.
3. Preferred stack: React + Node.js + MongoDB + Docker + AWS ECS. Why? Because it gives fast iteration for greenfield projects, scales for AI workloads, and keeps cloud costs predictable.


# ----------------------------------------------------------------------
# WRITING GUIDELINES (must follow for every generated letter)
# ----------------------------------------------------------------------
- Use only hyphen-minus " - " as dash, never em dash (—) or en dash (–).
- No bold text, no bullet points, no internal headers inside the letter.
- Case name and link on same line, e.g., "Project - https://example.com"
- Letter length: 150-200 words maximum.
- Screening answers always as a separate block after the signature.
- If client name is known, open with "Hi [Name],". If unknown, use no greeting or just "Hi there".
- If a test task or unpaid assessment is requested, reply in screening: "Test tasks are completed on a paid basis only. Terms can be discussed separately."
- For hourly jobs: include rate in Block 5 Closing.
- For fixed price: never mention rate.
- If urgent start required: add "available to start immediately" in Block 5.

Hook rules:
- Start with the statement like: "Let me be honest...", "From what I see...", "To be honest...", "Let me be direct...", or "Hi, the problem you come across is related to..." (with client name if known).
- Never start with "Most...".
- Must address a specific technical risk or business pain visible in the job description (e.g., scaling, security, cost, latency, compliance, greenfield uncertainty).
- One to two sentences maximum.
- No generic compliments.

Bridge rules:
- One sentence connecting the hook to the solution.
- Must name at least one concrete technology or method (e.g., "That's why I use Docker + GitHub Actions + Terraform").
- Avoid empty statements like "I focus on quality".

Case rules:
- Pull the two most relevant Priority 1 cases for the job (by keywords: AI, DevOps, stack, industry).
- Each case description must include: what was built, stack used, and a key result with metric (%, time saved, requests handled, etc.).
- If no perfect match exists, still provide two cases but explain briefly why relevant (e.g., "Matches your need for real-time processing").

Closing rules:
- Include years of experience + core stack match to job requirements + availability (40 hrs/week unless stated otherwise).
- Include hourly rate only if job is hourly; omit for fixed price.
- If job is urgent: add "available to start immediately".

Screening answers (if job has questions):
- Number each answer matching the job's question order.
- For "Describe recent experience" or "What project have you built": answer with full detail – project name, link, pain point, solution, stack, role, measurable result.
- For technical questions: give precise technical answer.
- For certifications: reference production experience instead (unless certification is mandatory).
- For "preferred stack and why": give explicit stack plus a reason tied to the job's needs (e.g., "Because it scales for AI workloads and keeps costs low").
- Never give a one-line generic answer.
"""

# ----------------------------------------------------------------------
# Путь к папке с кейсами (относительно корня проекта)
# ----------------------------------------------------------------------
CASES_DIR = Path(__file__).parent.parent / "backend" / "knowledge_base" / "cases"


async def load_case_content(case_id: str) -> str:
    case_path = CASES_DIR / f"{case_id}.md"
    if not case_path.exists():
        print(f"⚠️ Файл кейса {case_id} не найден по пути {case_path}")
        return ""
    with open(case_path, "r", encoding="utf-8") as f:
        return f.read()


def fix_newlines(text: str) -> str:
    text = text.replace('\\n', '\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def _expect_str(val, path: str) -> None:
    """Raise TypeError if val is not a plain string."""
    if not isinstance(val, str):
        raise TypeError(
            f"Field '{path}' must be a string, got {type(val).__name__}: {repr(val)[:80]}"
        )


def _expect_str_or_none(val, path: str) -> None:
    if val is not None:
        _expect_str(val, path)


def _validate_profile_data(name: str, data: dict) -> None:
    """
    Validate the shape of one candidate block in the model response.
    Raises TypeError with a descriptive message on the first violation found.
    """
    if not isinstance(data, dict):
        raise TypeError(
            f"Profile '{name}': expected object, got {type(data).__name__}"
        )

    # ---- Проверка наличия всех обязательных полей верхнего уровня ----
    required_top_keys = ("job_evaluation", "selected_cases", "hook_options", "selected_hook", "letter_parts", "screening_answers")
    for key in required_top_keys:
        if key not in data:
            raise TypeError(f"Profile '{name}': missing required key '{key}'")

    # ---- job_evaluation ----
    je = data["job_evaluation"]
    if not isinstance(je, dict):
        raise TypeError(f"Profile '{name}'.job_evaluation must be an object")
    required_je_keys = ("decision", "reasoning", "observations")
    for key in required_je_keys:
        if key not in je:
            raise TypeError(f"Profile '{name}'.job_evaluation missing required key '{key}'")
    decision = je["decision"]
    if not isinstance(decision, str) or decision not in ("PASS", "SKIP"):
        raise TypeError(
            f"Profile '{name}'.job_evaluation.decision must be 'PASS' or 'SKIP', got {repr(decision)}"
        )
    reasoning = je["reasoning"]
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise TypeError(
            f"Profile '{name}'.job_evaluation.reasoning must be a non-empty string"
        )
    observations = je["observations"]
    if not isinstance(observations, list):
        raise TypeError(f"Profile '{name}'.job_evaluation.observations must be a list")
    for i, obs in enumerate(observations):
        if not isinstance(obs, dict):
            raise TypeError(f"Profile '{name}'.job_evaluation.observations[{i}] must be an object")
        if "type" not in obs or "reasoning" not in obs:
            raise TypeError(f"Profile '{name}'.job_evaluation.observations[{i}] missing 'type' or 'reasoning'")
        obs_type = obs["type"]
        if not isinstance(obs_type, str) or not obs_type.strip():
            raise TypeError(
                f"Profile '{name}'.job_evaluation.observations[{i}].type must be a non-empty string"
            )
        obs_reason = obs["reasoning"]
        if not isinstance(obs_reason, str) or not obs_reason.strip():
            raise TypeError(
                f"Profile '{name}'.job_evaluation.observations[{i}].reasoning must be a non-empty string"
            )

    # ---- selected_cases ----
    cases = data["selected_cases"]
    if not isinstance(cases, list):
        raise TypeError(f"Profile '{name}'.selected_cases must be a list")
    if len(cases) != 2:
        raise TypeError(
            f"Profile '{name}'.selected_cases must contain exactly 2 cases, got {len(cases)}"
        )
    for i, c in enumerate(cases):
        if not isinstance(c, dict):
            raise TypeError(f"Profile '{name}'.selected_cases[{i}] must be an object")
        required_case_keys = ("case_id", "name", "link", "reasoning")
        for key in required_case_keys:
            if key not in c:
                raise TypeError(f"Profile '{name}'.selected_cases[{i}] missing required key '{key}'")
        case_id = c["case_id"]
        if not isinstance(case_id, str) or not case_id.strip():
            raise TypeError(
                f"Profile '{name}'.selected_cases[{i}].case_id must be a non-empty string"
            )
        c_name = c["name"]
        if not isinstance(c_name, str) or not c_name.strip():
            raise TypeError(
                f"Profile '{name}'.selected_cases[{i}].name must be a non-empty string"
            )
        link = c["link"]
        if not isinstance(link, str):
            raise TypeError(f"Profile '{name}'.selected_cases[{i}].link must be a string")
        reasoning = c["reasoning"]
        if not isinstance(reasoning, str) or not reasoning.strip():
            raise TypeError(
                f"Profile '{name}'.selected_cases[{i}].reasoning must be a non-empty string"
            )

    # ---- hook_options ----
    hooks = data["hook_options"]
    if not isinstance(hooks, list):
        raise TypeError(f"Profile '{name}'.hook_options must be a list")
    for i, h in enumerate(hooks):
        if not isinstance(h, dict):
            raise TypeError(f"Profile '{name}'.hook_options[{i}] must be an object")
        if "text" not in h:
            raise TypeError(f"Profile '{name}'.hook_options[{i}] missing required key 'text'")
        text = h["text"]
        if not isinstance(text, str) or not text.strip():
            raise TypeError(
                f"Profile '{name}'.hook_options[{i}].text must be a non-empty string"
            )

    # ---- selected_hook ----
    selected_hook = data["selected_hook"]
    if not isinstance(selected_hook, str) or not selected_hook.strip():
        raise TypeError(
            f"Profile '{name}'.selected_hook must be a non-empty string"
        )

    # ---- letter_parts ----
    lp = data["letter_parts"]
    if not isinstance(lp, dict):
        raise TypeError(f"Profile '{name}'.letter_parts must be an object")
    required_parts = ("hook", "bridge", "case1_text", "case2_text", "closing", "cta", "signature")
    for part in required_parts:
        if part not in lp:
            raise TypeError(f"Profile '{name}'.letter_parts missing required key '{part}'")
        val = lp[part]
        if not isinstance(val, str) or not val.strip():
            raise TypeError(
                f"Profile '{name}'.letter_parts.{part} must be a non-empty string"
            )

    # ---- screening_answers ----
    answers = data["screening_answers"]
    if not isinstance(answers, str):
        raise TypeError(f"Profile '{name}'.screening_answers must be a string")
    # screening_answers может быть пустой строкой — это допустимо

import re


def _normalize(s: str) -> str:
    """
    Convert any case identifier to a canonical lowercase-alphanum form so that
    'Scale AI', 'case_scale_ai', 'case_scale_ai.md', and 'ScaleAI' all map to
    the same key: 'scaleai'.

    Steps:
      1. Strip the leading 'case_' prefix (file-slug convention).
      2. Strip a trailing '.md' extension if present.
      3. Lowercase everything.
      4. Remove all non-alphanumeric characters (spaces, underscores, hyphens, etc.).
    """
    s = s.strip()
    # Remove leading 'case_' prefix (case-insensitive)
    s = re.sub(r'^case[_\-]', '', s, flags=re.IGNORECASE)
    # Remove trailing file extension
    s = re.sub(r'\.\w+$', '', s)
    # Lowercase and strip non-alphanumeric
    return re.sub(r'[^a-z0-9]', '', s.lower())


def build_cases_text(best_cases_with_content: list, profiles_to_use: list) -> str:
    """
    Build the cases section injected into the prompt.

    Ownership is resolved by normalising both the case ID/name from the
    retrieved list and the entries in each candidate's priority_cases to a
    common slug, then matching them. This handles the mismatch between
    human-readable names ("Scale AI") and file-slug IDs ("case_scale_ai").
    """
    # Build normalised_key -> list[candidate_name]
    # For each candidate, normalise every entry in priority_cases.
    norm_to_candidates: dict[str, list[str]] = {}
    for profile in profiles_to_use:
        for entry in profile.get("priority_cases", []):
            key = _normalize(entry)
            norm_to_candidates.setdefault(key, []).append(profile["name"])

    def eligible_for_case(case: dict) -> list[str]:
        """Return candidate names that own this case."""
        # Try matching against both the id field and the name field, taking
        # whichever produces a hit (some cases use slugs as id, others use
        # human-readable names).
        for field in ("id", "name"):
            key = _normalize(case.get(field, ""))
            if key and key in norm_to_candidates:
                return norm_to_candidates[key]
        return []

    # ── Index table ──────────────────────────────────────────────────────────
    index_lines = [
        "### Available cases",
        "",
        "Index (scan this first to find which cases each candidate may use):",
        "",
        f"{'Case ID':<28} {'Name':<32} Eligible candidates",
        "-" * 90,
    ]
    for case in best_cases_with_content:
        cid = case.get("id", "")
        name = case.get("name", "Unknown")[:30]
        eligible = eligible_for_case(case)
        index_lines.append(
            f"{cid:<28} {name:<32} {', '.join(eligible) if eligible else '(none)'}"
        )
    index_lines.append("")

    # ── Full case blocks ─────────────────────────────────────────────────────
    block_lines = ["Full case details:", ""]
    for case in best_cases_with_content:
        cid = case.get("id", "")
        name = case.get("name", "Unknown")
        link = case.get("link") or ""
        content = (case.get("content") or "")[:3000].strip()
        eligible = eligible_for_case(case)

        block_lines += [
            f"=== CASE {cid} ===",
            f"Name:                {name}",
            f"Link:                {link if link and link != 'N/A' else '(no external link)'}",
            f"Eligible candidates: {', '.join(eligible) if eligible else '(none in current profile set)'}",
            "Content:",
            content,
            "",
        ]

    return "\n".join(index_lines) + "\n" + "\n".join(block_lines)


async def generate_initial_response(
        job_description: str,
        best_cases_with_content: list,
        user_profiles: list,
        selection_rules: dict,
        cover_letter_rules: str,
        letter_template: str,
        api_key: str,
        allowed_profiles: list = None,
        forbidden_case_ids: list = None
) -> dict:
    client_local = AsyncOpenAI(api_key=api_key)
    profiles_to_use = [p for p in user_profiles if allowed_profiles is None or p["name"] in allowed_profiles]

    main_part = f"""
### Cover letter writing rules
 
**Letter structure (blocks):**
1. **Hook** – 1-2 conversational sentences addressing a specific technical risk or business pain from the job description. Never start with "Most...".
2. **Bridge** – one sentence connecting the hook to the solution, must name at least one concrete technology or method.
3. **Case 1** – name and link on the same line, then 1-2 lines: what was built, stack used, key result with metric.
4. **Case 2** – same format.
5. **Closing** – years of experience, core stack match, availability ({MAX_HOURS_PER_WEEKS}), hourly rate (if hourly), "available to start immediately" if urgent.
6. **CTA** – one natural call-to-action sentence.
7. **Signature** – "Best, [Name]" (+ Portfolio link if stated in user profile).
 
**Formatting:** Use only hyphen-minus " - " (not em dash or en dash). No bold, no bullet points, no headers. Letter length 150-200 words. Screening answers as a separate block after the signature.
 
---
 
### Step 0 – Job Analysis (semantic extraction)
 
Read the job description carefully word by word. Extract the following fields **only if the job description explicitly states them** — do not infer or assume:
 
- `required_skills` – skills listed under "Mandatory", "Required", "Must have", or explicitly stated as requirements.
- `core_technical_terms` – specialized terms verbatim from the text (e.g., "RAG", "knowledge graph", "multi-agent").
- `business_pain_points` – specific problems the client describes (quote or closely paraphrase).
- `screening_questions` – any questions the client asks applicants to answer (copy them verbatim).
- `budget` – min, max, currency, type (hourly/fixed). Only if a number is stated.
- `weekly_hours` – required hours per week. Only if a number is stated.
- `minimum_duration_months` - minimum job offer duration in months measurement.
 
**Observations — read every sentence for these triggers:**
 
An observation is a dict: `{{"type": "<type_string>", "reasoning": "<one sentence quoting or referencing the exact phrase that triggered this>"}}`.
 
Go through each observation type below and ask: "Does the job description contain this?" If yes, add it. If no, omit it. Never add an observation that is not triggered by explicit text.
 
| Type | Trigger condition |
|---|---|
| `loom_required` | Client says "record a Loom", "send a video", "include a short video", or similar — but does NOT say the video must be in the proposal itself |
| `loom_mandatory_in_proposal` | Client explicitly says the video must be attached to or included in the proposal (RED FLAG) |
| `urgent_start` | Client says "start immediately", "start ASAP", "available to start within X days", "need someone now", or similar urgency phrasing |
| `project_based` | Job described as "project-based", "one-off", "fixed scope", "milestone-based", or has a defined end date |
| `part_time` | Client states fewer than 30 hours/week, or uses the phrase "part-time" |
| `nda_required` | Client mentions NDA, non-disclosure agreement, or confidentiality agreement |
| `test_task_paid` | Client asks for a test task AND states it is paid |
| `test_task_unpaid` | Client asks for a test task AND does not mention payment (assume unpaid) |
| `screen_recorded_assessment` | Client requires a screen-recorded technical assessment (RED FLAG) |
| `geo_restriction` | Client restricts applicants by country, timezone beyond UTC±4, or residency (RED FLAG) |
| `niche_stack` | Client requires a highly specific technology that none of the candidate profiles contain (RED FLAG) |
| `no_job_details` | Job description is empty, fewer than 3 sentences, or contains no technical requirements (RED FLAG) |
 
**Red flags** = any of: `loom_mandatory_in_proposal`, `screen_recorded_assessment`, `geo_restriction`, `niche_stack`, `no_job_details`.
If ANY red flag is present → every candidate gets decision = SKIP. Do not evaluate further.
 
---
 
### Step 1 – Candidate Evaluation (strict decision tree, apply per candidate)
 
Evaluate each candidate independently using this exact sequence. Stop at the first matching rule.
 
**Rule 1 — Red flag (global)**
If Step 0 found any red flag observation → SKIP. Reasoning: state which red flag.
 
**Rule 2 — Budget hard block**
If `budget.max` was extracted AND `candidate.min_salary_per_hour_usd > budget.max` → SKIP.
Reasoning: state the numbers.
 
**Rule 3 — Hours hard block**
If `minimum_duration` was extracted AND `minimum_duration < {2}` → SKIP.
Reasoning: state the numbers.

**Rule 4 — Minimal Duration hard block**
If `minimum_duration_months` was extracted AND `minimum_duration_months < {MIN_DURATION_MONTHS}` → SKIP.
Reasoning: state the numbers.
 
**Rule 5 — Complete field mismatch**
The candidate's primary domain (e.g., mobile development, embedded systems, data science) has zero overlap with the job's domain AND the candidate has none of the required skills → SKIP.
This rule requires BOTH conditions. If the candidate has even one relevant skill or adjacent experience, do NOT apply this rule.
 
**Rule 6 — Weak fit (PASS with flag)**
The candidate's domain overlaps with the job OR the candidate has at least one relevant skill from the required list, BUT there are notable gaps (missing 2+ key required skills, or primary stack differs significantly) → PASS, and add a `weak_fit` observation.
`weak_fit` reasoning must list: which required skills are missing, and why the candidate still passes (what overlap exists).
 
**Rule 7 — Default PASS**
None of the above rules triggered → PASS.
 
**Key principle:** When in doubt between PASS and SKIP, prefer PASS with a `weak_fit` observation. A cover letter with caveats is more useful than silently skipping a borderline candidate.
 
---
 
### Step 2 – Case Selection (per candidate, PASS only)
 
You are given a list of cases with IDs, names, links, and full descriptions. Each case belongs to specific candidates as indicated by `priority_cases` in the candidate profile.
 
**Selection rules (apply in order):**
1. If provided cases are stated in the list of the priority cases of a candidate choose these cases in the first place.
2. From the eligible cases, select exactly 2 whose content best matches the job's `required_skills` and `core_technical_terms`.
3. If fewer than 2 eligible cases exist for this candidate → select all available (even 0 or 1), and note this in `selected_cases` reasoning.
4. Never reference a case that was not provided in the cases list below. Never invent a case name, link, or metric. Do not choose the priority cases if they are not provided by RAG system.
5. When writing `case1_text` and `case2_text` in `letter_parts`, use ONLY facts, technologies, and metrics that appear verbatim in the provided case content. Do not embellish or infer additional details.
 
**Case content reference:** Each case below has an ID. When you select a case, copy its `case_id` exactly into `selected_cases[].case_id`. The letter text for that case must be derived solely from that case's provided content.
 
---
 
### Step 3 – Cover Letter Generation (per candidate, PASS only)
 
- Use `selected_hook` as Block 1 (hook).
- Weave 3-5 required skills into case descriptions or closing — only skills present in the candidate's profile or demonstrated in the selected cases.
- Follow letter structure exactly.
- Use `\\n` for line breaks inside JSON strings.
 
**Observations → letter rules (check each one):**
- `loom_required` present → add exactly this phrase somewhere in the letter body: "I'll record a Loom as requested." Do not describe what the Loom will contain.
- `urgent_start` present → closing must include "available to start immediately" or "can start within [X] days".
- `nda_required` present → closing must mention willingness to sign NDA.
- `test_task_unpaid` present → screening answers must state test tasks are completed on a paid basis only.
 
**Uniqueness rules (each candidate's letter must be distinct):**
- Rotate hook angle across candidates: technical risk / missed revenue / slow time-to-market / scalability bottleneck / UX gap / cost inefficiency / security concern / team velocity.
- Bridge: vary sentence structure (start with technology / start with problem / start with outcome). Never reuse a bridging phrase.
- Cases: highlight different aspects even if candidates share projects. One focuses on latency, another on accuracy; one cites "40% load time drop", another cites "10k concurrent users".
- Closing: vary skill order and phrasing. Avoid the rigid "X years full-stack. Tech A, B, C. Rate $Z" pattern.
- CTA: rotate naturally — "Let's talk.", "Open to a quick call?", "I'd love to discuss how I can help.", "When works for you?"
- Never copy a full phrase from one candidate's letter to another's.
 
**Prohibited:** Do not mention any skill, technology, or achievement that is not in the candidate's `skills` list or explicitly described in a selected case's provided content.
 
**Case text format:**
[Case name] [link if valid external URL, else omit]
[One sentence: what was built + stack. One sentence: key result with a specific metric.]
 
Example:
Arcade - https://arcade.ai
Developed an AI-powered marketplace with real-time recommendation engine using Python, FastAPI, and PostgreSQL. Reduced page load time by 40% and increased user engagement by 25%.

    ---
    
### Step 3 – Differentiation Plan (internal, before writing any letter)
 
Before generating any letter text, produce a private plan (you do not output this, it guides your writing):
 
For each PASS candidate, decide:
- **Hook angle** – pick one from: technical risk / missed revenue / slow time-to-market / scalability bottleneck / UX gap / cost inefficiency / security concern / team velocity. No two candidates may share the same angle.
- **Bridge entry point** – choose one: start with the technology / start with the problem / start with the outcome. No two candidates may use the same entry point.
- **Case emphasis** – for each selected case, choose one dimension to foreground: speed metric / scale metric / cost metric / quality metric / user metric / architectural decision. If two candidates share a case, they must foreground different dimensions.
- **Closing structure** – choose one: lead with years of experience / lead with primary technology / lead with availability / lead with rate. No two candidates may use the same lead.
- **CTA** – assign a different CTA phrase to each candidate from: "Let's talk." / "Open to a quick call?" / "I'd love to discuss how I can help." / "When works for you?"
 
This plan enforces that every structural decision differs across candidates before a single word is written.
 
---
 
### Step 4 – Cover Letter Generation (per candidate, PASS only)
 
Apply the differentiation plan from Step 3. Then:
 
- Use `selected_hook` as the hook block.
- Weave 3-5 required skills into case descriptions or closing — only skills present in the candidate's `skills` list or explicitly stated in the selected case content.
- Follow the letter structure from the rules section exactly.
- Use `\\n` for line breaks inside JSON strings.
 
**Observation → letter rules (check each, apply all that match):**
- `loom_required` → add exactly: "I'll record a Loom as requested." Somewhere in the letter body. Do not describe Loom content anywhere.
- `urgent_start` → closing must contain "available to start immediately" or "can start within [X] days".
- `nda_required` → closing must mention willingness to sign NDA.
- `test_task_unpaid` → screening answers must state test tasks are completed on a paid basis only.
 
**Uniqueness enforcement — after drafting all letters, verify:**
1. No hook shares its opening word or angle with another candidate's hook.
2. No bridge sentence starts the same way as another candidate's bridge.
3. No case description sentence is shared verbatim between candidates.
4. No closing leads with the same element as another candidate's closing.
5. No two candidates share the same CTA phrase.
If any check fails, rewrite the offending field before outputting.
 
**Hard prohibition:** Do not write any skill, technology, tool, or metric that does not appear in the candidate's `skills` list or in the verbatim content of a selected case.
 
**Case text format inside `letter_parts`:**
[Case name] - [link only if a valid external client URL; omit if internal or app store]
[What was built and the stack used, one sentence.] [Key result with a specific number or percentage, one sentence.]
 
---
 
### Output format (strict JSON)
 
Return a single JSON object. Keys = candidate names exactly as given. Values = objects with:
 
- `job_evaluation`: `{{"decision": "PASS"|"SKIP", "reasoning": "<string>", "observations": [{{"type": "<string>", "reasoning": "<string>"}}]}}`
- `selected_cases`: array of `{{"case_id": "<string>", "name": "<string>", "link": "<string>", "reasoning": "<string>"}}`. Empty array if SKIP.
- `hook_options`: array of 3 `{{"text": "<string>", "specificity_score": <number 1-10>}}`. Empty array if SKIP.
- `selected_hook`: string. Empty string if SKIP.
- `letter_parts`: `{{"hook": "", "bridge": "", "case1_text": "", "case2_text": "", "closing": "", "cta": "", "signature": ""}}`. Empty object if SKIP.
- `screening_answers`: string. Empty string if SKIP.
 
All field values must be primitive strings or arrays of objects whose fields are primitive strings or numbers. No nested objects inside string fields.
 
SKIP candidates: include only `job_evaluation`. Set all other fields to their empty defaults.
 
Do not copy example values. Generate from the actual job description and candidate data.
 

Example of `letter_parts` (inside a candidate object):

```json
"letter_parts": {{
  "hook": "You are not considering the significant technical risk...",
  "bridge": "I build full stack platforms using React for complex admin UIs, Python for backend services...",
  "case1_text": "Arcade - https://arcade.ai\\nDeveloped an AI-powered marketplace with real-time recommendation engine using Python, FastAPI, and PostgreSQL. Reduced page load time by 40%.",
  "case2_text": "Classful - https://classful.com\\nEdTech SaaS serving 1M+ MAU. Rewrote backend from monolith to microservices with Node.js, Docker, and Kubernetes. Cut server costs by 30%.",
  "closing": "15+ years full-stack, 5+ years cloud/DevOps. React, Node.js, Python, Docker, AWS CDK. Available 40 hrs/week, rate $50/hr. I can start immediately.",
  "cta": "Let's talk.",
  "signature": "Best, Tilek\\nhttps://github.com/tilekchubakov"
}}
```

Example for two candidates:

```json
{{
  "Tilek Chubakov": {{
    "job_evaluation": {{
      "decision": "",
      "reasoning": "...",
      "observations": []
    }},
    "selected_cases": [
      {{ "case_id": "...", "name": "...", "link": "...", "reasoning": "..." }},
      {{ "case_id": "...", "name": "...", "link": "...", "reasoning": "..." }}
    ],
    "hook_options": [
      {{ "text": "...", "specificity_score": 0 }},
      {{ "text": "...", "specificity_score": 0 }},
      {{ "text": "...", "specificity_score": 0 }}
    ],
    "selected_hook": "...",
    "letter_parts": {{
      "hook": "...",
      "bridge": "...",
      "case1_text": "...",
      "case2_text": "...",
      "closing": "...",
      "cta": "...",
      "signature": "..."
    }},
    "screening_answers": "..."
  }},
  "Victoria": {{
    "job_evaluation": {{
      "decision": "",
      "reasoning": "...",
      "observations": []
    }}
  }},
  "Vicode Solutions": {{
    "job_evaluation": {{
      "decision": "",
      "reasoning": "...",
      "observations": []
    }},
    "selected_cases": [
      {{ "case_id": "...", "name": "...", "link": "...", "reasoning": "..." }},
      {{ "case_id": "...", "name": "...", "link": "...", "reasoning": "..." }}
    ],
    "hook_options": [
      {{ "text": "...", "specificity_score": 0 }},
      {{ "text": "...", "specificity_score": 0 }},
      {{ "text": "...", "specificity_score": 0 }}
    ],
    "selected_hook": "...",
    "letter_parts": {{
      "hook": "...",
      "bridge": "...",
      "case1_text": "...",
      "case2_text": "...",
      "closing": "...",
      "cta": "...",
      "signature": "..."
    }},
    "screening_answers": "..."
  }}
}}
    ```
    
### Candidate profiles
{json.dumps(
    [{{k: v for k, v in p.items() if k != "priority_cases"}} for p in profiles_to_use],
    indent=2, ensure_ascii=False
)}
"""

    cases_text = build_cases_text(best_cases_with_content, profiles_to_use)

    prompt = f"""
Ты – AI-ассистент по подбору персонала для IT-вакансий. Твоя задача – оценить вакансию, выбрать наиболее подходящего кандидата из списка профилей и сгенерировать готовое письмо-отклик и ответы на скрининг-вопросы (если есть).

### Описание вакансии:
{job_description}

### Список релевантных кейсов компании (каждый с ID, названием, ссылкой и полным описанием):
{cases_text}

### Базовые правила отбора работы (общие для всех кандидатов):
{json.dumps(selection_rules, indent=2, ensure_ascii=False)}

{main_part}
"""
    system_message = {"role": "system", "content": "Ты – экспертный помощник по подбору персонала для IT-компаний. Отвечай только JSON."}
    messages = [system_message, {"role": "user", "content": prompt}]
    logger.info("=== RESULT FROM process_job ===")
    logger.info(json.dumps(prompt, indent=2, ensure_ascii=False))
    logger.info("=== END RESULT ===")
    try:
        response = await client_local.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)

        if not isinstance(result, dict):
            raise TypeError(
                f"Top-level response must be an object, got {type(result).__name__}"
            )

        # Validate every profile block — raises TypeError on first bad field
        for profile_name, profile_data in result.items():
            _validate_profile_data(profile_name, profile_data)

        # All types are correct — apply fix_newlines only (no coercion)
        for name, data in result.items():
            lp = data.get("letter_parts", {})
            for part in ("hook", "bridge", "case1_text", "case2_text", "closing", "cta", "signature"):
                if lp.get(part):
                    lp[part] = fix_newlines(lp[part])
            if data.get("screening_answers"):
                data["screening_answers"] = fix_newlines(data["screening_answers"])
            if data.get("selected_hook"):
                data["selected_hook"] = fix_newlines(data["selected_hook"])
            for opt in data.get("hook_options", []):
                if opt.get("text"):
                    opt["text"] = fix_newlines(opt["text"])

            data.setdefault("job_evaluation",
                            {"decision": "SKIP", "reasoning": "Missing evaluation", "observations": []})
            data.setdefault("selected_cases", [])
            data.setdefault("hook_options", [])
            data.setdefault("selected_hook", "")
            data.setdefault("letter_parts", {})
            data.setdefault("screening_answers", "")

        return result

    except (json.JSONDecodeError, TypeError, ValueError) as e:
        msg = str(e)
        print(f"Initial generation type/format error: {msg}")
        return {"error": msg}
    except Exception as e:
        print(f"Initial generation error: {e}")
        return {"error": str(e)}


async def generate_edit_response(
        edit_request: str,
        previous_response: dict,
        conversation_history: list,
        api_key: str
) -> dict:
    client_local = AsyncOpenAI(api_key=api_key)
    system_message = {
        "role": "system",
        "content": (
            "Ты – помощник по редактированию сгенерированных писем. "
            "Пользователь хочет изменить предыдущий ответ. Ты получишь JSON с предыдущим ответом "
            "и запрос на изменение. Верни обновлённый JSON в том же формате, что и исходный. "
            "Не меняй структуру, только поля, которые нужно отредактировать (например, letter_parts, selected_hook, screening_answers). "
            "Если запрос неясен, оставь поля без изменений."
        )
    }
    messages = [system_message]
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "assistant", "content": json.dumps(previous_response, ensure_ascii=False)})
    messages.append({"role": "user", "content": f"Edit request: {edit_request}"})

    try:
        response = await client_local.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)

        if not isinstance(result, dict):
            raise TypeError(
                f"Top-level response must be an object, got {type(result).__name__}"
            )

        # Detect shape and validate
        first_val = next(iter(result.values()), None)
        if isinstance(first_val, dict) and "letter_parts" in first_val:
            # Multi-profile shape
            for profile_name, profile_data in result.items():
                _validate_profile_data(profile_name, profile_data)
            for name, data in result.items():
                lp = data.get("letter_parts", {})
                for part in ("hook", "bridge", "case1_text", "case2_text", "closing", "cta", "signature"):
                    if lp.get(part):
                        lp[part] = fix_newlines(lp[part])
                if data.get("screening_answers"):
                    data["screening_answers"] = fix_newlines(data["screening_answers"])
                if data.get("selected_hook"):
                    data["selected_hook"] = fix_newlines(data["selected_hook"])
                for opt in data.get("hook_options", []):
                    if opt.get("text"):
                        opt["text"] = fix_newlines(opt["text"])
        else:
            # Single-profile / flat shape
            _validate_profile_data("(edit response)", result)
            lp = result.get("letter_parts", {})
            for part in ("hook", "bridge", "case1_text", "case2_text", "closing", "cta", "signature"):
                if lp.get(part):
                    lp[part] = fix_newlines(lp[part])
            if result.get("screening_answers"):
                result["screening_answers"] = fix_newlines(result["screening_answers"])
            if result.get("selected_hook"):
                result["selected_hook"] = fix_newlines(result["selected_hook"])
            for opt in result.get("hook_options", []):
                if opt.get("text"):
                    opt["text"] = fix_newlines(opt["text"])

        return result

    except (json.JSONDecodeError, TypeError, ValueError) as e:
        msg = str(e)
        print(f"Edit generation type/format error: {msg}")
        return {"error": msg}
    except Exception as e:
        print(f"Edit generation error: {e}")
        return {"error": str(e)}


def append_to_google_sheet(
        job_description: str,
        profile_name: str,
        cover_letter: str,
        screening_answers: str = "",
) -> Optional[int]:
    """
    Appends a new row to the Google Sheet and returns the 1-based row number
    that was written (needed so we can update it later).  Returns None if
    Sheets is not configured or the write fails.
    """
    try:
        creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        worksheet_name = os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "Sheet1")

        if not creds_json or not spreadsheet_id:
            print("⚠️ Google Sheets credentials not configured, skipping logging")
            return None

        creds_dict = json.loads(creds_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client_gspread = gspread.authorize(creds)

        sheet = client_gspread.open_by_key(spreadsheet_id).worksheet(worksheet_name)
        now = datetime.now().isoformat()

        # Truncate oversized fields
        job_preview = job_description[:5000] + ("..." if len(job_description) > 5000 else "")
        letter_preview = cover_letter[:5000] + ("..." if len(cover_letter) > 5000 else "")
        screening_preview = screening_answers[:5000] + ("..." if len(screening_answers) > 5000 else "")

        row = [now, job_preview, profile_name, letter_preview, screening_preview]
        sheet.append_row(row)

        # gspread doesn't return the written row index directly, so we ask for
        # the current number of rows after the append.
        row_number = len(sheet.get_all_values())
        print(f"✅ Записано в Google Sheets: {profile_name} - PASS (row {row_number})")
        return row_number

    except Exception as e:
        import traceback
        print(f"❌ Ошибка записи в Google Sheets: {e}")
        traceback.print_exc()
        return None


def update_google_sheet_row(
        row_number: int,
        job_description: str,
        profile_name: str,
        cover_letter: str,
        screening_answers: str = "",
) -> None:
    """
    Overwrites an existing row (identified by its 1-based *row_number*) in the
    Google Sheet.  The timestamp in column A is refreshed to the current time
    so it's clear when the record was last edited.
    """
    try:
        creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        worksheet_name = os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "Sheet1")

        if not creds_json or not spreadsheet_id:
            print("⚠️ Google Sheets credentials not configured, skipping update")
            return

        creds_dict = json.loads(creds_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client_gspread = gspread.authorize(creds)

        sheet = client_gspread.open_by_key(spreadsheet_id).worksheet(worksheet_name)
        now = datetime.now().isoformat()

        # Truncate oversized fields (same limits as append)
        job_preview = job_description[:5000] + ("..." if len(job_description) > 5000 else "")
        letter_preview = cover_letter[:5000] + ("..." if len(cover_letter) > 5000 else "")
        screening_preview = screening_answers[:5000] + ("..." if len(screening_answers) > 5000 else "")

        # update() accepts A1 notation; we write columns A–E of the target row.
        cell_range = f"A{row_number}:E{row_number}"
        sheet.update(cell_range, [[now, job_preview, profile_name, letter_preview, screening_preview]])
        print(f"✅ Обновлено в Google Sheets: {profile_name} - row {row_number}")

    except Exception as e:
        import traceback
        print(f"❌ Ошибка обновления Google Sheets row {row_number}: {e}")
        traceback.print_exc()

# ----------------------------------------------------------------------
# Пайплайн обработки (без GUI)
# ----------------------------------------------------------------------
async def process_job(job_description: str, conversation_history: list = None, saved_state: dict = None):
    try:
        if conversation_history and len(conversation_history) > 1:
            if not saved_state:
                return {"error": "No saved state for editing."}, None
            edit_request = job_description
            old_responses = saved_state.get("responses", {})
            new_responses = {}
            for name, old_resp in old_responses.items():
                new_resp = await generate_edit_response(
                    edit_request=edit_request,
                    previous_response=old_resp,
                    conversation_history=conversation_history,
                    api_key=OPENAI_API_KEY
                )
                new_responses[name] = new_resp
            new_saved_state = {
                "cases": saved_state["cases"],
                "responses": new_responses
            }
            return new_responses, new_saved_state
        else:
            best_cases = await rag.retrieve_cases(job_description, OPENAI_API_KEY)
            if not best_cases:
                return {"error": "No relevant cases found."}, None
            best_cases_with_content = []
            for case in best_cases:
                case_id = case.get("id")
                if not case_id:
                    continue
                content = await load_case_content(case_id)
                if content:
                    best_cases_with_content.append({
                        "id": case_id,
                        "name": case.get("name", ""),
                        "link": case.get("link", ""),
                        "content": content
                    })
            if not best_cases_with_content:
                return {"error": "No cases could be loaded."}, None
            all_responses = await generate_initial_response(
                job_description=job_description,
                best_cases_with_content=best_cases_with_content,
                user_profiles=user_profiles,
                selection_rules=selection_rules,
                cover_letter_rules=cover_letter_rules,
                letter_template=letter_template,
                api_key=OPENAI_API_KEY,
                allowed_profiles=None
            )
            new_saved_state = {
                "cases": best_cases_with_content,
                "responses": all_responses
            }
            return all_responses, new_saved_state
    except Exception as e:
        return {"error": f"Processing failed: {str(e)}"}, None