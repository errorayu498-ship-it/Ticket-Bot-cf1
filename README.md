Project Structure

```
ticket-bot/
├── bot.py
├── config.json
├── .env
├── requirements.txt
├── memory.json
└── utils/
    ├── __init__.py
    ├── database.py
    ├── ticket_manager.py
    ├── embed_builder.py
    └── logger.py
```

1. requirements.txt

```txt
discord.py==2.3.2
python-dotenv==1.0.0
aiofiles==23.2.1
asyncio==3.4.3
```

Installation and Setup Instructions:

1. Create the project structure as shown above
2. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Configure config.json:
   · Set your bot owner ID
   · Set admin role IDs
   · Set category IDs for each ticket type
   · Set log channel ID
   · Set rating channel ID
   · Customize embed settings
   · Add support role IDs for each category
2. Set up .env file:
   · Add your Discord bot token
3. Create necessary channels in Discord:
   · Ticket categories (one for each ticket type)
   · Log channel
   · Rating channel
4. Run the bot:

```bash
python bot.py
```

Features Implemented:

✅ Error Handling System - Comprehensive error handling with logging
✅ Persistence - Tickets survive bot restarts (memory.json)
✅ Dropdown Menu - Premium dropdown for ticket types
✅ Customizable Categories - Buy, Support, Reseller, Join Team
✅ Auto Channel Creation - Creates ticket channels with proper permissions
✅ Close Button - Ticket closing with DM rating
✅ Rating System - 5-star rating with logs
✅ Logging System - Complete ticket logs in dedicated channel
✅ Auto Cleanup - Deletes tickets when members leave
✅ Premium Embeds - Fully customizable embed design
✅ Config System - All settings in config.json
✅ Rate Limiting - Prevents spam
✅ Role-Based Access - Admin, Support roles with permissions
✅ Blacklist System - Block users from creating tickets
✅ Temporary Removal - Temporarily disable ticket options
✅ Bot Stats - Complete statistics command
✅ Help Command - Shows all available commands
✅ Railway Compatible - Ready for deployment on Railway

Deployment on Railway:

1. Push code to GitHub repository
2. Create new project on Railway
3. Connect your GitHub repository
4. Add environment variable: DISCORD_BOT_TOKEN
5. Deploy!

The bot will automatically create memory.json on first run and maintain ticket state across restarts.
