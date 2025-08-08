
import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import json
import os

class ReactionRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reaction_roles = {}
        self.load_reaction_roles()

    def load_reaction_roles(self):
        """Load reaction roles from file"""
        try:
            file_path = "Cogs/Role/RoleData/reaction_roles.json"
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    self.reaction_roles = json.load(f)
        except Exception as e:
            print(f"Error loading reaction roles: {e}")
            self.reaction_roles = {}

    def save_reaction_roles(self):
        """Save reaction roles to file"""
        try:
            os.makedirs("Cogs/Role/RoleData", exist_ok=True)
            file_path = "Cogs/Role/RoleData/reaction_roles.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.reaction_roles, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving reaction roles: {e}")

    @slash_command(description="➕ Tambahkan reaction role")
    async def add_reaction_role(self, ctx, 
                              message_id: Option(str, "ID pesan untuk reaction role"), 
                              emoji: Option(str, "Emoji untuk reaction"), 
                              role: Option(discord.Role, "Role yang akan diberikan")):
        """Tambahkan reaction role ke pesan"""
        
        # Check permissions
        if not ctx.author.guild_permissions.manage_roles:
            embed = discord.Embed(
                title="❌ Izin Ditolak",
                description="Anda tidak memiliki izin untuk mengelola role!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        try:
            # Get the message
            message = await ctx.channel.fetch_message(int(message_id))
            
            # Check role hierarchy
            if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                embed = discord.Embed(
                    title="❌ Hierarki Role",
                    description="Anda tidak dapat mengatur reaction role untuk role yang lebih tinggi dari Anda!",
                    color=0xFF0000
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            if role >= ctx.guild.me.top_role:
                embed = discord.Embed(
                    title="❌ Hierarki Bot",
                    description="Bot tidak dapat memberikan role yang lebih tinggi dari role bot!",
                    color=0xFF0000
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            # Add reaction to message
            await message.add_reaction(emoji)

            # Store in data
            guild_id = str(ctx.guild.id)
            if guild_id not in self.reaction_roles:
                self.reaction_roles[guild_id] = {}
            
            if message_id not in self.reaction_roles[guild_id]:
                self.reaction_roles[guild_id][message_id] = {}

            self.reaction_roles[guild_id][message_id][emoji] = role.id
            self.save_reaction_roles()

            embed = discord.Embed(
                title="✅ Reaction Role Ditambahkan",
                description=f"Reaction role berhasil ditambahkan!",
                color=0x00FF00
            )
            embed.add_field(name="📝 Pesan ID", value=message_id, inline=True)
            embed.add_field(name="😀 Emoji", value=emoji, inline=True)
            embed.add_field(name="🎭 Role", value=role.mention, inline=True)
            embed.add_field(name="📍 Channel", value=ctx.channel.mention, inline=False)

            await ctx.respond(embed=embed)

        except discord.NotFound:
            embed = discord.Embed(
                title="❌ Pesan Tidak Ditemukan",
                description="Pesan dengan ID tersebut tidak ditemukan di channel ini!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except ValueError:
            embed = discord.Embed(
                title="❌ ID Tidak Valid",
                description="ID pesan yang dimasukkan tidak valid!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Terjadi kesalahan: {str(e)}",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(description="➖ Hapus reaction role")
    async def remove_reaction_role(self, ctx, 
                                  message_id: Option(str, "ID pesan reaction role"), 
                                  emoji: Option(str, "Emoji yang akan dihapus")):
        """Hapus reaction role dari pesan"""
        
        # Check permissions
        if not ctx.author.guild_permissions.manage_roles:
            embed = discord.Embed(
                title="❌ Izin Ditolak",
                description="Anda tidak memiliki izin untuk mengelola role!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        try:
            guild_id = str(ctx.guild.id)
            
            if (guild_id not in self.reaction_roles or 
                message_id not in self.reaction_roles[guild_id] or 
                emoji not in self.reaction_roles[guild_id][message_id]):
                
                embed = discord.Embed(
                    title="❌ Reaction Role Tidak Ditemukan",
                    description="Reaction role dengan kombinasi pesan dan emoji tersebut tidak ditemukan!",
                    color=0xFF0000
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            # Get the message and remove bot's reaction
            try:
                message = await ctx.channel.fetch_message(int(message_id))
                await message.remove_reaction(emoji, ctx.guild.me)
            except:
                pass  # Continue even if we can't remove the reaction

            # Get role info before removing
            role_id = self.reaction_roles[guild_id][message_id][emoji]
            role = ctx.guild.get_role(role_id)
            role_name = role.name if role else "Unknown Role"

            # Remove from data
            del self.reaction_roles[guild_id][message_id][emoji]
            
            # Clean up empty entries
            if not self.reaction_roles[guild_id][message_id]:
                del self.reaction_roles[guild_id][message_id]
            if not self.reaction_roles[guild_id]:
                del self.reaction_roles[guild_id]

            self.save_reaction_roles()

            embed = discord.Embed(
                title="✅ Reaction Role Dihapus",
                description=f"Reaction role berhasil dihapus!",
                color=0x00FF00
            )
            embed.add_field(name="📝 Pesan ID", value=message_id, inline=True)
            embed.add_field(name="😀 Emoji", value=emoji, inline=True)
            embed.add_field(name="🎭 Role", value=role_name, inline=True)

            await ctx.respond(embed=embed)

        except ValueError:
            embed = discord.Embed(
                title="❌ ID Tidak Valid",
                description="ID pesan yang dimasukkan tidak valid!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Terjadi kesalahan: {str(e)}",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(description="📋 Lihat semua reaction roles")
    async def list_reaction_roles(self, ctx):
        """Tampilkan daftar semua reaction roles di server"""
        
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.reaction_roles or not self.reaction_roles[guild_id]:
            embed = discord.Embed(
                title="📋 Tidak Ada Reaction Roles",
                description="Server ini belum memiliki reaction roles!",
                color=0xFFA500
            )
            await ctx.respond(embed=embed)
            return

        embed = discord.Embed(
            title="📋 Daftar Reaction Roles",
            description=f"Semua reaction roles di **{ctx.guild.name}**",
            color=0x00D4FF
        )

        count = 0
        for message_id, reactions in self.reaction_roles[guild_id].items():
            for emoji, role_id in reactions.items():
                role = ctx.guild.get_role(role_id)
                role_name = role.mention if role else "Role Tidak Ditemukan"
                
                count += 1
                embed.add_field(
                    name=f"#{count}",
                    value=f"**Pesan:** {message_id}\n**Emoji:** {emoji}\n**Role:** {role_name}",
                    inline=True
                )
                
                if count >= 25:  # Discord embed limit
                    break
            
            if count >= 25:
                break

        if count >= 25:
            embed.set_footer(text=f"Menampilkan 25 dari banyak reaction roles • Gunakan /remove_reaction_role untuk menghapus")
        else:
            embed.set_footer(text=f"Total: {count} reaction roles")

        await ctx.respond(embed=embed)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle reaction add for role assignment"""
        if user.bot:
            return

        guild_id = str(reaction.message.guild.id)
        message_id = str(reaction.message.id)
        emoji = str(reaction.emoji)

        if (guild_id in self.reaction_roles and 
            message_id in self.reaction_roles[guild_id] and 
            emoji in self.reaction_roles[guild_id][message_id]):
            
            role_id = self.reaction_roles[guild_id][message_id][emoji]
            role = reaction.message.guild.get_role(role_id)
            
            if role and role not in user.roles:
                try:
                    await user.add_roles(role, reason="Reaction role")
                except discord.Forbidden:
                    print(f"No permission to give role {role.name} to {user}")
                except Exception as e:
                    print(f"Error giving reaction role: {e}")

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        """Handle reaction remove for role removal"""
        if user.bot:
            return

        guild_id = str(reaction.message.guild.id)
        message_id = str(reaction.message.id)
        emoji = str(reaction.emoji)

        if (guild_id in self.reaction_roles and 
            message_id in self.reaction_roles[guild_id] and 
            emoji in self.reaction_roles[guild_id][message_id]):
            
            role_id = self.reaction_roles[guild_id][message_id][emoji]
            role = reaction.message.guild.get_role(role_id)
            
            if role and role in user.roles:
                try:
                    await user.remove_roles(role, reason="Reaction role removed")
                except discord.Forbidden:
                    print(f"No permission to remove role {role.name} from {user}")
                except Exception as e:
                    print(f"Error removing reaction role: {e}")

def setup(bot):
    bot.add_cog(ReactionRole(bot))
    print("✅ ReactionRole cog loaded successfully")
