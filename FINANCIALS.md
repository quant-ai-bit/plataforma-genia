# Financial Summary & Unit Economics: PLATAFORMA GENIA

Since we are in an early launch stage, we track our financial viability through **Non-monetary Barter Valuation** (service-to-space exchange), **Unit Economics** running on Google Cloud Vertex AI, and **Active Pilot Programs**.

---

## 1. Income Statement (P&L Equivalent) - Last 30 Days (USD)

| Category | Cash Value (USD) | Barter Equivalent (USD) | Description |
|---|---|---|---|
| **Direct Cash Revenue** | $0.00 | - | Pre-revenue / Early pilot stage |
| **Barter Revenue (Coworking)** | - | $250.00 | Reception Agent services traded for team workspace |
| **Total Income Value** | **$0.00** | **$250.00** | **Total validated economic utility** |
| **Infrastructure Costs (Vertex AI)**| ($15.00) | - | Gemini API usage for production agents |
| **Hosting & Domain (Vercel)** | ($20.00) | - | Next.js frontend + FastAPI server + domain |
| **Marketing / CAC** | $0.00 | - | 100% organic/referral onboarding for pilots |
| **Net Operational Benefit** | **($35.00)** | **$215.00** | **Positive net economic value** |

---

## 2. Unit Economics (Gemini 2.0 Flash)

Our business model is highly viable because running on **Google Cloud Vertex AI (Gemini 2.0 Flash)** gives us extremely high margins.

### Cost per 1,000 Chats:
*   **Average Tokens per Chat Session:** 4,000 input tokens + 800 output tokens.
*   **Gemini 2.0 Flash Pricing (Vertex AI):**
    *   Input: $0.075 per million tokens
    *   Output: $0.30 per million tokens
*   **Cost Calculation:**
    *   Input cost: 4,000,000 tokens * $0.075/M = $0.30
    *   Output cost: 800,000 tokens * $0.30/M = $0.24
    *   Total API Cost: **$0.54 per 1,000 full chat sessions**.
*   **Stripe Subscription Price (Starter):** $99.00 / month (includes up to 10,000 messages).
*   **Gross Margin:** **> 90%** (even including database queries and vector search).

---

## 3. Official Hackathon Financial & User Disclosure

The following fields provide direct evidence in accordance with the official rules of the *Build with Gemini XPRIZE Hackathon*:

### A. Financial Disclosures
*   **Total Revenue:** $0.00 USD (All direct commercial validation is currently conducted through our non-monetary barter model).
*   **Revenue by Month (Calendar 2026):**
    *   *May 2026:* $0.00 USD
    *   *June 2026:* $0.00 USD
    *   *July 2026:* $0.00 USD
    *   *August 2026:* $0.00 USD
*   **Total Costs (Excluding Marketing):** $35.00 USD.
    *   *One-Sentence Description:* These costs cover our Next.js dashboard deployment on Vercel, local database storage, and Google Cloud Vertex AI Gemini API token usage for our live agents.
*   **Marketing and Customer Acquisition Spend:** $0.00 USD (All pilots were onboarded organically through direct startup community outreach).
*   **Related-Party Revenue:** $0.00 USD.
*   **Related-Party Barter Valuation:** $250.00 USD (Reception Agent services traded for team workspace with our partner coworking space).

### B. User Evidence
*   **Number of Individual Users:** 3 active organizations/users running live agents in production.
*   **High-Level User Breakdown:**
    1.  *Digital Marketing & Tech Agency (GENIA Internal):* Operates an agent on WhatsApp to answer FAQs, pre-qualify incoming agency leads, and book meeting slots.
    2.  *Co-working Space (Barter Partner):* Operates a WhatsApp reception agent to schedule workspace tours and answer building FAQs.
    3.  *Independent Professional Contractor (Tutanqui Pilot):* Operates a WhatsApp agent to qualify painting and electrician leads while the contractor is working on-site.
*   **Customer Testimonial:**
    > "El agente de WhatsApp de GENIA nos ha permitido capturar y calificar prospectos a cualquier hora, incluso cuando estamos en reuniones o fuera de la oficina, ahorrándonos horas de atención repetitiva." — Coworking Space Manager.

### C. Evidence of Product Running (Continuous Production)
1.  **Agent Execution Logs:** Audited execution logs of tools and prompt workflows are stored in the database and made publicly downloadable in JSON/CSV format directly from the `/evidence` page.
2.  **API Usage Records:** Token count, provider information, and costs are tracked in real-time in the `agent_usages` database table.
3.  **Active Connections:** Agents manage live conversations on WhatsApp Cloud API, routed dynamically based on Meta’s incoming phone number payloads.
