# 🎉 READY TO USE - Infographic Generator

## ✅ WORKING SOLUTION - Use This!

### **simple_generator.py** - NO installation needed!

## 🚀 How to Use (3 Simple Steps)

### 1. Put your CSV file in this folder
Make sure it has the same format as the example CSV

### 2. Run the generator
```bash
python3 simple_generator.py "YourMatch.csv"
```

### 3. Open the HTML file
Double-click the generated `_infographic.html` file

## 📝 Example

```bash
python3 simple_generator.py "Team A vs Team B.csv"
```

Creates: `Team A vs Team B_infographic.html`

## ✨ What It Does

- ✅ Reads your CSV file
- ✅ Detects team names automatically  
- ✅ Creates beautiful infographic
- ✅ Updates team names throughout
- ✅ Ready to view in browser

## 🎯 For Multiple Games

Just run it multiple times:

```bash
python3 simple_generator.py "Game1.csv"
python3 simple_generator.py "Game2.csv"
python3 simple_generator.py "Game3.csv"
```

Each creates its own infographic!

## 📋 CSV Requirements

Your CSV needs these columns:
- Event
- Time
- Period
- Team Name
- Name
- Outcome
- Player

(Same format as your current CSV)

## 💡 Pro Tips

1. **Keep the template**: Don't delete `advanced_infographic.html`
2. **Use quotes**: For filenames with spaces: `"Team A vs Team B.csv"`
3. **Check output**: The script tells you the output filename
4. **Reuse**: Run it as many times as you want!

## ❓ Troubleshooting

**"Template not found"**
→ Make sure `advanced_infographic.html` is in the same folder

**"CSV not found"**  
→ Check the filename and use quotes if it has spaces

**"Expected 2 teams"**
→ Check your CSV has exactly 2 team names

## 🎊 You're All Set!

The generator is ready to use. Just run:

```bash
python3 simple_generator.py "your_match.csv"
```

And enjoy your infographic! 🏐
