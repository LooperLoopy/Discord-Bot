import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import yt_dlp
import asyncio
from collections import deque

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Global vars
queues = {}
voice_clients = {}

async def search_ytdlp_async(query, ydl_opts):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _extract(query, ydl_opts))

def _extract(query, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(query, download=False)
    
async def play_next_song(voice_client, gID, channel):
    if queues[gID]:
        audio_url, title = queues[gID].popleft()

        ffmpeg_opts = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn -c:a libopus -b:a 96k",
        }

        source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_opts, executable="bin\\ffmpeg\\ffmpeg.exe")

        def after_play(error):
            if error:
                print(f"Error playing {title}: {error}")
            asyncio.run_coroutine_threadsafe(play_next_song(voice_client, gID, channel), bot.loop)

        voice_client.play(source, after=after_play)
        asyncio.create_task(channel.send(f"Now Playing: {title}"))

    else:
        await voice_client.disconnect()
        queues[gID] = deque()


@bot.event
async def on_ready():
    print(f"Bot Ready: {bot.user.name}")

@bot.command(name="play")
async def play(ctx, *, arg):

    gID = ctx.guild.id
    voice_channel = None

    try:
        voice_channel = ctx.author.voice.channel
    except Exception as e:
        print(e)

    if voice_channel is None:
        await ctx.send(f"{ctx.author.mention} is not in a voice channel")
        return
    if ctx.guild.id not in voice_clients:
        await ctx.send(f"Joining {voice_channel}")
        voice_clients[gID] = await voice_channel.connect()

    voice_client = voice_clients[gID]

    ydl_options = {
        "format": "bestaudio[abr<=96]/bestaudio",
        "noplaylist": True,
        "youtube_include_dash_manifest": False,
        "youtube_include_hls_manifest": False,
    }
    
    query = "ytsearch1: " + arg
    results = await search_ytdlp_async(query, ydl_options)
    tracks = results.get("entries", [])

    if tracks is None:
        await ctx.send("No tracks found")
        return
    
    first_track = tracks[0]
    audio_url = first_track["url"]
    title = first_track.get("title", "Untitled")

    if gID not in queues:
        queues[gID] = deque()

    queues[gID].append((audio_url, title))

    if voice_client.is_playing() or voice_client.is_paused():
        await ctx.send(f"{title} - added to queue")
    else:
        await play_next_song(voice_client, gID, ctx.channel)

@bot.command(name="stop")
async def stop(ctx):
    voice_client = voice_clients[ctx.guild.id]

    if not voice_client or not voice_client.is_connected():
        return await ctx.send("Loobot currently isn't playing anything")
    
    gID = ctx.guild.id
    if gID in queues:
        queues[gID].clear()

    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()

    await ctx.send("Queue cleared and disconnected. Bye!")
    await voice_client.disconnect()

@bot.command(name="skip")
async def skip(ctx):
    gID = ctx.guild.id
    if gID in voice_clients and (voice_clients[gID].is_playing() or voice_clients[gID].is_paused()):
        voice_clients[gID].stop()
        await ctx.send("Current song skipped")
    else:
        await ctx.send("Loobot currently isn't playing anything")

@bot.command(name="pause")
async def pause(ctx):
    voice_client = voice_clients[ctx.guild.id]

    if voice_client is None:
        return await ctx.send("Loobot currently isn't in a channel")
    
    if not voice_client.is_playing():
        return await ctx.send("Loobot currently isn't playing anything")
    
    voice_client.pause()
    await ctx.send("Paused")

@bot.command(name="resume")
async def resume(ctx):
    voice_client = voice_clients[ctx.guild.id]

    if voice_client is None:
        return await ctx.send("Loobot currently isn't in a channel")
    
    if not voice_client.is_paused():
        return await ctx.send("Loobot currently isn't paused")
    
    voice_client.resume()
    await ctx.send("Resumed")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)