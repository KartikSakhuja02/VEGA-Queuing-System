import discord
from discord import app_commands
from discord.ext import commands
import os
import traceback
from dotenv import load_dotenv
import time
import asyncio
from database import db

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')  # Optional: for faster command sync during development

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class VegaAssassinsBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.start_time = time.time()
    
    async def setup_hook(self):
        """This is called when the bot starts up"""
        # Connect to database (failure is non-fatal — cogs still load)
        try:
            await db.connect()
            await db.initialize_schema()
            print("✅ Database connected and schema initialised")
        except Exception as e:
            tb = ''.join(traceback.format_exc())
            print(f"❌ Database connection failed — bot will start without DB:\n{tb}")
        
        # Load cogs (always, even if DB is down)
        await self.load_cogs()
        
        # Sync slash commands to the guild immediately (guild sync is instant;
        # global sync can take up to 1 hour so we always prefer guild sync)
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"✅ Commands synced to guild {GUILD_ID}")
        else:
            await self.tree.sync()
            print("✅ Commands synced globally (may take up to 1 hour to propagate)")
    
    async def load_cogs(self):
        """Load all cogs from the cogs directory"""
        cogs = ['cogs.skrimmish', 'cogs.verification']
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"✅ Loaded cog: {cog}")
            except Exception as e:
                print(f"❌ Failed to load cog {cog}: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready"""
        print(f'🤖 {self.user} has connected to Discord!')
        print(f'📊 Bot is in {len(self.guilds)} guilds')
        print('------')
    
    async def close(self):
        """Cleanup when bot is shutting down"""
        await db.disconnect()
        await super().close()

# Initialize bot
bot = VegaAssassinsBot()

# Error handler
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"Command is on cooldown. Try again in {error.retry_after:.2f}s", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
    else:
        # Log the full traceback so it appears in journalctl
        tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        print(f"Unhandled command error in /{interaction.command.name if interaction.command else '?'}:\n{tb}")
        msg = f"An error occurred: `{error}`"
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
        except Exception:
            pass

# Run the bot
if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not found in .env file!")
    else:
        bot.run(TOKEN)


