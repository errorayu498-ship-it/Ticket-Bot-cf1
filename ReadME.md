# 🎫 Discord Ticket Bot - Professional Edition

Complete Discord Ticket Management System with Premium Features

## ✨ Features

✅ **Complete Ticket System**
- Dropdown menu-based ticket creation
- Multiple ticket categories with specific support roles
- Automatic ticket channel creation with proper formatting

✅ **Premium Embeds**
- Custom embed colors, images, and thumbnails
- Professional footer with customizable branding
- Beautiful ticket panel with dropdown interface

✅ **Persistent Data**
- Automatic JSON file storage for all ticket data
- Bot remembers open tickets after restart
- Safe data persistence with error handling

✅ **Full Permission System**
- Owner (complete control)
- Admin (manage tickets and panel)
- Support staff (assigned categories only)
- Blacklist system for users

✅ **Advanced Features**
- Auto-delete tickets when member leaves
- 5-star rating system with automated logging
- Comprehensive logging channel
- Slash commands for easy management
- Advanced error handling and validation

✅ **Configuration**
- All settings in config.json
- Token secured in .env file
- Customizable embed colors (RGB)
- Custom images for panels and tickets
- Support role assignment per category

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Discord.py 2.3+
- A Discord server

### Installation

1. **Clone/Download Bot Files**
```bash
# All files should be in same directory
ticket_bot.py
config.json
.env
requirements.txt
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Get Discord Token**
- Go to [Discord Developer Portal](https://discord.com/developers/applications)
- Create new application
- Add bot to application
- Copy bot token

4. **Configure .env**
```
DISCORD_TOKEN=your_bot_token_here
```

5. **Get Server IDs** (Enable Developer Mode)
- Discord Settings → Advanced → Developer Mode ON
- Right-click and copy IDs for:
  - User ID (your ID)
  - Server ID
  - Role IDs
  - Channel IDs
  - Category IDs

6. **Edit config.json**
```json
{
    "OWNER_ID": your_id_here,
    "ADMIN_ROLE_ID": admin_role_id,
    "SUPPORT_ROLE_ID": support_role_id,
    "LOG_CHANNEL_ID": log_channel_id,
    "TICKET_OPTIONS": [
        {
            "name": "Buy",
            "description": "Make a purchase",
            "category_id": category_id_here,
            "emoji": "🛒",
            "support": []
        }
    ]
}
```

7. **Run Bot**
```bash
python ticket_bot.py
```

## 📌 Commands

### Owner Only
- `/addnewoption` - Add new ticket option
- `/removeoption` - Temporarily remove ticket option
- `/add_temp_option` - Restore removed option
- `/addblacklist` - Add member to blacklist

### Admin Only
- `/ticketpanel #channel` - Load ticket panel
- `/bot_stats` - Show statistics

### Everyone
- `/help` - Show all commands

## 📝 Configuration

### config.json Fields

```json
{
    "OWNER_ID": 1234567890,              // Bot owner ID
    "ADMIN_ROLE_ID": 9876543210,         // Admin role ID
    "SUPPORT_ROLE_ID": 5555555555,       // Support role ID
    "LOG_CHANNEL_ID": 1111111111,        // Ticket logs channel
    
    "PANEL_TITLE": "Ticket Bot",         // Panel title
    "PANEL_DESCRIPTION": "...",          // Panel description
    "PANEL_FOOTER": "Programmed By...",  // Footer text
    
    "PANEL_IMAGE": "image_url",          // Main image
    "PANEL_THUMBNAIL": "thumb_url",      // Thumbnail
    "PANEL_FOOTER_IMAGE": "footer_url",  // Footer icon
    
    "TICKET_IMAGE": "ticket_url",        // Ticket embed image
    "TICKET_THUMBNAIL": "ticket_thumb",  // Ticket thumbnail
    
    "EMBED_COLOR_R": 0,                  // Red value (0-255)
    "EMBED_COLOR_G": 100,                // Green value (0-255)
    "EMBED_COLOR_B": 255,                // Blue value (0-255)
    
    "BOT_STATUS": "Online",              // Status text
    "BOT_ACTIVITY": "Ticket System",     // Activity text
    
    "TICKET_OPTIONS": [                  // Available ticket types
        {
            "name": "Buy",
            "description": "Open ticket to buy",
            "category_id": 1122334455,
            "emoji": "🛒",
            "support": []                // Support role IDs if restricted
        }
    ]
}
```

## 🔐 Security

- Token stored in .env (never commit to git)
- Permission checks on all commands
- Input validation for all user data
- Error handling with safe fallbacks
- No sensitive data in logs

## 📁 Files

- `ticket_bot.py` - Main bot application (900+ lines)
- `config.json` - Configuration file
- `.env` - Environment variables (your token)
- `requirements.txt` - Python dependencies
- `GUIDE.txt` - Detailed guide (Urdu/English)
- `setup.py` - Quick setup verification

### Auto-Generated Files
- `tickets_data.json` - Open tickets (created automatically)
- `blacklist.json` - Blacklisted users (created automatically)
- `removed_options.json` - Hidden options (created automatically)

## 🛠️ Troubleshooting

### Bot won't start
- Check Python version (3.8+ required)
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check .env has valid token

### Slash commands not showing
- Restart bot
- Wait a few seconds for sync
- Check bot has APPLICATION.COMMANDS permission

### Tickets not creating
- Verify category ID in config.json
- Check bot has permission in category
- Bot role must be high enough

### DM errors
- Normal if user has DMs disabled
- Check bot logs for details

## ⚙️ Bot Permissions

Grant bot these permissions:
- ✅ Manage Channels (create/delete ticket channels)
- ✅ Manage Roles (set permissions)
- ✅ Send Messages (send embeds)
- ✅ Embed Links (show embeds)
- ✅ Read Message History
- ✅ View Channels
- ✅ Connect (voice channels)

## 📊 Logging

All ticket actions logged to configured LOG_CHANNEL_ID:
- ✅ Ticket created
- 🔒 Ticket closed
- ⭐ Rating received
- 🚪 Member left (ticket deleted)
- ⚠️ Errors and warnings

## 🎨 Customization

### Change Embed Color
Edit RGB values in config.json:
```json
"EMBED_COLOR_R": 0,
"EMBED_COLOR_G": 100,
"EMBED_COLOR_B": 255
```
[RGB Color Picker](https://www.rapidtables.com/web/color/RGB_Color.html)

### Add Custom Images
1. Upload to Imgur or Discord
2. Get image link
3. Paste in config.json:
```json
"PANEL_IMAGE": "https://example.com/image.png"
```

### Change Bot Status
Edit in config.json:
```json
"BOT_ACTIVITY": "Your custom activity"
"BOT_STATUS": "Your custom status"
```

## 📞 Support

For detailed help, see `GUIDE.txt` file in same directory.

### Common Issues
1. Run `python setup.py` to verify setup
2. Check console logs for specific errors
3. Verify all IDs are correct in config.json
4. Ensure bot token is valid

## 🚀 Production Deployment

Before deploying:
- Test in private server first
- Verify all IDs are production IDs
- Configure all text/images/colors
- Set up logging channel
- Grant appropriate role permissions
- Enable Message Content Intent in dev portal

## 📋 License

Professional ticket bot created with ❤️

---

**Version**: 1.0  
**Status**: Production Ready  
**Error Handling**: ✅ Full Coverage  
**Persistence**: ✅ All Data Saved  

🎉 Ready to use! Happy ticket management!
