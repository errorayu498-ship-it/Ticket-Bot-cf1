import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from dotenv import load_dotenv
from typing import Optional
import asyncio

# Load environment variables
load_dotenv()

# Import utils
from utils.database import Database
from utils.ticket_manager import TicketManager
from utils.embed_builder import EmbedBuilder
from utils.logger import logger

# Load config
with open('config.json', 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class TicketBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=CONFIG['prefix'], intents=intents)
        self.config = CONFIG
        self.db = Database()
        self.embed_builder = EmbedBuilder(CONFIG)
        self.ticket_manager = None
        
    async def setup_hook(self):
        await self.db.load_data()
        self.ticket_manager = TicketManager(self, self.db, self.embed_builder, self.config)
        await self.load_extension('commands')
        await self.tree.sync()
        logger.info("Bot setup complete")
    
    async def on_ready(self):
        logger.info(f'Bot logged in as {self.user.name}')
        
        # Set bot status
        status_config = self.config['bot_status']
        activity_type = status_config['activity_type'].lower()
        activity = None
        
        if activity_type == 'watching':
            activity = discord.Activity(type=discord.ActivityType.watching, name=status_config['activity_name'])
        elif activity_type == 'listening':
            activity = discord.Activity(type=discord.ActivityType.listening, name=status_config['activity_name'])
        elif activity_type == 'playing':
            activity = discord.Game(name=status_config['activity_name'])
        else:
            activity = discord.Activity(type=discord.ActivityType.watching, name=status_config['activity_name'])
        
        status = status_config['status']
        await self.change_presence(activity=activity, status=getattr(discord.Status, status))
        
        # Restore ticket panel
        await self.restore_ticket_panel()
    
    async def restore_ticket_panel(self):
        """Restore ticket panel after restart"""
        channel_id, message_id = await self.db.get_panel_info()
        if channel_id and message_id:
            channel = self.get_channel(channel_id)
            if channel:
                try:
                    message = await channel.fetch_message(message_id)
                    if message:
                        logger.info("Ticket panel restored successfully")
                except:
                    logger.warning("Could not restore ticket panel message")
    
    async def on_member_remove(self, member: discord.Member):
        """Handle member leaving"""
        await self.ticket_manager.check_member_left(member)

bot = TicketBot()

# Commands
@bot.tree.command(name="ticketpanel", description="Load ticket panel in current channel")
@app_commands.default_permissions(administrator=True)
async def ticketpanel(interaction: discord.Interaction):
    """Load ticket panel (Admin only)"""
    try:
        # Check permissions
        if not interaction.user.guild_permissions.administrator and interaction.user.id != bot.config['owner_id']:
            has_admin_role = any(role.id in bot.config['admin_roles'] for role in interaction.user.roles)
            if not has_admin_role:
                await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
                return
        
        # Create dropdown
        select = TicketDropdown(bot)
        view = discord.ui.View(timeout=None)
        view.add_item(select)
        
        embed = bot.embed_builder.create_ticket_panel()
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # Save panel info
        message = await interaction.original_response()
        await bot.db.update_panel_info(interaction.channel_id, message.id)
        
        logger.info(f"Ticket panel loaded by {interaction.user} in {interaction.channel}")
        
    except Exception as e:
        logger.error(f"Error loading ticket panel: {e}")
        await interaction.response.send_message("An error occurred while loading the ticket panel!", ephemeral=True)

class TicketDropdown(discord.ui.Select):
    def __init__(self, bot: TicketBot):
        self.bot = bot
        options = []
        
        # Get available options (not temporarily removed)
        temp_removed = [opt.get('name') for opt in bot.db.data.get('temp_removed_options', [])]
        
        for key, value in bot.config['ticket_categories'].items():
            if key not in temp_removed:
                options.append(
                    discord.SelectOption(
                        label=value['label'],
                        description=value['description'],
                        emoji=value.get('emoji'),
                        value=key
                    )
                )
        
        super().__init__(
            placeholder="Select a ticket type...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        option_data = self.bot.config['ticket_categories'].get(selected)
        
        if option_data:
            await self.bot.ticket_manager.create_ticket(interaction, selected, option_data)
        else:
            await interaction.response.send_message("Invalid ticket option!", ephemeral=True)

@bot.tree.command(name="addnewoption", description="Add a new ticket option")
@app_commands.default_permissions(administrator=True)
async def addnewoption(
    interaction: discord.Interaction,
    name: str,
    label: str,
    description: str,
    category_id: str,
    emoji: Optional[str] = None,
    support_role_id: Optional[str] = None
):
    """Add new ticket option"""
    try:
        if interaction.user.id != bot.config['owner_id'] and not any(role.id in bot.config['admin_roles'] for role in interaction.user.roles):
            await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
            return
        
        bot.config['ticket_categories'][name] = {
            "category_id": int(category_id),
            "label": label,
            "description": description,
            "emoji": emoji,
            "support_role_id": int(support_role_id) if support_role_id else None
        }
        
        # Save to config
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(bot.config, f, indent=4, ensure_ascii=False)
        
        await interaction.response.send_message(f"Ticket option '{label}' added successfully!", ephemeral=True)
        logger.info(f"New ticket option added: {name}")
        
    except Exception as e:
        logger.error(f"Error adding option: {e}")
        await interaction.response.send_message("An error occurred while adding the option!", ephemeral=True)

@bot.tree.command(name="removeoption", description="Temporarily remove a ticket option")
@app_commands.default_permissions(administrator=True)
async def removeoption(interaction: discord.Interaction):
    """Temporarily remove a ticket option"""
    try:
        if interaction.user.id != bot.config['owner_id'] and not any(role.id in bot.config['admin_roles'] for role in interaction.user.roles):
            await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
            return
        
        # Create dropdown for options to remove
        options = []
        for key, value in bot.config['ticket_categories'].items():
            if key not in [opt.get('name') for opt in bot.db.data.get('temp_removed_options', [])]:
                options.append(discord.SelectOption(label=value['label'], value=key))
        
        if not options:
            await interaction.response.send_message("No options available to remove!", ephemeral=True)
            return
        
        select = RemoveOptionSelect(bot, options)
        view = discord.ui.View(timeout=60)
        view.add_item(select)
        
        await interaction.response.send_message("Select the option to temporarily remove:", view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in removeoption: {e}")
        await interaction.response.send_message("An error occurred!", ephemeral=True)

class RemoveOptionSelect(discord.ui.Select):
    def __init__(self, bot: TicketBot, options):
        self.bot = bot
        super().__init__(placeholder="Select option to remove...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        option_name = self.values[0]
        option_data = self.bot.config['ticket_categories'][option_name]
        
        await self.bot.db.add_temp_removed_option({
            'name': option_name,
            'data': option_data
        })
        
        await interaction.response.send_message(f"Option '{option_data['label']}' temporarily removed!", ephemeral=True)
        logger.info(f"Option temporarily removed: {option_name}")

@bot.tree.command(name="add_temp_option", description="Add back a temporarily removed option")
@app_commands.default_permissions(administrator=True)
async def add_temp_option(interaction: discord.Interaction):
    """Add back temporarily removed option"""
    try:
        if interaction.user.id != bot.config['owner_id'] and not any(role.id in bot.config['admin_roles'] for role in interaction.user.roles):
            await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
            return
        
        temp_options = await bot.db.get_temp_removed_options()
        if not temp_options:
            await interaction.response.send_message("No temporarily removed options found!", ephemeral=True)
            return
        
        options = [discord.SelectOption(label=opt['data']['label'], value=opt['name']) for opt in temp_options]
        select = AddTempOptionSelect(bot, options)
        view = discord.ui.View(timeout=60)
        view.add_item(select)
        
        await interaction.response.send_message("Select the option to add back:", view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in add_temp_option: {e}")
        await interaction.response.send_message("An error occurred!", ephemeral=True)

class AddTempOptionSelect(discord.ui.Select):
    def __init__(self, bot: TicketBot, options):
        self.bot = bot
        super().__init__(placeholder="Select option to add back...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        option_name = self.values[0]
        await self.bot.db.remove_temp_removed_option(option_name)
        
        await interaction.response.send_message(f"Option added back successfully!", ephemeral=True)
        logger.info(f"Option added back: {option_name}")

@bot.tree.command(name="help", description="Show all commands")
async def help_command(interaction: discord.Interaction):
    """Show help menu"""
    embed = discord.Embed(
        title="Ticket Bot Commands",
        description="Here are all available commands:",
        color=bot.config['embed_settings']['color']
    )
    
    commands_list = [
        ("/ticketpanel", "Load ticket panel in current channel"),
        ("/addnewoption", "Add a new ticket option"),
        ("/removeoption", "Temporarily remove a ticket option"),
        ("/add_temp_option", "Add back a temporarily removed option"),
        ("/bot_stats", "Show bot statistics"),
        ("/addblacklist", "Blacklist a user from creating tickets"),
        ("/removeblacklist", "Remove user from blacklist"),
        ("/help", "Show this help menu")
    ]
    
    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)
    
    embed.set_footer(text=bot.config['embed_settings']['footer_text'])
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="bot_stats", description="Show bot statistics")
async def bot_stats(interaction: discord.Interaction):
    """Show bot statistics"""
    try:
        tickets = await bot.db.get_all_tickets()
        open_tickets = len([t for t in tickets.values() if t['status'] == 'open'])
        closed_tickets = len([t for t in tickets.values() if t['status'] == 'closed'])
        
        embed = discord.Embed(
            title="Bot Statistics",
            color=bot.config['embed_settings']['color'],
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="📊 Total Tickets", value=len(tickets), inline=True)
        embed.add_field(name="🟢 Open Tickets", value=open_tickets, inline=True)
        embed.add_field(name="🔴 Closed Tickets", value=closed_tickets, inline=True)
        embed.add_field(name="📁 Available Options", value=len(bot.config['ticket_categories']), inline=True)
        embed.add_field(name="🚫 Blacklisted Users", value=len(bot.db.data.get('blacklisted_users', [])), inline=True)
        embed.add_field(name="🏓 Bot Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="👑 Owner", value=f"<@{bot.config['owner_id']}>", inline=True)
        embed.add_field(name="📈 Ticket Counter", value=bot.db.data.get('ticket_counter', 0), inline=True)
        
        embed.set_footer(text=bot.config['embed_settings']['footer_text'])
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in bot_stats: {e}")
        await interaction.response.send_message("An error occurred!", ephemeral=True)

@bot.tree.command(name="addblacklist", description="Blacklist a user from creating tickets")
@app_commands.default_permissions(administrator=True)
async def addblacklist(interaction: discord.Interaction, user: discord.User):
    """Blacklist a user"""
    try:
        if interaction.user.id != bot.config['owner_id'] and not any(role.id in bot.config['admin_roles'] for role in interaction.user.roles):
            await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
            return
        
        await bot.db.add_blacklisted_user(user.id)
        await interaction.response.send_message(f"{user.mention} has been blacklisted from creating tickets!", ephemeral=True)
        logger.info(f"User {user} blacklisted by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error in addblacklist: {e}")
        await interaction.response.send_message("An error occurred!", ephemeral=True)

@bot.tree.command(name="removeblacklist", description="Remove user from blacklist")
@app_commands.default_permissions(administrator=True)
async def removeblacklist(interaction: discord.Interaction, user: discord.User):
    """Remove user from blacklist"""
    try:
        if interaction.user.id != bot.config['owner_id'] and not any(role.id in bot.config['admin_roles'] for role in interaction.user.roles):
            await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
            return
        
        await bot.db.remove_blacklisted_user(user.id)
        await interaction.response.send_message(f"{user.mention} has been removed from blacklist!", ephemeral=True)
        logger.info(f"User {user} removed from blacklist by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error in removeblacklist: {e}")
        await interaction.response.send_message("An error occurred!", ephemeral=True)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    logger.error(f"Command error: {error}")
    await ctx.send(f"An error occurred: {str(error)}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logger.error(f"Slash command error: {error}")
    await interaction.response.send_message(f"An error occurred: {str(error)}", ephemeral=True)

# Run bot
if __name__ == "__main__":
    try:
        bot.run(os.getenv('DISCORD_BOT_TOKEN'))
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
