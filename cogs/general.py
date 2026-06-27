import discord
from discord.ext import commands
from datetime import datetime, timedelta
import database as db
import config

def get_player(user_id, username=None):
    conn = db.get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE user_id = %s", (str(user_id),))
    player = c.fetchone()
    conn.close()
    return player

def create_player(user_id, username):
    conn = db.get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO players (user_id, username) VALUES (%s, %s)",
        (str(user_id), username)
    )
    conn.commit()
    conn.close()

def level_from_xp(xp):
    return max(1, int((xp / 100) ** 0.5) + 1)

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── !start ────────────────────────────────────────────────────────
    @commands.command(name="start")
    async def start(self, ctx):
        """Begin your Swarajya journey."""
        uid = str(ctx.author.id)
        player = get_player(uid)

        if player:
            embed = discord.Embed(
                title="⚔️ Already Enlisted!",
                description=f"{ctx.author.mention}, you have already joined the Swarajya!\nUse `jay!profile` to view your progress.",
                color=config.COLOR_ERROR
            )
            await ctx.send(embed=embed)
            return

        create_player(uid, ctx.author.name)

        embed = discord.Embed(
            title="🚩 **Jay Bhavani! Jay Shivaji!**",
            description=(
                f"Welcome, **{ctx.author.name}**! You have joined the Swarajya!\n\n"
                "You begin your journey as a **Mavla** — a humble foot soldier.\n"
                "Rise through the ranks, summon legendary warriors, and build the Maratha Empire!\n\n"
                "**Starter Rewards:**\n"
                "🪙 **500 Hon** — your starting currency\n\n"
                "**Quick Start:**\n"
                "`jay!summon` — Summon your first warrior\n"
                "`jay!profile` — View your profile\n"
                "`jay!daily` — Claim daily Hon\n"
                "`jay!gallery` — Browse all warriors\n"
                "`jay!help` — All commands"
            ),
            color=config.COLOR_MAIN
        )
        embed.set_footer(text="Swarajya Bot • Maratha Empire RPG")
        await ctx.send(embed=embed)

    # ── !profile ──────────────────────────────────────────────────────
    @commands.command(name="profile", aliases=["pf"])
    async def profile(self, ctx, member: discord.Member = None):
        """View your Sardar profile."""
        target = member or ctx.author
        player = get_player(str(target.id))

        if not player:
            msg = "You haven't started yet! Use `jay!start`." if not member else f"{target.name} hasn't started yet."
            await ctx.send(f"❌ {msg}")
            return

        conn = db.get_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as total FROM player_characters WHERE user_id = %s", (str(target.id),))
        char_count = c.fetchone()["total"]
        c.execute(
            "SELECT ch.name, ch.rarity FROM player_characters pc "
            "JOIN characters ch ON pc.char_id = ch.id "
            "WHERE pc.user_id = %s AND pc.id = %s",
            (str(target.id), player["selected_char"])
        )
        selected = c.fetchone()
        conn.close()

        level = level_from_xp(player["xp"])
        xp_needed = ((level) ** 2) * 100
        xp_bar_filled = int((player["xp"] % xp_needed) / xp_needed * 10)
        xp_bar = "█" * xp_bar_filled + "░" * (10 - xp_bar_filled)

        rank = "Mavla"
        if level >= 50: rank = "Chhatrapati"
        elif level >= 30: rank = "Senapati"
        elif level >= 20: rank = "Peshwa"
        elif level >= 10: rank = "Sardar"
        elif level >= 5:  rank = "Subhedar"

        embed = discord.Embed(
            title=f"⚔️ {target.name}'s Profile",
            color=config.COLOR_MAIN
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🏅 Rank", value=rank, inline=True)
        embed.add_field(name="⚡ Level", value=str(level), inline=True)
        embed.add_field(name="✨ XP", value=f"`{xp_bar}` {player['xp']}/{xp_needed}", inline=False)
        embed.add_field(name="🪙 Hon", value=f"{player['hon']:,}", inline=True)
        embed.add_field(name="💠 Mudra", value=f"{player['mudra']:,}", inline=True)
        embed.add_field(name="🏆 Medals", value=f"{player['medals']:,}", inline=True)
        embed.add_field(name="💎 Omni Shards", value=f"{player['omni_shards']:,}", inline=True)
        embed.add_field(name="🗡️ Warriors", value=str(char_count), inline=True)
        if selected:
            r = config.RARITY_EMOJI.get(selected["rarity"], "")
            embed.add_field(name="🎯 Selected", value=f"{r} {selected['name']}", inline=True)
        embed.set_footer(text="Swarajya Bot • Use !chars to view warriors")
        await ctx.send(embed=embed)

    # ── !bal ─────────────────────────────────────────────────────────
    @commands.command(name="bal", aliases=["balance", "zeni"])
    async def bal(self, ctx):
        """Check your currency balance."""
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        embed = discord.Embed(title=f"💰 {ctx.author.name}'s Treasury", color=config.COLOR_GOLD)
        embed.add_field(name="🪙 Hon",         value=f"`{player['hon']:,}`",         inline=True)
        embed.add_field(name="💠 Mudra",       value=f"`{player['mudra']:,}`",       inline=True)
        embed.add_field(name="🏆 Medals",      value=f"`{player['medals']:,}`",      inline=True)
        embed.add_field(name="💎 Omni Shards", value=f"`{player['omni_shards']:,}`", inline=True)
        embed.set_footer(text="Use !daily to earn more Hon!")
        await ctx.send(embed=embed)

    # ── !daily ────────────────────────────────────────────────────────
    @commands.command(name="daily")
    async def daily(self, ctx):
        """Claim your daily Hon reward."""
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        now = datetime.utcnow()
        last = player["last_daily"]

        if last:
            last_dt = datetime.fromisoformat(last)
            diff = now - last_dt
            if diff < timedelta(hours=24):
                remaining = timedelta(hours=24) - diff
                hrs, rem = divmod(int(remaining.total_seconds()), 3600)
                mins = rem // 60
                embed = discord.Embed(
                    title="⏰ Already Claimed!",
                    description=f"Come back in **{hrs}h {mins}m** for your next daily reward.",
                    color=config.COLOR_ERROR
                )
                await ctx.send(embed=embed)
                return

        conn = db.get_conn()
        c = conn.cursor()
        c.execute(
            "UPDATE players SET hon = hon + %s, last_daily = %s WHERE user_id = %s",
            (config.DAILY_HON_REWARD, now.isoformat(), str(ctx.author.id))
        )
        conn.commit()
        new_hon = conn.execute("SELECT hon FROM players WHERE user_id=%s", (str(ctx.author.id),)).fetchone()["hon"]
        conn.close()

        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=(
                f"**+{config.DAILY_HON_REWARD} 🪙 Hon** added to your treasury!\n\n"
                f"Balance: `{new_hon:,} Hon`\n\n"
                "Come back tomorrow for more!"
            ),
            color=config.COLOR_SUCCESS
        )
        embed.set_footer(text="Tip: Use !summon to spend your Hon!")
        await ctx.send(embed=embed)

    # ── !roll (hourly) ────────────────────────────────────────────────
    @commands.command(name="roll", aliases=["hourly"])
    async def roll_hourly(self, ctx):
        """Open your hourly chest for Hon."""
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        now = datetime.utcnow()
        last = player["last_hourly"]

        if last:
            last_dt = datetime.fromisoformat(last)
            diff = now - last_dt
            if diff < timedelta(hours=1):
                remaining = timedelta(hours=1) - diff
                mins = int(remaining.total_seconds() // 60)
                await ctx.send(f"⏰ Hourly chest resets in **{mins}m**.")
                return

        conn = db.get_conn()
        conn.execute(
            "UPDATE players SET hon = hon + %s, last_hourly = %s WHERE user_id = %s",
            (config.HOURLY_HON_REWARD, now.isoformat(), str(ctx.author.id))
        )
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="📦 Hourly Chest!",
            description=f"You received **+{config.HOURLY_HON_REWARD} 🪙 Hon**!\nNext chest in 1 hour.",
            color=config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

    # ── !leaderboard ──────────────────────────────────────────────────
    @commands.command(name="leaderboard", aliases=["lb", "rich"])
    async def leaderboard(self, ctx):
        """Top 10 richest players."""
        conn = db.get_conn()
        rows = conn.execute(
            "SELECT username, hon, xp FROM players ORDER BY hon DESC LIMIT 10"
        ).fetchall()
        conn.close()

        if not rows:
            await ctx.send("No players yet!")
            return

        embed = discord.Embed(title="🏆 Swarajya Leaderboard — Richest Sardars", color=config.COLOR_GOLD)
        medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
        desc = ""
        for i, row in enumerate(rows):
            lvl = level_from_xp(row["xp"])
            desc += f"{medals[i]} **{row['username']}** — `{row['hon']:,} Hon` | Lv.{lvl}\n"
        embed.description = desc
        embed.set_footer(text="Use !daily and !summon to climb the ranks!")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(General(bot))
