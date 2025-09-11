import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
# intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Global vars
queues = {}
voice_clients = {}

@bot.event
async def on_ready():
    print(f"Bot Ready: {bot.user.name}")

@bot.command(name="play")
async def play(ctx, *, arg):

    voice_channel = None

    try:
        voice_channel = ctx.author.voice.channel
    except Exception as e:
        print(e)

    if voice_channel is None:
        await ctx.send(f"{ctx.author.mention} is not in a voice channel")
        return
    await ctx.send(f"Joining {voice_channel}")

    voice_clients[ctx.guild.id] = await voice_channel.connect()

    await ctx.send(f"{ctx.author.mention} wants to play: {arg}")

@bot.command(name="stop")
async def stop(ctx):
    if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_connected():
        try:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
        except Exception as e:
            print(e)
        await ctx.send(f"Bye {ctx.author.mention}")
    else:
        await ctx.send("Loobot currently isn't playing anything")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)