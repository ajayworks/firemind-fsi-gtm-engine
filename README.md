# Firemind FSI GTM Engine

A Streamlit-based go-to-market intelligence prototype for identifying, prioritising, and engaging Financial Services accounts.

## What it does

Firemind FSI GTM Engine helps sales and GTM teams:

- Rank target accounts by priority
- Understand why an account is a good fit
- Review evidence behind account scores
- Identify relevant stakeholders
- Generate value hypotheses and conversation openers
- Create AI-assisted outreach drafts
- Track outreach activity in a lightweight CRM history view

## Core workflow

1. Review the account ranking table.
2. Select a target account.
3. Inspect the account’s score explanation and supporting evidence.
4. Review recommended use cases, timing signals, and key stakeholders.
5. Use the value hypothesis and conversation opener to prepare outreach.
6. Generate and save a personalised outreach draft.
7. Update outreach status in CRM history.

## Scoring methodology

Account scoring implements a use-case screen developed from buyer-side
research into AI adoption in mid-size UK financial institutions: **capability
contributes additively, permission acts as a ceiling, and data readiness acts
as a gate.**

The practical consequence is that this engine deliberately does *not* rank
the largest institutions highest. Company size is scored as a band centred on
the mid-size segment, because tier-1 banks are a different sales motion.

Each account is scored using five GTM signals:

- **Scale** — the size and strategic importance of the organisation.
- **Technology** — evidence of relevant technology, transformation, or platform activity.
- **Operational Pain** — evidence of operational complexity, incidents, regulatory pressure, or service-management challenges.
- **Use-Case Fit** — alignment with Firemind’s target use cases.
- **Timing** — recent signals that suggest a reason to engage now.

### Segment fit is structural, not a component

The partner defined the target segment as **200–2,000 staff with roughly
$100M+ revenue**, already comfortable buying vendor services. An organisation
outside that band is not a weaker prospect — it is a different sales motion,
with procurement measured in quarters, incumbent vendors and an internal
platform team that would build rather than buy.

So ICP fit **multiplies** the score rather than contributing to it (core 1.0,
adjacent 0.75, upper-mid 0.5, enterprise 0.25). Headcount is deliberately
excluded from the scale component, which measures operational footprint
instead — scoring size in both places would penalise the same fact twice.

**Account source** then multiplies the total. Expansion into an existing
consulting customer, or a partner-sourced lead, is a cheaper motion than
net-new acquisition — the commercial relationship exists, the data estate is
understood, and procurement has been through once. Relationship multiplies
rather than adds, because it shortens every stage of the funnel rather than
contributing points at one. This field is supplied by the operator; the
bundled demo data leaves every account as `unknown` and makes no claim about
any company's relationship with Firemind.

### Learning loop

Scoring weights are a hypothesis about which signals predict a buying
conversation. `src/feedback.py` reads outreach outcomes back out of the CRM
table and measures reply rate by signal type, proposing weight adjustments
only once there is enough data to justify them — at least 40 sends overall
and 15 per signal, with any single change capped at 25%. Below those
thresholds it reports what it sees and explicitly declines to adjust.

The application presents the supporting evidence alongside the score so users can review the reasoning rather than relying on a black-box recommendation.

## Data and AI use

The prototype uses stored account intelligence and public-source evidence
about companies. Company-level signals are drawn from public reporting.

### Personal data

Company signals are public corporate information. Stakeholder records are
personal data about identifiable people who did not ask to be in a sales
database, so the two are handled differently.

The engine stores the **role map** — job title, persona, source — and
resolves the **individual** at outreach time. Three modes, set with
`GTM_PERSONAL_DATA_MODE`:

| Mode | Live lookup | Role stored | Name stored |
|---|---|---|---|
| `demo` *(default)* | runs, discards | no | no |
| `ephemeral` | yes | yes | **no** — session memory only |
| `persisted` | yes | yes | yes, with 30-day retention |

A cloned repo runs in `demo` mode against synthetic stakeholder records. No
real individual's personal data is stored or published here.

People are deduplicated on a salted, non-reversible reference rather than a
name, so the engine recognises the same person across runs without holding
their identity — and the reference is not correlatable between accounts.
`privacy.purge_all_personal_data()` clears every stored name while leaving
the role map intact.

AI-generated outputs, including outreach drafts, are intended to support human decision-making. They should be reviewed and edited before being used externally.

## Technology

- Python
- Streamlit
- SQLite
- Public web research sources
- AI-assisted content generation

## Demo account

For the strongest end-to-end demonstration, use:

```text
Coventry Building Society
```

This account sits in the target segment, carries real operational-resilience
evidence, and scores through all four fit dimensions — so the reasoning is
visible end to end. Compare it with **Aviva**, which is gated to zero on
use-case fit, to see the engine decline an account and say why.

## Important note
This is a prototype created for GTM and sales-intelligence demonstration purposes. Account scores, stakeholder data, and generated outreach should be validated before production use.

## How to run the application

**1. Clone and install dependencies**

```bash
git clone https://github.com/ajayworks/firemind-fsi-gtm-engine.git
cd firemind-fsi-gtm-engine
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**2. Add an API key** (only needed for live research; the bundled demo
database works without one)

```bash
echo "TAVILY_API_KEY=your_key_here" > .env
```

**3. Run**

```bash
streamlit run app.py
```

Then open the local URL shown in the terminal, usually http://localhost:8501.

**4. Optional — research a new account**

```bash
python3 -m src.run_full_pipeline "Company Name"
```

This runs in `demo` personal-data mode by default, so stakeholder discovery
executes but no personal data is written. See *Personal data* below.


## Account intelligence model

Each account record brings together:

- **Account profile** — organisation name, sector, tier, priority, and funnel stage.
- **Score explanation** — the individual factors contributing to the account score.
- **Evidence and provenance** — source links, evidence types, and reliability indicators.
- **Why Now signals** — recent events or indicators that create a timely reason to engage.
- **Top People** — relevant stakeholders, job titles, personas, and available verification links.
- **GTM recommendations** — recommended use case, value hypothesis, conversation opener, and AI-assisted outreach draft.
- **CRM history** — saved outreach drafts and their current follow-up status.

This structure keeps account recommendations connected to visible evidence and practical sales actions.

## Limitations and responsible use

- Public research can be incomplete, outdated, or inaccurate.
- Account scores are prioritisation aids, not guaranteed buying-intent predictions.
- Stakeholder information should be verified before outreach.
- AI-generated messaging may require factual correction and tone adjustments.
- No generated content should be sent externally without human review.
- The prototype is designed for demonstration and portfolio use, not unattended production decision-making.