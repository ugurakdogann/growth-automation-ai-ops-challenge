# Submission Summary

## Project

Konuşarak Öğren Growth Automation & AI Ops Intern Challenge.

This repository contains a working prototype for collecting HR-focused leads,
cleaning and enriching them, scoring lead quality, estimating email addresses
with transparent evidence, and generating personalized outreach messages.

## What Was Built

- Input-driven lead pipeline for CSV/JSON data
- SerpAPI/Google-based public lead collection
- 181 HR-related leads from 42 Turkish companies
- Lead cleaning and duplicate handling
- Enrichment for sector, company size, HR role, pain point, English need and outreach angle
- Lead scoring
- Evidence-based email enrichment
- LinkedIn DM and cold email generation
- Output verification script

## Data Collection

The main dataset was collected from Google-indexed LinkedIn profile results via
SerpAPI. The collector searches queries like:

```text
site:linkedin.com/in/ "İK" "Turkcell"
```

The main pipeline uses Google-indexed public LinkedIn profile results through SerpAPI.

## Final Output

- Final lead file: `data/leads_final.xlsx`
- Company-level message files: `data/messages/`
- Email evidence report: `data/email_enrichment_report.md`

Verified final numbers:

- Total leads: 181
- Real public personal emails: 0
- Estimated emails: 181
- Evidence URLs for estimated emails: 181
- Email leaks into real email column: 0
- Rejected records: 0

## Email Methodology

No public personal HR emails were found. Therefore the real `email` field is
left empty.

For each company, a public official domain evidence URL was recorded. Estimated
emails are generated using a `first.last@domain` pattern and stored only in the
`estimated_email` field with:

- `email_status`
- `email_confidence`
- `email_evidence_url`
- `email_pattern`
- `email_pattern_source_note`

This keeps guessed email addresses clearly separated from verified public emails.

## How To Run

```bash
pip install -r requirements.txt
python main.py
python scripts/email_enrich.py
python main.py
python scripts/verify_outputs.py
```

To collect fresh leads:

```bash
python scripts/collect_leads.py --api-key YOUR_SERPAPI_KEY --max 4
python main.py
python scripts/email_enrich.py
python main.py
python scripts/verify_outputs.py
```

No real SerpAPI / Google Search API key is committed to the repository. A user
can pass their own key with `--api-key` or set `SERPAPI_KEY` as an environment
variable.

## Challenge Fit

The challenge asks for a small working prototype, not a perfect production
system. This submission provides a runnable end-to-end workflow:

1. Lead collection
2. Cleaning
3. Enrichment
4. Scoring
5. Email estimation with evidence
6. Personalized outreach generation
7. Output verification

Production improvements would include CRM integration, approved data providers,
human review for `needs_review` leads, reply classification and inbox automation.
