with open('bot.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'bot.auto_react_all = await db.load_auto_react_all()' in line:
        target = i + 3  # setelah except block auto_react_all
        break

new_code = '''
    try:
        loaded = await db.load_auto_react()
        bot.auto_react.enabled_channels = loaded
        print(f"✓ Loaded {len(loaded)} auto_react from database")
    except Exception as e:
        print(f"❌ Error loading auto_react: {e}")
'''

lines.insert(target, new_code)

with open('bot.py', 'w') as f:
    f.writelines(lines)
print('done')
