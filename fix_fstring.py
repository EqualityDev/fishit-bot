with open('bot.py', 'r') as f:
    content = f.read()

old = '''            await interaction.response.send_message(f"📊 **Auto-react all aktif**
Channel: {interaction.channel.mention}
Emoji: {' '.join(emoji_list)}")'''

new = '''            await interaction.response.send_message(f"📊 **Auto-react all aktif**\\nChannel: {interaction.channel.mention}\\nEmoji: {' '.join(emoji_list)}")'''

with open('bot.py', 'w') as f:
    f.write(content.replace(old, new))
print('done')
