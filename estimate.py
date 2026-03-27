from datetime import datetime
import os

def build_estimate_text(description, materials, hours, rate, margin=20):
    labor_total = hours * rate
    subtotal = materials + labor_total
    profit = subtotal * (margin / 100)
    total = subtotal + profit

    lines = [
        "================================================",
        "           CONSTRUCTION JOB ESTIMATE",
        "================================================",
        f"Date            : {datetime.now().strftime('%B %d, %Y')}",
        f"Job Description : {description}",
        "------------------------------------------------",
        f"Materials Cost  : $ {materials:10,.2f}",
        f"Labor Cost      : $ {labor_total:10,.2f}",
        "                    ------------",
        f"Subtotal        : $ {subtotal:10,.2f}",
        f"Profit ({margin}%)   : $ {profit:10,.2f}",
        "                    ------------",
        f"TOTAL ESTIMATE  : $ {total:10,.2f}",
        "================================================",
    ]
    return "\n".join(lines), total

def save_estimate(description, text):
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_name = "".join(c if c.isalnum() or c == "-" else "-" for c in description.strip().replace(" ", "-").lower())[:40]
    filename = f"{date_str}_{safe_name}.txt"
    save_dir = os.path.expanduser("~/Desktop/ai-business/estimates")
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, filename)
    with open(filepath, "w") as f:
        f.write(text + "\n")
    return filepath

# --- MAIN LOOP ---
while True:
    user_job = input("Enter the job description: ")
    user_mats = float(input("Enter materials cost: $"))
    user_hours = float(input("Enter labor hours: "))
    user_rate = float(input("Enter hourly rate: $"))

    margin_input = input("Enter your desired profit margin % (press Enter for default 20%): ").strip()
    user_margin = float(margin_input) if margin_input else 20

    estimate_text, total = build_estimate_text(user_job, user_mats, user_hours, user_rate, user_margin)

    # Print to screen
    print("\n" + estimate_text + "\n")

    # Save to file
    saved_file = save_estimate(user_job, estimate_text)
    print(f"Estimate saved to: {saved_file}")

    repeat = input("\nGenerate another estimate? (yes/no): ").lower()
    if repeat != "yes":
        print("Goodbye!")
        break
