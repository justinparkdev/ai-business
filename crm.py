"""
JP Automation CRM v1.0
Manage clients, finances, deployed files, and fix requests.

Requirements: pip3 install tabulate
Run:          python3 crm.py
"""

import json
import os
import uuid
from datetime import datetime

try:
    from tabulate import tabulate
except ImportError:
    print("Missing dependency. Run: pip3 install tabulate")
    exit(1)

# ─── COLORS (ANSI — works on Mac/Linux/modern Windows) ───────────────────────

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def g(t):    return f"{GREEN}{t}{RESET}"       # profit / success
def r(t):    return f"{RED}{t}{RESET}"         # costs / errors
def y(t):    return f"{YELLOW}{t}{RESET}"      # warnings / pending
def b(t):    return f"{BLUE}{t}{RESET}"        # in-progress
def bold(t): return f"{BOLD}{t}{RESET}"
def dim(t):  return f"{DIM}{t}{RESET}"

# ─── DATA PERSISTENCE ─────────────────────────────────────────────────────────

DATA_FILE = "clients.json"

def load_data() -> dict:
    """Load client data from disk. Returns empty structure if file doesn't exist."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"clients": {}}

def save_data(data: dict) -> None:
    """Write all data to clients.json."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ─── DISPLAY HELPERS ──────────────────────────────────────────────────────────

def header(title: str) -> None:
    W = 56
    print(f"\n{BOLD}{'═' * W}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'═' * W}{RESET}\n")

def divider() -> None:
    print(f"{DIM}{'─' * 56}{RESET}")

def pause() -> None:
    input(f"\n{DIM}  Press Enter to continue...{RESET}")

# ─── CLIENT SELECTION ─────────────────────────────────────────────────────────

def pick_client(data: dict, prompt: str = "  Select client ID: "):
    """
    Print a compact client list and return (client_id, client_dict).
    Returns (None, None) if no clients exist or user enters an invalid ID.
    """
    clients = data["clients"]
    if not clients:
        print(y("  No clients found. Add one first."))
        return None, None

    print()
    for cid, c in clients.items():
        open_fixes = sum(1 for fx in c["fixes"] if fx["status"] != "done")
        fix_badge  = f"  {y(str(open_fixes) + ' fix')}" if open_fixes else ""
        print(f"  {dim(cid)}  {bold(c['company'])} — {c['contact_name']}{fix_badge}")

    print()
    cid = input(prompt).strip()
    if cid not in clients:
        print(r("  Client ID not found."))
        return None, None
    return cid, clients[cid]

# ─── CLIENT MANAGEMENT ────────────────────────────────────────────────────────

def add_client(data: dict) -> None:
    header("ADD NEW CLIENT")

    company      = input("  Company name       : ").strip()
    contact_name = input("  Contact name       : ").strip()
    phone        = input("  Phone              : ").strip()
    email        = input("  Email              : ").strip()
    service_type = input("  Service type       : ").strip()
    start_date   = input("  Start date (YYYY-MM-DD, Enter = today): ").strip()
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")

    print(f"\n  {dim('─ Financials ─')}")
    try:
        monthly_retainer = float(input("  Monthly retainer ($) : ").strip() or 0)
        setup_fee        = float(input("  One-time setup fee ($): ").strip() or 0)
        monthly_costs    = float(input("  Your monthly costs ($): ").strip() or 0)
    except ValueError:
        print(r("  Invalid number — defaulting to $0."))
        monthly_retainer = setup_fee = monthly_costs = 0.0

    client_id = str(uuid.uuid4())[:8]
    data["clients"][client_id] = {
        "company":      company,
        "contact_name": contact_name,
        "phone":        phone,
        "email":        email,
        "service_type": service_type,
        "start_date":   start_date,
        "financials": {
            "monthly_retainer": monthly_retainer,
            "setup_fee":        setup_fee,
            "monthly_costs":    monthly_costs,
        },
        "files": [],
        "fixes": [],
    }
    save_data(data)
    print(g(f"\n  ✓ '{company}' added successfully.  ID: {client_id}"))
    pause()


def view_all_clients(data: dict) -> None:
    header("ALL CLIENTS")
    clients = data["clients"]
    if not clients:
        print(y("  No clients yet."))
        pause()
        return

    rows = []
    for cid, c in clients.items():
        f        = c["financials"]
        net      = f["monthly_retainer"] - f["monthly_costs"]
        net_str  = g(f"${net:,.2f}") if net >= 0 else r(f"${net:,.2f}")
        open_fixes = sum(1 for fx in c["fixes"] if fx["status"] != "done")
        fix_str    = y(str(open_fixes)) if open_fixes else g("0")
        rows.append([
            dim(cid),
            bold(c["company"]),
            c["contact_name"],
            c["service_type"],
            f"${f['monthly_retainer']:,.0f}/mo",
            net_str,
            fix_str,
            c["start_date"],
        ])

    print(tabulate(
        rows,
        headers=["ID", "Company", "Contact", "Service", "Retainer", "Net/mo", "Fixes", "Since"],
        tablefmt="rounded_outline",
    ))
    pause()


def search_client(data: dict) -> None:
    header("SEARCH CLIENT")
    query   = input("  Search (name or company): ").strip().lower()
    results = [
        (cid, c) for cid, c in data["clients"].items()
        if query in c["company"].lower() or query in c["contact_name"].lower()
    ]

    if not results:
        print(y("  No matches found."))
    else:
        for cid, c in results:
            f   = c["financials"]
            net = f["monthly_retainer"] - f["monthly_costs"]
            print(f"\n  {bold(c['company'])}  {dim(cid)}")
            print(f"  Contact  : {c['contact_name']}  |  {c['phone']}  |  {c['email']}")
            print(f"  Service  : {c['service_type']}  |  Since: {c['start_date']}")
            print(f"  Retainer : ${f['monthly_retainer']:,.2f}/mo  |  Net: {g(f'${net:,.2f}') if net >= 0 else r(f'${net:,.2f}')}")
    pause()


def edit_client(data: dict) -> None:
    header("EDIT CLIENT")
    cid, client = pick_client(data)
    if not cid:
        pause()
        return

    print("  (Press Enter to keep current value)\n")
    fields = ["company", "contact_name", "phone", "email", "service_type"]
    labels = ["Company name", "Contact name", "Phone", "Email", "Service type"]

    for field, label in zip(fields, labels):
        val = input(f"  {label} ({client[field]}): ").strip()
        if val:
            client[field] = val

    save_data(data)
    print(g("  ✓ Client updated."))
    pause()

# ─── FINANCIAL TRACKING ───────────────────────────────────────────────────────

def financial_summary(data: dict) -> None:
    header("FINANCIAL SUMMARY")
    clients = data["clients"]
    if not clients:
        print(y("  No clients yet."))
        pause()
        return

    rows               = []
    total_retainer     = 0.0
    total_costs        = 0.0
    total_setup        = 0.0

    for c in clients.values():
        f   = c["financials"]
        net = f["monthly_retainer"] - f["monthly_costs"]
        total_retainer += f["monthly_retainer"]
        total_costs    += f["monthly_costs"]
        total_setup    += f["setup_fee"]
        rows.append([
            bold(c["company"]),
            f"${f['monthly_retainer']:,.2f}",
            r(f"${f['monthly_costs']:,.2f}"),
            g(f"${net:,.2f}") if net >= 0 else r(f"${net:,.2f}"),
            f"${f['setup_fee']:,.2f}",
        ])

    print(tabulate(
        rows,
        headers=["Company", "Retainer/mo", "My Costs/mo", "Net Profit/mo", "Setup Fee"],
        tablefmt="rounded_outline",
    ))

    total_net = total_retainer - total_costs
    divider()
    print(f"  {'Monthly Revenue':<28} {g(f'${total_retainer:,.2f}')}")
    print(f"  {'Monthly Costs':<28} {r(f'${total_costs:,.2f}')}")
    print(f"  {'Monthly Net Profit':<28} {g(f'${total_net:,.2f}') if total_net >= 0 else r(f'${total_net:,.2f}')}")
    print(f"  {'Total Setup Fees Earned':<28} {g(f'${total_setup:,.2f}')}")
    pause()


def update_financials(data: dict) -> None:
    header("UPDATE CLIENT FINANCIALS")
    cid, client = pick_client(data)
    if not cid:
        pause()
        return

    f = client["financials"]
    print(f"  Current → retainer: ${f['monthly_retainer']}  costs: ${f['monthly_costs']}  setup: ${f['setup_fee']}")
    print("  (Press Enter to keep)\n")

    try:
        val = input(f"  Monthly retainer (${f['monthly_retainer']}): ").strip()
        if val: f["monthly_retainer"] = float(val)

        val = input(f"  Monthly costs    (${f['monthly_costs']}): ").strip()
        if val: f["monthly_costs"] = float(val)

        val = input(f"  Setup fee        (${f['setup_fee']}): ").strip()
        if val: f["setup_fee"] = float(val)
    except ValueError:
        print(r("  Invalid number — no changes saved."))
        pause()
        return

    save_data(data)
    print(g("  ✓ Financials updated."))
    pause()

# ─── FILE TRACKING ────────────────────────────────────────────────────────────

def add_file(data: dict) -> None:
    header("ADD DEPLOYED FILE")
    cid, client = pick_client(data)
    if not cid:
        pause()
        return

    name    = input("  File / tool name           : ").strip()
    date    = input("  Deploy date (Enter = today): ").strip() or datetime.now().strftime("%Y-%m-%d")
    version = input("  Version (e.g. 1.0)         : ").strip() or "1.0"

    # Check for existing file and update version instead of duplicating
    for existing in client["files"]:
        if existing["name"].lower() == name.lower():
            existing["version"]       = version
            existing["deployed_date"] = date
            save_data(data)
            print(g(f"  ✓ Updated existing '{name}' to v{version}."))
            pause()
            return

    client["files"].append({"name": name, "deployed_date": date, "version": version})
    save_data(data)
    print(g(f"  ✓ '{name}' v{version} added to {client['company']}."))
    pause()


def view_files(data: dict) -> None:
    header("DEPLOYED FILES")
    cid, client = pick_client(data)
    if not cid:
        pause()
        return

    files = client["files"]
    print(f"\n  Files for {bold(client['company'])}:\n")

    if not files:
        print(y("  No files deployed yet."))
    else:
        print(tabulate(
            [[f["name"], f["deployed_date"], f["version"]] for f in files],
            headers=["File / Tool", "Deployed", "Version"],
            tablefmt="rounded_outline",
        ))
    pause()

# ─── FIXES & REQUESTS ─────────────────────────────────────────────────────────

PRIORITY_COLOR = {"high": r, "medium": y, "low": g}
STATUS_COLOR   = {"pending": y, "in-progress": b, "done": g}


def add_fix(data: dict) -> None:
    header("ADD FIX / REQUEST")
    cid, client = pick_client(data)
    if not cid:
        pause()
        return

    desc     = input("  Description                   : ").strip()
    priority = input("  Priority (high/medium/low)    : ").strip().lower()
    if priority not in ("high", "medium", "low"):
        priority = "medium"

    fix_id = str(uuid.uuid4())[:6]
    client["fixes"].append({
        "id":             fix_id,
        "description":    desc,
        "priority":       priority,
        "status":         "pending",
        "date_added":     datetime.now().strftime("%Y-%m-%d"),
        "date_completed": None,
    })
    save_data(data)
    print(g(f"  ✓ Fix added to {client['company']}  (ID: {fix_id})"))
    pause()


def view_open_fixes(data: dict) -> None:
    header("ALL OPEN FIXES")
    rows = []

    for c in data["clients"].values():
        for fx in c["fixes"]:
            if fx["status"] != "done":
                pc = PRIORITY_COLOR.get(fx["priority"], dim)
                sc = STATUS_COLOR.get(fx["status"], dim)
                rows.append([
                    bold(c["company"]),
                    dim(fx["id"]),
                    fx["description"][:48],
                    pc(fx["priority"].upper()),
                    sc(fx["status"]),
                    fx["date_added"],
                ])

    if not rows:
        print(g("  ✓ No open fixes — all clear!"))
    else:
        print(tabulate(
            rows,
            headers=["Company", "ID", "Description", "Priority", "Status", "Added"],
            tablefmt="rounded_outline",
        ))
    pause()


def update_fix_status(data: dict) -> None:
    header("UPDATE FIX STATUS")
    cid, client = pick_client(data)
    if not cid:
        pause()
        return

    open_fixes = [fx for fx in client["fixes"] if fx["status"] != "done"]
    if not open_fixes:
        print(g("  No open fixes for this client."))
        pause()
        return

    for fx in open_fixes:
        pc = PRIORITY_COLOR.get(fx["priority"], dim)
        sc = STATUS_COLOR.get(fx["status"], dim)
        print(f"  {dim(fx['id'])}  [{pc(fx['priority'])}] [{sc(fx['status'])}]  {fx['description']}")

    fix_id = input("\n  Enter fix ID to update: ").strip()
    for fx in client["fixes"]:
        if fx["id"] == fix_id:
            print("  New status: [1] pending  [2] in-progress  [3] done")
            choice   = input("  Choice: ").strip()
            statuses = {"1": "pending", "2": "in-progress", "3": "done"}
            if choice in statuses:
                fx["status"] = statuses[choice]
                if fx["status"] == "done":
                    fx["date_completed"] = datetime.now().strftime("%Y-%m-%d")
                save_data(data)
                print(g(f"  ✓ Status updated to '{fx['status']}'."))
            else:
                print(r("  Invalid choice."))
            pause()
            return

    print(r("  Fix ID not found."))
    pause()


def mark_fix_done(data: dict) -> None:
    header("MARK FIX AS DONE")
    cid, client = pick_client(data)
    if not cid:
        pause()
        return

    open_fixes = [fx for fx in client["fixes"] if fx["status"] != "done"]
    if not open_fixes:
        print(g("  No open fixes for this client."))
        pause()
        return

    for fx in open_fixes:
        pc = PRIORITY_COLOR.get(fx["priority"], dim)
        print(f"  {dim(fx['id'])}  [{pc(fx['priority'])}]  {fx['description']}")

    fix_id = input("\n  Enter fix ID to mark done: ").strip()
    for fx in client["fixes"]:
        if fx["id"] == fix_id:
            fx["status"]         = "done"
            fx["date_completed"] = datetime.now().strftime("%Y-%m-%d")
            save_data(data)
            print(g(f"  ✓ '{fx['description'][:45]}' marked as done."))
            pause()
            return

    print(r("  Fix ID not found."))
    pause()


def view_fix_history(data: dict) -> None:
    header("FIX HISTORY")
    cid, client = pick_client(data)
    if not cid:
        pause()
        return

    fixes = client["fixes"]
    print(f"\n  Fix history for {bold(client['company'])}:\n")

    if not fixes:
        print(y("  No fixes recorded yet."))
    else:
        rows = []
        for fx in fixes:
            pc = PRIORITY_COLOR.get(fx["priority"], dim)
            sc = STATUS_COLOR.get(fx["status"], dim)
            rows.append([
                dim(fx["id"]),
                fx["description"][:48],
                pc(fx["priority"].upper()),
                sc(fx["status"]),
                fx["date_added"],
                fx["date_completed"] or dim("—"),
            ])
        print(tabulate(
            rows,
            headers=["ID", "Description", "Priority", "Status", "Added", "Completed"],
            tablefmt="rounded_outline",
        ))
    pause()

# ─── WEEKLY SUMMARY ───────────────────────────────────────────────────────────

def weekly_summary(data: dict) -> None:
    header("BUSINESS SUMMARY")
    clients = data["clients"]
    if not clients:
        print(y("  No clients yet."))
        pause()
        return

    total_retainer = sum(c["financials"]["monthly_retainer"] for c in clients.values())
    total_costs    = sum(c["financials"]["monthly_costs"]    for c in clients.values())
    total_setup    = sum(c["financials"]["setup_fee"]        for c in clients.values())
    total_net      = total_retainer - total_costs
    n_clients      = len(clients)
    open_fixes     = sum(1 for c in clients.values() for fx in c["fixes"] if fx["status"] != "done")
    high_priority  = sum(1 for c in clients.values() for fx in c["fixes"]
                         if fx["status"] != "done" and fx["priority"] == "high")
    total_files    = sum(len(c["files"]) for c in clients.values())

    print(f"  {'Active Clients':<30} {bold(str(n_clients))}")
    print(f"  {'Files / Tools Deployed':<30} {bold(str(total_files))}")
    divider()
    print(f"  {'Monthly Revenue':<30} {g(f'${total_retainer:,.2f}')}")
    print(f"  {'Monthly Costs':<30} {r(f'${total_costs:,.2f}')}")
    net_str = g(f"${total_net:,.2f}") if total_net >= 0 else r(f"${total_net:,.2f}")
    print(f"  {'Monthly Net Profit':<30} {net_str}")
    print(f"  {'Total Setup Fees Earned':<30} {g(f'${total_setup:,.2f}')}")
    divider()
    print(f"  {'Open Fixes':<30} {y(str(open_fixes)) if open_fixes else g('0')}")
    print(f"  {'High Priority Fixes':<30} {r(str(high_priority)) if high_priority else g('0')}")

    if high_priority:
        print(f"\n  {r('⚠  High priority items need attention:')}")
        for c in clients.values():
            for fx in c["fixes"]:
                if fx["status"] != "done" and fx["priority"] == "high":
                    print(f"     • {bold(c['company'])}: {fx['description']}")

    pause()

# ─── SUBMENUS ─────────────────────────────────────────────────────────────────

def client_menu(data: dict) -> None:
    while True:
        header("CLIENT MANAGEMENT")
        print("  [1] Add new client")
        print("  [2] View all clients")
        print("  [3] Search client")
        print("  [4] Edit client details")
        print("  [B] Back")
        choice = input("\n  Choice: ").strip().upper()
        if   choice == "1": add_client(data)
        elif choice == "2": view_all_clients(data)
        elif choice == "3": search_client(data)
        elif choice == "4": edit_client(data)
        elif choice == "B": break
        else: print(r("  Invalid choice."))


def financial_menu(data: dict) -> None:
    while True:
        header("FINANCIAL TRACKING")
        print("  [1] Full financial summary")
        print("  [2] Update client financials")
        print("  [B] Back")
        choice = input("\n  Choice: ").strip().upper()
        if   choice == "1": financial_summary(data)
        elif choice == "2": update_financials(data)
        elif choice == "B": break
        else: print(r("  Invalid choice."))


def files_menu(data: dict) -> None:
    while True:
        header("FILE TRACKING")
        print("  [1] Add / update deployed file")
        print("  [2] View files for client")
        print("  [B] Back")
        choice = input("\n  Choice: ").strip().upper()
        if   choice == "1": add_file(data)
        elif choice == "2": view_files(data)
        elif choice == "B": break
        else: print(r("  Invalid choice."))


def fixes_menu(data: dict) -> None:
    while True:
        header("FIXES & REQUESTS")
        print("  [1] Add fix / request")
        print("  [2] View all open fixes")
        print("  [3] Update fix status")
        print("  [4] Mark fix as done")
        print("  [5] View fix history for client")
        print("  [B] Back")
        choice = input("\n  Choice: ").strip().upper()
        if   choice == "1": add_fix(data)
        elif choice == "2": view_open_fixes(data)
        elif choice == "3": update_fix_status(data)
        elif choice == "4": mark_fix_done(data)
        elif choice == "5": view_fix_history(data)
        elif choice == "B": break
        else: print(r("  Invalid choice."))

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main() -> None:
    data = load_data()

    while True:
        clients     = data["clients"]
        n_clients   = len(clients)
        open_fixes  = sum(1 for c in clients.values() for fx in c["fixes"] if fx["status"] != "done")
        monthly_net = sum(
            c["financials"]["monthly_retainer"] - c["financials"]["monthly_costs"]
            for c in clients.values()
        )

        # Dashboard header
        print(f"\n{BOLD}{'═' * 56}{RESET}")
        print(f"{BOLD}   JP AUTOMATION CRM  v1.0{RESET}")
        print(f"{BOLD}{'═' * 56}{RESET}")
        print(
            f"  {dim('Clients:')} {bold(str(n_clients))}   "
            f"{dim('Open fixes:')} {y(str(open_fixes)) if open_fixes else g('0')}   "
            f"{dim('Net/mo:')} {g(f'${monthly_net:,.0f}') if monthly_net >= 0 else r(f'${monthly_net:,.0f}')}"
        )
        print(f"{DIM}{'─' * 56}{RESET}\n")
        print("  [1] Client Management")
        print("  [2] Financial Tracking")
        print("  [3] File Tracking")
        print("  [4] Fixes & Requests")
        print("  [5] Business Summary")
        print("  [Q] Quit")

        choice = input("\n  Choice: ").strip().upper()
        if   choice == "1": client_menu(data)
        elif choice == "2": financial_menu(data)
        elif choice == "3": files_menu(data)
        elif choice == "4": fixes_menu(data)
        elif choice == "5": weekly_summary(data)
        elif choice == "Q":
            print(f"\n  {g('Goodbye!')}\n")
            break
        else:
            print(r("  Invalid choice. Enter 1–5 or Q."))


if __name__ == "__main__":
    main()
