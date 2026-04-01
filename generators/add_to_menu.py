#!/usr/bin/env python3
import sys
import re

def add_game_to_menu(csv_filename):
    # Extract game info from filename
    base_name = csv_filename.replace('.csv', '')
    html_file = f"{base_name}_FULL_infographic.html"
    
    # Parse teams and score from filename
    # Format: "Killinkere 5 - 16 v 1 - 6 Ballymahon"
    match = re.match(r'(.+?)\s+(\d+)\s*-\s*(\d+)\s+v\s+(\d+)\s*-\s*(\d+)\s+(.+)', base_name)
    if not match:
        print(f"❌ Could not parse filename: {base_name}")
        return
    
    team1, goals1, points1, goals2, points2, team2 = match.groups()
    total1 = int(goals1) * 3 + int(points1)
    total2 = int(goals2) * 3 + int(points2)
    
    option_text = f"{team1} {goals1}-{points1} ({total1}pts) vs {team2} {goals2}-{points2} ({total2}pts) ✓"
    option_html = f'                <option value="{html_file}">{option_text}</option>'
    
    # Read ALL_GAMES_FULL.html
    with open('ALL_GAMES_FULL.html', 'r') as f:
        content = f.read()
    
    # Find the Challenges 2026 section and add the new game
    challenges_pattern = r'(<optgroup label="Challenges 2026">)(.*?)(</optgroup>)'
    
    def replace_challenges(match):
        start = match.group(1)
        existing = match.group(2)
        end = match.group(3)
        return f"{start}{existing}\n{option_html}\n            {end}"
    
    new_content = re.sub(challenges_pattern, replace_challenges, content, flags=re.DOTALL)
    
    # Write back
    with open('ALL_GAMES_FULL.html', 'w') as f:
        f.write(new_content)
    
    print(f"✅ Added to menu: {option_text}")
    print(f"📄 File: {html_file}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 add_to_menu.py 'Game.csv'")
        sys.exit(1)
    
    add_game_to_menu(sys.argv[1])
