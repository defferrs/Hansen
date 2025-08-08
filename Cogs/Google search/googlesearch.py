import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import requests
from bs4 import BeautifulSoup
import urllib.parse
import asyncio
from googlesearch import search

class Search(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="🔍 Cari informasi di Google")
    async def search(self, ctx, *, query: Option(str, "Kata kunci pencarian")):
        """Cari Google dan tampilkan hasil dengan tampilan yang dioptimalkan untuk mobile"""

        # Send initial loading message
        loading_embed = discord.Embed(
            title="🔍 Mencari...",
            description=f"Sedang mencari: **{query}**",
            color=0xFFA500
        )
        await ctx.respond(embed=loading_embed)

        try:
            # Perform Google search
            search_results = []

            # Use googlesearch-python library
            for i, url in enumerate(search(query, num_results=5, lang='id')):
                if i >= 5:  # Limit to 5 results
                    break

                try:
                    # Try to get page title
                    response = requests.get(url, timeout=5, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    soup = BeautifulSoup(response.content, 'html.parser')
                    title = soup.find('title')
                    title_text = title.text if title else "No Title"

                    # Batasi panjang judul untuk tampilan mobile
                    if len(title_text) > 60:
                        title_text = title_text[:57] + "..."

                    search_results.append({
                        'title': title_text,
                        'url': url
                    })
                except:
                    # Jika tidak bisa mendapatkan judul, gunakan URL saja
                    search_results.append({
                        'title': f"Hasil {i+1}",
                        'url': url
                    })

            if not search_results:
                error_embed = discord.Embed(
                    title="❌ Tidak Ada Hasil",
                    description=f"Tidak ditemukan hasil untuk: **{query}**",
                    color=0xFF0000
                )
                await ctx.edit(embed=error_embed)
                return

            # Create results embed
            results_embed = discord.Embed(
                title="🔍 Hasil Pencarian Google",
                description=f"Menampilkan **{len(search_results)}** hasil untuk: **{query}**",
                color=0x4285F4
            )

            for i, result in enumerate(search_results, 1):
                results_embed.add_field(
                    name=f"{i}. {result['title']}",
                    value=f"[🔗 Buka Link]({result['url']})",
                    inline=False
                )

            results_embed.set_footer(
                text="📱 Tap link untuk membuka • Hasil dari Google Search",
                icon_url="https://www.google.com/favicon.ico"
            )

            await ctx.edit(embed=results_embed)

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error Pencarian",
                description=f"Terjadi kesalahan saat mencari: **{query}**\n\nError: {str(e)}",
                color=0xFF0000
            )
            error_embed.add_field(
                name="💡 Saran",
                value="• Coba kata kunci yang berbeda\n• Periksa koneksi internet\n• Coba lagi dalam beberapa saat",
                inline=False
            )
            await ctx.edit(embed=error_embed)

def setup(bot):
    bot.add_cog(Search(bot))
    print("✅ Google Search cog loaded successfully")