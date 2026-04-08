import discord
from discord.ext import commands
from typing import Dict, Optional
from datetime import datetime
from .database import Database
from .embed_builder import EmbedBuilder
from .logger import logger

class TicketManager:
    def __init__(self, bot: commands.Bot, db: Database, embed_builder: EmbedBuilder, config: Dict):
        self.bot = bot
        self.db = db
        self.embed_builder = embed_builder
        self.config = config
        self.active_tickets = {}
    
    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str, option_data: Dict):
        """Create a new ticket"""
        try:
            # Check blacklist
            if await self.db.is_blacklisted(interaction.user.id):
                await interaction.response.send_message("You are blacklisted from creating tickets!", ephemeral=True)
                return
            
            # Check rate limits
            user_tickets = [t for t in (await self.db.get_all_tickets()).values() if t['user_id'] == interaction.user.id and t['status'] == 'open']
            if len(user_tickets) >= self.config["rate_limits"]["max_tickets_per_user"]:
                await interaction.response.send_message(f"You can only have {self.config['rate_limits']['max_tickets_per_user']} open tickets at a time!", ephemeral=True)
                return
            
            # Get category
            category_id = option_data.get('category_id') or self.config["ticket_categories"].get(ticket_type, {}).get('category_id')
            if not category_id:
                await interaction.response.send_message("Category not configured for this ticket type!", ephemeral=True)
                return
            
            category = interaction.guild.get_channel(category_id)
            if not category:
                await interaction.response.send_message("Ticket category not found!", ephemeral=True)
                return
            
            # Get ticket number
            ticket_number = await self.db.get_next_ticket_number()
            
            # Create channel
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            }
            
            # Add support roles
            support_role_id = option_data.get('support_role_id') or self.config["ticket_categories"].get(ticket_type, {}).get('support_role_id')
            if support_role_id:
                support_role = interaction.guild.get_role(support_role_id)
                if support_role:
                    overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            
            # Add admin roles
            for admin_role_id in self.config["admin_roles"]:
                admin_role = interaction.guild.get_role(admin_role_id)
                if admin_role:
                    overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            
            channel = await interaction.guild.create_text_channel(
                name=f"🎫-ticket-{ticket_number}",
                category=category,
                overwrites=overwrites
            )
            
            # Send welcome message
            embed = self.embed_builder.create_ticket_embed(interaction.user, option_data['label'], ticket_number)
            view = TicketControls(self.bot, self.db, self.embed_builder, self.config)
            await channel.send(interaction.user.mention, embed=embed, view=view)
            
            # Mention everyone role (optional - can be configured)
            await channel.send(f"{interaction.guild.default_role.mention} New ticket created!")
            
            # Store ticket data
            ticket_data = {
                'id': channel.id,
                'number': ticket_number,
                'user_id': interaction.user.id,
                'type': option_data['label'],
                'category': ticket_type,
                'open_date': datetime.utcnow().isoformat(),
                'status': 'open',
                'channel_id': channel.id
            }
            
            await self.db.add_ticket(str(channel.id), ticket_data)
            
            # Send log
            await self.send_log(interaction.guild, "Opened", interaction.user, ticket_data)
            
            await interaction.response.send_message(f"Ticket created! {channel.mention}", ephemeral=True)
            logger.info(f"Ticket #{ticket_number} created by {interaction.user} in {interaction.guild.name}")
            
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await interaction.response.send_message("An error occurred while creating the ticket!", ephemeral=True)
    
    async def close_ticket(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Close a ticket"""
        try:
            ticket_data = await self.db.get_ticket(str(channel.id))
            if not ticket_data:
                await interaction.response.send_message("Ticket data not found!", ephemeral=True)
                return
            
            # Update ticket status
            await self.db.update_ticket(str(channel.id), {'status': 'closed', 'close_date': datetime.utcnow().isoformat(), 'closed_by': interaction.user.id})
            
            # Send DM with rating
            user = await self.bot.fetch_user(ticket_data['user_id'])
            embed = self.embed_builder.create_ticket_closed_embed(ticket_data, interaction.user)
            view = RatingView(self.bot, self.db, self.embed_builder, self.config, ticket_data['number'])
            
            try:
                await user.send(embed=embed, view=view)
            except discord.Forbidden:
                pass
            
            # Send log
            await self.send_log(interaction.guild, "Closed", interaction.user, ticket_data)
            
            # Delete channel
            await channel.delete()
            await self.db.remove_ticket(str(channel.id))
            
            await interaction.response.send_message("Ticket closed and channel deleted!", ephemeral=True)
            logger.info(f"Ticket #{ticket_data['number']} closed by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error closing ticket: {e}")
            await interaction.response.send_message("An error occurred while closing the ticket!", ephemeral=True)
    
    async def send_log(self, guild: discord.Guild, action: str, user: discord.User, ticket_data: Dict = None):
        """Send log to log channel"""
        log_channel_id = self.config.get("log_channel_id")
        if not log_channel_id:
            return
        
        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return
        
        embed = self.embed_builder.create_log_embed(action, user, ticket_data)
        await log_channel.send(embed=embed)
    
    async def check_member_left(self, member: discord.Member):
        """Check if member left and close their tickets"""
        tickets = await self.db.get_all_tickets()
        for ticket_id, ticket_data in tickets.items():
            if ticket_data['user_id'] == member.id and ticket_data['status'] == 'open':
                channel = member.guild.get_channel(int(ticket_id))
                if channel:
                    await self.close_ticket_on_leave(channel, member)
    
    async def close_ticket_on_leave(self, channel: discord.TextChannel, member: discord.Member):
        """Close ticket when member leaves"""
        try:
            ticket_data = await self.db.get_ticket(str(channel.id))
            if ticket_data:
                await self.db.update_ticket(str(channel.id), {'status': 'closed', 'close_date': datetime.utcnow().isoformat(), 'closed_by': 'System (User Left)'})
                await self.send_log(member.guild, "Auto-Closed (User Left)", member, ticket_data)
                await channel.delete()
                await self.db.remove_ticket(str(channel.id))
                logger.info(f"Ticket #{ticket_data['number']} auto-closed because {member} left")
        except Exception as e:
            logger.error(f"Error auto-closing ticket: {e}")

class TicketControls(discord.ui.View):
    def __init__(self, bot: commands.Bot, db: Database, embed_builder: EmbedBuilder, config: Dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.db = db
        self.embed_builder = embed_builder
        self.config = config
    
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_manager = TicketManager(self.bot, self.db, self.embed_builder, self.config)
        await ticket_manager.close_ticket(interaction, interaction.channel)

class RatingView(discord.ui.View):
    def __init__(self, bot: commands.Bot, db: Database, embed_builder: EmbedBuilder, config: Dict, ticket_number: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.db = db
        self.embed_builder = embed_builder
        self.config = config
        self.ticket_number = ticket_number
    
    @discord.ui.button(label="⭐", style=discord.ButtonStyle.secondary, custom_id="rate_1")
    async def rate_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.submit_rating(interaction, 1)
    
    @discord.ui.button(label="⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rate_2")
    async def rate_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.submit_rating(interaction, 2)
    
    @discord.ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rate_3")
    async def rate_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.submit_rating(interaction, 3)
    
    @discord.ui.button(label="⭐⭐⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rate_4")
    async def rate_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.submit_rating(interaction, 4)
    
    @discord.ui.button(label="⭐⭐⭐⭐⭐", style=discord.ButtonStyle.success, custom_id="rate_5")
    async def rate_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.submit_rating(interaction, 5)
    
    async def submit_rating(self, interaction: discord.Interaction, rating: int):
        rating_channel_id = self.config.get("rating_channel_id")
        if rating_channel_id:
            channel = interaction.guild.get_channel(rating_channel_id)
            if channel:
                embed = self.embed_builder.create_rating_embed(interaction.user, self.ticket_number, rating)
                await channel.send(embed=embed)
        
        await interaction.response.send_message(f"Thank you for rating {rating}/5 stars! 🌟", ephemeral=True)
        self.stop()
