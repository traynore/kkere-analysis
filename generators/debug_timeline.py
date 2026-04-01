import csv

events = []
with open("Killinkere 4 - 9 v 0 - 12 Aughadrumsee.csv", 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get('Team Name'):
            events.append(row)

scoring_events = [e for e in events if e.get('Name') in ['Shot from play', 'Scoreable free'] and e.get('Outcome') in ['Goal', 'Point', '2 Points']]
scoring_events.sort(key=lambda x: (int(x.get('Period', '1')), x.get('Time', '00:00:00')))

print("First 10 scoring events:")
for i, e in enumerate(scoring_events[:10]):
    print(f"{i+1}. {e['Time']} P{e['Period']} - {e['Team Name']}: {e['Outcome']} by {e.get('Player', 'Unknown')}")
