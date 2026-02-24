with open('bot.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'class ProductsCache:' in line:
        target = i
        break

new_code = '''    async def save_auto_react(self, channel_id, emojis):
        """Simpan auto_react ke database"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(\'\'\'INSERT OR REPLACE INTO auto_react
                    (channel_id, emojis) VALUES (?, ?)\'\'\',
                    (str(channel_id), json.dumps(emojis)))
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error save auto_react: {e}")
            return False

    async def delete_auto_react(self, channel_id):
        """Hapus auto_react dari database"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(\'DELETE FROM auto_react WHERE channel_id = ?\', (str(channel_id),))
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error delete auto_react: {e}")
            return False

    async def load_auto_react(self):
        """Load auto_react dari database"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute(\'SELECT channel_id, emojis FROM auto_react\')
                rows = await cursor.fetchall()
            result = {}
            for row in rows:
                result[int(row[0])] = json.loads(row[1])
            print(f"✓ Loaded {len(result)} auto_react from database")
            return result
        except Exception as e:
            print(f"❌ Error load auto_react: {e}")
            return {}

'''

lines.insert(target, new_code)

with open('bot.py', 'w') as f:
    f.writelines(lines)
print('done')
