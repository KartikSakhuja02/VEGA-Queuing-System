import discord
from discord import app_commands
from discord.ext import commands
import os

BRAND_NAME = "VEGA Assassins Matchmaking"
VERIFICATION_BANNER_CANDIDATES = ["Vega Banner.jpg", "valm_india_banner.jpg"]
VERIFICATION_LOGO_CANDIDATES = ["Vega Logo.jpg", "LOGO.jpeg"]


def resolve_gfx_path(candidates: list[str]) -> str | None:
    gfx_dir = os.path.join(os.getcwd(), "GFX")
    for filename in candidates:
        path = os.path.join(gfx_dir, filename)
        if os.path.exists(path):
            return path
    return None

class VerificationButton(discord.ui.Button):
    """Persistent button for verification"""
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Verify Access",
            custom_id="verification_button"  # Persistent ID
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle verification button click"""
        # Get role ID from environment
        role_id = int(os.getenv('VERIFICATION_ROLE_ID'))
        role = interaction.guild.get_role(role_id)
        
        if not role:
            await interaction.response.send_message(
                "Verification role not found. Please contact an admin.",
                ephemeral=True
            )
            return
        
        # Check if user already has the role
        if role in interaction.user.roles:
            await interaction.response.send_message(
                "You are already verified and have access to matchmaking.",
                ephemeral=True
            )
            return
        
        # Assign the role
        try:
            await interaction.user.add_roles(role)
            embed = discord.Embed(
                title="Verification Complete",
                description=(
                    f"Welcome to **{BRAND_NAME}**.\n\n"
                    f"You now have the {role.mention} role and can participate in scrimmage matchmaking.\n\n"
                    "Next Steps:\n"
                    "- Register your IGN with `/ign <your_name>`\n"
                    "- Open the queue channel and select Join Queue"
                ),
                color=0xED4245
            )
            embed.set_footer(text=f"{BRAND_NAME} • Competitive Matchmaking")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I do not have permission to assign roles. Please contact an admin.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

class VerificationView(discord.ui.View):
    """Persistent view for verification"""
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view - never times out
        self.add_item(VerificationButton())

class VerificationCog(commands.Cog):
    """Cog for handling matchmaking verification"""
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Add persistent view when bot starts"""
        # Register the persistent view
        self.bot.add_view(VerificationView())
        print("✅ Verification view registered")
    
    @app_commands.command(name="setup_verification", description="Setup verification UI in this channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_verification(self, interaction: discord.Interaction):
        """Setup the verification UI"""
        # Get verification role and channel from environment
        role_id = os.getenv('VERIFICATION_ROLE_ID')
        channel_id = os.getenv('VERIFICATION_CHANNEL_ID')
        
        if not role_id or not channel_id:
            await interaction.response.send_message(
                "Please configure VERIFICATION_ROLE_ID and VERIFICATION_CHANNEL_ID in the .env file first.",
                ephemeral=True
            )
            return
        
        role = interaction.guild.get_role(int(role_id))
        if not role:
            await interaction.response.send_message(
                "Verification role not found. Please check VERIFICATION_ROLE_ID in .env.",
                ephemeral=True
            )
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"{BRAND_NAME} Verification",
            description=(
                f"Welcome to **{BRAND_NAME}**.\n\n"
                "Verify to unlock competitive matchmaking, track performance, "
                "and appear on the persistent leaderboard.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "What You Get:\n"
                f"- {role.mention} role\n"
                "- Access to ranked scrimmage matches\n"
                "- Player stats tracking (wins, losses, MMR)\n"
                "- Leaderboard ranking\n"
                "- Match history and progression\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Select Verify Access below to continue."
            ),
            color=0xED4245
        )

        files = []
        banner_path = resolve_gfx_path(VERIFICATION_BANNER_CANDIDATES)
        if banner_path:
            files.append(discord.File(banner_path, filename="vega_verification_banner.jpg"))
            embed.set_image(url="attachment://vega_verification_banner.jpg")

        logo_path = resolve_gfx_path(VERIFICATION_LOGO_CANDIDATES)
        if logo_path:
            files.append(discord.File(logo_path, filename="vega_verification_logo.jpg"))
            embed.set_thumbnail(url="attachment://vega_verification_logo.jpg")
        elif interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.set_footer(
            text=f"{BRAND_NAME} • Competitive Matchmaking",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        # Send the verification message
        view = VerificationView()
        await interaction.channel.send(embed=embed, view=view, files=files)
        
        await interaction.response.send_message(
            "Verification UI has been posted.",
            ephemeral=True
        )
    
    @setup_verification.error
    async def setup_verification_error(self, interaction: discord.Interaction, error):
        """Handle setup verification errors"""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You need Administrator permissions to use this command.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(VerificationCog(bot))
