import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime
import aiofiles
from dotenv import load_dotenv
import logging
from typing import Optional, Dict, List
import traceback

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("config.json not found!")
        return {}
    except json.JSONDecodeError:
        logger.error("config.json is not valid JSON!")
        return {}

class TicketBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.tickets_file = 'tickets_data.json'
        self.load_tickets_data()
        self.load_removed_options()
        self.load_blacklist()
        
    async def save_tickets_data(self):
        """Save tickets data to JSON file"""
        try:
            async with aiofiles.open(self.tickets_file, 'w') as f:
                await f.write(json.dumps(self.tickets_data, indent=4))
        except Exception as e:
            logger.error(f"Error saving tickets data: {e}")
    
    def load_tickets_data(self):
        """Load tickets data from JSON file"""
        try:
            if os.path.exists(self.tickets_file):
                with open(self.tickets_file, 'r') as f:
                    self.tickets_data = json.load(f)
            else:
                self.tickets_data = {}
        except Exception as e:
            logger.error(f"Error loading tickets data: {e}")
            self.tickets_data = {}
    
    def load_removed_options(self):
        """Load removed ticket options"""
        try:
            if os.path.exists('removed_options.json'):
                with open('removed_options.json', 'r') as f:
                    self.removed_options = json.load(f)
            else:
                self.removed_options = {}
        except Exception as e:
            logger.error(f"Error loading removed options: {e}")
            self.removed_options = {}
    
    async def save_removed_options(self):
        """Save removed options to file"""
        try:
            async with aiofiles.open('removed_options.json', 'w') as f:
                await f.write(json.dumps(self.removed_options, indent=4))
        except Exception as e:
            logger.error(f"Error saving removed options: {e}")
    
    def load_blacklist(self):
        """Load blacklist data"""
        try:
            if os.path.exists('blacklist.json'):
                with open('blacklist.json', 'r') as f:
                    self.blacklist = json.load(f)
            else:
                self.blacklist = {"members": []}
        except Exception as e:
            logger.error(f"Error loading blacklist: {e}")
            self.blacklist = {"members": []}
    
    async def save_blacklist(self):
        """Save blacklist to file"""
        try:
            async with aiofiles.open('blacklist.json', 'w') as f:
                await f.write(json.dumps(self.blacklist, indent=4))
        except Exception as e:
            logger.error(f"Error saving blacklist: {e}")
    
    def is_owner(self, user_id: int) -> bool:
        """Check if user is bot owner"""
        return user_id == self.config.get('OWNER_ID')
    
    def is_admin(self, user_id: int, roles) -> bool:
        """Check if user is admin"""
        if self.is_owner(user_id):
            return True
        admin_role_id = self.config.get('ADMIN_ROLE_ID')
        if admin_role_id and any(role.id == admin_role_id for role in roles):
            return True
        return False
    
    def is_support(self, user_id: int, roles) -> bool:
        """Check if user is support staff"""
        support_role_id = self.config.get('SUPPORT_ROLE_ID')
        if support_role_id and any(role.id == support_role_id for role in roles):
            return True
        return False
    
    def is_blacklisted(self, user_id: int) -> bool:
        """Check if user is blacklisted"""
        return user_id in self.blacklist.get("members", [])
    
    async def create_ticket_panel(self, channel: discord.TextChannel):
        """Create ticket panel embed"""
        try:
            config = self.config
            options = config.get('TICKET_OPTIONS', [])
            active_options = [opt for opt in options if opt.get('name') not in self.removed_options]
            
            embed = discord.Embed(
                title=config.get('PANEL_TITLE', 'Ticket Bot'),
                description=config.get('PANEL_DESCRIPTION', 'Open ticket to buy'),
                color=discord.Color.from_rgb(
                    config.get('EMBED_COLOR_R', 0),
                    config.get('EMBED_COLOR_G', 100),
                    config.get('EMBED_COLOR_B', 255)
                )
            )
            
            if config.get('PANEL_IMAGE'):
                embed.set_image(url=config.get('PANEL_IMAGE'))
            if config.get('PANEL_THUMBNAIL'):
                embed.set_thumbnail(url=config.get('PANEL_THUMBNAIL'))
            
            embed.set_footer(
                text=config.get('PANEL_FOOTER', 'Programed By Subhan'),
                icon_url=config.get('PANEL_FOOTER_IMAGE')
            )
            
            select_options = []
            for option in active_options:
                emoji = option.get('emoji', '')
                label = option.get('name', 'Unknown')
                description = option.get('description', 'Open a ticket')
                
                select_option = discord.SelectOption(
                    label=label[:100],
                    value=option.get('name'),
                    description=description[:100] if description else None,
                    emoji=emoji if emoji else None
                )
                select_options.append(select_option)
            
            if not select_options:
                select_options.append(discord.SelectOption(label="No options available", value="none"))
            
            view = discord.ui.View(timeout=None)
            
            select = discord.ui.Select(
                placeholder="Select ticket type",
                min_values=1,
                max_values=1,
                options=select_options,
                custom_id="ticket_select"
            )
            
            async def select_callback(interaction: discord.Interaction):
                await self.handle_ticket_select(interaction)
            
            select.callback = select_callback
            view.add_item(select)
            
            await channel.send(embed=embed, view=view)
            return True
        except Exception as e:
            logger.error(f"Error creating ticket panel: {e}\n{traceback.format_exc()}")
            return False
    
    async def handle_ticket_select(self, interaction: discord.Interaction):
        """Handle ticket selection"""
        try:
            await interaction.response.defer(thinking=True)
            
            # Check blacklist
            if self.is_blacklisted(interaction.user.id):
                embed = discord.Embed(
                    title="❌ Blacklisted",
                    description="You are blacklisted and cannot open tickets.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            selected_option = interaction.data['values'][0]
            option_config = None
            
            for opt in self.config.get('TICKET_OPTIONS', []):
                if opt.get('name') == selected_option:
                    option_config = opt
                    break
            
            if not option_config:
                await interaction.followup.send("Option not found!", ephemeral=True)
                return
            
            # Check support role access
            if self.is_support(interaction.user.id, interaction.user.roles):
                support_categories = option_config.get('support', [])
                if support_categories and option_config.get('category_id') not in support_categories:
                    embed = discord.Embed(
                        title="❌ Access Denied",
                        description="You don't have access to this ticket category.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            category_id = option_config.get('category_id')
            if not category_id:
                await interaction.followup.send("Category not configured!", ephemeral=True)
                return
            
            category = interaction.guild.get_channel(category_id)
            if not category:
                await interaction.followup.send("Category not found!", ephemeral=True)
                return
            
            # Generate ticket number
            ticket_number = self.get_next_ticket_number()
            channel_name = f"🎫-ticket-{ticket_number}"
            
            # Create ticket channel
            ticket_channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                reason=f"Ticket opened by {interaction.user}"
            )
            
            # Set permissions
            await ticket_channel.set_permissions(interaction.guild.default_role, view_channel=False)
            await ticket_channel.set_permissions(interaction.user, view_channel=True)
            
            # Add support role permissions if configured
            if option_config.get('support'):
                support_role_id = self.config.get('SUPPORT_ROLE_ID')
                if support_role_id:
                    support_role = interaction.guild.get_role(support_role_id)
                    if support_role:
                        await ticket_channel.set_permissions(support_role, view_channel=True)
            
            # Create ticket embed
            embed = discord.Embed(
                title=f"🎫 Ticket #{ticket_number}",
                description=f"{interaction.user.mention}\n\n**Ticket Type:** {selected_option}\n**Opened:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                color=discord.Color.from_rgb(
                    self.config.get('EMBED_COLOR_R', 0),
                    self.config.get('EMBED_COLOR_G', 100),
                    self.config.get('EMBED_COLOR_B', 255)
                )
            )
            
            embed.add_field(name="User", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
            embed.add_field(name="Category", value=selected_option, inline=False)
            
            if self.config.get('TICKET_IMAGE'):
                embed.set_image(url=self.config.get('TICKET_IMAGE'))
            if self.config.get('TICKET_THUMBNAIL'):
                embed.set_thumbnail(url=self.config.get('TICKET_THUMBNAIL'))
            
            embed.set_footer(
                text=self.config.get('PANEL_FOOTER', 'Programed By Subhan'),
                icon_url=self.config.get('PANEL_FOOTER_IMAGE')
            )
            
            # Create close button
            view = discord.ui.View(timeout=None)
            
            async def close_callback(button_interaction: discord.Interaction):
                await self.close_ticket(button_interaction, ticket_channel, interaction.user, selected_option)
            
            close_button = discord.ui.Button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id=f"close_ticket_{ticket_channel.id}")
            close_button.callback = close_callback
            view.add_item(close_button)
            
            await ticket_channel.send(embed=embed, view=view)
            
            # Save ticket data
            self.tickets_data[str(ticket_channel.id)] = {
                "number": ticket_number,
                "user_id": interaction.user.id,
                "user_name": str(interaction.user),
                "category": selected_option,
                "opened_at": datetime.now().isoformat(),
                "channel_id": ticket_channel.id
            }
            await self.save_tickets_data()
            
            # Log ticket open
            await self.log_ticket_action(interaction.guild, f"✅ Ticket #{ticket_number} opened by {interaction.user.mention}", discord.Color.green())
            
            embed = discord.Embed(
                title="✅ Ticket Created",
                description=f"Your ticket has been created: {ticket_channel.mention}",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error handling ticket select: {e}\n{traceback.format_exc()}")
            try:
                embed = discord.Embed(
                    title="❌ Error",
                    description="An error occurred while creating your ticket. Please try again later.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass
    
    async def close_ticket(self, interaction: discord.Interaction, ticket_channel: discord.TextChannel, ticket_user: discord.User, ticket_type: str):
        """Close a ticket"""
        try:
            await interaction.response.defer()
            
            ticket_id = str(ticket_channel.id)
            if ticket_id not in self.tickets_data:
                await interaction.followup.send("Ticket data not found!", ephemeral=True)
                return
            
            ticket_data = self.tickets_data[ticket_id]
            
            # Create closed ticket embed
            embed = discord.Embed(
                title="🎫 Ticket Closed",
                description=f"Your ticket has been closed.",
                color=discord.Color.from_rgb(
                    self.config.get('EMBED_COLOR_R', 0),
                    self.config.get('EMBED_COLOR_G', 100),
                    self.config.get('EMBED_COLOR_B', 255)
                )
            )
            
            embed.add_field(name="Ticket Number", value=f"#{ticket_data['number']}", inline=True)
            embed.add_field(name="Type", value=ticket_type, inline=True)
            embed.add_field(name="Opened", value=ticket_data['opened_at'], inline=False)
            embed.add_field(name="Closed", value=datetime.now().isoformat(), inline=False)
            embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
            
            embed.set_footer(
                text=self.config.get('PANEL_FOOTER', 'Programed By Subhan'),
                icon_url=self.config.get('PANEL_FOOTER_IMAGE')
            )
            
            # Send to ticket user DM with rating
            try:
                rating_view = discord.ui.View(timeout=None)
                
                async def rate_callback(rate_interaction: discord.Interaction):
                    await self.handle_rating(rate_interaction, ticket_data)
                
                for i in range(1, 6):
                    button = discord.ui.Button(label="⭐" * i, style=discord.ButtonStyle.primary, custom_id=f"rate_{i}")
                    button.callback = rate_callback
                    rating_view.add_item(button)
                
                await ticket_user.send(embed=embed, view=rating_view)
            except Exception as e:
                logger.warning(f"Could not send DM to {ticket_user}: {e}")
            
            # Log ticket close
            await self.log_ticket_action(
                interaction.guild,
                f"🔒 Ticket #{ticket_data['number']} closed by {interaction.user.mention}",
                discord.Color.orange()
            )
            
            # Delete ticket data
            del self.tickets_data[ticket_id]
            await self.save_tickets_data()
            
            # Delete channel
            await ticket_channel.delete(reason=f"Ticket closed by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error closing ticket: {e}\n{traceback.format_exc()}")
            try:
                await interaction.followup.send("An error occurred while closing the ticket.", ephemeral=True)
            except:
                pass
    
    async def handle_rating(self, interaction: discord.Interaction, ticket_data: dict):
        """Handle ticket rating"""
        try:
            await interaction.response.defer()
            
            rating = interaction.data['custom_id'].split('_')[1]
            
            # Get guild and send rating to log channel
            guild = self.bot.get_guild(interaction.guild.id) if interaction.guild else None
            if guild:
                log_channel_id = self.config.get('LOG_CHANNEL_ID')
                if log_channel_id:
                    log_channel = guild.get_channel(log_channel_id)
                    if log_channel:
                        embed = discord.Embed(
                            title="⭐ Ticket Rating",
                            description=f"Ticket #{ticket_data['number']} rated {rating} stars",
                            color=discord.Color.gold()
                        )
                        embed.add_field(name="User", value=f"<@{ticket_data['user_id']}>", inline=False)
                        embed.add_field(name="Category", value=ticket_data['category'], inline=False)
                        embed.add_field(name="Rating", value="⭐" * int(rating), inline=False)
                        embed.set_footer(
                            text=self.config.get('PANEL_FOOTER', 'Programed By Subhan'),
                            icon_url=self.config.get('PANEL_FOOTER_IMAGE')
                        )
                        
                        try:
                            await log_channel.send(embed=embed)
                        except Exception as e:
                            logger.error(f"Error sending rating to log channel: {e}")
            
            await interaction.followup.send("Thank you for your rating!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error handling rating: {e}\n{traceback.format_exc()}")
    
    async def log_ticket_action(self, guild: discord.Guild, message: str, color: discord.Color):
        """Log ticket action to log channel"""
        try:
            log_channel_id = self.config.get('LOG_CHANNEL_ID')
            if not log_channel_id:
                return
            
            log_channel = guild.get_channel(log_channel_id)
            if not log_channel:
                return
            
            embed = discord.Embed(
                title="🎫 Ticket Log",
                description=message,
                color=color,
                timestamp=datetime.now()
            )
            embed.set_footer(
                text=self.config.get('PANEL_FOOTER', 'Programed By Subhan'),
                icon_url=self.config.get('PANEL_FOOTER_IMAGE')
            )
            
            await log_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging ticket action: {e}")
    
    def get_next_ticket_number(self) -> int:
        """Get next ticket number"""
        if not self.tickets_data:
            return 1
        numbers = [data.get('number', 0) for data in self.tickets_data.values()]
        return max(numbers) + 1 if numbers else 1
    
    @app_commands.command(name="ticketpanel", description="Load ticket panel in channel")
    @app_commands.describe(channel="Channel to load panel in")
    async def ticketpanel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Load ticket panel"""
        try:
            if not self.is_admin(interaction.user.id, interaction.user.roles):
                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="Only admins can use this command.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.response.defer()
            
            success = await self.create_ticket_panel(channel)
            
            if success:
                embed = discord.Embed(
                    title="✅ Panel Created",
                    description=f"Ticket panel loaded in {channel.mention}",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to create ticket panel.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in ticketpanel command: {e}\n{traceback.format_exc()}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)[:100]}",
                color=discord.Color.red()
            )
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="addnewoption", description="Add new ticket option")
    @app_commands.describe(
        label="Option label",
        description="Option description",
        category_id="Category ID",
        emoji="Emoji (optional)",
        support_roles="Support role IDs (comma-separated, optional)"
    )
    async def addnewoption(self, interaction: discord.Interaction, label: str, description: str, category_id: str, emoji: Optional[str] = None, support_roles: Optional[str] = None):
        """Add new ticket option"""
        try:
            if not self.is_owner(interaction.user.id):
                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="Only the bot owner can use this command.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.response.defer()
            
            try:
                category_id_int = int(category_id)
            except ValueError:
                embed = discord.Embed(
                    title="❌ Invalid Category ID",
                    description="Category ID must be a valid number.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            new_option = {
                "name": label,
                "description": description,
                "category_id": category_id_int,
                "emoji": emoji if emoji else "",
                "support": [] if not support_roles else [int(x.strip()) for x in support_roles.split(',')]
            }
            
            self.config['TICKET_OPTIONS'].append(new_option)
            
            with open('config.json', 'w') as f:
                json.dump(self.config, f, indent=4)
            
            embed = discord.Embed(
                title="✅ Option Added",
                description=f"New ticket option '{label}' has been added.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in addnewoption command: {e}\n{traceback.format_exc()}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)[:100]}",
                color=discord.Color.red()
            )
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass
    
    @app_commands.command(name="removeoption", description="Temporarily remove ticket option")
    async def removeoption(self, interaction: discord.Interaction):
        """Remove ticket option"""
        try:
            if not self.is_owner(interaction.user.id):
                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="Only the bot owner can use this command.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.response.defer()
            
            options = self.config.get('TICKET_OPTIONS', [])
            if not options:
                embed = discord.Embed(
                    title="❌ No Options",
                    description="There are no ticket options to remove.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            select_options = []
            for i, opt in enumerate(options):
                select_options.append(discord.SelectOption(
                    label=opt.get('name', 'Unknown')[:100],
                    value=str(i),
                    description=opt.get('description', 'No description')[:100]
                ))
            
            view = discord.ui.View(timeout=60)
            
            async def select_callback(select_interaction: discord.Interaction):
                try:
                    index = int(select_interaction.data['values'][0])
                    option_name = options[index].get('name')
                    
                    self.removed_options[option_name] = True
                    await self.save_removed_options()
                    
                    embed = discord.Embed(
                        title="✅ Option Removed",
                        description=f"Option '{option_name}' has been temporarily removed.",
                        color=discord.Color.green()
                    )
                    await select_interaction.response.send_message(embed=embed, ephemeral=True)
                except Exception as e:
                    logger.error(f"Error in removeoption select: {e}")
                    await select_interaction.response.send_message("An error occurred.", ephemeral=True)
            
            select = discord.ui.Select(
                placeholder="Select option to remove",
                options=select_options,
                custom_id="remove_option_select"
            )
            select.callback = select_callback
            view.add_item(select)
            
            embed = discord.Embed(
                title="🗑️ Remove Option",
                description="Select an option to temporarily remove:",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in removeoption command: {e}\n{traceback.format_exc()}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)[:100]}",
                color=discord.Color.red()
            )
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass
    
    @app_commands.command(name="add_temp_option", description="Re-add temporarily removed option")
    async def add_temp_option(self, interaction: discord.Interaction):
        """Re-add removed option"""
        try:
            if not self.is_owner(interaction.user.id):
                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="Only the bot owner can use this command.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.response.defer()
            
            if not self.removed_options:
                embed = discord.Embed(
                    title="❌ No Removed Options",
                    description="There are no removed options to restore.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            select_options = [
                discord.SelectOption(label=name, value=name)
                for name in self.removed_options.keys()
            ]
            
            view = discord.ui.View(timeout=60)
            
            async def select_callback(select_interaction: discord.Interaction):
                try:
                    option_name = select_interaction.data['values'][0]
                    del self.removed_options[option_name]
                    await self.save_removed_options()
                    
                    embed = discord.Embed(
                        title="✅ Option Restored",
                        description=f"Option '{option_name}' has been restored.",
                        color=discord.Color.green()
                    )
                    await select_interaction.response.send_message(embed=embed, ephemeral=True)
                except Exception as e:
                    logger.error(f"Error in add_temp_option select: {e}")
                    await select_interaction.response.send_message("An error occurred.", ephemeral=True)
            
            select = discord.ui.Select(
                placeholder="Select option to restore",
                options=select_options,
                custom_id="restore_option_select"
            )
            select.callback = select_callback
            view.add_item(select)
            
            embed = discord.Embed(
                title="♻️ Restore Option",
                description="Select an option to restore:",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in add_temp_option command: {e}\n{traceback.format_exc()}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)[:100]}",
                color=discord.Color.red()
            )
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass
    
    @app_commands.command(name="stats", description="Show bot statistics")
    async def ticket_stats(self, interaction: discord.Interaction):
        """Show bot statistics"""
        try:
            if not self.is_admin(interaction.user.id, interaction.user.roles):
                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="Only admins can use this command.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.response.defer()
            
            embed = discord.Embed(
                title="📊 Bot Statistics",
                color=discord.Color.from_rgb(0, 100, 255)
            )
            
            embed.add_field(name="👑 Owner", value=f"<@{self.config.get('OWNER_ID')}>", inline=False)
            embed.add_field(name="👮 Admin Role", value=f"<@&{self.config.get('ADMIN_ROLE_ID', 'Not set')}>", inline=False)
            embed.add_field(name="🆘 Support Role", value=f"<@&{self.config.get('SUPPORT_ROLE_ID', 'Not set')}>", inline=False)
            embed.add_field(name="📝 Ticket Options", value=str(len(self.config.get('TICKET_OPTIONS', []))), inline=True)
            embed.add_field(name="🎫 Open Tickets", value=str(len(self.tickets_data)), inline=True)
            embed.add_field(name="🚫 Blacklisted Members", value=str(len(self.blacklist.get('members', []))), inline=True)
            embed.add_field(name="⏱️ Bot Ping", value=f"{round(self.bot.latency * 1000)}ms", inline=False)
            embed.add_field(name="📊 Status", value=self.config.get('BOT_STATUS', 'Online'), inline=False)
            embed.add_field(name="🎮 Activity", value=self.config.get('BOT_ACTIVITY', 'Ticket System'), inline=False)
            
            embed.set_footer(
                text=self.config.get('PANEL_FOOTER', 'Programed By Subhan'),
                icon_url=self.config.get('PANEL_FOOTER_IMAGE')
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in ticket_stats command: {e}\n{traceback.format_exc()}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)[:100]}",
                color=discord.Color.red()
            )
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass
    
    @app_commands.command(name="addblacklist", description="Add member to blacklist")
    @app_commands.describe(member_id="Member ID")
    async def addblacklist(self, interaction: discord.Interaction, member_id: str):
        """Add member to blacklist"""
        try:
            if not self.is_owner(interaction.user.id):
                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="Only the bot owner can use this command.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.response.defer()
            
            try:
                member_id_int = int(member_id)
            except ValueError:
                embed = discord.Embed(
                    title="❌ Invalid ID",
                    description="Member ID must be a valid number.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if member_id_int in self.blacklist.get('members', []):
                embed = discord.Embed(
                    title="⚠️ Already Blacklisted",
                    description="This member is already blacklisted.",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if 'members' not in self.blacklist:
                self.blacklist['members'] = []
            
            self.blacklist['members'].append(member_id_int)
            await self.save_blacklist()
            
            embed = discord.Embed(
                title="✅ Blacklisted",
                description=f"Member {member_id} has been blacklisted.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in addblacklist command: {e}\n{traceback.format_exc()}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)[:100]}",
                color=discord.Color.red()
            )
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass
    
    @app_commands.command(name="help", description="Show all commands and guide")
    async def help(self, interaction: discord.Interaction):
        """Show help"""
        try:
            await interaction.response.defer()
            
            embed = discord.Embed(
                title="📖 Ticket Bot Help",
                description="Complete guide to all available commands",
                color=discord.Color.from_rgb(0, 100, 255)
            )
            
            embed.add_field(
                name="/ticketpanel",
                value="Load ticket panel in a channel (Admin only)",
                inline=False
            )
            embed.add_field(
                name="/addnewoption",
                value="Add new ticket option (Owner only)",
                inline=False
            )
            embed.add_field(
                name="/removeoption",
                value="Temporarily remove a ticket option (Owner only)",
                inline=False
            )
            embed.add_field(
                name="/add_temp_option",
                value="Restore a temporarily removed option (Owner only)",
                inline=False
            )
            embed.add_field(
                name="/stats",
                value="Show bot statistics and configuration (Admin only)",
                inline=False
            )
            embed.add_field(
                name="/addblacklist",
                value="Add a member to blacklist (Owner only)",
                inline=False
            )
            embed.add_field(
                name="/help",
                value="Show this help message",
                inline=False
            )
            
            embed.set_footer(
                text=self.config.get('PANEL_FOOTER', 'Programed By Subhan'),
                icon_url=self.config.get('PANEL_FOOTER_IMAGE')
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in help command: {e}\n{traceback.format_exc()}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)[:100]}",
                color=discord.Color.red()
            )
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Delete ticket if member leaves"""
        try:
            tickets_to_delete = []
            for ticket_id, ticket_data in self.tickets_data.items():
                if ticket_data['user_id'] == member.id:
                    tickets_to_delete.append((ticket_id, ticket_data))
            
            for ticket_id, ticket_data in tickets_to_delete:
                try:
                    channel = member.guild.get_channel(int(ticket_id))
                    if channel:
                        await channel.delete(reason=f"Ticket user {member} left the server")
                    
                    del self.tickets_data[ticket_id]
                    await self.log_ticket_action(
                        member.guild,
                        f"🚪 Ticket #{ticket_data['number']} deleted - User left server",
                        discord.Color.red()
                    )
                except Exception as e:
                    logger.error(f"Error deleting ticket: {e}")
            
            await self.save_tickets_data()
        except Exception as e:
            logger.error(f"Error in on_member_remove: {e}")

class TicketBotMain(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        
        super().__init__(command_prefix="!", intents=intents)
        self.config = load_config()
    
    async def setup_hook(self):
        """Setup bot"""
        try:
            await self.add_cog(TicketBot(self))
            await self.tree.sync()
            logger.info("Bot setup completed")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}\n{traceback.format_exc()}")
    
    async def on_ready(self):
        """Bot ready"""
        try:
            logger.info(f"Bot logged in as {self.user}")
            
            activity_text = self.config.get('BOT_ACTIVITY', 'Ticket System')
            await self.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name=activity_text)
            )
        except Exception as e:
            logger.error(f"Error in on_ready: {e}")
    
    async def on_error(self, event, *args, **kwargs):
        """Handle errors"""
        logger.error(f"Error in {event}: {traceback.format_exc()}")

def main():
    """Main function"""
    try:
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            logger.error("DISCORD_TOKEN not found in .env file")
            return
        
        bot = TicketBotMain()
        bot.run(token)
    except Exception as e:
        logger.error(f"Error in main: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
