import csv

events = []
with open("Killinkere 4 - 9 v 0 - 12 Aughadrumsee.csv", 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get('Team Name'):
            events.append(row)

scoring_events = [e for e in events if e.get('Name') in ['Shot from play', 'Scoreable free'] and e.get('Outcome') in ['Goal', 'Point', '2 Points']]
scoring_events.sort(key=lambda x: (int(x.get('Period', '1')), x.get('Time', '00:00:00')))

t1_point_styles = ['circle']  # Start
t1_point_colors = ['']
t2_point_styles = ['circle']
t2_point_colors = ['']

for i, e in enumerate(scoring_events):
    if e['Team Name'] == 'Killinkere':
        if e['Outcome'] == 'Goal':
            t1_point_styles.append('rectRot')
            t1_point_colors.append('green')
        elif e['Outcome'] == '2 Points':
            t1_point_styles.append('rectRot')
            t1_point_colors.append('orange')
        else:
            t1_point_styles.append('circle')
            t1_point_colors.append('white')
        t2_point_styles.append('circle')
        t2_point_colors.append('')
    else:
        if e['Outcome'] == 'Goal':
            t2_point_styles.append('rectRot')
            t2_point_colors.append('green')
        elif e['Outcome'] == '2 Points':
            t2_point_styles.append('rectRot')
            t2_point_colors.append('orange')
        else:
            t2_point_styles.append('circle')
            t2_point_colors.append('white')
        t1_point_styles.append('circle')
        t1_point_colors.append('')
    
    print(f"{i+1}. {e['Time']} - {e['Team Name']}: {e['Outcome']}")
    print(f"   T1 style: {t1_point_styles[-1]}, color: {t1_point_colors[-1]}")
    print(f"   T2 style: {t2_point_styles[-1]}, color: {t2_point_colors[-1]}")
    if i >= 9:
        break

print(f"\nFirst 11 T1 styles: {t1_point_styles[:11]}")
print(f"First 11 T1 colors: {t1_point_colors[:11]}")
