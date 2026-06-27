import discord
from discord.ext import commands
import random
import config
import database as db

CHARS_PER_PAGE   = 15
GALLERY_PER_PAGE = 9

def get_player(user_id):
    conn = db.get_conn()
    p = conn.execute("SELECT * FROM players WHERE user_id=%s", (str(user_id),)).fetchone()
    conn.close()
    return p

def do_summon(banner_key="1"):
    banner = config.BANNERS.get(banner_key, config.BANNERS["1"])
    pool   = banner["pool"]

    # Pick rarity
    roll = random.random()
    cumulative = 0
    chosen_rarity = pool[-1]
    for r in sorted(pool, key=lambda x: config.SUMMON_RATES[x]):
        cumulative += config.SUMMON_RATES[r]
        if roll <= cumulative:
            chosen_rarity = r
            break

    # Pick character of that rarity
    conn = db.get_conn()
    chars = conn.execute(
        "SELECT * FROM characters WHERE rarity=%s", (chosen_rarity,)
    ).fetchall()
    conn.close()

    if not chars:
        return None
    return random.choice(chars)

class Characters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── !summon ───────────────────────────────────────────────────────
    @commands.command(name="summon", aliases=["pull"])
    async def summon(self, ctx, banner: str = "1"):
        """Summon a warrior. Usage: !summon or !summon 2"""
        player = get_player(ctx.author.id)
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        b = config.BANNERS.get(banner, config.BANNERS["1"])
        cost = b["cost"]

        if player["hon"] < cost:
            await ctx.send(f"❌ Not enough Hon! You need **{cost} 🪙** but have **{player['hon']:,} 🪙**.")
            return

        char = do_summon(banner)
        if not char:
            await ctx.send("❌ No characters found in banner!")
            return

        conn = db.get_conn()
        conn.execute(
            "UPDATE players SET hon = hon - %s WHERE user_id=%s",
            (cost, str(ctx.author.id))
        )
        conn.execute(
            "INSERT INTO player_characters (user_id, char_id) VALUES (%s,%s)",
            (str(ctx.author.id), char["id"])
        )
        conn.commit()
        new_hon = conn.execute("SELECT hon FROM players WHERE user_id=%s", (str(ctx.author.id),)).fetchone()["hon"]
        conn.close()

        r_emoji = config.RARITY_EMOJI.get(char["rarity"], "")
        e_emoji = config.ELEMENT_EMOJI.get(char["element"], "")
        color   = config.RARITY_COLOR.get(char["rarity"], config.COLOR_MAIN)

        embed = discord.Embed(
            title=f"✨ Summoning from {b['name']}...",
            description=(
                f"**{r_emoji} {char['name']}** {e_emoji}\n\n"
                f"*{char['description']}*\n\n"
                f"Rarity: **{config.RARITY_LABEL[char['rarity']]}**\n"
                f"Element: **{char['element']}**\n"
                f"HP: `{char['base_hp']}` | ATK: `{char['base_atk']}` | DEF: `{char['base_def']}`\n\n"
                f"Remaining Hon: `{new_hon:,} 🪙`"
            ),
            color=color
        )
        embed.set_footer(text=f"Cost: {cost} Hon • Use !multi for 10x summon")
        await ctx.send(embed=embed)

    # ── !multi ────────────────────────────────────────────────────────
    @commands.command(name="multi")
    async def multi(self, ctx, banner: str = "1"):
        """Multi-summon 10 warriors. Usage: !multi or !multi 2"""
        player = get_player(ctx.author.id)
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        cost = config.MULTI_SUMMON_COST
        if player["hon"] < cost:
            await ctx.send(f"❌ Not enough Hon! You need **{cost} 🪙** for a multi-summon.")
            return

        results = [do_summon(banner) for _ in range(config.MULTI_SUMMON_COUNT)]
        results = [r for r in results if r]

        conn = db.get_conn()
        conn.execute("UPDATE players SET hon=hon-%s WHERE user_id=%s", (cost, str(ctx.author.id)))
        for char in results:
            conn.execute(
                "INSERT INTO player_characters (user_id, char_id) VALUES (%s,%s)",
                (str(ctx.author.id), char["id"])
            )
        conn.commit()
        new_hon = conn.execute("SELECT hon FROM players WHERE user_id=%s", (str(ctx.author.id),)).fetchone()["hon"]
        conn.close()

        b = config.BANNERS.get(banner, config.BANNERS["1"])
        lines = []
        for char in results:
            r = config.RARITY_EMOJI.get(char["rarity"], "")
            e = config.ELEMENT_EMOJI.get(char["element"], "")
            lines.append(f"{r} **{char['name']}** {e}")

        embed = discord.Embed(
            title=f"✨ {config.MULTI_SUMMON_COUNT}x Summon — {b['name']}",
            description="\n".join(lines) + f"\n\nRemaining Hon: `{new_hon:,} 🪙`",
            color=config.COLOR_MAIN
        )
        embed.set_footer(text=f"Cost: {cost} Hon • 10 warriors summoned!")
        await ctx.send(embed=embed)

    # ── !banner ───────────────────────────────────────────────────────
    @commands.command(name="banner", aliases=["banners"])
    async def banner(self, ctx):
        """View all summon banners."""
        embed = discord.Embed(title="🏹 Summon Banners", color=config.COLOR_MAIN)
        for key, b in config.BANNERS.items():
            pool_str = " / ".join([f"{config.RARITY_LABEL[r]}" for r in b["pool"]])
            embed.add_field(
                name=f"Banner {key} — {b['name']}",
                value=f"{b['description']}\nPool: {pool_str}\nCost: **{b['cost']} 🪙 Hon**",
                inline=False
            )
        embed.set_footer(text="Use !summon <number> or !multi <number>")
        await ctx.send(embed=embed)

    # ── !chars ────────────────────────────────────────────────────────
    @commands.command(name="chars", aliases=["characters", "inventory"])
    async def chars(self, ctx, member: discord.Member = None, page: int = 1):
        """View your warrior inventory. Usage: !chars [page]"""
        target = member or ctx.author
        player = get_player(str(target.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        conn = db.get_conn()
        rows = conn.execute(
            """SELECT pc.id, pc.level, pc.tier, pc.is_favorite, ch.name, ch.rarity, ch.element
               FROM player_characters pc
               JOIN characters ch ON pc.char_id = ch.id
               WHERE pc.user_id = %s
               ORDER BY ch.rarity DESC, pc.level DESC""",
            (str(target.id),)
        ).fetchall()
        conn.close()

        if not rows:
            await ctx.send(f"{'You have' if not member else target.name + ' has'} no warriors yet! Use `jay!summon`.")
            return

        total = len(rows)
        total_pages = max(1, (total + CHARS_PER_PAGE - 1) // CHARS_PER_PAGE)
        page = max(1, min(page, total_pages))
        start = (page - 1) * CHARS_PER_PAGE
        chunk = rows[start:start + CHARS_PER_PAGE]

        # Build 3-column grid like DBOV
        lines = []
        for i in range(0, len(chunk), 3):
            row_items = chunk[i:i+3]
            parts = []
            for pc in row_items:
                r  = config.RARITY_EMOJI.get(pc["rarity"], "")
                e  = config.ELEMENT_EMOJI.get(pc["element"], "")
                fav = "⭐" if pc["is_favorite"] else ""
                parts.append(f"**(ID:{pc['id']})** {r} {pc['name']} {e}{fav}\nLv:{pc['level']} | Tier:x{pc['tier']}")
            lines.append("   ".join(parts))

        embed = discord.Embed(
            title=f"⚔️ {target.name}'s Warriors",
            description="**Character Inventory**\n\n" + "\n\n".join(lines),
            color=config.COLOR_MAIN
        )
        embed.add_field(
            name="——Helpful Commands——",
            value="`!select <ID>` — Select a warrior\n`!info <ID>` — View warrior info\n`!fav <ID>` — Favourite a warrior",
            inline=False
        )
        embed.set_footer(text=f"Page [{page}/{total_pages}] • Total {total} warriors • !chars [page]")
        await ctx.send(embed=embed)

    # ── !gallery ──────────────────────────────────────────────────────
    @commands.command(name="gallery")
    async def gallery(self, ctx, page: int = 1):
        """Browse all available warriors."""
        conn = db.get_conn()
        rows = conn.execute(
            "SELECT * FROM characters ORDER BY rarity DESC, name ASC"
        ).fetchall()
        conn.close()

        total = len(rows)
        total_pages = max(1, (total + GALLERY_PER_PAGE - 1) // GALLERY_PER_PAGE)
        page = max(1, min(page, total_pages))
        start = (page - 1) * GALLERY_PER_PAGE
        chunk = rows[start:start + GALLERY_PER_PAGE]

        embed = discord.Embed(title="📜 Warrior Gallery — All Warriors", color=config.COLOR_MAIN)
        for char in chunk:
            r = config.RARITY_EMOJI.get(char["rarity"], "")
            e = config.ELEMENT_EMOJI.get(char["element"], "")
            embed.add_field(
                name=f"{r} {char['name']} {e}",
                value=(
                    f"Rarity: **{config.RARITY_LABEL[char['rarity']]}**\n"
                    f"HP:`{char['base_hp']}` ATK:`{char['base_atk']}` DEF:`{char['base_def']}`"
                ),
                inline=True
            )
        embed.set_footer(text=f"Page [{page}/{total_pages}] • !gallery [page]")
        await ctx.send(embed=embed)

    # ── !info ─────────────────────────────────────────────────────────
    @commands.command(name="info")
    async def info(self, ctx, char_id: int = None):
        """View detailed info on a warrior. Usage: !info <ID>"""
        if char_id is None:
            await ctx.send("❌ Usage: `!info <warrior ID>`")
            return

        conn = db.get_conn()
        pc = conn.execute(
            """SELECT pc.*, ch.name, ch.rarity, ch.element, ch.base_hp, ch.base_atk,
                      ch.base_def, ch.description
               FROM player_characters pc
               JOIN characters ch ON pc.char_id = ch.id
               WHERE pc.id = %s AND pc.user_id = %s""",
            (char_id, str(ctx.author.id))
        ).fetchone()
        conn.close()

        if not pc:
            await ctx.send(f"❌ No warrior with ID `{char_id}` in your inventory.")
            return

        r = config.RARITY_EMOJI.get(pc["rarity"], "")
        e = config.ELEMENT_EMOJI.get(pc["element"], "")
        color = config.RARITY_COLOR.get(pc["rarity"], config.COLOR_MAIN)

        # Scale stats with level
        lv = pc["level"]
        hp  = int(pc["base_hp"]  * (1 + 0.05 * (lv - 1)))
        atk = int(pc["base_atk"] * (1 + 0.05 * (lv - 1)))
        def_ = int(pc["base_def"] * (1 + 0.05 * (lv - 1)))

        embed = discord.Embed(
            title=f"{r} {pc['name']} {e}",
            description=pc["description"],
            color=color
        )
        embed.add_field(name="Rarity",  value=config.RARITY_LABEL[pc["rarity"]], inline=True)
        embed.add_field(name="Element", value=pc["element"],  inline=True)
        embed.add_field(name="Level",   value=str(lv),        inline=True)
        embed.add_field(name="Tier",    value=f"x{pc['tier']}", inline=True)
        embed.add_field(name="❤️ HP",  value=str(hp),         inline=True)
        embed.add_field(name="⚔️ ATK", value=str(atk),        inline=True)
        embed.add_field(name="🛡️ DEF", value=str(def_),       inline=True)
        embed.set_footer(text=f"Warrior ID: {char_id} • Use !select {char_id} to equip")
        await ctx.send(embed=embed)

    # ── !select ───────────────────────────────────────────────────────
    @commands.command(name="select")
    async def select(self, ctx, char_id: int = None):
        """Select a warrior as your active fighter. Usage: !select <ID>"""
        if char_id is None:
            await ctx.send("❌ Usage: `!select <warrior ID>`")
            return

        conn = db.get_conn()
        pc = conn.execute(
            "SELECT pc.id, ch.name FROM player_characters pc JOIN characters ch ON pc.char_id=ch.id WHERE pc.id=%s AND pc.user_id=%s",
            (char_id, str(ctx.author.id))
        ).fetchone()

        if not pc:
            conn.close()
            await ctx.send(f"❌ No warrior with ID `{char_id}` in your inventory.")
            return

        conn.execute("UPDATE players SET selected_char=%s WHERE user_id=%s", (char_id, str(ctx.author.id)))
        conn.commit()
        conn.close()

        await ctx.send(f"✅ **{pc['name']}** is now your selected warrior! Use `!profile` to verify.")

    # ── !fav ─────────────────────────────────────────────────────────
    @commands.command(name="fav")
    async def fav(self, ctx, char_id: int = None):
        """Favourite/unfavourite a warrior. Usage: !fav <ID>"""
        if char_id is None:
            await ctx.send("❌ Usage: `!fav <warrior ID>`")
            return

        conn = db.get_conn()
        pc = conn.execute(
            "SELECT pc.id, pc.is_favorite, ch.name FROM player_characters pc JOIN characters ch ON pc.char_id=ch.id WHERE pc.id=%s AND pc.user_id=%s",
            (char_id, str(ctx.author.id))
        ).fetchone()

        if not pc:
            conn.close()
            await ctx.send(f"❌ No warrior with ID `{char_id}` in your inventory.")
            return

        new_fav = 0 if pc["is_favorite"] else 1
        conn.execute("UPDATE player_characters SET is_favorite=%s WHERE id=%s", (new_fav, char_id))
        conn.commit()
        conn.close()

        status = "⭐ added to" if new_fav else "removed from"
        await ctx.send(f"**{pc['name']}** {status} favourites!")

    # ── !favs ─────────────────────────────────────────────────────────
    @commands.command(name="favs", aliases=["favorites", "fav_list"])
    async def favs(self, ctx):
        """View your favourite warriors."""
        conn = db.get_conn()
        rows = conn.execute(
            """SELECT pc.id, pc.level, pc.tier, ch.name, ch.rarity, ch.element
               FROM player_characters pc JOIN characters ch ON pc.char_id=ch.id
               WHERE pc.user_id=%s AND pc.is_favorite=1""",
            (str(ctx.author.id),)
        ).fetchall()
        conn.close()

        if not rows:
            await ctx.send("⭐ You have no favourite warriors yet. Use `!fav <ID>`.")
            return

        lines = []
        for pc in rows:
            r = config.RARITY_EMOJI.get(pc["rarity"], "")
            e = config.ELEMENT_EMOJI.get(pc["element"], "")
            lines.append(f"{r} **(ID:{pc['id']})** {pc['name']} {e} — Lv.{pc['level']} | Tier:x{pc['tier']}")

        embed = discord.Embed(
            title=f"⭐ {ctx.author.name}'s Favourite Warriors",
            description="\n".join(lines),
            color=config.COLOR_GOLD
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Characters(bot))
