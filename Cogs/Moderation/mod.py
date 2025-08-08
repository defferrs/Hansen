import discord
from discord.ext import commands
import json
import datetime
from discord.commands import slash_command, Option
import os
import asyncio

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warnings = {}
        self.load_warnings()

    def load_warnings(self):
        """Load warnings from file"""
        try:
            if os.path.exists("Cogs/Moderation/warnings.json"):
                with open("Cogs/Moderation/warnings.json", "r") as f:
                    self.warnings = json.load(f)
        except Exception as e:
            print(f"Error loading warnings: {e}")
            self.warnings = {}

    def save_warnings(self):
        """Save warnings to file"""
        try:
            with open("Cogs/Moderation/warnings.json", "w") as f:
                json.dump(self.warnings, f, indent=2)
        except Exception as e:
            print(f"Error saving warnings: {e}")

    @slash_command(description="👟 Keluarkan anggota dari server")
    async def kick(self, ctx, member: discord.Member, *, reason: Option(str, "Alasan dikeluarkan", default="Tidak ada alasan")):
        if not ctx.author.guild_permissions.kick_members:
            await ctx.respond("❌ Anda tidak memiliki izin untuk mengeluarkan anggota!", ephemeral=True)
            return

        try:
            await member.kick(reason=reason)

            embed = discord.Embed(
                title="👟 Anggota Dikeluarkan",
                description=f"**{member.mention} telah dikeluarkan**",
                color=0xFFA500
            )
            embed.add_field(name="👤 Anggota", value=f"{member.name}#{member.discriminator}", inline=True)
            embed.add_field(name="🛡️ Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="📝 Alasan", value=reason, inline=False)
            embed.set_footer(text=f"ID Pengguna: {member.id}")

            await ctx.respond(embed=embed)

        except Exception as e:
            await ctx.respond(f"❌ Gagal mengeluarkan anggota: {str(e)}", ephemeral=True)

    @slash_command(description="🔨 Larang anggota dari server")
    async def ban(self, ctx, member: discord.Member, *, reason: Option(str, "Alasan dilarang", default="Tidak ada alasan")):
        if not ctx.author.guild_permissions.ban_members:
            await ctx.respond("❌ Anda tidak memiliki izin untuk melarang anggota!", ephemeral=True)
            return

        try:
            await member.ban(reason=reason)

            embed = discord.Embed(
                title="🔨 Anggota Dilarang",
                description=f"**{member.mention} telah dilarang**",
                color=0xFF0000
            )
            embed.add_field(name="👤 Anggota", value=f"{member.name}#{member.discriminator}", inline=True)
            embed.add_field(name="🛡️ Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="📝 Alasan", value=reason, inline=False)
            embed.set_footer(text=f"ID Pengguna: {member.id}")

            await ctx.respond(embed=embed)

        except Exception as e:
            await ctx.respond(f"❌ Gagal melarang anggota: {str(e)}", ephemeral=True)

    @slash_command(description="🔓 Unban a user by their ID")
    async def unban(self, ctx, user_id: Option(str, "User ID to unban")):
        if not ctx.author.guild_permissions.ban_members:
            await ctx.respond("❌ You don't have permission to unban members!", ephemeral=True)
            return

        try:
            user_id = int(user_id)
            banned_users = [entry async for entry in ctx.guild.bans()]

            for ban_entry in banned_users:
                if ban_entry.user.id == user_id:
                    await ctx.guild.unban(ban_entry.user)

                    embed = discord.Embed(
                        title="🔓 Member Unbanned",
                        description=f"**{ban_entry.user.name}#{ban_entry.user.discriminator} has been unbanned**",
                        color=0x00FF00
                    )
                    embed.add_field(name="🛡️ Moderator", value=ctx.author.mention, inline=True)
                    embed.set_footer(text=f"User ID: {user_id}")

                    await ctx.respond(embed=embed)
                    return

            await ctx.respond("❌ User not found in ban list!", ephemeral=True)

        except ValueError:
            await ctx.respond("❌ Invalid user ID!", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"❌ Failed to unban user: {str(e)}", ephemeral=True)

    @slash_command(description="⚠️ Warn a member")
    async def warn(self, ctx, member: discord.Member, *, reason: Option(str, "Reason for warning", default="No reason provided")):
        if not ctx.author.guild_permissions.moderate_members:
            await ctx.respond("❌ You don't have permission to warn members!", ephemeral=True)
            return

        try:
            guild_id = str(ctx.guild.id)
            user_id = str(member.id)

            if guild_id not in self.warnings:
                self.warnings[guild_id] = {}
            if user_id not in self.warnings[guild_id]:
                self.warnings[guild_id][user_id] = []

            warning = {
                "reason": reason,
                "moderator": str(ctx.author.id),
                "timestamp": datetime.datetime.now().isoformat()
            }

            self.warnings[guild_id][user_id].append(warning)
            self.save_warnings()

            warning_count = len(self.warnings[guild_id][user_id])

            embed = discord.Embed(
                title="⚠️ Member Warned",
                description=f"**{member.mention} has been warned**",
                color=0xFFFF00
            )
            embed.add_field(name="👤 Member", value=f"{member.name}#{member.discriminator}", inline=True)
            embed.add_field(name="🛡️ Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="📝 Reason", value=reason, inline=False)
            embed.add_field(name="📊 Total Warnings", value=str(warning_count), inline=True)
            embed.set_footer(text=f"User ID: {member.id}")

            await ctx.respond(embed=embed)

        except Exception as e:
            await ctx.respond(f"❌ Failed to warn member: {str(e)}", ephemeral=True)

    @slash_command(description="📊 View warnings for a member")
    async def warnings(self, ctx, member: discord.Member):
        if not ctx.author.guild_permissions.moderate_members:
            await ctx.respond("❌ You don't have permission to view warnings!", ephemeral=True)
            return

        try:
            guild_id = str(ctx.guild.id)
            user_id = str(member.id)

            if guild_id not in self.warnings or user_id not in self.warnings[guild_id]:
                embed = discord.Embed(
                    title="📊 No Warnings",
                    description=f"**{member.name}#{member.discriminator}** has no warnings",
                    color=0x00FF00
                )
                await ctx.respond(embed=embed)
                return

            user_warnings = self.warnings[guild_id][user_id]

            embed = discord.Embed(
                title="📊 Member Warnings",
                description=f"**{member.name}#{member.discriminator}** has {len(user_warnings)} warning(s)",
                color=0xFFFF00
            )

            for i, warning in enumerate(user_warnings[-5:], 1):  # Show last 5 warnings
                moderator = self.bot.get_user(int(warning["moderator"]))
                mod_name = moderator.name if moderator else "Unknown"

                timestamp = datetime.datetime.fromisoformat(warning["timestamp"])
                formatted_time = timestamp.strftime("%Y-%m-%d %H:%M")

                embed.add_field(
                    name=f"Warning #{len(user_warnings) - 5 + i}",
                    value=f"**Reason:** {warning['reason']}\n**By:** {mod_name}\n**Date:** {formatted_time}",
                    inline=False
                )

            if len(user_warnings) > 5:
                embed.set_footer(text=f"Showing last 5 of {len(user_warnings)} warnings")

            await ctx.respond(embed=embed)

        except Exception as e:
            await ctx.respond(f"❌ Failed to retrieve warnings: {str(e)}", ephemeral=True)

    @slash_command(description="🧹 Clear messages from channel")
    async def clear(self, ctx, amount: Option(int, "Number of messages to delete", min_value=1, max_value=100)):
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.respond("❌ You don't have permission to manage messages!", ephemeral=True)
            return

        try:
            deleted = await ctx.channel.purge(limit=amount)

            embed = discord.Embed(
                title="🧹 Messages Cleared",
                description=f"Deleted **{len(deleted)}** messages from {ctx.channel.mention}",
                color=0x00FF00
            )
            embed.add_field(name="🛡️ Moderator", value=ctx.author.mention, inline=True)

            await ctx.respond(embed=embed, ephemeral=True, delete_after=5)

        except Exception as e:
            await ctx.respond(f"❌ Failed to clear messages: {str(e)}", ephemeral=True)

    @slash_command(description="🔇 Timeout a member")
    async def timeout(self, ctx, member: discord.Member, duration: Option(int, "Duration in minutes", min_value=1, max_value=40320), *, reason: Option(str, "Reason for timeout", default="No reason provided")):
        if not ctx.author.guild_permissions.moderate_members:
            await ctx.respond("❌ You don't have permission to moderate members!", ephemeral=True)
            return

        try:
            timeout_duration = datetime.timedelta(minutes=duration)
            await member.timeout_for(timeout_duration, reason=reason)

            embed = discord.Embed(
                title="🔇 Member Timed Out",
                description=f"**{member.mention}** has been timed out for **{duration} minutes**",
                color=0xFF8C00
            )
            embed.add_field(name="🛡️ Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="⏰ Duration", value=f"{duration} minutes", inline=True)
            embed.add_field(name="📝 Reason", value=reason, inline=False)

            await ctx.respond(embed=embed)

        except Exception as e:
            await ctx.respond(f"❌ Failed to timeout member: {e}")

def setup(bot):
    bot.add_cog(Moderation(bot))
    print("✅ Moderation cog loaded successfully")