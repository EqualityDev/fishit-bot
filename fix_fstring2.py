with open('bot.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '✅ **Auto-react all diaktifkan!**' in line:
        target = i
        break

# Gabungin 3 baris jadi 1
lines[target] = f'    await interaction.response.send_message(f"✅ **Auto-react all diaktifkan!**\\nChannel: {{interaction.channel.mention}}\\nEmoji: {{\" \".join(emoji_list)}}")\n'
lines.pop(target + 1)
lines.pop(target + 1)

with open('bot.py', 'w') as f:
    f.writelines(lines)
print('done')
