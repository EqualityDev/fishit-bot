with open('bot.py', 'r') as f:
    lines = f.readlines()

# Fix 1: save ke DB saat set emoji
for i, line in enumerate(lines):
    if 'bot.auto_react.enabled_channels[channel_id] = emoji_list' in line:
        target_save = i
        break

lines.insert(target_save + 1, '    await db.save_auto_react(channel_id, emoji_list)\n')

# Fix 2: delete dari DB saat disable
for i, line in enumerate(lines):
    if 'del bot.auto_react.enabled_channels[channel_id]' in line:
        target_del = i
        break

lines.insert(target_del + 1, '            await db.delete_auto_react(channel_id)\n')

with open('bot.py', 'w') as f:
    f.writelines(lines)
print('done')
