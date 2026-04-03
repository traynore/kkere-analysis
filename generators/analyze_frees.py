import csv

csv_file = "Killinkere 4 - 16 v 2 - 6 Ballymahon.csv"

with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    data = list(reader)

# Find Killinkere frees conceded (Name column contains the event type)
killinkere_frees = [row for row in data if row['Team Name'].strip() == 'Killinkere' and row['Name'].strip() == 'Free conceded']

# Find Ballymahon scoreable frees
ballymahon_scores = [row for row in data if row['Team Name'].strip() == 'Ballymahon' and row['Name'].strip() == 'Scoreable free']

print(f"\n=== KILLINKERE FREES CONCEDED ===")
print(f"Total frees conceded: {len(killinkere_frees)}\n")

print(f"=== BALLYMAHON SCOREABLE FREES ===")
points = sum(1 for s in ballymahon_scores if s['Outcome'].strip() == 'Point')
goals = sum(1 for s in ballymahon_scores if s['Outcome'].strip() == 'Goal')
wide = sum(1 for s in ballymahon_scores if s['Outcome'].strip() in ['Wide', 'Short'])

print(f"Points scored: {points}")
print(f"Goals scored: {goals}")
print(f"Missed (Wide/Short): {wide}")
print(f"\nTotal scores from frees: {points + goals * 3} points ({points} points + {goals} goals)")
print(f"\nBreakdown:")
for s in ballymahon_scores:
    print(f"  {s['Time']} (Period {s['Period']}): {s['Outcome']} - {s['Player']}")
