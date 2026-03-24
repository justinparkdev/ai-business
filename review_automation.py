"""
Review Automation System
Generates personalized SMS review request messages for local businesses.
Powered by Claude AI (claude-haiku-4-5-20251001).

Setup: export ANTHROPIC_API_KEY="your-key-here"
Run:   python3 review_automation.py
"""

import anthropic
import csv
import os
import re
from datetime import datetime, timedelta

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

MODEL = "claude-haiku-4-5-20251001"
LOG_FILE = "message_log.csv"
MAX_SMS_LENGTH = 160


# ─── PHONE VALIDATION ─────────────────────────────────────────────────────────

def validate_phone(phone: str) -> bool:
    """
    Validate phone number format.
    Accepts: 5551234567, 555-123-4567, (555) 123-4567, +15551234567
    """
    digits = re.sub(r'\D', '', phone)
    return len(digits) == 10 or (len(digits) == 11 and digits[0] == '1')


# ─── PERSONALIZATION SCORING ──────────────────────────────────────────────────

def score_message(message: str, customer_name: str, job_type: str, business_name: str) -> int:
    """
    Score a message 1-10 for personalization quality.
    Checks for: customer name, job type, business name, length, tone, link.
    """
    score = 0
    msg_lower = message.lower()
    first_name = customer_name.split()[0].lower()

    # Contains customer's first name (+2)
    if first_name in msg_lower:
        score += 2

    # References the specific job type (+2)
    if job_type:
        job_words = job_type.lower().split()
        if any(word in msg_lower for word in job_words):
            score += 2

    # Contains business name (+2)
    if business_name.lower() in msg_lower:
        score += 2

    # Fits in a single SMS — under 160 chars (+1)
    if len(message) <= MAX_SMS_LENGTH:
        score += 1

    # Ends with the review link placeholder (+1)
    if message.strip().endswith("[REVIEW_LINK]"):
        score += 1

    # Has a warm, personal opening (+1)
    if any(message.lower().startswith(w) for w in ["hi ", "hey ", "thank"]):
        score += 1

    # Substantial enough to feel real — at least 60 chars (+1)
    if len(message) >= 60:
        score += 1

    return min(score, 10)


# ─── FALLBACK TEMPLATES (used if API call fails) ──────────────────────────────

def generate_fallback_messages(customer_name: str, job_type: str, business_name: str) -> list:
    """
    Generate 3 messages from hardcoded templates.
    Called automatically when the API is unavailable.
    """
    first_name = customer_name.split()[0]
    job = job_type if job_type else "service"

    templates = [
        f"Hi {first_name}! Thanks for choosing {business_name} for your {job}. We'd love a quick Google review! [REVIEW_LINK]",
        f"Hey {first_name}, it was great working on your {job}! {business_name} would really appreciate a review. [REVIEW_LINK]",
        f"Hi {first_name}! Hope you're happy with your {job}. A quick review helps {business_name} grow — thank you! [REVIEW_LINK]",
    ]

    return [
        {
            "text": msg,
            "char_count": len(msg),
            "score": score_message(msg, customer_name, job_type, business_name)
        }
        for msg in templates
    ]


# ─── AI MESSAGE GENERATION ────────────────────────────────────────────────────

def generate_messages_with_ai(
    customer_name: str,
    phone: str,
    job_type: str,
    business_name: str
) -> list:
    """
    Call Claude Haiku to generate 3 unique, personalized SMS variations.
    Returns a list of dicts with 'text', 'char_count', and 'score'.
    Falls back to templates automatically if the API call fails.
    """
    client = anthropic.Anthropic()
    job_context = job_type if job_type else "general service"

    prompt = f"""Generate exactly 3 different SMS review request messages for a local business.

Customer name: {customer_name}
Job completed: {job_context}
Business name: {business_name}

Strict rules:
- Each message MUST be under {MAX_SMS_LENGTH} characters total (count carefully)
- Every message MUST end with exactly: [REVIEW_LINK]
- Use the customer's first name naturally
- Mention the specific job type naturally
- Include the business name
- Sound warm, human, and genuine — not robotic or spammy
- Each of the 3 messages should have a noticeably different tone or angle
- Output ONLY the 3 messages, one per line, with no labels, numbers, or extra text"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )

    raw_text = response.content[0].text.strip()
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    messages = lines[:3]

    # Pad with fallbacks if Claude returned fewer than 3 lines
    fallbacks = generate_fallback_messages(customer_name, job_type, business_name)
    while len(messages) < 3:
        messages.append(fallbacks[len(messages)]["text"])

    results = []
    for msg in messages:
        # Guarantee the link placeholder is present
        if not msg.endswith("[REVIEW_LINK]"):
            msg = msg.rstrip() + " [REVIEW_LINK]"
        results.append({
            "text": msg,
            "char_count": len(msg),
            "score": score_message(msg, customer_name, job_type, business_name)
        })

    return results


# ─── INPUT COLLECTION ─────────────────────────────────────────────────────────

def get_customer_inputs() -> dict:
    """Prompt for all required customer info with validation."""
    print("\n" + "─" * 52)
    print("  NEW REVIEW REQUEST")
    print("─" * 52)

    # Customer name — required
    while True:
        name = input("  Customer name     : ").strip()
        if name:
            break
        print("  ! Name is required.")

    # Phone — required and validated
    while True:
        phone = input("  Phone number      : ").strip()
        if not phone:
            print("  ! Phone number is required.")
            continue
        if validate_phone(phone):
            break
        print("  ! Invalid format. Try: 555-123-4567 or (555) 123-4567")

    # Job type — optional, defaults to generic
    job_type = input("  Job type (optional): ").strip()

    # Business name — required
    while True:
        business = input("  Business name     : ").strip()
        if business:
            break
        print("  ! Business name is required.")

    return {
        "customer_name": name,
        "phone": phone,
        "job_type": job_type,
        "business_name": business
    }


# ─── DISPLAY ──────────────────────────────────────────────────────────────────

def display_variations(variations: list) -> None:
    """Print all 3 message variations with character count and score."""
    print("\n" + "═" * 52)
    print("  GENERATED MESSAGE VARIATIONS")
    print("═" * 52)

    for i, v in enumerate(variations, 1):
        sms_status = "OK" if v["char_count"] <= MAX_SMS_LENGTH else "TOO LONG"
        print(f"\n  Variation {i}")
        print(f"  Score: {v['score']}/10  |  {v['char_count']} chars  |  {sms_status}")
        print(f"  \"{v['text']}\"")

    print("\n" + "─" * 52)


# ─── CSV LOGGING ──────────────────────────────────────────────────────────────

def log_message(inputs: dict, selected: dict) -> None:
    """
    Append the selected message to message_log.csv.
    Creates the file with headers if it doesn't exist yet.
    """
    file_exists = os.path.exists(LOG_FILE)

    with open(LOG_FILE, "a", newline="") as f:
        fieldnames = [
            "timestamp", "customer_name", "phone",
            "job_type", "business_name", "message",
            "char_count", "score"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        # Write headers only on the first entry
        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "timestamp":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "customer_name": inputs["customer_name"],
            "phone":         inputs["phone"],
            "job_type":      inputs["job_type"],
            "business_name": inputs["business_name"],
            "message":       selected["text"],
            "char_count":    selected["char_count"],
            "score":         selected["score"]
        })

    print(f"  Logged to {LOG_FILE}")


# ─── WEEKLY SUMMARY ───────────────────────────────────────────────────────────

def weekly_summary() -> None:
    """Read message_log.csv and print stats for the past 7 days."""
    if not os.path.exists(LOG_FILE):
        print("\n  No log file found — no messages have been sent yet.")
        return

    cutoff = datetime.now() - timedelta(days=7)
    total = 0
    scores = []
    by_business = {}

    with open(LOG_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
            except (ValueError, KeyError):
                continue  # Skip malformed rows

            if ts >= cutoff:
                total += 1
                try:
                    scores.append(int(row["score"]))
                except (ValueError, KeyError):
                    pass
                biz = row.get("business_name", "Unknown")
                by_business[biz] = by_business.get(biz, 0) + 1

    print("\n" + "═" * 52)
    print("  WEEKLY SUMMARY  (last 7 days)")
    print("═" * 52)

    if total == 0:
        print("  No messages sent in the past 7 days.")
    else:
        avg_score = sum(scores) / len(scores) if scores else 0
        print(f"  Total messages sent     : {total}")
        print(f"  Avg personalization score: {avg_score:.1f} / 10")
        print(f"\n  Breakdown by business:")
        for biz, count in sorted(by_business.items(), key=lambda x: -x[1]):
            label = "message" if count == 1 else "messages"
            print(f"    {biz}: {count} {label}")

    print("─" * 52)


# ─── MAIN LOOP ────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 52)
    print("   REVIEW AUTOMATION SYSTEM  v1.0")
    print("═" * 52)
    print("  [G] Generate messages for a customer")
    print("  [S] Weekly summary")
    print("  [Q] Quit")

    while True:
        print()
        action = input("  Action (G / S / Q): ").strip().upper()

        # ── Quit ──────────────────────────────────────────────────────────────
        if action == "Q":
            print("\n  Goodbye!\n")
            break

        # ── Weekly summary ────────────────────────────────────────────────────
        elif action == "S":
            weekly_summary()

        # ── Generate messages ─────────────────────────────────────────────────
        elif action == "G":
            inputs = get_customer_inputs()

            print("\n  Generating messages...", end="", flush=True)

            try:
                variations = generate_messages_with_ai(
                    inputs["customer_name"],
                    inputs["phone"],
                    inputs["job_type"],
                    inputs["business_name"]
                )
                print(" done.")

            except anthropic.AuthenticationError:
                print("\n  ! API key missing or invalid.")
                print("  ! Set it with: export ANTHROPIC_API_KEY='your-key'")
                print("  ! Using fallback templates instead.\n")
                variations = generate_fallback_messages(
                    inputs["customer_name"],
                    inputs["job_type"],
                    inputs["business_name"]
                )

            except Exception as e:
                print(f"\n  ! API unavailable ({type(e).__name__}). Using fallback templates.")
                variations = generate_fallback_messages(
                    inputs["customer_name"],
                    inputs["job_type"],
                    inputs["business_name"]
                )

            display_variations(variations)

            # Let user pick which variation to log
            while True:
                choice = input("  Select variation to log (1 / 2 / 3) or [S] to skip: ").strip().upper()
                if choice in ("1", "2", "3"):
                    selected = variations[int(choice) - 1]
                    log_message(inputs, selected)
                    print("  Message logged successfully.")
                    break
                elif choice == "S":
                    print("  Skipped — nothing logged.")
                    break
                else:
                    print("  Enter 1, 2, 3, or S.")

        else:
            print("  Enter G, S, or Q.")


if __name__ == "__main__":
    main()
