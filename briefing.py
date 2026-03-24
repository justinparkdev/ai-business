from datetime import datetime

now = datetime.now()
days_to_jimmy = (datetime(2026, 3, 29) - now).days
days_to_graduation = (datetime(2028, 5, 31) - now).days

print("=" * 40)
print(f"Date: {now.strftime('%A %B %d %Y')}")
print(f"Time: {now.strftime('%I:%M %p')}")
print(f"Days until Jimmy meeting: {days_to_jimmy}")
print(f"Days until graduation: {days_to_graduation}")
print(f"Current clients: 0")
print(f"Monthly revenue: $0")
print("=" * 40)
