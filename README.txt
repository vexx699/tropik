INFINITY SLOTS - BUY ACCESS BOT

Files:
- bot.py
- requirements.txt

HOST SETUP (generic Python bot host):
1. Upload bot.py and requirements.txt to the host.
2. Set the startup command to: python bot.py
3. Install dependencies using: pip install -r requirements.txt
4. Add an environment variable named DISCORD_TOKEN with your bot token.
5. Enable Server Members Intent in Discord Developer Portal > Bot.
6. Invite the bot with scopes: bot and applications.commands.
   Permissions needed: View Channels, Send Messages, Embed Links, Read Message History,
   Manage Channels, Manage Roles.
7. Move the bot's role ABOVE Access 1D and Access 7D roles in Server Settings > Roles.
8. Run the bot, then use /buyaccess in the channel where you want the panel.
   The command requires Manage Server permission.

IMPORTANT:
- Keep the host's persistent disk/storage enabled. The SQLite database stores orders and role expirations.
- This bot polls BlockCypher's public Litecoin API every 60 seconds; public API limits/outages may affect detection.
- Payments are matched by exact amount in litoshi. Each invoice adds a small unique amount to help distinguish
  simultaneous purchases. The user must send the exact displayed LTC amount.
- The EUR/LTC conversion is fetched when the ticket is created. The displayed LTC amount is the amount due.
- The bot requires 6 blockchain confirmations before granting the role.
- If you redeploy, preserve buy_access.sqlite3 or pending orders and expiry records will be lost.
- For a production store, consider a dedicated payment processor/webhook and monitoring.
- Never put your bot token in bot.py or share it with anyone.
