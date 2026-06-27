import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import database as db
import config

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="jay!", intents=intents, help_command=None)

COGS = ["cogs.general", "cogs.characters", "cogs.battle", "cogs.saga", "cogs.tower", "cogs.items", "cogs.clans", "cogs.market"]

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    await bot.change_presence(activity=discord.Game(name="!start | Swarajya Bot"))

@bot.command(name="help")
async def help_cmd(ctx, section: str = None):
    """Show all commands."""
    if section == "chars" or section == "characters":
        embed = discord.Embed(title="⚔️ Character Commands", color=config.COLOR_MAIN)
        cmds = [
            ("!chars [page]",    "View your warrior inventory"),
            ("!gallery [page]",  "Browse all warriors"),
            ("!info <ID>",       "Detailed warrior info"),
            ("!select <ID>",     "Set active warrior"),
            ("!fav <ID>",        "Favourite/unfavourite warrior"),
            ("!favs",            "View favourite warriors"),
            ("!summon [banner]", "Summon a warrior (cost: 300 Hon)"),
            ("!multi [banner]",  "10x summon (cost: 2700 Hon)"),
            ("!banner",          "View available banners"),
        ]
        for name, desc in cmds:
            embed.add_field(name=f"`{name}`", value=desc, inline=False)
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="🚩 Swarajya Bot — Commands",
        description="Jay Bhavani! Jay Shivaji! Here are all commands:",
        color=config.COLOR_MAIN
    )
    embed.add_field(
        name="⚙️ General",
        value=(
            "`jay!start` — Begin your journey\n"
            "`jay!profile` / `jay!pf` — View your profile\n"
            "`jay!bal` — Check your currency\n"
            "`jay!daily` — Claim daily Hon (500 🪙)\n"
            "`jay!roll` — Claim hourly chest (100 🪙)\n"
            "`jay!leaderboard` / `jay!lb` — Top players"
        ),
        inline=False
    )
    embed.add_field(
        name="⚔️ Characters",
        value=(
            "`jay!chars` — Your warrior inventory\n"
            "`jay!gallery` — All warriors\n"
            "`!info <ID>` — Warrior details\n"
            "`!select <ID>` — Equip warrior\n"
            "`!fav <ID>` — Favourite warrior\n"
            "`jay!favs` — View favourites"
        ),
        inline=False
    )
    embed.add_field(
        name="🏹 Summon",
        value=(
            "`!summon [1/2]` — Summon warrior (300 Hon)\n"
            "`!multi [1/2]` — 10x summon (2700 Hon)\n"
            "`jay!banner` — View banners"
        ),
        inline=False
    )
    embed.add_field(
        name="📖 Detailed Help",
        value="`!help chars` — Character command details",
        inline=False
    )
    embed.set_footer(text="Swarajya Bot • Maratha Empire RPG • More features coming soon!")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ Unknown command. Use `jay!help` to see all commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument. Use `jay!help` for usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument. Use `jay!help` for usage.")
    else:
        print(f"Error: {error}")

async def main():
    db.init_db()
    async with bot:
        for cog in COGS:
            await bot.load_extension(cog)
            print(f"✅ Loaded {cog}")
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
