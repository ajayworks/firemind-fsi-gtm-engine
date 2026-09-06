import json
import streamlit as st
from src.outreach_generator import generate_outreach, save_outreach_draft
from src.run_full_pipeline import run_pipeline
from src.database import get_connection
from src import privacy
from src.feedback import signal_reply_rates, suggest_weight_adjustments
from src.scoring import PAIN_SIGNAL_WEIGHTS
from src.update_account_score import update_company_score
from src.account_brief_plus import build_evidence_brief
from src.add_company import add_company
from src.save_research_signals import save_signals
from src.enrich_company import enrich_company
from src.save_verified_people import save_verified_people

# Words .title() would mangle.
_ACRONYMS = {"ict", "dora", "kyc", "jml", "sre", "it", "ai", "crm", "gtm"}
_MIXED_CASE = {"finops": "FinOps"}


def pretty_label(value):
    if value is None:
        return ""

    words = str(value).replace("_", " ").strip().split()

    return " ".join(
        _MIXED_CASE.get(w.lower())
        or (w.upper() if w.lower() in _ACRONYMS else w.capitalize())
        for w in words
    )

st.set_page_config(
    page_title="Firemind FSI GTM Engine",
    page_icon="🔥",
    layout="wide"
)

def get_companies():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT company_name
        FROM companies
        ORDER BY company_name
    """)

    companies = [
        row[0]
        for row in cursor.fetchall()
    ]

    conn.close()

    return companies

def get_ranked_accounts():
    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.company_name,
            c.sector,
            s.total_score,
            s.tier,
            s.recommended_use_case,
            s.confidence
        FROM companies c
        JOIN account_scores s
            ON c.company_id = s.company_id
        ORDER BY s.total_score DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows

def get_outreach_history(company_name):
    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            o.outreach_id,
            o.channel,
            o.subject_line,
            o.status,
            o.message_version,
            o.sent_at,
            o.replied_at,
            o.meeting_booked,
            p.full_name,
            p.job_title
        FROM outreach o
        JOIN companies c
            ON o.company_id = c.company_id
        LEFT JOIN people p
            ON o.person_id = p.person_id
        WHERE c.company_name = ?
        ORDER BY o.outreach_id DESC
    """, (company_name,))

    rows = cursor.fetchall()
    conn.close()

    return rows

def update_outreach_status(outreach_id, new_status):
    conn = get_connection()
    cursor = conn.cursor()

    if new_status == "sent":
        cursor.execute("""
            UPDATE outreach
            SET status = ?,
                sent_at = CURRENT_TIMESTAMP
            WHERE outreach_id = ?
        """, (
            new_status,
            outreach_id
        ))

    elif new_status == "replied":
        cursor.execute("""
            UPDATE outreach
            SET status = ?,
                replied_at = CURRENT_TIMESTAMP
            WHERE outreach_id = ?
        """, (
            new_status,
            outreach_id
        ))

    elif new_status == "meeting":
        cursor.execute("""
            UPDATE outreach
            SET status = ?,
                meeting_booked = 1
            WHERE outreach_id = ?
        """, (
            new_status,
            outreach_id
        ))

    else:
        cursor.execute("""
            UPDATE outreach
            SET status = ?
            WHERE outreach_id = ?
        """, (
            new_status,
            outreach_id
        ))

    conn.commit()
    conn.close()


st.title("Firemind FSI GTM Engine")

st.caption(
    "Evidence-driven account prioritisation, persona targeting, "
    "outreach generation and lightweight CRM tracking for UK FSI."
)

st.divider()

with st.sidebar:
    st.caption(f"Personal-data mode: **{privacy.current_mode()}**")
    st.caption(privacy.NOTICE)

    if st.button("Purge stored names"):
        _conn = get_connection()
        _n = privacy.purge_all_personal_data(_conn)
        _conn.close()
        st.success(f"Cleared names from {_n} records. Role map retained.")

st.subheader("UK FSI Account Ranking")
st.caption(
    "Accounts are ranked using deterministic scoring across scale, "
    "technology complexity, operational pain, use-case fit and timing."
)

ranked_accounts = get_ranked_accounts()

ranking_data = []

for index, row in enumerate(ranked_accounts, start=1):
    score = row["total_score"]

    if score >= 80:
        priority_label = "Immediate priority"
        recommended_action = "Engage now"

    elif score >= 65:
        priority_label = "High priority"
        recommended_action = "Start targeted outreach"

    elif score >= 50:
        priority_label = "Research-qualified"
        recommended_action = "Validate buyer and engage"

    elif score >= 35:
        priority_label = "Needs more evidence"
        recommended_action = "Research more"

    else:
        priority_label = "Low current evidence"
        recommended_action = "Monitor"

    if score >= 80:
        funnel_stage = "Engage"

    elif score >= 65:
        funnel_stage = "Outreach"

    elif score >= 50:
        funnel_stage = "Qualified"

    elif score >= 35:
        funnel_stage = "Research"

    else:
        funnel_stage = "Monitor"

    ranking_data.append({
        "Rank": index,
        "Account": row["company_name"],
        "Sector": pretty_label(row["sector"]),
        "Score": row["total_score"],
        "Priority": priority_label,
        "Funnel Stage": funnel_stage,
        "Recommended Action": recommended_action,
        "Recommended Use Case": pretty_label(row["recommended_use_case"]),
        "Confidence": row["confidence"],
    })

st.dataframe(
    ranking_data,
    use_container_width=True,
    hide_index=True
)

st.divider()

st.subheader("Research New Account")

st.caption(
    "Enter a UK financial institution to research, enrich, score "
    "and add to the GTM engine."
)

new_company = st.text_input(
    "Company name",
    placeholder="e.g. Lloyds Banking Group"
)

refresh_research = st.checkbox(
    "Refresh public research",
    value=False,
    help=(
        "Turn this on to ignore cached research and run "
        "a fresh public search for the account."
    )
)

if st.button("Research New Account"):

    if not new_company.strip():
        st.warning("Please enter a company name.")

    else:
        from src.add_company import add_company, normalise_company_name

        company_to_research = normalise_company_name(new_company)

        status = st.status(
            f"Researching {company_to_research}...",
            expanded=True
        )

        try:
            status.write("1. Adding account to database...")
            add_company(company_to_research)

            status.write("2. Collecting public research and buying signals...")
            save_signals(
                company_to_research,
                refresh=refresh_research
            )

            status.write(
                "3. Enriching company size, geography, "
                "technology and recalculating score..."
            )
            enrich_company(company_to_research)

            status.write(
                "4. Discovering and verifying target personas..."
            )
            save_verified_people(company_to_research)

            status.update(
                label=f"{company_to_research} research complete.",
                state="complete",
                expanded=True
            )

            st.success(
                f"{company_to_research} has been added to the GTM engine."
            )

            st.session_state.selected_company = company_to_research
            st.session_state.show_account = True
            st.session_state.companies_refresh = True

            st.rerun()

        except Exception as error:

            status.update(
                label="Research failed.",
                state="error",
                expanded=True
            )

            st.error(
                f"Research failed: {error}"
            )

st.divider()

st.subheader("Account Intelligence")

st.caption(
    "Select an account to inspect evidence, score rationale, "
    "target personas and outreach."
)

if st.session_state.get("companies_refresh"):
    st.session_state.companies_refresh = False
    
companies = get_companies()

default_index = 0

if "selected_company" in st.session_state:
    if st.session_state.selected_company in companies:
        default_index = companies.index(
            st.session_state.selected_company
        )

selected_company = st.selectbox(
    "Select company",
    companies,
    index=default_index
)

st.session_state.selected_company = selected_company

if "show_account" not in st.session_state:
    st.session_state.show_account = False

if st.button("Why this account?"):
    st.session_state.show_account = True

if st.session_state.show_account:

    brief = build_evidence_brief(selected_company)

    if not brief:
        st.error("No account data found.")

    else:
        account = brief["account"]

        st.header(account["company_name"])

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Firemind Fit",
            f'{account["total_score"]}',
            help=(
                "Prioritisation score, not a percentage. The nominal maximum "
                "of 100 assumes maximum pain, technology, timing and a perfect "
                "permission ceiling at once; no workflow has a permission "
                "ceiling above 4, so the realistic ceiling on rich evidence is "
                "around 55-60. Rank within the pipeline is what matters."
            )
        )

        col2.metric(
            "Tier",
            pretty_label(account["tier"])
        )

        col3.metric(
            "Confidence",
            account["confidence"]
        )

        st.subheader("Why This Score?")

        with st.expander(
            f'Scale — {account["scale_score"]} / 15'
        ):
            st.write(
                "Based on company size, geographic reach and technology scale."
            )

        with st.expander(
            f'Technology — {account["technology_score"]} / 25'
        ):
            st.write(
                "Based on evidence of cloud adoption, infrastructure complexity "
                "and technical operations teams."
            )

            technology = brief.get(
                "technology_evidence",
                {}
            )

            cloud_evidence = technology.get(
                "cloud_evidence",
                []
            )

            infra_evidence = technology.get(
                "infra_evidence",
                []
            )

            team_evidence = technology.get(
                "team_evidence",
                []
            )

            if cloud_evidence:
                st.markdown("**Cloud evidence**")

                for item in cloud_evidence:
                    st.write(f"- {item}")

            if infra_evidence:
                st.markdown("**Infrastructure evidence**")

                for item in infra_evidence:
                    st.write(f"- {item}")

            if team_evidence:
                st.markdown("**Technical team evidence**")

                for item in team_evidence:
                    st.write(f"- {item}")

        with st.expander(
            f'Operational Pain — {account["operational_pain_score"]} / 25'
        ):
            st.write(
                "Based on signals such as outages, service disruption, "
                "operational resilience pressure and infrastructure hiring."
            )

            pain_signals = [
                item for item in brief["evidence"]
                if item["signal_type"] in [
                    "it_outage",
                    "service_disruption",
                    "incident_management_pressure",
                    "operational_resilience",
                    "sre_hiring",
                    "infrastructure_hiring",
                    "cost_reduction",
                    "operational_efficiency",
                ]
            ]

            if pain_signals:
                for item in pain_signals:
                    st.write(
                        f'- {item["signal_title"]}'
                    )
            else:
                st.write("No strong operational pain evidence found.")

        with st.expander(
            f'Use-Case Fit — {account["use_case_fit_score"]} / 25'
        ):
            st.write(
                f'Recommended use case: '
                f'**{account["recommended_use_case"].replace("_", " ")}**'
            )

            st.write(
                "Scored on four dimensions: verifiability and permission "
                "ceiling are properties of the workflow, taken from the buyer "
                "research; data readiness and system reachability are "
                "properties of this account. Capability adds, permission "
                "multiplies, readiness gates."
            )

        with st.expander(
            f'Timing — {account["timing_score"]} / 10'
        ):
            st.write(
                "Based on recent transformation, resilience, outage, AI, "
                "cloud and technology-investment signals."
            )

            timing_signals = [
                item for item in brief["evidence"]
                if item["signal_type"] in [
                    "it_outage",
                    "service_disruption",
                    "cloud_transformation",
                    "cloud_migration",
                    "infrastructure_modernisation",
                    "automation_programme",
                    "ai_adoption",
                    "agentic_ai_initiative",
                    "operational_resilience",
                    "dora_programme",
                    "technology_investment",
                    "managed_services",
                    "vendor_change",
                    "outsourcing_change",
                    "new_cto",
                    "new_cio",
                    "leadership_change",
                ]
            ]

            if timing_signals:
                for item in timing_signals:
                    st.write(
                        f'- {item["signal_title"]}'
                    )
            else:
                st.write("No strong timing signals found.")

        st.subheader("Data Provenance")

        enrichment_sources = brief.get(
            "enrichment_sources",
            []
        )

        if enrichment_sources:

            for source in enrichment_sources:

                with st.expander(
                    f'{source["evidence_type"]} — '
                    f'{source["source_title"]}'
                ):
                    st.write(
                        f'**Supports:** {source["evidence_type"]}'
                    )

                    st.write(
                        f'**Source type:** '
                        f'{pretty_label(source["source_type"])}'
                    )

                    st.write(
                        f'**Reliability:** {source["reliability"]}'
                    )

                    if source["url"]:
                        st.markdown(
                            f'[Open source]({source["url"]})'
                        )

        else:
            st.info(
                "No enrichment provenance available "
                "for this account."
            )

        st.divider()

        st.subheader("Account Source")

        _sources = ["existing_customer", "partner_sourced", "net_new", "unknown"]
        _labels = {
            "existing_customer": "Existing consulting customer (x1.35)",
            "partner_sourced": "Partner / AWS co-sell sourced (x1.15)",
            "net_new": "Net new — cold, from public signals (x1.00)",
            "unknown": "Unknown (x1.00)",
        }

        _current = (
            account["account_source"]
            if "account_source" in account.keys() and account["account_source"]
            else "net_new"
        )

        _choice = st.selectbox(
            "How did this account enter the pipeline?",
            _sources,
            index=_sources.index(_current) if _current in _sources else 2,
            format_func=lambda s: _labels[s],
        )

        st.caption(
            "This field is supplied by the operator, not inferred by the engine — "
            "the bundled demo data makes no claim about any company's commercial "
            "relationship with Firemind. "
            "Expansion into an existing consulting customer is a cheaper motion "
            "than net-new acquisition: the commercial relationship exists, the "
            "data estate is already understood, and procurement has been through "
            "once. Relationship multiplies the whole score rather than adding to "
            "it, because it shortens every stage of the funnel."
        )

        if _choice != _current:
            _conn = get_connection()
            _conn.execute(
                "UPDATE companies SET account_source = ? WHERE company_id = ?",
                (_choice, account["company_id"]),
            )
            _conn.commit()
            _conn.close()

            update_company_score(selected_company)
            st.rerun()

        st.subheader("Recommended Use Case")

        st.write(
            pretty_label(
                account["recommended_use_case"]
            )
        )

        # Four-dimension use-case fit screen.
        # Capability adds, permission multiplies, readiness gates - so the
        # reasoning is shown, not just the number.
        fit = json.loads(account["fit_breakdown"] or "{}") if "fit_breakdown" in account.keys() else {}

        if fit.get("gated"):
            st.warning(
                f'**Use-case fit gated — scores 0.** {fit["gate_reason"]}'
            )

        elif fit:
            c1, c2, c3, c4 = st.columns(4)

            c1.metric("Verifiability", f'{fit["verifiability"]}/7')
            c2.metric("Data readiness", f'{fit["data_readiness"]}/9')
            c3.metric("Reachability", f'{fit["system_reachability"]}/9')
            c4.metric("Permission", f'x{fit["permission_multiplier"]}')

            st.caption(
                f'Capability {fit["raw_capability"]} '
                f'x permission ceiling {fit["permission_multiplier"]} '
                f'= use-case fit {account["use_case_fit_score"]}. '
                "Verifiability and permission are properties of the workflow; "
                "data readiness and reachability are properties of the account."
            )

        st.subheader("Why Now")

        if not brief["evidence"]:
            st.info(
                "No public evidence found for this account. That is a research "
                "gap, not a finding — mid-size institutions publish far less "
                "than large banks. Qualify by phone before dropping it."
            )

        for item in brief["evidence"][:5]:

            st.write(
                f'**{item["signal_type"]}** — '
                f'{item["signal_title"]}'
            )

            if item["url"]:
                st.caption(item["url"])

        st.subheader("Top People")

        if not brief["people"]:
            st.info(
                "No stakeholder identified. Role discovery verifies a name "
                "against a public appointment announcement before recording it, "
                "and will not guess — run discovery in `ephemeral` mode to "
                "populate roles without storing personal data."
            )

        for person in brief["people"][:3]:

            st.markdown(
                f'**{person["name"]}** — '
                f'{person["title"]} '
                f'({pretty_label(person["persona"])})'
            )

            if person.get("verification_source_title"):
                st.caption(
                    "Verified from: "
                    f'{person["verification_source_title"]}'
                )

            if person.get("verification_source_url"):
                st.markdown(
                    f'[Open verification source]'
                    f'({person["verification_source_url"]})'
                )

            elif person.get("linkedin_url"):
                st.markdown(
                    f'[Open public profile]'
                    f'({person["linkedin_url"]})'
                )

        st.subheader("Value Hypothesis")

        st.write(
            brief["value_hypothesis"]
        )

        st.subheader("Conversation Opener")

        st.info(
            brief["conversation_opener"]
        )

        st.subheader("Next Action")

        st.success(
            brief["next_action"]
        )

        st.divider()

        st.subheader("Personalised Outreach Draft")

        st.caption(
            "AI-assisted draft for human review. No outreach is sent automatically."
        )

        outreach = generate_outreach(selected_company)

        if outreach:

            st.write(
                f'**Recipient:** {outreach["recipient_name"]} '
                f'— {outreach["recipient_title"]}'
            )

            st.write(
                f'**Persona:** {outreach["persona"]}'
            )

            st.write(
                f'**Subject:** {outreach["subject"]}'
     )

            st.text_area(
                "Draft message",
                outreach["message"],
                height=320
            )

            if st.button("Save Outreach Draft"):
                saved = save_outreach_draft(
                    selected_company,
                    outreach
                )

                if saved:
                    st.success("Outreach draft saved to CRM.")
                else:
                    st.error("Could not save outreach draft.")

            st.divider()

            history = get_outreach_history(selected_company)

            draft_count = sum(
                1 for row in history
                if row["status"] == "draft"
            )

            ready_count = sum(
                1 for row in history
                if row["status"] == "ready"
            )

            sent_count = sum(
                1 for row in history
                if row["status"] == "sent"
            )

            replied_count = sum(
                1 for row in history
                if row["status"] == "replied"
            )

            meeting_count = sum(
                1 for row in history
                if row["meeting_booked"]
            )

            st.subheader("CRM Funnel")

            col1, col2, col3, col4, col5 = st.columns(5)

            col1.metric("Draft", draft_count)
            col2.metric("Ready", ready_count)
            col3.metric("Sent", sent_count)
            col4.metric("Replied", replied_count)
            col5.metric("Meetings", meeting_count)

            st.subheader("Outreach History")


            if history:

                history_data = []

                for row in history:
                   history_data.append({
                        "ID": row["outreach_id"],
                        "Person": row["full_name"] or "Unknown",
                        "Title": row["job_title"] or "",
                        "Channel": row["channel"],
                        "Subject": row["subject_line"],
                        "Status": row["status"],
                        "Version": row["message_version"],
                        "Sent At": row["sent_at"] or "",
                        "Replied At": row["replied_at"] or "",
                        "Meeting": "Yes" if row["meeting_booked"] else "No",
                    })

                st.dataframe(
                    history_data,
                    use_container_width=True,
                    hide_index=True
                )

                st.write("### Update Outreach Status")

                outreach_options = {
                    f'#{row["outreach_id"]} — {row["full_name"] or "Unknown"} — {row["subject_line"]}':
                        row["outreach_id"]
                    for row in history
                }

                selected_outreach_label = st.selectbox(
                    "Select outreach",
                    list(outreach_options.keys())
                )

                selected_outreach_id = outreach_options[
                    selected_outreach_label
                ]

                status_options = [
                    "draft",
                    "ready",
                    "sent",
                    "replied",
                    "meeting"
                ]

                new_status = st.selectbox(
                    "New status",
                    status_options
                )

                if st.button("Update Status"):

                    update_outreach_status(
                        selected_outreach_id,
                        new_status
                    )

                    st.success(
                        f"Outreach status updated to: {new_status}"
                    )

                    st.rerun()

            else:
                st.info("No saved outreach yet for this account.")
            
            if outreach["evidence_url"]:
                st.caption(
                    f'Evidence source: {outreach["evidence_url"]}'
            )

        else:
            st.info(
                "No stakeholder identified for this account yet, so no draft "
                "has been generated. Run stakeholder discovery from the "
                "**Research New Account** panel above to populate contacts."
            )

        st.divider()

        with st.expander("Learning Loop — do the signals actually predict replies?"):

            st.caption(
                "Scoring weights are a hypothesis about which public signals "
                "predict a buying conversation. This compares them against what "
                "happened when messages were actually sent."
            )

            _conn = get_connection()
            _rates = signal_reply_rates(_conn)
            _adj, _why = suggest_weight_adjustments(_conn, PAIN_SIGNAL_WEIGHTS)
            _conn.close()

            if _rates:
                st.dataframe(
                    [
                        {
                            "Signal": k,
                            "Sent": v["sent"],
                            "Replied": v["positive"],
                            "Reply rate": f'{v["reply_rate"]:.0%}',
                            "Enough data?": "yes" if v["sufficient_sample"] else "no",
                        }
                        for k, v in _rates.items()
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("No outreach has been sent yet, so there is nothing to learn from.")

            st.info(_why)

            if _adj:
                st.write("**Proposed weight changes**")
                st.json(_adj)

        with st.expander("How the GTM Engine Works"):

            st.write(
                """
                The engine turns public evidence into a ranked call list, and shows
                its reasoning at every step.

                **1. Research** Two searches per account — one for operational
                pain (outages, incidents, DORA, cost pressure), one for the
                technology estate. Status pages, social posts and content farms
                are rejected before they can become evidence.

                **2. Scoring** Five components: scale, technology estate,
                operational pain, use-case fit and timing. Only the strongest
                signals count, so press coverage cannot stand in for need.

                **3. Segment fit** Headcount sets a multiplier rather than a
                score. The target segment is 200–2,000 staff; an organisation
                outside it is a different sales motion, not a weaker prospect.

                **4. Use-case fit** A four-dimension screen from buyer
                interviews. Verifiability and permission ceiling are properties
                of the workflow; data readiness and system reachability are
                properties of the account. Capability adds, permission
                multiplies, readiness gates.

                **5. People** Roles are verified against public announcements.
                By default no personal data is stored — the role map is kept
                and the individual resolved at outreach time.

                **6. Outreach and learning** Drafts are generated for human
                review, never sent. Reply outcomes feed back to test whether
                the scoring weights actually predict conversations.
                """
            )

            st.info(
                "Scores are deterministic and explainable. "
                "AI-assisted outputs are used for research and drafting, "
                "not autonomous outreach or final sales decisions."
            )