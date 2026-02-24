with open('bot.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'except Exception as e:' in line and i > 2570 and i < 2580:
        # Cek kalau baris berikutnya kosong atau try baru
        if lines[i+1].strip() == '' or lines[i+1].strip().startswith('try:'):
            lines.insert(i+1, '        print(f"❌ Error loading auto_react_all: {e}")\n')
            break

with open('bot.py', 'w') as f:
    f.writelines(lines)
print('done')
