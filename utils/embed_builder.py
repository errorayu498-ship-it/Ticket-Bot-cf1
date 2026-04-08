import discord
from typing import Dict, Optional
from datetime import datetime

class EmbedBuilder:
    def __init__(self, config: Dict):
        self.config = config
    
    def create_ticket_panel(self) -> discord.Embed:
        """Create ticket panel embed"""
        embed_settings = self.config["embed_settings"]
        embed = discord.Embed(
            title=embed_settings["title"],
            description=embed_settings["description"],
            color=embed_settings["color"],
            timestamp=datetime.utcnow()
        )
        
        if embed_settings.get("thumbnail_url"):
            embed.set_thumbnail(url=embed_settings["thumbnail_url"])
        
        if embed_settings.get("image_url"):
            embed.set_image(url=embed_settings["image_url"])
        
        if embed_settings.get("footer_text"):
            embed.set_footer(
                text=embed_settings["footer_text"],
                icon_url=embed_settings.get("footer_icon")
            )
        
        return embed
    
    def create_ticket_embed(self, user: discord.User, ticket_type: str, ticket_number: int) -> discord.Embed:
        """Create ticket channel embed"""
        embed = discord.Embed(
            title=f"Ticket #{ticket_number}",
            description=f"Welcome {user.mention}! Support team will assist you shortly.",
            color=self.config["embed_settings"]["color"],
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Ticket Opener", value=user.mention, inline=True)
        embed.add_field(name="Ticket Type", value=ticket_type, inline=True)
        embed.add_field(name="Ticket Number", value=f"#{ticket_number}", inline=True)
        embed.add_field(name="Open Date", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        
        embed.set_footer(
            text=self.config["embed_settings"]["footer_text"],
            icon_url=self.config["embed_settings"].get("footer_icon")
        )
        
        return embed
    
    def create_ticket_closed_embed(self, ticket_data: Dict, closed_by: discord.User) -> discord.Embed:
        """Create ticket closed embed for DM"""
        embed = discord.Embed(
            title="Ticket Closed",
            description=f"Your ticket #{ticket_data['number']} has been closed.",
            color=self.config["embed_settings"]["closed_color"],
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Ticket Type", value=ticket_data['type'], inline=True)
        embed.add_field(name="Closed By", value=closed_by.mention, inline=True)
        embed.add_field(name="Open Date", value=ticket_data['open_date'], inline=False)
        embed.add_field(name="Close Date", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        
        embed.set_footer(
            text=self.config["embed_settings"]["footer_text"],
            icon_url=self.config["embed_settings"].get("footer_icon")
        )
        
        return embed
    
    def create_log_embed(self, action: str, user: discord.User, ticket_data: Dict = None, **kwargs) -> discord.Embed:
        """Create log embed"""
        embed = discord.Embed(
            title=f"Ticket {action}",
            color=0x00ff00 if action == "Opened" else 0xff0000,
            timestamp=datetime.utcnow()
        )
        
        if ticket_data:
            embed.add_field(name="Ticket Number", value=f"#{ticket_data['number']}", inline=True)
            embed.add_field(name="Ticket Type", value=ticket_data['type'], inline=True)
            embed.add_field(name="Opened By", value=f"{user.mention} ({user.id})", inline=False)
        
        if kwargs:
            for key, value in kwargs.items():
                embed.add_field(name=key.replace('_', ' ').title(), value=value, inline=False)
        
        embed.set_footer(text=self.config["embed_settings"]["footer_text"])
        
        return embed
    
    def create_rating_embed(self, user: discord.User, ticket_number: int, rating: int) -> discord.Embed:
        """Create rating embed"""
        embed = discord.Embed(
            title="Ticket Rating Submitted",
            description=f"User {user.mention} has rated their experience",
            color=self.config["embed_settings"]["color"],
            timestamp=datetime.utcnow()
        )
        
        stars = "⭐" * rating + "☆" * (5 - rating)
        embed.add_field(name="Ticket Number", value=f"#{ticket_number}", inline=True)
        embed.add_field(name="Rating", value=f"{stars} ({rating}/5)", inline=True)
        
        return embed
