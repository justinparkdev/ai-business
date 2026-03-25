"""
Lead Follow-Up System v1.0
AI-powered lead management for local businesses.

Requirements: pip3 install anthropic
Setup:        export ANTHROPIC_API_KEY="your-key-here"
Run:          python3 lead_followup.py
"""

import anthropic
import csv
import os
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

MODEL       = "claude-haiku-4-5-20251001"
LEADS_FILE  = "leads.csv"
EXPORT_FILE = "lead_report.txt"
MAX_SMS     = 160

# ─── ANSI COLORS ──────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def g(t):    return f"{GREEN}{t}{RESET}"
def r(t):    return f"{RED}{t}{RESET}"
def y(t):    return f"{YELLOW}{t}{RESET}"
def b(t):    return f"{BLUE}{t}{RESET}"
def bold(t): return f"{BOLD}{t}{RESET}"
def dim(t):  return f"{DIM}{t}{RESET}"

# ─── CSV SCHEMA ───────────────────────────────────────────────────────────────

FIELDS = [
    "id", "name", "phone", "service", "business_name", "source",
    "status", "urgency_score", "revenue_low", "revenue_high",
    "date_added", "date_contacted", "date_converted", "notes",
]

# ─── DATA LAYER ───────────────────────────────────────────────────────────────

def load_leads() -> list:
    """Load all leads from leads.csv on startup."""
    if not os.path.exists(LEADS_FILE):
        return []
    with open(LEADS_FILE, newline="") as f:
        return list(csv.DictReader(f))


def save_all_leads(leads: list) -> None:
    """Rewrite entire leads.csv. Called after every change."""
    with open(LEADS_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(leads)

# ─── VALIDATION ───────────────────────────────────────────────────────────────

def validate_phone(phone: str) -> bool:
    """Accept any standard US format: 10 digits or 11 starting with 1."""
    digits = re.sub(r'\D', '', phone)
    return len(digits) == 10 or (len(digits) == 11 and digits[0] == '1')


def check_duplicate(phone: str, leads: list) -> Optional[dict]:
    """Return the existing lead dict if this phone number is already in the system."""
    digits = re.sub(r'\D', '', phone)
    for lead in leads:
        if re.sub(r'\D', '', lead.get("phone", "")) == digits:
            return lead
    return None

# ─── URGENCY SCORING ──────────────────────────────────────────────────────────

# Estimated revenue range (low, high) by service keyword
REVENUE_MAP = {
    "roof":            (8000,  20000),
    "hvac":            (3000,  10000),
    "heat":            (2000,   8000),
    "air condition":   (2000,   8000),
    "plumb":           (500,    5000),
    "electric":        (1000,   8000),
    "construction":    (10000, 50000),
    "remodel":         (5000,  30000),
    "landscape":       (1000,   8000),
    "lawn":            (500,    3000),
    "clean":           (300,    2000),
    "paint":           (1000,   6000),
    "flooring":        (2000,  10000),
    "dental":          (500,    3000),
    "legal":           (1000,  10000),
    "auto":            (500,    5000),
    "pest":            (300,    1500),
    "window":          (1000,   5000),
}

SOURCE_URGENCY = {
    "walk-in":     9,
    "referral":    8,
    "website":     6,
    "social media": 5,
}


def estimate_revenue(service: str) -> tuple:
    """Return (low, high) revenue estimate based on service keywords."""
    service_lower = service.lower()
    for keyword, (low, high) in REVENUE_MAP.items():
        if keyword in service_lower:
            return low, high
    return 1000, 5000  # default for unknown service types


def calculate_urgency(source: str, service: str) -> int:
    """
    Score lead urgency 1-10.
    - Walk-ins and referrals start highest (already warm).
    - Emergency or high-value service keywords add +1 or +2.
    """
    base          = SOURCE_URGENCY.get(source.lower(), 5)
    service_lower = service.lower()

    emergency_kw   = ["emergency", "urgent", "leak", "broken", "flood", "no heat", "no ac", "burst"]
    high_value_kw  = ["roof", "construction", "remodel", "hvac", "electric", "flooring"]

    if any(kw in service_lower for kw in emergency_kw):
        base = min(base + 2, 10)
    elif any(kw in service_lower for kw in high_value_kw):
        base = min(base + 1, 10)

    return base

# ─── MESSAGE GENERATION ───────────────────────────────────────────────────────

def _fallback_messages(first_name: str, service: str, business_name: str) -> list:
    """Three pre-written templates used when the API is unavailable."""
    return [
        f"Hi {first_name}! Thanks for your interest in {service}. We'd love to help — when's a good time to connect?",
        f"Hey {first_name}, {business_name} here. Just following up on your {service} inquiry. Available this week?",
        f"Hi {first_name}! Still thinking about {service}? We have availability this week and would love to get you taken care of.",
    ]


def generate_messages(name: str, service: str, business_name: str, source: str) -> list:
    """
    Call Claude Haiku to generate 3 personalized follow-up SMS messages.
    Returns list of dicts with 'text' and 'char_count'.
    Falls back to templates automatically on any API failure.
    """
    client     = anthropic.Anthropic()
    first_name = name.split()[0]

    prompt = f"""Generate exactly 3 different follow-up SMS messages for a business lead.

Lead first name: {first_name}
Service they asked about: {service}
Business name: {business_name}
How they found us: {source}

Rules:
- Each message MUST be under {MAX_SMS} characters
- Reference the specific service naturally
- Sound warm, personal, and human — not robotic
- Create a gentle sense of urgency without being pushy
- Each message should have a noticeably different tone
- Do NOT include a URL or phone number
- Output ONLY the 3 messages, one per line, no labels or numbers"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw      = response.content[0].text.strip()
    lines    = [line.strip() for line in raw.split('\n') if line.strip()]
    messages = lines[:3]

    # Pad with fallbacks if Claude returned fewer than 3
    fallbacks = _fallback_messages(first_name, service, business_name)
    while len(messages) < 3:
        messages.append(fallbacks[len(messages)])

    return [
        {"text": msg[:MAX_SMS], "char_count": min(len(msg), MAX_SMS)}
        for msg in messages
    ]

# ─── STATUS & TIME HELPERS ────────────────────────────────────────────────────

STATUS_COLOR = {
    "new":       y,
    "contacted": b,
    "converted": g,
    "lost":      dim,
}


def color_status(status: str) -> str:
    fn = STATUS_COLOR.get(status.lower(), str)
    return fn(status.upper())


def is_overdue(lead: dict) -> bool:
    """True if lead is still 'new' and was added 48+ hours ago."""
    if lead.get("status", "").lower() != "new":
        return False
    try:
        added = datetime.strptime(lead["date_added"], "%Y-%m-%d %H:%M:%S")
        return datetime.now() - added > timedelta(hours=48)
    except (ValueError, KeyError):
        return False


def time_since(date_str: str) -> str:
    """Human-readable elapsed time: '3h ago', '2d ago', etc."""
    if not date_str:
        return "—"
    try:
        dt   = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        diff = datetime.now() - dt
        if diff.days == 0:
            return f"{diff.seconds // 3600}h ago"
        return f"{diff.days}d ago"
    except ValueError:
        return date_str

# ─── DISPLAY HELPERS ──────────────────────────────────────────────────────────

def header(title: str) -> None:
    W = 58
    print(f"\n{BOLD}{'═' * W}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'═' * W}{RESET}\n")


def divider() -> None:
    print(f"{DIM}{'─' * 58}{RESET}")


def pause() -> None:
    input(f"\n{DIM}  Press Enter to continue...{RESET}")

# ─── DASHBOARD ────────────────────────────────────────────────────────────────

def dashboard(leads: list) -> None:
    """Print the live stats bar at the top of every menu."""
    now          = datetime.now()
    week_ago     = now - timedelta(days=7)

    total        = len(leads)
    new_leads    = [l for l in leads if l["status"].lower() == "new"]
    overdue      = [l for l in leads if is_overdue(l)]
    converted    = [l for l in leads if l["status"].lower() == "converted"]
    lost         = [l for l in leads if l["status"].lower() == "lost"]

    # Conversions closed this calendar week
    week_converted = []
    for l in converted:
        try:
            if datetime.strptime(l.get("date_converted", ""), "%Y-%m-%d %H:%M:%S") >= week_ago:
                week_converted.append(l)
        except ValueError:
            pass

    # Revenue potential in the active pipeline
    pipeline = sum(
        int(l.get("revenue_low", 0))
        for l in leads
        if l["status"].lower() in ("new", "contacted")
    )

    # All-time conversion rate
    closed    = len(converted) + len(lost)
    conv_rate = (len(converted) / closed * 100) if closed else 0.0

    print(f"\n{BOLD}{'═' * 58}{RESET}")
    print(f"{BOLD}   LEAD FOLLOW-UP SYSTEM  v1.0{RESET}")
    print(f"{BOLD}{'═' * 58}{RESET}")
    print(
        f"  {dim('Total:')} {bold(str(total))}   "
        f"{dim('New:')} {y(str(len(new_leads)))}   "
        f"{dim('Overdue:')} {r(str(len(overdue))) if overdue else g('0')}   "
        f"{dim('Converted:')} {g(str(len(converted)))}   "
        f"{dim('Rate:')} {bold(f'{conv_rate:.0f}%')}"
    )
    print(
        f"  {dim('Pipeline:')} {y(f'${pipeline:,}')}   "
        f"{dim('This week:')} {g(str(len(week_converted)) + ' closed')}"
    )
    print(f"{DIM}{'─' * 58}{RESET}")

# ─── LEAD LIST VIEW ───────────────────────────────────────────────────────────

def view_leads(leads: list, filter_status: str = None) -> None:
    """Display leads sorted by urgency descending, with optional status filter."""
    display = leads if not filter_status else [
        l for l in leads if l["status"].lower() == filter_status
    ]

    if not display:
        print(y("  No leads match that filter."))
        return

    sorted_leads = sorted(display, key=lambda l: int(l.get("urgency_score", 0)), reverse=True)

    print(f"  {'NAME':<18} {'PHONE':<14} {'SERVICE':<22} {'SOURCE':<12} {'STATUS':<13} {'URG':<5} {'ADDED'}")
    divider()

    for l in sorted_leads:
        urg          = int(l.get("urgency_score", 0))
        urg_str      = r(str(urg)) if urg >= 8 else y(str(urg)) if urg >= 6 else g(str(urg))
        overdue_flag = r(" ⚠") if is_overdue(l) else ""
        print(
            f"  {l['name']:<18} {l['phone']:<14} {l['service'][:21]:<22} "
            f"{l['source'][:11]:<12} {color_status(l['status']):<21} {urg_str:<13} "
            f"{time_since(l.get('date_added',''))}{overdue_flag}"
        )


def view_overdue(leads: list) -> None:
    header("OVERDUE LEADS  (48+ hours, still uncontacted)")
    overdue = sorted(
        [l for l in leads if is_overdue(l)],
        key=lambda x: int(x.get("urgency_score", 0)),
        reverse=True,
    )
    if not overdue:
        print(g("  ✓ No overdue leads — great response time!"))
    else:
        print(r(f"  ⚠  {len(overdue)} lead(s) need immediate follow-up:\n"))
        for l in overdue:
            print(f"  {bold(l['name'])} — {l['service']} — {l['phone']}")
            print(f"  Source: {l['source']}  |  Urgency: {l['urgency_score']}/10  |  Added: {time_since(l['date_added'])}\n")
    pause()

# ─── ADD LEAD ─────────────────────────────────────────────────────────────────

def add_lead(leads: list) -> None:
    header("ADD NEW LEAD")

    # Name — required
    while True:
        name = input("  Lead name            : ").strip()
        if name:
            break
        print("  ! Name is required.")

    # Phone — required, validated, duplicate-checked
    while True:
        phone = input("  Phone number         : ").strip()
        if not phone:
            print("  ! Phone is required.")
            continue
        if not validate_phone(phone):
            print("  ! Invalid format. Try: 555-123-4567")
            continue
        existing = check_duplicate(phone, leads)
        if existing:
            print(r("\n  ⚠  DUPLICATE LEAD — this number is already in the system."))
            print(f"  Existing: {existing['name']} — {existing['service']} — {existing['status'].upper()}")
            pause()
            return
        break

    # Service — required
    while True:
        service = input("  Service interest     : ").strip()
        if service:
            break
        print("  ! Service interest is required.")

    # Business name — required
    while True:
        business_name = input("  Your business name   : ").strip()
        if business_name:
            break
        print("  ! Business name is required.")

    # Lead source
    print("  Source: [1] Walk-in  [2] Website  [3] Referral  [4] Social Media")
    source_map    = {"1": "walk-in", "2": "website", "3": "referral", "4": "social media"}
    source_choice = input("  Lead source          : ").strip()
    source        = source_map.get(source_choice, "website")

    # Score and estimate
    urgency           = calculate_urgency(source, service)
    rev_low, rev_high = estimate_revenue(service)

    # Generate messages
    print(f"\n  Generating follow-up messages...", end="", flush=True)
    try:
        messages = generate_messages(name, service, business_name, source)
        print(" done.")
    except anthropic.AuthenticationError:
        print(f"\n  {r('API key missing or invalid — using fallback messages.')}")
        msgs     = _fallback_messages(name.split()[0], service, business_name)
        messages = [{"text": m[:MAX_SMS], "char_count": len(m[:MAX_SMS])} for m in msgs]
    except Exception as e:
        print(f"\n  {r(f'API unavailable ({type(e).__name__}) — using fallback messages.')}")
        msgs     = _fallback_messages(name.split()[0], service, business_name)
        messages = [{"text": m[:MAX_SMS], "char_count": len(m[:MAX_SMS])} for m in msgs]

    # Display messages + urgency
    urg_color = r(str(urgency)) if urgency >= 8 else y(str(urgency)) if urgency >= 6 else g(str(urgency))
    print(f"\n{'─' * 58}")
    print(f"  FOLLOW-UP MESSAGES    Urgency: {urg_color}/10    Revenue est: {g(f'${rev_low:,}–${rev_high:,}')}")
    print(f"{'─' * 58}")
    for i, msg in enumerate(messages, 1):
        print(f"\n  [{i}] {msg['char_count']} chars")
        print(f"      \"{msg['text']}\"")
    print(f"{'─' * 58}")

    if urgency >= 8:
        print(r("\n  ⚠  HIGH URGENCY — follow up within the hour!"))
    elif urgency >= 6:
        print(y("\n  Follow up within 24 hours for best results."))

    # Build and save lead record
    lead = {
        "id":             str(uuid.uuid4())[:8],
        "name":           name,
        "phone":          phone,
        "service":        service,
        "business_name":  business_name,
        "source":         source,
        "status":         "new",
        "urgency_score":  str(urgency),
        "revenue_low":    str(rev_low),
        "revenue_high":   str(rev_high),
        "date_added":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "date_contacted": "",
        "date_converted": "",
        "notes":          "",
    }

    leads.append(lead)
    save_all_leads(leads)
    print(g(f"\n  ✓ Lead saved. ID: {lead['id']}"))
    pause()

# ─── UPDATE LEAD STATUS ───────────────────────────────────────────────────────

def update_status(leads: list) -> None:
    header("UPDATE LEAD STATUS")

    if not leads:
        print(y("  No leads yet."))
        pause()
        return

    # Show active leads sorted by urgency
    active = sorted(
        [l for l in leads if l["status"].lower() not in ("converted", "lost")],
        key=lambda x: int(x.get("urgency_score", 0)),
        reverse=True,
    )

    if not active:
        print(g("  All leads are closed (converted or lost)."))
        pause()
        return

    print(f"  {'ID':<10} {'Name':<18} {'Service':<22} {'Status':<13} Urgency")
    divider()
    for l in active:
        urg          = int(l.get("urgency_score", 0))
        urg_str      = r(str(urg)) if urg >= 8 else y(str(urg)) if urg >= 6 else g(str(urg))
        overdue_flag = r(" ⚠ OVERDUE") if is_overdue(l) else ""
        print(
            f"  {dim(l['id']):<18} {l['name']:<18} {l['service'][:21]:<22} "
            f"{color_status(l['status']):<21} {urg_str}{overdue_flag}"
        )

    print()
    lead_id = input("  Enter lead ID: ").strip()
    target  = next((l for l in leads if l["id"] == lead_id), None)

    if not target:
        print(r("  Lead ID not found."))
        pause()
        return

    print(f"\n  Updating: {bold(target['name'])} — {target['service']}")
    print("  [1] New  [2] Contacted  [3] Converted  [4] Lost")
    choice   = input("  New status: ").strip()
    statuses = {"1": "new", "2": "contacted", "3": "converted", "4": "lost"}

    if choice not in statuses:
        print(r("  Invalid choice."))
        pause()
        return

    new_status      = statuses[choice]
    target["status"] = new_status
    now_str          = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if new_status == "contacted":
        target["date_contacted"] = now_str
    elif new_status == "converted":
        target["date_converted"] = now_str
        if not target["date_contacted"]:
            target["date_contacted"] = now_str  # mark contacted too

    # Optional note
    note = input("  Add a note (optional, Enter to skip): ").strip()
    if note:
        prev = target.get("notes", "")
        target["notes"] = f"{prev} | {now_str[:10]}: {note}".lstrip(" | ")

    save_all_leads(leads)
    print(g(f"  ✓ {target['name']} → {new_status.upper()}"))
    pause()

# ─── WEEKLY SUMMARY ───────────────────────────────────────────────────────────

def weekly_summary(leads: list) -> None:
    header("WEEKLY PERFORMANCE SUMMARY")

    if not leads:
        print(y("  No leads yet."))
        pause()
        return

    now      = datetime.now()
    week_ago = now - timedelta(days=7)

    def in_week(date_str: str) -> bool:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S") >= week_ago
        except (ValueError, TypeError):
            return False

    week_new       = [l for l in leads if in_week(l.get("date_added", ""))]
    week_converted = [l for l in leads if in_week(l.get("date_converted", ""))]
    week_contacted = [l for l in leads if in_week(l.get("date_contacted", ""))]
    all_converted  = [l for l in leads if l["status"].lower() == "converted"]
    all_closed     = [l for l in leads if l["status"].lower() in ("converted", "lost")]
    overdue        = [l for l in leads if is_overdue(l)]

    conv_rate = (len(all_converted) / len(all_closed) * 100) if all_closed else 0.0

    # Average response time for leads that were contacted
    response_times = []
    for l in leads:
        if l.get("date_contacted") and l.get("date_added"):
            try:
                added     = datetime.strptime(l["date_added"],     "%Y-%m-%d %H:%M:%S")
                contacted = datetime.strptime(l["date_contacted"], "%Y-%m-%d %H:%M:%S")
                hrs       = (contacted - added).total_seconds() / 3600
                if hrs >= 0:
                    response_times.append(hrs)
            except ValueError:
                pass

    avg_response = (sum(response_times) / len(response_times)) if response_times else None

    # Revenue totals
    revenue_generated = sum(int(l.get("revenue_low", 0)) for l in all_converted)
    pipeline_value    = sum(
        int(l.get("revenue_low", 0))
        for l in leads
        if l["status"].lower() in ("new", "contacted")
    )

    # Best source by conversion count
    source_conv = {}
    for l in all_converted:
        src = l.get("source", "unknown")
        source_conv[src] = source_conv.get(src, 0) + 1

    print(f"  {'THIS WEEK':<38}")
    divider()
    print(f"  {'New Leads':<36} {bold(str(len(week_new)))}")
    print(f"  {'Contacted':<36} {bold(str(len(week_contacted)))}")
    print(f"  {'Converted':<36} {g(str(len(week_converted)))}")
    print()
    print(f"  {'ALL TIME':<38}")
    divider()
    print(f"  {'Total Leads':<36} {bold(str(len(leads)))}")
    print(f"  {'Conversion Rate':<36} {g(f'{conv_rate:.1f}%')}")

    if avg_response is not None:
        resp_str = f"{avg_response:.1f} hours"
        if avg_response <= 2:
            resp_col = g(resp_str)
        elif avg_response <= 24:
            resp_col = y(resp_str)
        else:
            resp_col = r(resp_str)
        print(f"  {'Avg Response Time':<36} {resp_col}")

    print(f"  {'Revenue Generated (est.)':<36} {g(f'${revenue_generated:,}')}")
    print(f"  {'Active Pipeline Value':<36} {y(f'${pipeline_value:,}')}")
    print(f"  {'Overdue Leads':<36} {r(str(len(overdue))) if overdue else g('0')}")

    if source_conv:
        print()
        print(f"  {'CONVERSIONS BY SOURCE':<38}")
        divider()
        for src, count in sorted(source_conv.items(), key=lambda x: -x[1]):
            print(f"  {'  ' + src.title():<36} {g(str(count))}")

    if overdue:
        print()
        print(r(f"  ⚠  {len(overdue)} lead(s) are overdue and need immediate follow-up."))

    pause()

# ─── EXPORT REPORT ────────────────────────────────────────────────────────────

def export_report(leads: list) -> None:
    """Generate a clean plain-text report the business owner can read or print."""
    header("EXPORT REPORT")

    if not leads:
        print(y("  No leads to export."))
        pause()
        return

    now           = datetime.now().strftime("%B %d, %Y  %I:%M %p")
    all_converted = [l for l in leads if l["status"].lower() == "converted"]
    all_closed    = [l for l in leads if l["status"].lower() in ("converted", "lost")]
    new_leads     = [l for l in leads if l["status"].lower() == "new"]
    overdue       = [l for l in leads if is_overdue(l)]
    conv_rate     = (len(all_converted) / len(all_closed) * 100) if all_closed else 0.0
    revenue       = sum(int(l.get("revenue_low", 0)) for l in all_converted)
    pipeline      = sum(
        int(l.get("revenue_low", 0))
        for l in leads
        if l["status"].lower() in ("new", "contacted")
    )

    lines = [
        "=" * 58,
        "  LEAD FOLLOW-UP SYSTEM — PERFORMANCE REPORT",
        f"  Generated: {now}",
        "=" * 58,
        "",
        f"  Total Leads               : {len(leads)}",
        f"  New (Uncontacted)         : {len(new_leads)}",
        f"  Converted                 : {len(all_converted)}",
        f"  Overdue (48h+)            : {len(overdue)}",
        f"  Conversion Rate           : {conv_rate:.1f}%",
        f"  Revenue Generated (est.)  : ${revenue:,}",
        f"  Active Pipeline Value     : ${pipeline:,}",
        "",
        "─" * 58,
        "  ALL LEADS  (sorted by urgency)",
        "─" * 58,
    ]

    sorted_leads = sorted(leads, key=lambda x: int(x.get("urgency_score", 0)), reverse=True)
    for l in sorted_leads:
        overdue_flag = "  *** OVERDUE ***" if is_overdue(l) else ""
        lines += [
            "",
            f"  {l['name']}  |  {l['phone']}",
            f"  Service  : {l['service']}",
            f"  Source   : {l['source']}  |  Status: {l['status'].upper()}  |  Urgency: {l['urgency_score']}/10{overdue_flag}",
            f"  Added    : {l['date_added']}  |  Rev Est: ${int(l.get('revenue_low',0)):,} – ${int(l.get('revenue_high',0)):,}",
        ]
        if l.get("date_contacted"):
            lines.append(f"  Contacted: {l['date_contacted']}")
        if l.get("date_converted"):
            lines.append(f"  Converted: {l['date_converted']}")
        if l.get("notes"):
            lines.append(f"  Notes    : {l['notes']}")

    lines += ["", "=" * 58, "  End of Report — JP Automation Lead System", "=" * 58]

    with open(EXPORT_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(g(f"  ✓ Report saved to {EXPORT_FILE}"))
    print(dim("  Share this file directly with your client."))
    pause()

# ─── MENUS ────────────────────────────────────────────────────────────────────

def leads_menu(leads: list) -> None:
    while True:
        dashboard(leads)
        print("  [1] Add new lead")
        print("  [2] View all leads")
        print("  [3] View overdue leads")
        print("  [4] Update lead status")
        print("  [5] View new leads only")
        print("  [B] Back")
        choice = input("\n  Choice: ").strip().upper()

        if   choice == "1": add_lead(leads)
        elif choice == "2":
            header("ALL LEADS — sorted by urgency")
            view_leads(leads)
            pause()
        elif choice == "3": view_overdue(leads)
        elif choice == "4": update_status(leads)
        elif choice == "5":
            header("NEW LEADS")
            view_leads(leads, filter_status="new")
            pause()
        elif choice == "B": break
        else: print(r("  Invalid choice."))

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main() -> None:
    leads = load_leads()

    while True:
        dashboard(leads)
        print("  [1] Lead Management")
        print("  [2] Weekly Summary")
        print("  [3] Export Report")
        print("  [Q] Quit")

        choice = input("\n  Choice: ").strip().upper()
        if   choice == "1": leads_menu(leads)
        elif choice == "2": weekly_summary(leads)
        elif choice == "3": export_report(leads)
        elif choice == "Q":
            print(f"\n  {g('Goodbye!')}\n")
            break
        else:
            print(r("  Invalid choice."))


if __name__ == "__main__":
    main()
