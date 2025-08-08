
import discord
from discord.ext import commands
from discord.commands import slash_command, Option

class RemoveRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="➖ Hapus role dari anggota")
    async def removerole(self, ctx, member: Option(discord.Member, "Anggota yang akan dihapus rolenya"), role: Option(discord.Role, "Role yang akan dihapus")):
        """Hapus role dari anggota server"""
        
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
                description="Anda tidak dapat menghapus role yang lebih tinggi atau setara dengan role tertinggi Anda!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        if role >= ctx.guild.me.top_role:
            embed = discord.Embed(
                title="❌ Hierarki Bot",
                description="Bot tidak dapat menghapus role yang lebih tinggi atau setara dengan role tertinggi bot!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        try:
            if role not in member.roles:
                embed = discord.Embed(
                    title="⚠️ Role Tidak Ditemukan",
                    description=f"**{member.name}** tidak memiliki role **{role.name}**!",
                    color=0xFFA500
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            await member.remove_roles(role, reason=f"Role dihapus oleh {ctx.author}")

            embed = discord.Embed(
                title="✅ Role Berhasil Dihapus",
                description=f"Role **{role.name}** telah dihapus dari **{member.name}**!",
                color=0x00FF00
            )
            embed.add_field(name="👤 Anggota", value=member.mention, inline=True)
            embed.add_field(name="🎭 Role", value=role.mention, inline=True)
            embed.add_field(name="🛡️ Dihapus oleh", value=ctx.author.mention, inline=True)
            embed.set_footer(text=f"Role ID: {role.id}")

            await ctx.respond(embed=embed)

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Akses Ditolak",
                description="Bot tidak memiliki izin yang cukup untuk menghapus role ini!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="❌ Error HTTP",
                description=f"Terjadi kesalahan saat menghapus role: {str(e)}",
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
    bot.add_cog(RemoveRole(bot))
    print("✅ RemoveRole cog loaded successfully")
