from discord.ext import commands
import discord
from typing import Optional

class ExtraCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='ticketpanel')
    @commands.has_permissions(administrator=True)
    async def prefix_ticketpanel(self, ctx):
        """Load ticket panel using prefix"""
        await ctx.invoke(self.bot.get_command('ticketpanel'))

async def setup(bot):
    await bot.add_cog(ExtraCommands(bot))
