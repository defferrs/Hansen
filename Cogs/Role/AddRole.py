
import discord
from discord.ext import commands
from discord.commands import slash_command, Option

class AddRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="➕ Tambahkan role ke anggota")
    async def addrole(self, ctx, member: Option(discord.Member, "Anggota yang akan diberi role"), role: Option(discord.Role, "Role yang akan ditambahkan")):
        """Tambahkan role ke anggota server"""
        
        # Check permissions
        if not ctx.author.guild_permissions.manage_roles:
            embed = discord.Embed(
                title="❌ Izin Ditolak",
                description="Anda tidak memiliki izin untuk mengelola role!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        # Check bot permissions
        if not ctx.guild.me.guild_permissions.manage_roles:
            embed = discord.Embed(
                title="❌ Bot Tidak Memiliki Izin",
                description="Bot tidak memiliki izin untuk mengelola role!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        # Check role hierarchy
        if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            embed = discord.Embed(
                title="❌ Hierarki Role",
                description="Anda tidak dapat memberikan role yang lebih tinggi atau setara dengan role tertinggi Anda!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        if role >= ctx.guild.me.top_role:
            embed = discord.Embed(
                title="❌ Hierarki Bot",
                description="Bot tidak dapat memberikan role yang lebih tinggi atau setara dengan role tertinggi bot!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        try:
            if role in member.roles:
                embed = discord.Embed(
                    title="⚠️ Role Sudah Ada",
                    description=f"**{member.name}** sudah memiliki role **{role.name}**!",
                    color=0xFFA500
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            await member.add_roles(role, reason=f"Role ditambahkan oleh {ctx.author}")

            embed = discord.Embed(
                title="✅ Role Berhasil Ditambahkan",
                description=f"Role **{role.name}** telah ditambahkan ke **{member.name}**!",
                color=0x00FF00
            )
            embed.add_field(name="👤 Anggota", value=member.mention, inline=True)
            embed.add_field(name="🎭 Role", value=role.mention, inline=True)
            embed.add_field(name="🛡️ Ditambahkan oleh", value=ctx.author.mention, inline=True)
            embed.set_footer(text=f"Role ID: {role.id}")

            await ctx.respond(embed=embed)

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Akses Ditolak",
                description="Bot tidak memiliki izin yang cukup untuk memberikan role ini!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="❌ Error HTTP",
                description=f"Terjadi kesalahan saat menambahkan role: {str(e)}",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error Tidak Terduga",
                description=f"Terjadi kesalahan: {str(e)}",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)

def setup(bot):
    bot.add_cog(AddRole(bot))
    print("✅ AddRole cog loaded successfully")
