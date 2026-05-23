# Prompt Examples
## HumanMaximizer AI Lead Generation System
**Razor Infotech Pvt Ltd — AI Architect / GenAI Engineer Assignment**

All prompts are Jinja2 templates in `backend/prompts/`. They use `StrictUndefined` mode — any missing variable raises an error at render time rather than silently producing a hallucination-prone prompt.

---

## 1. ResearchAgent — `research_summary.j2`

### Purpose
Generates a 3-paragraph structured company intelligence report that the QualificationAgent and SalesAgent consume downstream.

### Template Structure

```jinja2
You are an expert B2B sales researcher for an HRMS software company.

COMPANY INFORMATION:
Company: {{ company_name }}
Domain: {{ domain }}
Industry: {{ industry }}
Employees: {{ employee_count or "Unknown" }}
Location: {{ hq_location or "Unknown" }}
Current HR Tech: {{ tech_stack | join(", ") if tech_stack else "Unknown" }}
Growth Signal: {{ growth_signal | replace("_", " ") | title }}

WEBSITE CONTENT (scraped):
{{ description[:2000] if description else "No website content available." }}

---

Write a 3-paragraph lead summary using ONLY the facts above. Do not invent statistics, metrics, or contact names.

Format your response exactly as follows:

COMPANY OVERVIEW: [One paragraph summarising the company's business, scale, and market position]

HR PAIN POINTS: [One paragraph describing specific HR, payroll, or workforce challenges this company likely faces based on its size, industry, and current tech stack]

HRMS FIT SIGNAL: [One paragraph explaining why or why not this company is a good candidate for HumanMaximizer HRMS, with specific signals from the data above]
```

### Example Input

```
Company: Metropolis Healthcare Ltd
Domain: metropolishealthcare.com
Industry: Healthcare
Employees: 4,000
Location: Mumbai, Maharashtra
Current HR Tech: Excel, Google Sheets
Growth Signal: Expansion (entering tier-2 cities)
Website Content: "Metropolis Healthcare operates 220+ diagnostic labs across 
India... recently expanded to Patna, Bhopal, and Nagpur... managing 4,000+ 
employees across clinical and administrative roles..."
```

### Example Output (Mistral-7B)

```
COMPANY OVERVIEW: Metropolis Healthcare Ltd is one of India's leading diagnostic 
chains, operating 220+ labs across major cities and now expanding aggressively into 
tier-2 markets. With 4,000 employees spanning clinical staff, phlebotomists, lab 
technicians, and administrative teams, Metropolis operates a complex multi-location 
workforce that spans multiple states.

HR PAIN POINTS: Managing HR for 4,000 employees across 220+ labs using Excel and 
Google Sheets creates significant operational risk. Every statutory filing cycle — PF, 
ESIC, PT across multiple states — requires manual reconciliation. As Metropolis expands 
into tier-2 cities, each new location adds a new state's compliance requirements, 
multi-site attendance tracking complexity, and onboarding volume that spreadsheet-based 
systems cannot handle efficiently.

HRMS FIT SIGNAL: Strong HRMS candidate. Metropolis's spreadsheet-based HR is a critical 
signal — at 4,000 employees across 220+ multi-state labs, they are well past the threshold 
where manual HR creates measurable compliance risk and cost. The tier-2 expansion directly 
increases this complexity. HumanMaximizer's multi-state statutory compliance module and 
multi-location attendance management directly address Metropolis's stated pain points.
```

---

## 2. QualificationAgent — `qualification_reasoning.j2`

### Purpose
Generates a 2-sentence qualification reasoning that explains the strongest signal and the biggest risk — used by sales reps to understand the opportunity at a glance.

### Template Structure

```jinja2
You are a B2B sales qualification analyst for HumanMaximizer HRMS.

LEAD DATA:
Company: {{ company_name }}
Industry: {{ industry }}
Employees: {{ employee_count or "Unknown" }}
Location: {{ hq_location or "Unknown" }}
Tech Stack: {{ tech_stack | join(", ") if tech_stack else "Unknown" }}
Growth Signal: {{ growth_signal | replace("_", " ") | title }}
Decision Makers: {{ decision_makers | length }} found

SCORE BREAKDOWN:
- Company Size Fit:             {{ score_breakdown.company_size_fit }}/20
- Industry Relevance:           {{ score_breakdown.industry_relevance }}/20
- Tech Stack Gap:               {{ score_breakdown.tech_stack_gap }}/20
- Decision Maker Reachability:  {{ score_breakdown.decision_maker_reachability }}/20
- Growth Signal:                {{ score_breakdown.growth_signal }}/20
Total Score: {{ qualification_score }}/100

---

Write exactly 2 sentences:
1. The strongest qualification signal (why this lead is a good HRMS prospect)
2. The biggest risk or blocker for this opportunity

Be specific. Reference the actual score values and company data.
```

### Example Input

```
Company: Metropolis Healthcare Ltd
Industry: Healthcare
Employees: 4,000
Tech Stack: Excel, Google Sheets
Growth Signal: Expansion

Score Breakdown:
- Company Size Fit:             20/20
- Industry Relevance:           20/20
- Tech Stack Gap:               18/20
- Decision Maker Reachability:  0/20
- Growth Signal:                20/20
Total: 78/100
```

### Example Output (Mistral-7B)

```
Metropolis Healthcare's Excel-based HR for 4,000 employees across 220+ labs is the strongest 
HRMS fit signal in this dataset (18/20 tech gap), compounded by active tier-2 city expansion 
adding new state compliance obligations at exactly the point where manual systems break down. 
The primary risk is zero decision-maker reachability (0/20) — no CHRO, HR Director, or 
People Manager contact was identified, making multi-channel outreach impossible without a 
warm introduction or LinkedIn search.
```

---

## 3. SalesAgent — `cold_email.j2`

### Purpose
Generates a personalized B2B cold email grounded exclusively in retrieved HumanMaximizer product knowledge. The template explicitly forbids hallucination.

### Template Structure

```jinja2
You are a B2B sales copywriter for HumanMaximizer HRMS.

COMPANY PROFILE:
Company: {{ company_name }}
Industry: {{ industry }}
Employees: {{ employee_count or "Unknown" }}
Location: {{ hq_location or "Unknown" }}
Current HR Tech: {{ tech_stack | join(", ") if tech_stack else "Unknown" }}
Growth Signal: {{ growth_signal | replace("_", " ") | title }}
{% if decision_makers %}
Decision Maker: {{ decision_makers[0].name }}, {{ decision_makers[0].title }}
{% endif %}

QUALIFICATION SUMMARY:
{{ qualification_reasoning }}

HUMANMAXIMIZER PRODUCT KNOWLEDGE (RAG — use ONLY these facts):
{% for chunk in rag_chunks %}
---
{{ chunk }}
{% endfor %}

---

Write a personalized cold email using ONLY the facts above. Do not invent statistics, 
percentages, customer names, or product features not mentioned in the knowledge above.

Requirements:
- Subject line: specific to this company, ≤ 8 words
- Body: 150–220 words
- Tone: professional but conversational, peer-to-peer
- Reference specific HR pain points from the company profile
- Mention 1–2 specific HumanMaximizer features from the RAG knowledge above
- End with a single, low-friction call to action (15-minute demo)

Format exactly as:
SUBJECT: [subject line]

BODY:
[email body]
```

### Example Output (Mistral-7B)

```
SUBJECT: Automate Multi-State HR Compliance at Metropolis Healthcare

BODY:
Dear [CHRO Name],

Managing HR for 4,000 employees across 220+ labs in Excel means every PF, ESIC, and PT 
filing cycle across multiple states is a manual reconciliation exercise — and your tier-2 
expansion into Patna and Nagpur just added three new compliance jurisdictions.

HumanMaximizer's statutory compliance module handles PF, ESIC, and PT filings across all 
states automatically — generating forms, calculating deductions, and filing on schedule 
from a single dashboard, without reconciliation.

Our multi-location attendance management integrates across all your lab locations into one 
view, so payroll runs on clean data from day one of every expansion.

Healthcare chains similar to Metropolis — with distributed multi-state workforces — are 
exactly the use case we've built for.

Would you have 15 minutes this week for a demo tailored to multi-location diagnostics 
operations? I can walk through the compliance automation end to end.

Best regards,
HumanMaximizer Sales Team
```

---

## 4. SalesAgent — `linkedin_message.j2`

### Purpose
Generates a short, high-conversion LinkedIn connection request message. Strictly limited to ≤300 characters to fit LinkedIn's DM character limit.

### Template Structure

```jinja2
You are a B2B sales outreach specialist.

RECIPIENT: {{ dm_name }}, {{ dm_title }} at {{ company_name }}

PAIN HOOK (the key HR challenge for this company):
{{ pain_hook }}

HUMANMAXIMIZER ONE-LINER (use this exact product description):
{{ hm_one_liner }}

---

Write a LinkedIn connection request message. Requirements:
- Maximum 300 characters total
- No emojis
- No exclamation marks
- Start with "Hi {{ dm_name_first }},"
- Reference the specific pain hook
- Mention HumanMaximizer in one sentence
- End with an open question
```

### Example Input

```
Recipient: Priya Mehta, CHRO at Metropolis Healthcare
Pain Hook: Managing HR for 220 labs through Excel is creating compliance risk as you expand to tier-2 cities
HM one-liner: HumanMaximizer automates multi-state statutory compliance for Indian enterprises with distributed workforces
```

### Example Output (Mistral-7B)

```
Hi Priya, scaling Metropolis across 220 labs while managing multi-state compliance on 
Excel must be creating real pressure as you enter tier-2 markets. HumanMaximizer automates 
this end-to-end. Would you be open to a quick chat?
```
*(≤ 300 characters: 264)*

---

## 5. SalesAgent — `self_critique.j2`

### Purpose
A second Mistral-7B pass that verifies the generated email contains no claims unsupported by the provided RAG chunks. Emits structured JSON for the Prometheus hallucination counter.

### Template Structure

```jinja2
You are a fact-checker for B2B sales emails.

GENERATED EMAIL:
{{ email_body }}

APPROVED PRODUCT FACTS (from HumanMaximizer knowledge base):
{% for chunk in rag_chunks %}
---
{{ chunk }}
{% endfor %}

---

Review the email above. Identify any specific claims, statistics, percentages, customer 
names, or product features that are NOT supported by the approved facts above.

Respond in JSON format only:
{
  "hallucinated_claims": ["<claim 1>", "<claim 2>"],
  "is_grounded": true or false,
  "verdict": "<one sentence summary>"
}

If all claims are supported, return:
{
  "hallucinated_claims": [],
  "is_grounded": true,
  "verdict": "All claims verified against product knowledge base."
}
```

### Example Output (Mistral-7B)

```json
{
  "hallucinated_claims": [],
  "is_grounded": true,
  "verdict": "All claims verified against product knowledge base — statutory compliance module, multi-location attendance, and PF/ESIC/PT filing automation are all present in the retrieved chunks."
}
```

---

## Summary

| Template | Agent | Model Calls | Temperature | Context Budget |
|---|---|---|---|---|
| `research_summary.j2` | ResearchAgent | 1 | 0.2 | ~2,000 tokens input, ~400 output |
| `qualification_reasoning.j2` | QualificationAgent | 1 | 0.1 | ~800 tokens input, ~80 output |
| `cold_email.j2` | SalesAgent | 1 | 0.3 | ~3,000 tokens input, ~250 output |
| `linkedin_message.j2` | SalesAgent | 1 | 0.3 | ~600 tokens input, ~60 output |
| `self_critique.j2` | SalesAgent | 1 | 0.0 | ~2,500 tokens input, ~100 output |

**Total LLM calls per qualified lead: 5** (4 generation + 1 critique)  
**Total LLM calls per disqualified lead: 2** (research summary + qualification reasoning)
