with open('bot.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'await db.commit()' in line and i < 115:
        target = i
        break

new_lines = [
    '\n',
    "            await db.execute('''CREATE TABLE IF NOT EXISTS auto_react\n",
    "                         (channel_id TEXT PRIMARY KEY,\n",
    "                          emojis TEXT)''')\n",
    '\n'
]

for j, l in enumerate(new_lines):
    lines.insert(target + j, l)

with open('bot.py', 'w') as f:
    f.writelines(lines)
print('done')
