import discord
import asyncio
import random
import time
import json
import os
from dotenv import load_dotenv
load_dotenv()
from discord.ext import commands

WATCHLIST_FILE = "watchlists.json"
NOTIFY_INTERVAL = 3600  # seconds (1 hour)

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.dm_messages = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# {watcher_id: [target_id1, target_id2, ...]}
watchlists = {}
# {(watcher_id, target_id): last_notification_timestamp}
last_notified = {}

whimsical_templates = [
    "🌬️ The wind shifts... **{user}** has appeared in **{channel}**!",
    "⚔️ Brace yourself — **{user}** just joined **{channel}**.",
    "🚨 Alert! **{user}** has materialized in **{channel}**.",
    "🕵️ Rumor has it that **{user}** was spotted in **{channel}**.",
    "📞 Hold the phone! **{user}** is now lurking in **{channel}**.",
    "📜 The prophecy foretold: **{user}** enters **{channel}**.",
    "⚡ A ripple in the fabric of space... {user} emerges in {channel}!",
    "🎩 With a flourish and a poof, {user} appears in {channel}.",
    "🔮 The oracle speaks: {user} has joined {channel}.",
    "🐾 Mysterious footsteps echo... it’s {user} in {channel}.",
    "🚪 You hear a door creak open. {user} just slipped into {channel}.",
    "📡 Incoming transmission: {user} has landed in {channel}.",
    "🌪️ A gust of wind, a swirl of leaves — and {user} is now in {channel}.",
    "🎭 The curtain rises, and {user} takes the stage in {channel}.",
    "👀 You blink — and suddenly, {user} is in {channel}.",
    "🌀 Reality distorts slightly. {user} is now in {channel}.",
    "🧙 A wizard whispers... ‘{user} has entered {channel}.’",
    "🌠 A star twinkles twice. That means {user} is here — in {channel}.",
    "📖 The next chapter begins: {user} appears in {channel}.",
    "🗝️ A hidden door opens... {user} steps into {channel}.",
    "🐉 A dragon stirs. No — just {user}, arriving in {channel}.",
    "🌙 The moon glows brighter as {user} enters {channel}.",
    "🍄 A peculiar silence falls. {user} has joined {channel}.",
    "💾 Upload complete. {user} has spawned in {channel}.",
    "🌈 Somewhere over the bandwidth, {user} is now in {channel}.",
    "🚀 Lift-off confirmed — {user} has docked in {channel}."
]

def load_watchlists():
    global watchlists
    try:
        with open(WATCHLIST_FILE, "r") as f:
            watchlists = json.load(f)
            # convert keys back to ints
            watchlists = {int(k): v for k, v in watchlists.items()}
    except FileNotFoundError:
        watchlists = {}

def save_watchlists():
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlists, f, indent=2)

@bot.event
async def on_ready():
    load_watchlists()
    print(f"Bot is ready. Logged in as {bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel is not None:
        now = time.time()
        for watcher_id, targets in watchlists.items():
            if member.id in targets:
                key = (watcher_id, member.id)
                if key in last_notified and now - last_notified[key] < NOTIFY_INTERVAL:
                    continue
                last_notified[key] = now

                watcher = bot.get_user(watcher_id)
                if watcher:
                    template = random.choice(whimsical_templates)
                    message = template.format(user=member.name, channel=after.channel.name)
                    try:
                        await watcher.send(message)
                    except discord.Forbidden:
                        print(f"Could not DM user {watcher_id}")

# === User Watchlist Commands ===
@bot.command()
async def watchme(ctx, action: str = None, target: discord.Member = None):
    user_id = ctx.author.id

    if user_id not in watchlists:
        watchlists[user_id] = []

    # Ensure valid target for add/remove
    if action in {"add", "remove"} and target is None:
        await ctx.send("I couldn’t find that user in this server. Please mention someone currently in the server.")
        return

    # Add
    if action == "add" and target:
        if target.id not in watchlists[user_id]:
            watchlists[user_id].append(target.id)
            save_watchlists()
            await ctx.send(
                f"Added **{target.display_name}** to your watchlist.",
                allowed_mentions=discord.AllowedMentions.none()
            )
        else:
            await ctx.send(
                f"**{target.display_name}** is already on your watchlist.",
                allowed_mentions=discord.AllowedMentions.none()
            )

    # Remove
    elif action == "remove" and target:
        if target.id in watchlists[user_id]:
            watchlists[user_id].remove(target.id)
            save_watchlists()
            await ctx.send(
                f"Removed **{target.display_name}** from your watchlist.",
                allowed_mentions=discord.AllowedMentions.none()
            )
        else:
            await ctx.send(
                f"**{target.display_name}** is not on your watchlist.",
                allowed_mentions=discord.AllowedMentions.none()
            )

    # List
    elif action == "list":
        if not watchlists[user_id]:
            await ctx.send("Your watchlist is empty.")
        else:
            names = []
            for t_id in watchlists[user_id]:
                t = ctx.guild.get_member(t_id)
                names.append(t.display_name if t else f"<Unknown {t_id}>")
            await ctx.send(
                "You're watching:\n```" + "\n".join(names) + "```",
                allowed_mentions=discord.AllowedMentions.none()
            )

    # Fallback
    else:
        await ctx.send("Usage:\n`!watchme add @user`\n`!watchme remove @user`\n`!watchme list`")

@bot.command()
async def watchid(ctx, action: str = None, user_id: str = None):
    """Quietly manage watchlist by raw user ID. No mentions or bot messages."""
    author_id = ctx.author.id

    if author_id not in watchlists:
        watchlists[author_id] = []

    if action == "add" and user_id:
        try:
            uid = int(user_id)
            if uid not in watchlists[author_id]:
                watchlists[author_id].append(uid)
                save_watchlists()
                # Silent success
            # else: already on list, do nothing
        except ValueError:
            pass  # silently ignore malformed ID

    elif action == "remove" and user_id:
        try:
            uid = int(user_id)
            if uid in watchlists[author_id]:
                watchlists[author_id].remove(uid)
                save_watchlists()
                # Silent success
        except ValueError:
            pass

    # Do nothing for unknown actions or no user_id



@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# Replace with your bot token
bot.run(os.environ["DISCORD_BOT_TOKEN"])
