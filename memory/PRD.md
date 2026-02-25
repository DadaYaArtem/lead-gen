# Interexy Lead Analyzer - PRD

## Problem Statement
B2B sales lead analysis web app for Interexy. Fetches unread LinkedIn conversations from HeyReach API, filters "Catch Up" leads (who replied with thank-you to congratulations), runs deep OpenAI analysis with web search per lead, generates 10-15 personalized follow-up messages.

## Architecture
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React with Shadcn UI, Tailwind CSS
- **APIs**: HeyReach API (conversation fetch), OpenAI Responses API (gpt-4o with web_search)
- **Storage**: In-memory job store (no database needed)

## User Personas
- Non-technical B2B sales team at Interexy

## Core Requirements
- One-click "Run Analysis" workflow
- Real-time progress tracking (polling every 3s)
- Lead cards with fit scores (color-coded), executive summaries
- 10-15 message variants per lead grouped by type
- Copy-to-clipboard for each message
- Top 3 recommended messages highlighted

## What's Been Implemented (Jan 2026)
- Full backend pipeline: HeyReach fetch → OpenAI filtering → Deep analysis → Message generation
- POST /api/run-analysis, GET /api/status/{job_id}, GET /api/results/{job_id}
- Frontend dashboard with progress bar, lead cards, message groups
- All tests passing (100% backend, 100% frontend)

## Backlog
- P1: Export results to CSV/PDF
- P1: History of past analysis runs (persist to MongoDB)
- P2: Manual lead URL input for individual analysis
- P2: Message sending integration back to HeyReach
- P3: Analytics dashboard (lead scores over time)
