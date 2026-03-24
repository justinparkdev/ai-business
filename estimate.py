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
    # Build filename: YYYY-MM-DD_job-description.txt
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_name = description.strip().replace(" ", "-").lower()
    filename = f"{date_str}_{safe_name}.txt"

    with open(filename, "w") as f:
        f.write(text + "\n")

    return filename

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
