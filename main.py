import discord
from discord.ext import commands
from discord.commands import slash_command
from dotenv import load_dotenv
import os
import asyncio
import datetime

load_dotenv()
TOKEN = os.getenv('TOKEN')

# Cek token dengan pesan yang lebih informatif
if not TOKEN:
    print("❌ ERROR: Token Discord tidak ditemukan!")
    print("\n🔧 Cara mengatur token:")
    print("1. Buka tab 'Secrets' di sidebar kiri")
    print("2. Klik tombol 'New Secret'")
    print("3. Key: TOKEN")
    print("4. Value: paste_token_discord_bot_anda_disini")
    print("\n📝 Cara mendapatkan token:")
    print("1. Buka https://discord.com/developers/applications")
    print("2. Buat aplikasi baru atau pilih yang sudah ada")
    print("3. Pergi ke tab 'Bot'")
    print("4. Copy token dari bagian 'Token'")
    print("\n⚠️ Jangan share token Anda dengan siapa pun!")
    exit(1)

if len(TOKEN) < 50:
    print("⚠️ PERINGATAN: Token yang dimasukkan terlihat terlalu pendek.")
    print("Token Discord biasanya panjang dan berisi karakter acak.")
intents = discord.Intents.all() #need to enable
# Ensure voice intents are enabled
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(
    command_prefix='~', 
    intents=intents,
    help_command=None,
    case_insensitive=True
)

@bot.event
async def on_ready():
    print(f'\n🤖 {bot.user} sekarang ONLINE dan siap!')
    print(f'📱 UI dioptimalkan untuk mobile telah aktif')
    
    # Load cogs after bot is ready
    cogs_loaded, cogs_failed = await load_cogs()
    
    print(f'🌟 Semua fitur bot All-in-One telah dimuat')
    print(f'🏠 Terhubung ke {len(bot.guilds)} server')
    print(f'👥 Melayani {len(bot.users)} pengguna')
    
    # Check voice capabilities
    try:
        import nacl
        print("✅ Dukungan voice diaktifkan (PyNaCl terinstal)")
    except ImportError:
        print("⚠️ Dukungan voice dinonaktifkan (PyNaCl tidak terinstal)")
    
    # Check Opus library
    try:
        if not discord.opus.is_loaded():
            # Try different opus library names
            opus_loaded = False
            for opus_name in ['libopus.so.0', 'libopus.so', 'opus', 'libopus']:
                try:
                    discord.opus.load_opus(opus_name)
                    opus_loaded = True
                    print(f"✅ Pustaka Opus dimuat ({opus_name})")
                    break
                except:
                    continue
            
            if not opus_loaded:
                print("⚠️ Pustaka Opus tidak ditemukan - fitur musik mungkin tidak berfungsi")
        else:
            print("✅ Pustaka Opus sudah dimuat")
    except Exception as e:
        print(f"⚠️ Pemeriksaan Opus gagal: {e}")
    
    # py-cord automatically syncs slash commands, no manual sync needed
    print(f"✅ Perintah slash siap")
    print(f'🚀 Bot sepenuhnya operasional dengan fitur interaktif!')

@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state changes - minimal logging only"""
    # Only handle bot's own voice state changes for logging
    if member.id != bot.user.id:
        return
    
    # Just log the changes, let the Music cog handle all cleanup
    try:
        if before.channel is not None and after.channel is None:
            print(f"Bot terputus dari saluran suara: {before.channel.name}")
        elif before.channel != after.channel and after.channel is not None:
            print(f"Bot pindah ke saluran suara: {after.channel.name}")
    except Exception as e:
        print(f"Error dalam logging voice state: {e}")

@bot.event
async def on_disconnect():
    """Handle cleanup when bot disconnects"""
    print("Bot sedang terputus...")

@bot.event
async def on_resumed():
    """Handle reconnection"""
    print("Koneksi bot dilanjutkan")

@slash_command(description="🏓 Cek latency bot")
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    
    if latency < 100:
        color = 0x00FF00  # Green
        status = "Sangat Baik"
    elif latency < 200:
        color = 0xFFFF00  # Yellow
        status = "Baik"
    else:
        color = 0xFF0000  # Red
        status = "Lambat"
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"**Latency:** {latency}ms\n**Status:** {status}",
        color=color
    )
    embed.add_field(name="🌐 WebSocket", value=f"{latency}ms", inline=True)
    embed.add_field(name="📊 Status", value=status, inline=True)
    embed.set_footer(text="🚀 Bot berjalan lancar")
    
    await ctx.respond(embed=embed)

bot.add_application_command(ping)

@bot.event
async def on_guild_join(guild):
    """Send welcome message when bot joins a server"""
    # Find the best channel to send welcome message
    channel = None
    
    # Try to find system channel first
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        channel = guild.system_channel
    else:
        # Find first text channel we can send to
        for text_channel in guild.text_channels:
            if text_channel.permissions_for(guild.me).send_messages:
                channel = text_channel
                break
    
    if channel:
        embed = discord.Embed(
            title="🤖 Terima kasih telah menambahkan saya!",
            description="**Saya bot Discord all-in-one baru Anda dengan visual menakjubkan dan optimasi mobile!**",
            color=0x00D4FF
        )
        
        embed.add_field(
            name="🌟 Apa yang bisa saya lakukan:",
            value="```\n🛡️ Moderasi Canggih\n🎵 Musik Berkualitas Tinggi\n👤 Manajemen Role\n🔍 Pencarian Google\n⚙️ Pengaturan Server```",
            inline=True
        )
        
        embed.add_field(
            name="📱 Fitur Mobile:",
            value="```\n✅ Tombol ramah sentuh\n✅ Menu interaktif\n✅ Desain responsif\n✅ Layout yang dioptimalkan```",
            inline=True
        )
        
        embed.add_field(
            name="🚀 Mulai:",
            value="Gunakan `/bantuan` untuk melihat semua fitur saya!\nSemua command berfungsi sempurna di perangkat mobile.",
            inline=False
        )
        
        embed.set_footer(text="🎯 Ketik /bantuan untuk menjelajahi semua fitur • Dioptimalkan untuk mobile")
        
        try:
            await channel.send(embed=embed)
        except:
            pass  # If we can't send, that's okay

async def load_cogs():
    """Load all cogs asynchronously"""
    print("🔄 Memuat cogs...")
    if not os.path.exists('./Cogs'):
        print("❌ Direktori Cogs tidak ditemukan!")
        return 0, 1
    
    cogs_loaded = 0
    cogs_failed = 0
    
    for foldername in os.listdir('./Cogs'): #for every folder in cogs
        folder_path = f'./Cogs/{foldername}'
        if os.path.isdir(folder_path):  # Make sure it's a directory
            for filename in os.listdir(folder_path):# for every file in a folder in cogs
                if filename.endswith('.py') and filename not in ['util.py', 'error.py', '__init__.py']: #if the file is a python file and if the file is a cog
                    try:
                        extension_name = f'Cogs.{foldername}.{filename[:-3]}'
                        print(f"🔄 Loading {extension_name}...")
                        bot.load_extension(extension_name)
                        #load the extension
                        print(f"✅ Berhasil memuat {extension_name}")
                        cogs_loaded += 1
                    except Exception as e:
                        print(f"❌ Gagal memuat {foldername}.{filename[:-3]}: {e}")
                        cogs_failed += 1
                        import traceback
                        traceback.print_exc()
    
    print(f"📊 Ringkasan pemuatan cog: {cogs_loaded} dimuat, {cogs_failed} gagal")
    return cogs_loaded, cogs_failed

print("🚀 Memulai bot...")

try:
    print(f"🔑 Token ditemukan (panjang: {len(TOKEN)} karakter)")
    print("🔄 Mencoba menghubungkan ke Discord...")
    bot.run(TOKEN)
except discord.LoginFailure:
    print("\n❌ ERROR: Token tidak valid!")
    print("🔧 Pastikan token yang Anda masukkan benar:")
    print("   • Token tidak boleh mengandung spasi di awal/akhir")
    print("   • Token harus dari bot yang sudah dibuat di Discord Developer Portal")
    print("   • Pastikan bot memiliki permissions yang diperlukan")
except discord.HTTPException as e:
    print(f"\n❌ ERROR: Masalah koneksi Discord: {e}")
    print("🌐 Coba lagi dalam beberapa menit")
except discord.PrivilegedIntentsRequired:
    print("\n❌ ERROR: Privileged Intents diperlukan!")
    print("🔧 Aktifkan intents berikut di Discord Developer Portal:")
    print("   • Server Members Intent")
    print("   • Message Content Intent")
except Exception as e:
    print(f"\n❌ ERROR: Bot gagal dimulai: {e}")
    print("\n📋 Detail error:")
    import traceback
    traceback.print_exc()