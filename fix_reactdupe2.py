with open('bot.py', 'r') as f:
    lines = f.readlines()

# Cari dan hapus duplikat tabel auto_react
found_first = False
to_remove = []
for i, line in enumerate(lines):
    if "CREATE TABLE IF NOT EXISTS auto_react'" in line or "CREATE TABLE IF NOT EXISTS auto_react\n" in line:
        if not found_first:
            found_first = True
        else:
            # Hapus 4 baris duplikat (dari CREATE sampai closing ''')
            to_remove.extend([i-1, i, i+1, i+2, i+3])

lines = [l for i, l in enumerate(lines) if i not in to_remove]

with open('bot.py', 'w') as f:
    f.writelines(lines)
print('done')
