import base64
import io
import os
import re

import aiohttp
import discord
from discord.ext import commands

from database import db

try:
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

BRAND_NAME = "VEGA Assassins Matchmaking"


class VerificationCog(commands.Cog):
    """Screenshot-based verification with admin reaction approval."""

    def __init__(self, bot):
        self.bot = bot
        self.pending_submissions: dict[int, dict] = {}

    @staticmethod
    def _env_int(name: str) -> int | None:
        value = os.getenv(name)
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _verification_channel_id(self) -> int | None:
        return self._env_int("MM_VERIFICATION_CHANNEL_ID")

    def _matchmaking_role_id(self) -> int | None:
        return self._env_int("MATCHMAKING_VERIFIED_ROLE_ID")

    def _moderator_role_id(self) -> int | None:
        return self._env_int("MODERATOR_ROLE_ID")

    def _skrimmish_role_id(self) -> int | None:
        # Preferred key after rename: SKRIMMISH_VERIFIED_ROLE.
        # Keep legacy fallbacks for compatibility.
        return (
            self._env_int("SKRIMMISH_VERIFIED_ROLE")
            or self._env_int("SKRIMMISH_VERIFIED_ROLE_ID")
            or self._env_int("VERIFICATION_ROLE_ID")
        )

    def _logs_channel_id(self) -> int | None:
        return self._env_int("LOGS_CHANNEL_ID")

    def _ocr_logs_channel_id(self) -> int | None:
        # Dedicated OCR logs channel. Falls back to LOGS_CHANNEL_ID if not set.
        return self._env_int("OCR_LOGS_CHANNEL_ID") or self._logs_channel_id()

    async def _get_logs_channel(self, guild: discord.Guild):
        logs_channel_id = self._logs_channel_id()
        if not logs_channel_id:
            return None

        logs_channel = guild.get_channel(logs_channel_id)
        if logs_channel:
            return logs_channel

        try:
            return await self.bot.fetch_channel(logs_channel_id)
        except Exception:
            return None

    async def _send_log_message(self, guild: discord.Guild, content: str | None = None, embed: discord.Embed | None = None):
        logs_channel = await self._get_logs_channel(guild)
        if logs_channel:
            await logs_channel.send(content=content, embed=embed)

    async def _send_ocr_log_message(self, guild: discord.Guild, content: str | None = None, embed: discord.Embed | None = None):
        ocr_channel_id = self._ocr_logs_channel_id()
        if not ocr_channel_id:
            return

        ocr_channel = guild.get_channel(ocr_channel_id)
        if not ocr_channel:
            try:
                ocr_channel = await self.bot.fetch_channel(ocr_channel_id)
            except Exception:
                return

        await ocr_channel.send(content=content, embed=embed)

    def _can_review_submission(self, member: discord.Member) -> bool:
        permissions = member.guild_permissions
        if permissions.administrator:
            return True
        if permissions.manage_guild or permissions.manage_roles or permissions.moderate_members:
            return True

        moderator_role_id = self._moderator_role_id()
        if moderator_role_id and any(role.id == moderator_role_id for role in member.roles):
            return True

        return False

    async def _send_ocr_log(self, guild: discord.Guild, user: discord.Member | discord.User, ign: str | None, source_message_id: int):
        log_embed = discord.Embed(
            title="Matchmaking Verification OCR",
            color=0xED4245,
            description=(
                f"User: {user.mention}\n"
                f"Detected IGN: **{ign or 'Not detected'}**\n"
                f"Source Message ID: `{source_message_id}`"
            ),
        )
        log_embed.timestamp = discord.utils.utcnow()
        await self._send_ocr_log_message(guild, embed=log_embed)

    async def _extract_ign_from_attachment(self, attachment: discord.Attachment) -> str | None:
        if not OCR_AVAILABLE:
            return None

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None

        image_data = await attachment.read()
        image = Image.open(io.BytesIO(image_data))
        if image.mode != "RGB":
            image = image.convert("RGB")

        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        image_b64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")

        prompt = (
            "Extract the player's in-game name (IGN) from this screenshot. "
            "Return ONLY one line in this exact format: IGN: <name>."
        )

        url = (
            "https://generativelanguage.googleapis.com/v1/models/"
            f"gemini-2.5-flash:generateContent?key={api_key}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": image_b64,
                            }
                        },
                    ]
                }
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    return None
                result = await resp.json()

        try:
            result_text = result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return None

        ign_match = re.search(r"IGN\s*:\s*(.+)", result_text, re.IGNORECASE)
        ign = ign_match.group(1).strip() if ign_match else result_text.strip().splitlines()[0].strip()
        ign = ign.strip("`\"' ")

        if not ign or len(ign) > 64:
            return None
        return ign

    @commands.Cog.listener()
    async def on_ready(self):
        channel_id = self._verification_channel_id()
        if channel_id:
            print(f"✅ Screenshot verification enabled on channel {channel_id}")
        else:
            print("ℹ️ MM_VERIFICATION_CHANNEL_ID not configured; screenshot verification disabled")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        channel_id = self._verification_channel_id()
        if not channel_id or message.channel.id != channel_id:
            return

        image_attachment = next(
            (
                att
                for att in message.attachments
                if att.content_type and att.content_type.startswith("image/")
            ),
            None,
        )
        if not image_attachment:
            return

        ign = await self._extract_ign_from_attachment(image_attachment)
        self.pending_submissions[message.id] = {
            "user_id": message.author.id,
            "ign": ign,
            "processed": False,
        }

        await self._send_ocr_log(message.guild, message.author, ign, message.id)

        try:
            await message.add_reaction("✅")
            await message.add_reaction("❌")
        except Exception:
            pass

        review_embed = discord.Embed(
            title="Verification Submission Received",
            color=0xED4245,
            description=(
                f"User: {message.author.mention}\n"
                f"Detected IGN: **{ign if ign else 'Not detected'}**\n\n"
                "Admin Review: react ✅ on the screenshot message to approve or ❌ to reject."
            ),
        )
        review_embed.timestamp = discord.utils.utcnow()
        await self._send_log_message(message.guild, embed=review_embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return

        emoji = str(payload.emoji)
        if emoji not in {"✅", "❌"}:
            return

        if self.bot.user and payload.user_id == self.bot.user.id:
            return

        channel_id = self._verification_channel_id()
        if not channel_id or payload.channel_id != channel_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        admin_member = payload.member or guild.get_member(payload.user_id)
        if not admin_member:
            try:
                admin_member = await guild.fetch_member(payload.user_id)
            except Exception:
                return

        if not self._can_review_submission(admin_member):
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(payload.channel_id)
            except Exception:
                return

        try:
            message = await channel.fetch_message(payload.message_id)
        except Exception:
            return

        if message.author.bot:
            return

        submission = self.pending_submissions.get(message.id)
        if not submission:
            image_attachment = next(
                (
                    att
                    for att in message.attachments
                    if att.content_type and att.content_type.startswith("image/")
                ),
                None,
            )
            if not image_attachment:
                return
            submission = {
                "user_id": message.author.id,
                "ign": await self._extract_ign_from_attachment(image_attachment) if image_attachment else None,
                "processed": False,
            }
            self.pending_submissions[message.id] = submission
            await self._send_ocr_log(guild, message.author, submission.get("ign"), message.id)

        if submission.get("processed"):
            return

        reviewed_user = guild.get_member(submission["user_id"])
        if not reviewed_user:
            try:
                reviewed_user = await guild.fetch_member(submission["user_id"])
            except Exception:
                await self._send_log_message(guild, "Submission user was not found in this server.")
                submission["processed"] = True
                return

        if emoji == "❌":
            submission["processed"] = True
            await self._send_log_message(guild,
                f"Submission rejected by {admin_member.mention}. No roles assigned for {reviewed_user.mention}."
            )
            return

        matchmaking_role_id = self._matchmaking_role_id()
        skrimmish_role_id = self._skrimmish_role_id()
        if not matchmaking_role_id or not skrimmish_role_id:
            await self._send_log_message(guild,
                "Role IDs are not configured. Set MATCHMAKING_VERIFIED_ROLE_ID and SKRIMMISH_VERIFIED_ROLE."
            )
            return

        matchmaking_role = guild.get_role(matchmaking_role_id)
        skrimmish_role = guild.get_role(skrimmish_role_id)
        if not matchmaking_role or not skrimmish_role:
            await self._send_log_message(guild, "One or more configured verification roles were not found in this server.")
            return

        roles_to_add = [
            role for role in (matchmaking_role, skrimmish_role) if role not in reviewed_user.roles
        ]
        if roles_to_add:
            await reviewed_user.add_roles(*roles_to_add, reason="Approved screenshot verification")

        ign = submission.get("ign")
        ign_note = "IGN could not be detected. Use /admin-set-ign to set it manually."
        if ign:
            success, _ = await db.register_player(reviewed_user.id, str(reviewed_user), ign)
            if success:
                ign_note = f"IGN registered as **{ign}**."

        submission["processed"] = True
        await self._send_log_message(guild,
            f"Submission approved by {admin_member.mention}. {reviewed_user.mention} has been verified and assigned both roles. {ign_note}"
        )

async def setup(bot):
    await bot.add_cog(VerificationCog(bot))
