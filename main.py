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
    await bot.change_presence(activity=discord.Game(name="jay!help | Swarajya Bot"))

@bot.command(name="help")
async def help_cmd(ctx, section: str = None):
    """Show all commands."""

    if section in ("chars", "characters"):
        embed = discord.Embed(title="⚔️ Character Commands", color=config.COLOR_MAIN)
        for name, desc in [
            ("jay!chars [page]",           "View your warrior inventory"),
            ("jay!gallery [page]",         "Browse all warriors"),
            ("jay!info <ID>",              "Detailed warrior info"),
            ("jay!select <ID>",            "Set active warrior"),
            ("jay!fav <ID>",              "Favourite/unfavourite warrior"),
            ("jay!favs",                   "View favourite warriors"),
            ("jay!summon [1/2]",           "Summon a warrior (300 Hon)"),
            ("jay!multi [1/2]",            "10x summon (2700 Hon)"),
            ("jay!banner",                 "View available banners"),
        ]:
            embed.add_field(name=f"`{name}`", value=desc, inline=False)
        await ctx.send(embed=embed)
        return

    if section in ("clan", "clans"):
        embed = discord.Embed(title="🏰 Clan Commands", color=config.COLOR_MAIN)
        for name, desc in [
            ("jay!clancreate <TAG> <Name>", "Create a clan (costs 1000 🪙)"),
            ("jay!claninfo",                "View your clan info"),
            ("jay!claninfo <name>",         "View any clan's info"),
            ("jay!clanjoin <TAG>",          "Join a clan by tag"),
            ("jay!clanleave",               "Leave your clan"),
            ("jay!clandisband",             "Disband your clan (leader only)"),
            ("jay!clandonate <amount>",     "Donate Hon to clan bank"),
            ("jay!clanlist",                "View all clan rankings"),
        ]:
            embed.add_field(name=f"`{name}`", value=desc, inline=False)
        await ctx.send(embed=embed)
        return

    if section in ("market", "trade"):
        embed = discord.Embed(title="🏪 Market & Trade Commands", color=config.COLOR_MAIN)
        for name, desc in [
            ("jay!market [page]",           "Browse the player market"),
            ("jay!mlist char <ID> <price>", "List a warrior for sale"),
            ("jay!mlist item <ID> <price>", "List an item for sale"),
            ("jay!mbuy <listing ID>",       "Buy a market listing"),
            ("jay!mremove <listing ID>",    "Remove your listing"),
            ("jay!mylistings",              "View your active listings"),
            ("jay!trade @user <hon>",       "Send a Hon trade offer"),
        ]:
            embed.add_field(name=f"`{name}`", value=desc, inline=False)
        await ctx.send(embed=embed)
        return

    if section in ("items", "shop"):
        embed = discord.Embed(title="🛡️ Items & Pets Commands", color=config.COLOR_MAIN)
        for name, desc in [
            ("jay!shop",                    "Browse the Swarajya Armoury"),
            ("jay!shop 2",                  "Browse the War Animal Egg Shop"),
            ("jay!buyitem <ID>",            "Purchase an item"),
            ("jay!items [page]",            "Your item inventory"),
            ("jay!iinfo <ID>",              "Item details & stats"),
            ("jay!iequip <charID> <itemID>","Equip item to a warrior"),
            ("jay!iunequip <itemID>",       "Unequip an item"),
            ("jay!buyegg small/medium/large","Buy a War Animal egg"),
            ("jay!eggs",                    "View your incubating eggs"),
            ("jay!hatch",                   "Hatch a ready egg"),
            ("jay!pets",                    "View your War Animals"),
            ("jay!petequip <ID>",           "Activate a War Animal"),
        ]:
            embed.add_field(name=f"`{name}`", value=desc, inline=False)
        await ctx.send(embed=embed)
        return

    # ── Main help embed ───────────────────────────────────────────────
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
            "`jay!info <ID>` — Warrior details\n"
            "`jay!select <ID>` — Equip warrior\n"
            "`jay!fav <ID>` — Favourite warrior\n"
            "`jay!favs` — View favourites"
        ),
        inline=False
    )
    embed.add_field(
        name="🏹 Summon",
        value=(
            "`jay!summon [1/2]` — Summon warrior (300 Hon)\n"
            "`jay!multi [1/2]` — 10x summon (2700 Hon)\n"
            "`jay!banner` — View banners"
        ),
        inline=False
    )
    embed.add_field(
        name="⚔️ Battle",
        value=(
            "`jay!fight @user` — PvP battle\n"
            "`jay!boss [name]` — Fight a boss (needs 🗝️)\n"
            "`jay!bosses` — View all bosses\n"
            "`jay!stats` — Battle stats"
        ),
        inline=False
    )
    embed.add_field(
        name="📖 Saga & Tower",
        value=(
            "`jay!saga` — View/select a saga\n"
            "`jay!mi [n]` — Fight a mission\n"
            "`jay!tc [1-4]` — Gadkille Tower\n"
            "`jay!keys` — Check Boss Keys"
        ),
        inline=False
    )
    embed.add_field(
        name="🛡️ Items & Pets",
        value=(
            "`jay!shop` — Swarajya Armoury\n"
            "`jay!items` — Your inventory\n"
            "`jay!eggs` / `jay!hatch` — War Animal eggs\n"
            "`jay!pets` — Your War Animals"
        ),
        inline=False
    )
    embed.add_field(
        name="🏰 Clans",
        value=(
            "`jay!clancreate` — Create a clan\n"
            "`jay!clanjoin <TAG>` — Join a clan\n"
            "`jay!claninfo` — View clan info\n"
            "`jay!clanlist` — All clan rankings"
        ),
        inline=False
    )
    embed.add_field(
        name="🏪 Market & Trade",
        value=(
            "`jay!market` — Player market\n"
            "`jay!mlist char/item <ID> <price>` — Sell\n"
            "`jay!mbuy <ID>` — Buy listing\n"
            "`jay!trade @user <hon>` — Trade Hon"
        ),
        inline=False
    )
    embed.add_field(
        name="📖 Detailed Help",
        value=(
            "`jay!help chars` — Character commands\n"
            "`jay!help clan` — Clan commands\n"
            "`jay!help market` — Market commands\n"
            "`jay!help items` — Items & Pets commands"
        ),
        inline=False
    )
    embed.set_footer(text="Swarajya Bot • Maratha Empire RPG • Jay Bhavani! 🚩")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Unknown command. Use `jay!help` to see all commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing argument. Use `jay!help` for usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument. Use `jay!help` for usage.")
    else:
        print(f"Error: {error}")

async def main():
    db.init_db()
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"✅ Loaded {cog}")
            except Exception as e:
                print(f"❌ Failed to load {cog}: {e}")
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
