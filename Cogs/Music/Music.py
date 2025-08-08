import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import asyncio
import os
import json
from datetime import datetime, timedelta
import time
import random
import socket
import aiohttp

# Try to import required dependencies with better error handling
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    print("⚠️ Warning: yt-dlp tidak tersedia, fungsi musik akan terbatas")
    YT_DLP_AVAILABLE = False

try:
    from concurrent.futures import ThreadPoolExecutor
    THREAD_POOL_AVAILABLE = True
except ImportError:
    print("⚠️ Warning: ThreadPoolExecutor tidak tersedia")
    THREAD_POOL_AVAILABLE = False

# Try to import hashlib for safe filename generation
try:
    import hashlib
    HASHLIB_AVAILABLE = True
except ImportError:
    print("⚠️ Warning: hashlib tidak tersedia")
    HASHLIB_AVAILABLE = False

# Global flags - will be checked at runtime, not import time
VOICE_ENABLED = None
OPUS_ENABLED = None

async def check_network_connectivity():
    """Check network connectivity untuk diagnosis koneksi"""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get('https://www.google.com') as response:
                if response.status == 200:
                    return True, "Koneksi internet OK"
                else:
                    return False, f"HTTP status: {response.status}"
    except asyncio.TimeoutError:
        return False, "Timeout - koneksi lambat"
    except Exception as e:
        return False, f"Error koneksi: {str(e)}"

def check_voice_dependencies():
    """Check if all voice dependencies are available"""
    issues = []

    if not YT_DLP_AVAILABLE:
        issues.append("yt-dlp tidak terinstal")

    try:
        import nacl
    except ImportError:
        issues.append("PyNaCl tidak terinstal")

    # Try to load opus from discord.py with better error handling
    try:
        if not discord.opus.is_loaded():
            opus_names = ['libopus.so.0', 'libopus.so', 'opus', 'libopus', 'libopus-0.dll', 'opus.dll']
            opus_loaded = False
            for opus_name in opus_names:
                try:
                    discord.opus.load_opus(opus_name)
                    if discord.opus.is_loaded():
                        opus_loaded = True
                        print(f"✅ Berhasil memuat opus: {opus_name}")
                        break
                except Exception as opus_error:
                    print(f"⚠️ Gagal memuat {opus_name}: {opus_error}")
                    continue
            if not opus_loaded:
                issues.append("Library Opus tidak tersedia")
    except Exception as discord_error:
        print(f"Error mengakses discord.opus: {discord_error}")
        issues.append("Error mengakses discord.opus")

    if issues:
        return False, f"Dependency yang hilang: {', '.join(issues)}"

    return True, "Semua dependency tersedia"

# FFmpeg options for better audio quality
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# yt-dlp options for downloading
YDL_OPTIONS = {
    'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
    'noplaylist': True,
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'no_warnings': True,
    'logtostderr': False,
    'ignoreerrors': False,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'user_agent': 'Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
} if YT_DLP_AVAILABLE else {}

class MusicControls(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.secondary, custom_id="pause")
    async def pause_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
            if voice and voice.is_playing():
                voice.pause()
                embed = discord.Embed(
                    title="⏸️ Music Paused",
                    description="Music has been paused. Click ▶️ to resume.",
                    color=0xFFA500
                )
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.response.send_message("❌ No music is currently playing!", ephemeral=True)
        except discord.NotFound:
            # Interaction already responded to or expired
            pass
        except Exception as e:
            print(f"Pause button error: {e}")
            await interaction.response.send_message("❌ An error occurred!", ephemeral=True)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.success, custom_id="resume")
    async def resume_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
            if voice and voice.is_paused():
                voice.resume()
                embed = discord.Embed(
                    title="▶️ Music Resumed",
                    description="Music playback has been resumed!",
                    color=0x00FF00
                )
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.response.send_message("❌ No music is currently paused!", ephemeral=True)
        except discord.NotFound:
            # Interaction already responded to or expired
            pass
        except Exception as e:
            print(f"Resume button error: {e}")
            await interaction.response.send_message("❌ An error occurred!", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary, custom_id="skip")
    async def skip_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
            if voice and (voice.is_playing() or voice.is_paused()):
                # Check if auto-play is active
                music_cog = self.bot.get_cog('Music')
                is_auto_play = (music_cog and hasattr(music_cog, 'auto_play_mode') and
                               interaction.guild.id in music_cog.auto_play_mode)

                voice.stop()

                # If auto-play is active and queue is low, get more recommendations
                if is_auto_play and music_cog and interaction.guild.id in music_cog.queue:
                    if len(music_cog.queue[interaction.guild.id]) <= 2:  # When queue is getting low
                        try:
                            last_played = music_cog.auto_play_mode.get(interaction.guild.id)
                            if last_played:
                                # Add small delay to prevent rate limiting
                                await asyncio.sleep(1)
                                recommendations = await music_cog.get_youtube_recommendations(last_played)
                                for rec in recommendations[:3]:  # Add 3 more songs to prevent overwhelming
                                    music_cog.queue[interaction.guild.id].append((rec['title'], rec['webpage_url']))
                                print(f"Auto-play: Added {len(recommendations)} more recommendations")
                        except Exception as rec_error:
                            print(f"Auto-play recommendation error: {rec_error}")

                embed = discord.Embed(
                    title="⏭️ Song Skipped",
                    description="Skipped to the next song in queue!" +
                               ("\n🎵 Auto-play: Getting more recommendations..." if is_auto_play else ""),
                    color=0x3498DB
                )
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.response.send_message("❌ No music is currently playing!", ephemeral=True)
        except discord.NotFound:
            # Interaction already responded to or expired
            pass
        except Exception as e:
            print(f"Skip button error: {e}")
            await interaction.response.send_message("❌ An error occurred while skipping!", ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="stop")
    async def stop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
            if voice:
                music_cog = self.bot.get_cog('Music')
                if music_cog and hasattr(music_cog, 'queue') and interaction.guild.id in music_cog.queue:
                    music_cog.queue[interaction.guild.id].clear()
                if music_cog and hasattr(music_cog, 'auto_play_mode') and interaction.guild.id in music_cog.auto_play_mode:
                    del music_cog.auto_play_mode[interaction.guild.id]
                await voice.disconnect()
                embed = discord.Embed(
                    title="⏹️ Music Stopped",
                    description="Music stopped and queue cleared. Disconnected from voice channel.",
                    color=0xFF0000
                )
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                await interaction.response.send_message("❌ Bot is not connected to a voice channel!", ephemeral=True)
        except discord.NotFound:
            # Interaction already responded to or expired
            pass
        except Exception as e:
            print(f"Stop button error: {e}")
            await interaction.response.send_message("❌ An error occurred!", ephemeral=True)

    @discord.ui.button(emoji="🎵", style=discord.ButtonStyle.secondary, custom_id="autoplay")
    async def autoplay_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            music_cog = self.bot.get_cog('Music')
            if not music_cog:
                await interaction.response.send_message("❌ Music system not available!", ephemeral=True)
                return

            # Initialize auto_play_mode if it doesn't exist
            if not hasattr(music_cog, 'auto_play_mode'):
                music_cog.auto_play_mode = {}

            guild_id = interaction.guild.id

            # Toggle auto-play mode
            if guild_id in music_cog.auto_play_mode:
                # Disable auto-play
                del music_cog.auto_play_mode[guild_id]
                embed = discord.Embed(
                    title="🎵 Auto-Play Disabled",
                    description="Auto-play mode has been turned off. Music will stop after the current queue ends.",
                    color=0xFF6B6B
                )
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                # Enable auto-play - need a current song to base recommendations on
                current_song_url = None

                # Try to get the last played song or current song
                if hasattr(music_cog, 'last_played') and guild_id in music_cog.last_played:
                    current_song_url = music_cog.last_played[guild_id]
                elif hasattr(music_cog, 'queue') and guild_id in music_cog.queue and music_cog.queue[guild_id]:
                    # Get URL from current queue
                    current_song_url = music_cog.queue[guild_id][0][1] if music_cog.queue[guild_id] else None

                if current_song_url:
                    # Enable auto-play
                    music_cog.auto_play_mode[guild_id] = current_song_url

                    # Get recommendations and add to queue
                    embed = discord.Embed(
                        title="🎵 Auto-Play Enabled!",
                        description="Getting recommendations based on current music...",
                        color=0x9B59B6
                    )
                    await interaction.response.edit_message(embed=embed, view=self)

                    # Add recommendations to queue
                    try:
                        recommendations = await music_cog.get_youtube_recommendations(current_song_url)

                        # Initialize queue if needed
                        if guild_id not in music_cog.queue:
                            music_cog.queue[guild_id] = []

                        for rec in recommendations:
                            music_cog.queue[guild_id].append((rec['title'], rec['webpage_url']))

                        # Update embed with success message
                        success_embed = discord.Embed(
                            title="🎵 Auto-Play Enabled!",
                            description=f"Added **{len(recommendations)}** recommended songs to queue.\n\nAuto-play will continue finding similar music!",
                            color=0x9B59B6
                        )

                        if recommendations:
                            rec_list = "\n".join([f"• {rec['title'][:30]}{'...' if len(rec['title']) > 30 else ''}" for rec in recommendations[:3]])
                            success_embed.add_field(name="🎵 Added to Queue", value=rec_list, inline=False)

                        await interaction.edit_original_response(embed=success_embed, view=self)

                    except Exception as rec_error:
                        print(f"Auto-play recommendation error: {rec_error}")
                        error_embed = discord.Embed(
                            title="🎵 Auto-Play Enabled",
                            description="Auto-play mode is now active, but couldn't get recommendations right now. It will try again when songs change.",
                            color=0xFFA500
                        )
                        await interaction.edit_original_response(embed=error_embed, view=self)
                else:
                    await interaction.response.send_message("❌ No current song to base recommendations on! Play a song first.", ephemeral=True)

        except discord.NotFound:
            # Interaction already responded to or expired
            pass
        except Exception as e:
            print(f"Auto-play button error: {e}")
            await interaction.response.send_message("❌ An error occurred!", ephemeral=True)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="shuffle")
    async def shuffle_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            music_cog = self.bot.get_cog('Music')
            if music_cog and hasattr(music_cog, 'queue') and interaction.guild.id in music_cog.queue:
                if len(music_cog.queue[interaction.guild.id]) > 1:
                    random.shuffle(music_cog.queue[interaction.guild.id])
                    embed = discord.Embed(
                        title="🔀 Queue Shuffled",
                        description=f"Shuffled {len(music_cog.queue[interaction.guild.id])} songs in the queue!",
                        color=0x9B59B6
                    )
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    await interaction.response.send_message("❌ Need at least 2 songs in queue to shuffle!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ No songs in queue!", ephemeral=True)
        except discord.NotFound:
            # Interaction already responded to or expired
            pass
        except Exception as e:
            print(f"Shuffle button error: {e}")
            await interaction.response.send_message("❌ An error occurred!", ephemeral=True)

class SearchResultsView(discord.ui.View):
    def __init__(self, bot, ctx, search_results, voice_channel):
        super().__init__(timeout=60)
        self.bot = bot
        self.ctx = ctx
        self.search_results = search_results
        self.voice_channel = voice_channel

        # Add buttons for each search result
        for i, result in enumerate(search_results[:5]):
            button = discord.ui.Button(
                label=f"{i+1}. {result['title'][:40]}{'...' if len(result['title']) > 40 else ''}",
                style=discord.ButtonStyle.primary,
                custom_id=f"select_song_{i}",
                emoji="🎵"
            )
            button.callback = self.create_song_callback(i)
            self.add_item(button)

    def create_song_callback(self, index):
        async def song_callback(interaction):
            if interaction.user != self.ctx.author:
                await interaction.response.send_message("❌ Only the person who requested the search can select a song!", ephemeral=True)
                return

            selected_song = self.search_results[index]
            await interaction.response.edit_message(content="🎵 Processing your selection...", embed=None, view=None)

            # Now play the selected song
            music_cog = self.bot.get_cog('Music')
            if music_cog:
                await music_cog.play_selected_song(self.ctx, selected_song, self.voice_channel)

        return song_callback

class QueueView(discord.ui.View):
    def __init__(self, bot, guild_id, page=0):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.page = page

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def previous_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.page > 0:
            self.page -= 1
            embed = self.create_queue_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ Already on the first page!", ephemeral=True)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        music_cog = self.bot.get_cog('Music')
        if music_cog and hasattr(music_cog, 'queue') and self.guild_id in music_cog.queue:
            total_pages = (len(music_cog.queue[self.guild_id]) - 1) // 10 + 1
            if self.page < total_pages - 1:
                self.page += 1
                embed = self.create_queue_embed()
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.response.send_message("❌ Already on the last page!", ephemeral=True)

    def create_queue_embed(self):
        music_cog = self.bot.get_cog('Music')
        if not music_cog or not hasattr(music_cog, 'queue') or self.guild_id not in music_cog.queue:
            return discord.Embed(title="📝 Queue Empty", description="No songs in queue!", color=0xFF0000)

        queue = music_cog.queue[self.guild_id]
        if not queue:
            return discord.Embed(title="📝 Queue Empty", description="No songs in queue!", color=0xFF0000)

        start = self.page * 10
        end = start + 10
        page_queue = queue[start:end]

        embed = discord.Embed(
            title="📝 Music Queue",
            description=f"**Total songs:** {len(queue)} | **Page:** {self.page + 1}/{(len(queue) - 1) // 10 + 1}",
            color=0x1DB954
        )

        for i, (title, url) in enumerate(page_queue, start=start + 1):
            embed.add_field(
                name=f"**{i}.** {title[:50]}{'...' if len(title) > 50 else ''}",
                value=f"[🔗 YouTube Link]({url})",
                inline=False
            )

        embed.set_footer(text="🎵 Use the buttons to navigate • Mobile optimized")
        return embed

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = {}
        self.current_song = {}
        self.auto_play_mode = {}
        self.downloaded_files = {}  # Track downloaded files per guild
        self.download_tasks = {}    # Track ongoing downloads
        self.cleanup_tasks = {}     # Track cleanup tasks for auto-deletion

        # Initialize ThreadPoolExecutor with fallback
        if THREAD_POOL_AVAILABLE:
            try:
                self.executor = ThreadPoolExecutor(max_workers=3)
            except Exception as e:
                print(f"⚠️ Gagal membuat ThreadPoolExecutor: {e}")
                self.executor = None
        else:
            self.executor = None

        # Create downloads directory
        if not os.path.exists('downloads'):
            os.makedirs('downloads')

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        print("Music cog unloading, cleaning up...")

        # Cancel all download tasks
        for guild_tasks in self.download_tasks.values():
            for task_url in guild_tasks.copy():
                try:
                    # Task cleanup handled in the task itself
                    pass
                except:
                    pass

        # Cancel all cleanup tasks
        for guild_tasks in self.cleanup_tasks.values():
            for task in guild_tasks.copy().values():
                try:
                    task.cancel()
                except:
                    pass

        # Shutdown ThreadPoolExecutor
        if hasattr(self, 'executor') and self.executor:
            try:
                self.executor.shutdown(wait=False)
            except:
                pass

        # Disconnect all voice clients with improved cleanup
        async def cleanup_voice():
            print("Music cog: Cleaning up voice connections...")

            # Create a copy of voice clients to avoid modification during iteration
            voice_clients_copy = []
            try:
                if hasattr(self.bot, 'voice_clients'):
                    voice_clients_copy = list(self.bot.voice_clients)
            except:
                pass

            for voice_client in voice_clients_copy:
                try:
                    guild_name = "Unknown"
                    if hasattr(voice_client, 'guild') and voice_client.guild:
                        guild_name = voice_client.guild.name

                    # Stop any playing audio immediately
                    if hasattr(voice_client, 'is_playing'):
                        try:
                            if voice_client.is_playing():
                                voice_client.stop()
                        except:
                            pass

                    # Force disconnect without waiting for graceful shutdown
                    if hasattr(voice_client, 'is_connected'):
                        try:
                            if voice_client.is_connected():
                                await asyncio.wait_for(voice_client.disconnect(force=True), timeout=5.0)
                                print(f"Music cog: Force disconnected from {guild_name}")
                        except asyncio.TimeoutError:
                            print(f"Music cog: Timeout disconnecting from {guild_name}")
                        except:
                            pass

                    # Cleanup internal resources
                    if hasattr(voice_client, 'cleanup'):
                        try:
                            await asyncio.wait_for(voice_client.cleanup(), timeout=3.0)
                        except:
                            pass

                    # Brief pause to prevent overwhelming the event loop
                    await asyncio.sleep(0.1)

                except Exception as e:
                    print(f"Music cog: Error cleaning voice connection: {e}")
                    # Continue with other connections even if one fails

            print("Music cog: Voice cleanup completed")

        # Schedule voice cleanup if event loop is available
        try:
            if hasattr(self.bot, 'loop') and self.bot.loop and not self.bot.loop.is_closed():
                asyncio.create_task(cleanup_voice())
        except Exception as e:
            print(f"Music cog: Could not schedule cleanup: {e}")

    def get_safe_filename(self, url):
        """Generate a safe filename from URL"""
        if HASHLIB_AVAILABLE:
            import hashlib
            url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
            return f"downloads/audio_{url_hash}.mp3"
        else:
            # Fallback: use simple string replacement
            safe_url = url.replace('/', '_').replace(':', '_').replace('?', '_')[:20]
            return f"downloads/audio_{safe_url}.mp3"

    async def download_audio(self, url, title="Unknown"):
        """Download audio file from URL dengan penanganan koneksi yang lebih baik"""
        if not YT_DLP_AVAILABLE:
            print(f"yt-dlp tidak tersedia, tidak dapat mengunduh: {title}")
            return None

        try:
            filename = self.get_safe_filename(url)

            # Check if already downloaded
            if os.path.exists(filename):
                return filename

            # Download options yang dioptimalkan dengan penanganan koneksi yang lebih baik
            download_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
                'outtmpl': filename,
                'extractaudio': True,
                'audioformat': 'mp3',
                'audioquality': '192K',
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'socket_timeout': 30,  # Kurangi timeout untuk koneksi yang lebih cepat
                'retries': 5,  # Tingkatkan retry
                'fragment_retries': 5,
                'retry_sleep_functions': {'http': lambda n: min(4 * (2 ** n), 30)},
                'user_agent': 'Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
                'extractor_args': {
                    'youtube': {
                        'skip': ['dash', 'hls'],
                        'player_client': ['android', 'web']
                    }
                },
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'cross-site'
                }
            }

            # Run download dengan atau tanpa thread pool
            if self.executor and THREAD_POOL_AVAILABLE:
                loop = asyncio.get_event_loop()
                try:
                    await loop.run_in_executor(self.executor, self._download_sync, url, download_opts)
                except Exception as thread_error:
                    print(f"Thread pool error, fallback ke sync: {thread_error}")
                    try:
                        await asyncio.to_thread(self._download_sync, url, download_opts)
                    except Exception as sync_error:
                        print(f"Sync download juga gagal: {sync_error}")
                        # Fallback manual
                        self._download_sync(url, download_opts)
            else:
                # Fallback tanpa thread pool
                try:
                    await asyncio.to_thread(self._download_sync, url, download_opts)
                except Exception as sync_error:
                    print(f"Async download gagal: {sync_error}")
                    # Fallback manual
                    self._download_sync(url, download_opts)

            if os.path.exists(filename):
                print(f"✅ Berhasil diunduh: {title}")
                return filename
            else:
                print(f"❌ Gagal mengunduh: {title}")
                return None

        except Exception as e:
            print(f"Error mengunduh {title}: {e}")
            return None

    def _download_sync(self, url, opts):
        """Synchronous download function for thread pool"""
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"Sync download error: {e}")

    async def download_in_background(self, guild_id, songs_to_download):
        """Download multiple songs in background for auto-play"""
        if not YT_DLP_AVAILABLE:
            return # Don't attempt download if yt-dlp is not available

        if guild_id not in self.download_tasks:
            self.download_tasks[guild_id] = set()

        for title, url in songs_to_download:
            if url not in self.download_tasks[guild_id]:
                self.download_tasks[guild_id].add(url)
                # Start download task
                task = asyncio.create_task(self._background_download_task(guild_id, title, url))
                # Don't await, let it run in background

    async def _background_download_task(self, guild_id, title, url):
        """Background task for downloading a single song"""
        try:
            filename = await self.download_audio(url, title)
            if filename:
                if guild_id not in self.downloaded_files:
                    self.downloaded_files[guild_id] = {}
                self.downloaded_files[guild_id][url] = filename
                print(f"🎵 Background downloaded: {title}")
        except Exception as e:
            print(f"Background download error for {title}: {e}")
        finally:
            # Remove from active downloads
            if guild_id in self.download_tasks:
                self.download_tasks[guild_id].discard(url)

    def schedule_file_cleanup(self, guild_id, url, filename, delay_minutes=5):
        """Schedule a file for deletion after specified delay"""
        if guild_id not in self.cleanup_tasks:
            self.cleanup_tasks[guild_id] = {}

        # Cancel existing cleanup task if it exists
        if url in self.cleanup_tasks[guild_id]:
            self.cleanup_tasks[guild_id][url].cancel()

        # Schedule new cleanup task
        task = asyncio.create_task(self._cleanup_after_delay(guild_id, url, filename, delay_minutes * 60))
        self.cleanup_tasks[guild_id][url] = task

    async def check_voice_connection(self, guild):
        """Check and maintain voice connection health"""
        try:
            voice = discord.utils.get(self.bot.voice_clients, guild=guild)
            if not voice:
                return False

            # Check if voice client is properly connected
            if not hasattr(voice, 'is_connected') or not voice.is_connected():
                return False

            # Test connection by checking if we can access voice properties safely
            try:
                if not voice.channel:
                    return False

                # Check if we can call basic voice methods
                voice.is_playing()
                voice.is_paused()
            except Exception:
                return False

            # Additional check: ensure the voice client's websocket is healthy
            try:
                if hasattr(voice, 'ws') and voice.ws and voice.ws.closed:
                    print("Voice websocket is closed")
                    return False
            except Exception:
                pass  # WebSocket check is optional

            return True
        except Exception as e:
            print(f"Voice connection health check failed: {e}")
            return False

    async def ensure_voice_connection(self, ctx, voice_channel):
        """Pastikan koneksi voice yang stabil dengan recovery otomatis"""
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        # Cek apakah koneksi saat ini sehat
        if voice and await self.check_voice_connection(ctx.guild):
            return voice

        # Bersihkan koneksi yang tidak sehat
        if voice:
            try:
                await asyncio.wait_for(voice.disconnect(force=True), timeout=5.0)
                await asyncio.sleep(0.5)  # Tunggu sebentar untuk cleanup
            except asyncio.TimeoutError:
                print("⚠️ Timeout saat disconnect, melanjutkan...")
            except Exception as e:
                print(f"⚠️ Error saat disconnect: {e}")

            # Hapus dari daftar voice clients bot
            try:
                if hasattr(voice, 'cleanup'):
                    await asyncio.wait_for(voice.cleanup(), timeout=3.0)
            except:
                pass

        # Buat koneksi baru dengan error handling yang lebih baik
        max_attempts = 3
        base_delay = 1

        for attempt in range(max_attempts):
            try:
                # Gunakan timeout yang berbeda untuk setiap attempt
                timeout_values = [15.0, 25.0, 35.0]
                current_timeout = timeout_values[min(attempt, len(timeout_values) - 1)]

                print(f"🔄 Percobaan koneksi {attempt + 1}/{max_attempts} ke {voice_channel.name}...")

                voice = await asyncio.wait_for(
                    voice_channel.connect(reconnect=False),
                    timeout=current_timeout
                )

                # Verifikasi koneksi
                await asyncio.sleep(0.5)  # Beri waktu untuk stabilitas
                if await self.check_voice_connection(ctx.guild):
                    print(f"✅ Berhasil terhubung ke {voice_channel.name} pada percobaan {attempt + 1}")
                    return voice
                else:
                    print(f"⚠️ Koneksi tidak stabil, mencoba lagi...")
                    try:
                        await voice.disconnect(force=True)
                        await asyncio.sleep(1)
                    except:
                        pass

            except asyncio.TimeoutError:
                print(f"⏰ Timeout pada percobaan {attempt + 1}")

            except discord.ClientException as e:
                error_msg = str(e).lower()
                print(f"❌ ClientException pada percobaan {attempt + 1}: {e}")

                if "already connected" in error_msg:
                    # Handle error sudah terhubung
                    existing_voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
                    if existing_voice:
                        try:
                            await existing_voice.disconnect(force=True)
                            await asyncio.sleep(1)
                        except:
                            pass

                elif "no permission" in error_msg or "missing access" in error_msg:
                    print("❌ Bot tidak memiliki izin untuk bergabung ke channel voice")
                    return None

            except discord.HTTPException as e:
                print(f"🌐 HTTP Error pada percobaan {attempt + 1}: {e}")

            except Exception as e:
                print(f"❌ Error tidak terduga pada percobaan {attempt + 1}: {e}")

            # Delay sebelum percobaan berikutnya dengan exponential backoff
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                delay = min(delay, 10)  # Cap pada 10 detik
                print(f"⏳ Menunggu {delay} detik sebelum percobaan berikutnya...")
                await asyncio.sleep(delay)

        print("❌ Semua percobaan koneksi gagal")
        return None

    async def _cleanup_after_delay(self, guild_id, url, filename, delay_seconds):
        """Delete file after delay"""
        try:
            await asyncio.sleep(delay_seconds)

            # Check if file still exists and remove it
            if os.path.exists(filename):
                os.remove(filename)
                print(f"🗑️ Auto-deleted: {filename}")

            # Remove from tracking
            if (guild_id in self.downloaded_files and
                url in self.downloaded_files[guild_id]):
                del self.downloaded_files[guild_id][url]

            # Remove cleanup task from tracking
            if (guild_id in self.cleanup_tasks and
                url in self.cleanup_tasks[guild_id]):
                del self.cleanup_tasks[guild_id][url]

        except asyncio.CancelledError:
            # Task was cancelled, don't delete file
            pass
        except Exception as e:
            print(f"Cleanup error for {filename}: {e}")

    async def search_youtube(self, query):
        """Search for music on YouTube"""
        if not YT_DLP_AVAILABLE:
            return None

        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)
                if 'entries' in info and len(info['entries']) > 0:
                    entry = info['entries'][0]
                    return {
                        'title': entry.get('title', 'Unknown'),
                        'url': entry.get('webpage_url', ''),
                        'duration': entry.get('duration', 0),
                        'uploader': entry.get('uploader', 'Unknown')
                    }
        except Exception as e:
            print(f"Search error: {e}")
            return None

    async def search_youtube_multiple(self, query, max_results=5):
        """Search for multiple songs on YouTube"""
        if not YT_DLP_AVAILABLE:
            return []

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extractflat': False,
                'nocheckcertificate': True,
                'ignoreerrors': True,
                'default_search': 'ytsearch',
                'extract_flat': False,
                'user_agent': 'Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_query = f"ytsearch{max_results}:{query}"
                info = ydl.extract_info(search_query, download=False)

                if not info or 'entries' not in info or not info['entries']:
                    return []

                results = []
                for entry in info['entries'][:max_results]:
                    if entry:
                        results.append({
                            'title': entry.get('title', 'Unknown'),
                            'url': entry.get('webpage_url', ''),
                            'duration': entry.get('duration', 0),
                            'uploader': entry.get('uploader', 'Unknown'),
                            'thumbnail': entry.get('thumbnail', '')
                        })

                return results
        except Exception as e:
            print(f"Multiple search error: {e}")
            return []

    async def play_selected_song(self, ctx, selected_song, voice_channel):
        """Play the selected song from search results - now with download first"""
        try:
            # Show downloading status
            download_embed = discord.Embed(
                title="⬬ Downloading...",
                description=f"**{selected_song['title']}**\n\nDownloading for better quality playback...",
                color=0xFFA500
            )
            await ctx.edit(embed=download_embed)

            # Download the song first
            downloaded_file = await self.download_audio(selected_song['url'], selected_song['title'])

            # Connect to voice channel with retry logic
            voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

            connection_attempts = 0
            max_attempts = 3

            while connection_attempts < max_attempts:
                try:
                    if not voice or not voice.is_connected():
                        # Try to connect with different timeout values
                        timeout_values = [30.0, 45.0, 60.0]
                        voice = await voice_channel.connect(
                            reconnect=True,
                            timeout=timeout_values[connection_attempts]
                        )
                        break
                    elif voice.channel != voice_channel:
                        await voice.move_to(voice_channel)
                        break
                    else:
                        # Already connected properly
                        break
                except (discord.ClientException, asyncio.TimeoutError, socket.gaierror) as e:
                    connection_attempts += 1
                    if connection_attempts < max_attempts:
                        await asyncio.sleep(2)  # Wait before retry
                        continue
                    else:
                        error_embed = discord.Embed(
                            title="❌ Voice Connection Failed",
                            description=f"Could not connect to voice channel after {max_attempts} attempts.\n\nError: {str(e)}\n\nTry again in a moment.",
                            color=0xFF0000
                        )
                        await ctx.edit(embed=error_embed)
                        return
                except Exception as e:
                    error_embed = discord.Embed(
                        title="❌ Voice Connection Failed",
                        description=f"Unexpected connection error: {str(e)}",
                        color=0xFF0000
                    )
                    await ctx.edit(embed=error_embed)
                    return

            # Initialize queues if not exists
            if ctx.guild.id not in self.queue:
                self.queue[ctx.guild.id] = []
            if ctx.guild.id not in self.downloaded_files:
                self.downloaded_files[ctx.guild.id] = {}

            # Add to queue and track download
            self.queue[ctx.guild.id].append((selected_song['title'], selected_song['url']))
            if downloaded_file:
                self.downloaded_files[ctx.guild.id][selected_song['url']] = downloaded_file

            # Track the song for potential auto-play recommendations
            if not hasattr(self, 'last_played'):
                self.last_played = {}
            self.last_played[ctx.guild.id] = selected_song['url']

            # If not currently playing, start playing
            if not voice.is_playing() and not voice.is_paused():
                await self.play_next(ctx, voice)
            else:
                # Song added to queue
                status_icon = "✅" if downloaded_file else "⚠️"
                status_text = "Downloaded & ready" if downloaded_file else "Download failed, will stream"

                embed = discord.Embed(
                    title="📝 Added to Queue",
                    description=f"**{selected_song['title']}**\n\nPosition in queue: **{len(self.queue[ctx.guild.id])}**\n{status_icon} {status_text}",
                    color=0x00FF00
                )
                embed.add_field(name="Duration", value=f"{selected_song['duration']//60}:{selected_song['duration']%60:02d}" if selected_song['duration'] else "Unknown", inline=True)
                embed.add_field(name="Queue Length", value=f"{len(self.queue[ctx.guild.id])} songs", inline=True)
                embed.add_field(name="Uploader", value=selected_song['uploader'], inline=True)

                if selected_song['thumbnail']:
                    embed.set_thumbnail(url=selected_song['thumbnail'])
                embed.set_footer(text="🎵 Your song will play when queue reaches it • Use 🎵 button for auto-play")

                view = MusicControls(self.bot)
                await ctx.edit(embed=embed, view=view)

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Playback Failed",
                description=f"Could not play the selected song: {str(e)}",
                color=0xFF0000
            )
            await ctx.edit(embed=error_embed)

    @slash_command(description="🎵 Play music from YouTube with interactive controls")
    async def play(self, ctx, *, query: Option(str, "Song name or YouTube URL")):
        """Play music with interactive controls (use auto-play button to enable auto-play)"""

        # Check all dependencies at runtime
        deps_ready, deps_message = check_voice_dependencies()
        if not deps_ready:
            embed = discord.Embed(
                title="❌ Dependensi Suara Hilang",
                description=f"{deps_message}\n\nFungsi musik saat ini tidak tersedia.",
                color=0xFF0000
            )
            await ctx.respond(embed=embed)
            return

        # Check if user is in voice channel with proper error handling
        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(
                title="❌ Saluran Suara Diperlukan",
                description="Anda perlu bergabung ke saluran suara terlebih dahulu!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed)
            return

        # Loading embed
        loading_embed = discord.Embed(
            title="🔍 Searching...",
            description=f"Looking for: **{query}**",
            color=0xFFA500
        )
        await ctx.respond(embed=loading_embed)

        # Get voice channel for later use
        voice_channel = ctx.author.voice.channel

        # Check if it's a direct YouTube URL
        if 'youtube.com' in query or 'youtu.be' in query:
            # Direct URL - extract info and play immediately
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extractflat': False,
                'nocheckcertificate': True,
                'ignoreerrors': True,
                'user_agent': 'Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    selected_song = {
                        'title': info['title'],
                        'url': info['webpage_url'],
                        'duration': info.get('duration', 0),
                        'thumbnail': info.get('thumbnail', ''),
                        'uploader': info.get('uploader', 'Unknown')
                    }
                    await self.play_selected_song(ctx, selected_song, voice_channel)
                    return
            except Exception as e:
                error_embed = discord.Embed(
                    title="❌ URL Processing Failed",
                    description=f"Could not process YouTube URL: **{query}**\n\nError: {str(e)}",
                    color=0xFF0000
                )
                await ctx.edit(embed=error_embed)
                return
        else:
            # Search query - show multiple results
            search_results = await self.search_youtube_multiple(query, 5)

            if not search_results:
                error_embed = discord.Embed(
                    title="❌ Search Failed",
                    description=f"Could not find any results for: **{query}**\n\nTry using different keywords or a direct YouTube URL.",
                    color=0xFF0000
                )
                await ctx.edit(embed=error_embed)
                return

            # Create search results embed
            embed = discord.Embed(
                title="🔍 Search Results",
                description=f"Found **{len(search_results)}** results for: **{query}**\n\nClick a button below to select a song:",
                color=0x1DB954
            )

            for i, result in enumerate(search_results):
                duration_str = f"{result['duration']//60}:{result['duration']%60:02d}" if result['duration'] else "Unknown"
                embed.add_field(
                    name=f"{i+1}. {result['title'][:50]}{'...' if len(result['title']) > 50 else ''}",
                    value=f"**Duration:** {duration_str} | **Uploader:** {result['uploader'][:20]}{'...' if len(result['uploader']) > 20 else ''}",
                    inline=False
                )

            embed.set_footer(text="🎵 Select a song using the buttons below • 60 seconds to choose")

            if search_results[0]['thumbnail']:
                embed.set_thumbnail(url=search_results[0]['thumbnail'])

            # Create view with selection buttons
            view = SearchResultsView(self.bot, ctx, search_results, voice_channel)
            await ctx.edit(embed=embed, view=view)
            return

    async def play_next(self, ctx, voice):
        """Play the next song in queue - using downloaded files when available"""
        # Cek apakah voice masih terhubung dan sambung kembali jika diperlukan
        if not voice or not voice.is_connected():
            print("🔄 Voice client terputus, mencoba menyambung kembali...")
            try:
                # Bersihkan voice client lama terlebih dahulu
                if voice:
                    try:
                        await asyncio.wait_for(voice.disconnect(force=True), timeout=3.0)
                        if hasattr(voice, 'cleanup'):
                            await asyncio.wait_for(voice.cleanup(), timeout=2.0)
                        await asyncio.sleep(0.3)  # Tunggu cleanup
                    except asyncio.TimeoutError:
                        print("⚠️ Timeout saat cleanup voice client")
                    except Exception as cleanup_error:
                        print(f"⚠️ Error cleanup: {cleanup_error}")

                # Coba dapatkan voice channel dari guild
                voice_channel = None

                # Pertama coba dari bot's current voice state
                try:
                    if ctx.guild.me.voice and ctx.guild.me.voice.channel:
                        voice_channel = ctx.guild.me.voice.channel
                        print(f"🎯 Ditemukan channel dari voice state: {voice_channel.name}")
                except Exception as voice_state_error:
                    print(f"Error mengakses voice state: {voice_state_error}")

                if not voice_channel:
                    # Coba cari channel dengan member (fallback)
                    print("🔍 Mencari channel voice dengan member...")
                    try:
                        for channel in ctx.guild.voice_channels:
                            # Prioritaskan channel dengan member yang lebih banyak
                            if len([m for m in channel.members if not m.bot]) > 0:
                                voice_channel = channel
                                print(f"🎯 Ditemukan channel dengan member: {voice_channel.name}")
                                break
                    except Exception as channel_search_error:
                        print(f"Error mencari voice channel: {channel_search_error}")

                if voice_channel:
                    # Gunakan metode koneksi yang telah diperbaiki
                    print(f"🔗 Mencoba menyambung ke {voice_channel.name}...")
                    voice = await self.ensure_voice_connection(ctx, voice_channel)
                    if voice:
                        print(f"✅ Berhasil menyambung kembali ke {voice_channel.name}")
                    else:
                        print("❌ Gagal menyambung kembali setelah beberapa percobaan")
                        if ctx.guild.id in self.queue:
                            self.queue[ctx.guild.id].clear()
                        return
                else:
                    print("❌ Tidak ditemukan channel voice untuk menyambung kembali")
                    # Bersihkan queue karena tidak bisa main lagi
                    if ctx.guild.id in self.queue:
                        self.queue[ctx.guild.id].clear()
                    return

            except Exception as e:
                print(f"❌ Gagal menyambung kembali ke voice: {e}")
                # Bersihkan queue karena tidak bisa main lagi
                if ctx.guild.id in self.queue:
                    self.queue[ctx.guild.id].clear()
                return

        if ctx.guild.id not in self.queue or not self.queue[ctx.guild.id]:
            # Auto-play mode: If queue is empty, try to get more recommendations
            if hasattr(self, 'auto_play_mode') and ctx.guild.id in getattr(self, 'auto_play_mode', {}):
                last_played = getattr(self, 'auto_play_mode', {}).get(ctx.guild.id)
                if last_played:
                    print(f"Auto-play mode: Getting recommendations for {last_played}")
                    new_recommendations = await self.get_youtube_recommendations(last_played)
                    if new_recommendations:
                        # Initialize queue if it doesn't exist
                        if ctx.guild.id not in self.queue:
                            self.queue[ctx.guild.id] = []

                        # Add to queue
                        songs_to_add = []
                        for rec in new_recommendations[:5]:  # Add 5 more songs for better continuity
                            self.queue[ctx.guild.id].append((rec['title'], rec['webpage_url']))
                            songs_to_add.append((rec['title'], rec['webpage_url']))

                        # Start background downloads for auto-play songs
                        if songs_to_add:
                            await self.download_in_background(ctx.guild.id, songs_to_add)

                        # Continue playing
                        if self.queue[ctx.guild.id]:
                            await self.play_next(ctx, voice)
                    else:
                        print("Auto-play: No recommendations found, stopping")
            return

        title, url = self.queue[ctx.guild.id].pop(0)
        self.current_song[ctx.guild.id] = title

        # Track for auto-play mode
        if not hasattr(self, 'auto_play_mode'):
            self.auto_play_mode = {}
        if ctx.guild.id in getattr(self, 'auto_play_mode', {}):
            self.auto_play_mode[ctx.guild.id] = url

        # Auto-download upcoming songs if auto-play is active
        if (hasattr(self, 'auto_play_mode') and ctx.guild.id in self.auto_play_mode and
            ctx.guild.id in self.queue and len(self.queue[ctx.guild.id]) <= 2):
            # When queue is getting low, get more recommendations and download them
            try:
                new_recommendations = await self.get_youtube_recommendations(url)
                if new_recommendations:
                    songs_to_add = []
                    for rec in new_recommendations[:3]:  # Add 3 more songs
                        self.queue[ctx.guild.id].append((rec['title'], rec['webpage_url']))
                        songs_to_add.append((rec['title'], rec['webpage_url']))

                    # Start downloading these in background
                    await self.download_in_background(ctx.guild.id, songs_to_add)
                    print(f"Auto-play: Queued and downloading {len(songs_to_add)} more songs")
            except Exception as e:
                print(f"Auto-play recommendation error: {e}")

        # Check if we have a downloaded file first
        audio_source = None
        duration = 0
        thumbnail = ''
        using_downloaded = False

        if (ctx.guild.id in self.downloaded_files and
            url in self.downloaded_files[ctx.guild.id]):

            downloaded_file = self.downloaded_files[ctx.guild.id][url]
            if os.path.exists(downloaded_file):
                try:
                    # Use downloaded file - much more reliable!
                    audio_source = discord.FFmpegPCMAudio(
                        downloaded_file,
                        options='-vn -filter:a "volume=0.5"'
                    )
                    using_downloaded = True
                    print(f"✅ Playing from downloaded file: {title}")

                    # Get metadata from downloaded file for duration
                    try:
                        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                            info = ydl.extract_info(url, download=False)
                            duration = info.get('duration', 0)
                            thumbnail = info.get('thumbnail', '')
                    except:
                        pass  # Metadata not critical for playback

                except Exception as e:
                    print(f"Failed to play downloaded file: {e}")
                    audio_source = None

        # Fallback to streaming if download not available
        if not audio_source:
            print(f"⚠️ No download available for {title}, streaming instead...")

            # Get audio source with streaming fallback
            ydl_opts_play = {
                'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extractaudio': False,
                'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
                'restrictfilenames': True,
                'noplaylist': True,
                'nocheckcertificate': True,
                'ignoreerrors': True,
                'logtostderr': False,
                'age_limit': 18,
                'default_search': 'auto',
                'cookiefile': None,
                'extractor_args': {
                    'youtube': {
                        'skip': ['dash', 'hls'],
                        'player_client': ['android', 'web']
                    }
                },
                'user_agent': 'Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Origin': 'https://www.youtube.com',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin',
                }
            }

            audio_url = None

            try:
                with yt_dlp.YoutubeDL(ydl_opts_play) as ydl:
                    info = ydl.extract_info(url, download=False)

                    # Get the best audio format
                    if 'formats' in info:
                        for format in info['formats']:
                            if format.get('acodec') != 'none' and format.get('url'):
                                audio_url = format['url']
                                break

                    if not audio_url and 'url' in info:
                        audio_url = info['url']

                    if audio_url:
                        duration = info.get('duration', 0)
                        thumbnail = info.get('thumbnail', '')

            except Exception as extraction_error:
                print(f"Streaming extraction failed: {str(extraction_error)}")

            if not audio_url:
                raise Exception("Could not extract audio URL for streaming")

            # Create streaming source
            try:
                ffmpeg_options_list = [
                    {
                        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin -user_agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"',
                        'options': '-vn -filter:a "volume=0.5"'
                    },
                    {
                        'before_options': '-nostdin',
                        'options': '-vn'
                    },
                    {}  # No options fallback
                ]

                audio_source = None
                for i, ffmpeg_options in enumerate(ffmpeg_options_list):
                    try:
                        if ffmpeg_options:
                            audio_source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
                        else:
                            audio_source = discord.FFmpegPCMAudio(audio_url)
                        break
                    except Exception as ffmpeg_error:
                        print(f"FFmpeg method {i+1} failed: {str(ffmpeg_error)}")
                        continue

                if not audio_source:
                    raise Exception("Could not create streaming audio source")

            except Exception as e:
                raise Exception(f"Streaming playback failed: {e}")

        try:
            # Verify voice connection one more time before playing
            if not voice or not voice.is_connected():
                print("Voice connection lost just before playing")
                return

            # Play audio with better error handling in the after callback
            def after_playing(error):
                if error:
                    print(f"Player error: {error}")

                # Schedule next song
                coro = self.play_next(ctx, voice)
                future = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)

                # Handle callback errors
                def handle_callback_error(fut):
                    try:
                        fut.result()
                    except Exception as e:
                        print(f"Error in play_next callback: {e}")

                future.add_done_callback(handle_callback_error)

            voice.play(audio_source, after=after_playing)

            # Schedule file cleanup for downloaded files (5 minutes after song starts)
            if using_downloaded and ctx.guild.id in self.downloaded_files and url in self.downloaded_files[ctx.guild.id]:
                downloaded_file = self.downloaded_files[ctx.guild.id][url]
                # Calculate cleanup time: song duration + 5 minutes buffer
                cleanup_delay = max(5, (duration // 60) + 5) if duration else 5
                self.schedule_file_cleanup(ctx.guild.id, url, downloaded_file, cleanup_delay)
                print(f"🕒 Scheduled cleanup for {title} in {cleanup_delay} minutes")

            # Now playing embed with source status
            source_icon = "💾" if using_downloaded else "🌐"
            source_text = "Downloaded" if using_downloaded else "Streaming"

            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**{title}**\n{source_icon} {source_text}",
                color=0x1DB954
            )
            embed.add_field(name="Duration", value=f"{duration//60}:{duration%60:02d}" if duration else "Unknown", inline=True)
            embed.add_field(name="Remaining", value=f"{len(self.queue[ctx.guild.id])} songs", inline=True)
            embed.add_field(name="Requested by", value=ctx.author.mention, inline=True)

            if thumbnail:
                embed.set_thumbnail(url=thumbnail)

            # Show auto-play status
            auto_play_status = ""
            if hasattr(self, 'auto_play_mode') and ctx.guild.id in self.auto_play_mode:
                auto_play_status = " • 🎵 Auto-play active"

            cleanup_info = f" • 🗑️ Auto-cleanup in {max(5, (duration // 60) + 5) if duration else 5}min" if using_downloaded else ""
            embed.set_footer(text=f"🎵 Use the buttons below to control playback • Mobile optimized{auto_play_status}{cleanup_info}")

            view = MusicControls(self.bot)
            await ctx.edit(embed=embed, view=view)

        except Exception as e:
            error_msg = str(e)
            print(f"Playback error for {title}: {error_msg}")

            # Provide user-friendly error messages
            if "Sign in to confirm you're not a bot" in error_msg or "not a bot" in error_msg.lower():
                user_error = "YouTube is temporarily blocking requests. Skipping to next song..."
            elif "Video unavailable" in error_msg:
                user_error = "This video is not available. It may be region-locked or private."
            elif "Private video" in error_msg:
                user_error = "This video is private and cannot be played."
            elif "HTTP Error 429" in error_msg:
                user_error = "Rate limited by YouTube. Please wait a moment before trying again."
            else:
                user_error = f"Playback failed: {error_msg[:80]}..."

            error_embed = discord.Embed(
                title="❌ Playback Error",
                description=f"Could not play: **{title}**\n\n**Issue:** {user_error}",
                color=0xFF0000
            )

            # Check if there are more songs in queue
            if self.queue[ctx.guild.id]:
                error_embed.add_field(
                    name="🔄 Auto-Skip",
                    value=f"Trying next song... ({len(self.queue[ctx.guild.id])} remaining)",
                    inline=False
                )
                await ctx.edit(embed=error_embed)

                # Wait a moment before trying next song
                await asyncio.sleep(3)
                await self.play_next(ctx, voice)
            else:
                error_embed.add_field(
                    name="💡 Suggestion",
                    value="Try searching for a different song or check if the video is publicly available.",
                    inline=False
                )
                await ctx.edit(embed=error_embed)

                # Disconnect after error if no more songs
                if voice and voice.is_connected():
                    await asyncio.sleep(5)
                    await voice.disconnect()

    @slash_command(description="📝 View the music queue with interactive navigation")
    async def queue(self, ctx):
        """Display music queue with pagination"""
        try:
            if ctx.guild.id not in self.queue or not self.queue[ctx.guild.id]:
                embed = discord.Embed(
                    title="📝 Queue Empty",
                    description="No songs in the queue! Use `/play` to add some music.",
                    color=0xFF0000
                )
                await ctx.respond(embed=embed)
                return

            view = QueueView(self.bot, ctx.guild.id)
            embed = view.create_queue_embed()
            await ctx.respond(embed=embed, view=view)
        except discord.NotFound:
            # Interaction already responded to or expired
            pass
        except Exception as e:
            print(f"Queue command error: {e}")
            await ctx.respond("❌ An error occurred while displaying the queue!", ephemeral=True)

    @slash_command(description="⏹️ Stop music and clear queue")
    async def stop(self, ctx):
        """Stop music with confirmation"""
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice:
            if ctx.guild.id in self.queue:
                self.queue[ctx.guild.id].clear()
            await voice.disconnect()

            embed = discord.Embed(
                title="⏹️ Music Stopped",
                description="Music stopped, queue cleared, and disconnected from voice channel.",
                color=0xFF0000
            )
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Not Connected",
                description="Bot is not connected to a voice channel!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed)

    @slash_command(description="🗑️ Remove a song from the queue")
    async def remove(self, ctx, position: Option(int, "Position of song to remove (starting from 1)")):
        """Remove song from queue by position"""
        if ctx.guild.id not in self.queue or not self.queue[ctx.guild.id]:
            embed = discord.Embed(
                title="❌ Queue Empty",
                description="No songs in the queue to remove!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed)
            return

        if position < 1 or position > len(self.queue[ctx.guild.id]):
            embed = discord.Embed(
                title="❌ Invalid Position",
                description=f"Please provide a position between 1 and {len(self.queue[ctx.guild.id])}",
                color=0xFF0000
            )
            await ctx.respond(embed=embed)
            return

        removed_song = self.queue[ctx.guild.id].pop(position - 1)
        embed = discord.Embed(
            title="🗑️ Song Removed",
            description=f"Removed **{removed_song[0]}** from position {position}",
            color=0x00FF00
        )
        embed.add_field(name="Remaining Songs", value=f"{len(self.queue[ctx.guild.id])} in queue", inline=True)
        await ctx.respond(embed=embed)

    async def get_youtube_recommendations(self, video_url):
        """Get YouTube recommendations based on a video URL - simplified for better reliability"""
        if not YT_DLP_AVAILABLE:
            return []

        try:
            # Simple options for faster extraction
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'extract_flat': False
            }

            related_videos = []

            try:
                # Extract basic info from the current video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)

                    if info and 'title' in info:
                        title = info['title']
                        uploader = info.get('uploader', '')

                        # Create simple search queries based on the song
                        search_queries = []

                        # Use uploader for recommendations (artist's other songs)
                        if uploader and uploader != 'Unknown':
                            search_queries.append(uploader)

                        # Use first few words of title
                        title_words = title.split()[:3]  # First 3 words
                        if title_words:
                            search_queries.append(' '.join(title_words))

                        # Try each search query
                        for query in search_queries[:2]:  # Maximum 2 searches
                            try:
                                search_info = ydl.extract_info(f"ytsearch5:{query}", download=False)
                                if search_info and 'entries' in search_info:
                                    for entry in search_info['entries']:
                                        if (entry and 'webpage_url' in entry and
                                            entry['webpage_url'] != video_url and
                                            entry.get('title')):
                                            related_videos.append({
                                                'title': entry['title'],
                                                'webpage_url': entry['webpage_url'],
                                                'uploader': entry.get('uploader', 'Unknown')
                                            })
                                            if len(related_videos) >= 5:
                                                break
                            except Exception as search_error:
                                print(f"Search for '{query}' failed: {search_error}")
                                continue

                            if len(related_videos) >= 5:
                                break

            except Exception as info_error:
                print(f"Video info extraction failed: {info_error}")

            # Fallback: Search for popular music if no recommendations found
            if not related_videos:
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        fallback_info = ydl.extract_info("ytsearch5:popular music", download=False)
                        if fallback_info and 'entries' in fallback_info:
                            for entry in fallback_info['entries'][:3]:
                                if entry and entry.get('title'):
                                    related_videos.append({
                                        'title': entry['title'],
                                        'webpage_url': entry['webpage_url'],
                                        'uploader': entry.get('uploader', 'Unknown')
                                    })
                except Exception as fallback_error:
                    print(f"Fallback search failed: {fallback_error}")

            print(f"Found {len(related_videos)} recommendations")
            return related_videos[:5]

        except Exception as e:
            print(f"Recommendation error: {e}")
            return []

    @slash_command(description="🎲 Advanced auto-play with custom seed song")
    async def auto_play(self, ctx, *, seed_query: Option(str, "Starting song or search term for recommendations")):
        """Advanced auto-play system with custom seed song (alternative to /play)"""

        # Check dependencies first
        deps_ready, deps_message = check_voice_dependencies()
        if not deps_ready:
            embed = discord.Embed(
                title="❌ Dependensi Suara Hilang",
                description=f"{deps_message}\n\nFungsi musik saat ini tidak tersedia.",
                color=0xFF0000
            )
            await ctx.respond(embed=embed)
            return

        # Check if user is in voice channel with proper error handling
        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(
                title="❌ Saluran Suara Diperlukan",
                description="Anda perlu bergabung ke saluran suara terlebih dahulu!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed)
            return

        # Loading embed
        loading_embed = discord.Embed(
            title="🎲 Auto-Play Starting...",
            description=f"Finding **{seed_query}** and getting recommendations...",
            color=0x9B59B6
        )
        await ctx.respond(embed=loading_embed)

        # Search for the seed song with enhanced bot detection avoidance
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extractflat': False,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'default_search': 'ytsearch',
            'extract_flat': False,
            'age_limit': 18,
            'cookiefile': None,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_client': ['android', 'web']
                }
            },
            'user_agent': 'Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate'
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if 'youtube.com' in seed_query or 'youtu.be' in seed_query:
                    info = ydl.extract_info(seed_query, download=False)
                else:
                    search_query = f"ytsearch:{seed_query}"
                    info = ydl.extract_info(search_query, download=False)

                    # Check if search returned any results
                    if not info or 'entries' not in info or not info['entries']:
                        raise Exception("No search results found")

                    info = info['entries'][0]

                seed_title = info['title']
                seed_url = info['webpage_url']
                duration = info.get('duration', 0)
                thumbnail = info.get('thumbnail', '')

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Auto-Play Failed",
                description=f"Could not find: **{seed_query}**\n\nError: {str(e)}",
                color=0xFF0000
            )
            await ctx.edit(embed=error_embed)
            return

        # Connect to voice channel with retry logic
        voice_channel = ctx.author.voice.channel
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        connection_attempts = 0
        max_attempts = 3

        while connection_attempts < max_attempts:
            try:
                if not voice or not voice.is_connected():
                    voice = await voice_channel.connect(reconnect=True, timeout=30.0)
                    break
                elif voice.channel != voice_channel:
                    await voice.move_to(voice_channel)
                    break
                else:
                    break
            except (discord.ClientException, asyncio.TimeoutError, socket.gaierror) as e:
                connection_attempts += 1
                if connection_attempts < max_attempts:
                    await asyncio.sleep(2)
                    continue
                else:
                    error_embed = discord.Embed(
                        title="❌ Voice Connection Failed",
                        description=f"Could not connect to voice channel after {max_attempts} attempts: {str(e)}",
                        color=0xFF0000
                    )
                    await ctx.edit(embed=error_embed)
                    return
            except Exception as e:
                error_embed = discord.Embed(
                    title="❌ Voice Connection Failed",
                    description=f"Unexpected connection error: {str(e)}",
                    color=0xFF0000
                )
                await ctx.edit(embed=error_embed)
                return

        # Initialize queue if not exists
        if ctx.guild.id not in self.queue:
            self.queue[ctx.guild.id] = []

        # Clear existing queue for auto-play mode
        self.queue[ctx.guild.id].clear()

        # Add seed song to queue
        self.queue[ctx.guild.id].append((seed_title, seed_url))

        # Enable auto-play mode for this guild
        if not hasattr(self, 'auto_play_mode'):
            self.auto_play_mode = {}
        self.auto_play_mode[ctx.guild.id] = seed_url

        # Get recommendations based on the seed song
        update_embed = discord.Embed(
            title="🎲 Getting Recommendations...",
            description=f"Added **{seed_title}** to queue\nFinding similar songs...\n\n🎵 **Auto-play mode activated!**",
            color=0x9B59B6
        )
        await ctx.edit(embed=update_embed)

        recommendations = await self.get_youtube_recommendations(seed_url)

        # Add recommendations to queue
        songs_to_download = []
        for rec in recommendations:
            self.queue[ctx.guild.id].append((rec['title'], rec['webpage_url']))
            songs_to_download.append((rec['title'], rec['webpage_url']))

        # Start background downloads for auto-play
        if songs_to_download:
            await self.download_in_background(ctx.guild.id, songs_to_download)

        # Start playing
        if not voice.is_playing() and not voice.is_paused():
            await self.play_next(ctx, voice)

        # Auto-play started embed
        embed = discord.Embed(
            title="🎲 Auto-Play Started!",
            description=f"**Now Playing:** {seed_title}\n\n**Recommendations Added:** {len(recommendations)} songs\n💾 **Downloading in background for smooth playback**",
            color=0x9B59B6
        )
        embed.add_field(name="Queue Length", value=f"{len(self.queue[ctx.guild.id])} songs", inline=True)
        embed.add_field(name="Mode", value="🎵 Auto-Play + Download", inline=True)
        embed.add_field(name="Based on", value=f"**{seed_title}**", inline=True)

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        # Show some recommendations
        if recommendations:
            rec_list = "\n".join([f"• {rec['title'][:40]}{'...' if len(rec['title']) > 40 else ''}" for rec in recommendations[:3]])
            embed.add_field(name="🎵 Coming Up", value=rec_list, inline=False)

        embed.set_footer(text="🎵 Auto-Play with downloads active • Songs will be downloaded for better quality")

        view = MusicControls(self.bot)
        await ctx.edit(embed=embed, view=view)

    @slash_command(description="🧹 Clean up downloaded music files")
    async def cleanup(self, ctx):
        """Clean up downloaded music files to free space"""
        try:
            # Count files
            download_dir = "downloads"
            file_count = 0
            total_size = 0

            if os.path.exists(download_dir):
                for filename in os.listdir(download_dir):
                    filepath = os.path.join(download_dir, filename)
                    if os.path.isfile(filepath):
                        file_count += 1
                        total_size += os.path.getsize(filepath)
                        os.remove(filepath)

                # Clear tracking dictionaries
                if ctx.guild.id in self.downloaded_files:
                    del self.downloaded_files[ctx.guild.id]

                # Cancel all scheduled cleanup tasks for this guild
                if ctx.guild.id in self.cleanup_tasks:
                    for task in self.cleanup_tasks[ctx.guild.id].values():
                        task.cancel()
                    del self.cleanup_tasks[ctx.guild.id]

                size_mb = total_size / (1024 * 1024)

                embed = discord.Embed(
                    title="🧹 Cleanup Complete",
                    description=f"Removed **{file_count}** downloaded files\nFreed **{size_mb:.1f} MB** of storage space\n⏰ Cancelled all scheduled cleanups",
                    color=0x00FF00
                )
            else:
                embed = discord.Embed(
                    title="🧹 Nothing to Clean",
                    description="No downloaded files found!",
                    color=0xFFA500
                )

            await ctx.respond(embed=embed)

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Cleanup Failed",
                description=f"Could not clean up files: {str(e)}",
                color=0xFF0000
            )
            await ctx.respond(error_embed)

def setup(bot):
    try:
        music_cog = Music(bot)
        bot.add_cog(music_cog)
        print("✅ Music cog loaded successfully")
        print("  ↳ Dependencies will be checked when commands are used")
    except Exception as e:
        print(f"⚠️ Music cog failed to load: {e}")