"""
Outreach feedback loop.

WHY THIS EXISTS
---------------
Scoring weights are a hypothesis about which public signals predict a buying
conversation. The only way to know whether the hypothesis holds is to compare
what the engine predicted against what actually happened when messages were
sent.

This module closes that loop: it reads outreach outcomes back out of the CRM
table, measures reply rate by signal type, and proposes weight adjustments.

It refuses to adjust anything until there is enough data to justify it. Two
replies out of three sends is not evidence; it is noise. The engine declining
to learn from a sample of three is the same principle as declining to draft
outreach to an account with no identified stakeholder - it should say what it
does not know rather than manufacture an answer.
"""

MIN_SAMPLE_PER_SIGNAL = 15      # sends needed before a signal's rate means anything
MIN_TOTAL_SENDS = 40            # sends needed before touching weights at all
MAX_ADJUSTMENT = 0.25           # never move a weight by more than 25% at once

POSITIVE_OUTCOMES = ("replied", "meeting_booked", "interested")


def outreach_outcomes(conn):
    """Every sent outreach, with the signal types present on that account."""
    conn.row_factory = __import__("sqlite3").Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            o.outreach_id,
            o.company_id,
            o.status,
            o.response_type,
            o.meeting_booked,
            o.sent_at,
            o.replied_at
        FROM outreach o
        WHERE o.sent_at IS NOT NULL
    """)

    sent = [dict(r) for r in cursor.fetchall()]

    for row in sent:
        cursor.execute(
            "SELECT DISTINCT signal_type FROM signals WHERE company_id = ?",
            (row["company_id"],)
        )
        row["signal_types"] = [r[0] for r in cursor.fetchall()]
        row["positive"] = bool(
            row["meeting_booked"]
            or (row["replied_at"] is not None)
            or (row["response_type"] or "").lower() in POSITIVE_OUTCOMES
        )

    return sent


def signal_reply_rates(conn):
    """
    Reply rate per signal type: of the accounts carrying this signal that were
    contacted, how many responded?
    """
    sent = outreach_outcomes(conn)

    stats = {}

    for row in sent:
        for signal_type in row["signal_types"]:
            entry = stats.setdefault(signal_type, {"sent": 0, "positive": 0})
            entry["sent"] += 1
            entry["positive"] += 1 if row["positive"] else 0

    for signal_type, entry in stats.items():
        entry["reply_rate"] = (
            round(entry["positive"] / entry["sent"], 3) if entry["sent"] else 0.0
        )
        entry["sufficient_sample"] = entry["sent"] >= MIN_SAMPLE_PER_SIGNAL

    return dict(
        sorted(stats.items(), key=lambda kv: kv[1]["reply_rate"], reverse=True)
    )


def suggest_weight_adjustments(conn, current_weights):
    """
    Propose scoring-weight changes from observed reply rates.

    Returns (adjustments, explanation). Adjustments is empty whenever the
    evidence is too thin - which, with a young pipeline, is the normal and
    correct answer.
    """
    sent = outreach_outcomes(conn)
    total = len(sent)

    if total < MIN_TOTAL_SENDS:
        return {}, (
            f"{total} outreach messages sent. At least {MIN_TOTAL_SENDS} are "
            "needed before reply data should influence scoring weights. "
            "No adjustments proposed."
        )

    rates = signal_reply_rates(conn)
    usable = {k: v for k, v in rates.items() if v["sufficient_sample"]}

    if not usable:
        return {}, (
            f"No signal type has reached {MIN_SAMPLE_PER_SIGNAL} sends. "
            "No adjustments proposed."
        )

    baseline = sum(v["positive"] for v in usable.values()) / \
               sum(v["sent"] for v in usable.values())

    adjustments = {}

    for signal_type, stat in usable.items():
        if signal_type not in current_weights:
            continue

        # How far this signal's reply rate sits from the overall baseline,
        # clamped so one good quarter cannot dominate the model.
        delta = (stat["reply_rate"] - baseline) / baseline if baseline else 0
        delta = max(-MAX_ADJUSTMENT, min(MAX_ADJUSTMENT, delta))

        if abs(delta) < 0.05:
            continue

        adjustments[signal_type] = {
            "current": current_weights[signal_type],
            "proposed": round(current_weights[signal_type] * (1 + delta), 2),
            "reply_rate": stat["reply_rate"],
            "baseline": round(baseline, 3),
            "sample": stat["sent"],
        }

    return adjustments, (
        f"Based on {total} sends. Baseline reply rate {baseline:.1%}. "
        f"{len(adjustments)} weight change(s) proposed, each capped at "
        f"{int(MAX_ADJUSTMENT * 100)}%."
    )
