import discord
from discord.ext import commands
from datetime import datetime, timedelta
import random
import config
import database as db

RARITY_COLOR = config.RARITY_COLOR
RARITY_EMOJI = config.RARITY_EMOJI
RARITY_LABEL = config.RARITY_LABEL

ITEM_TYPE_EMOJI = {
    "weapon":  "🗡️",
    "armor":   "🛡️",
    "helmet":  "⛑️",
}

EGG_TYPES = {
    "small":  {"name": "Small Egg",  "emoji": "🥚", "hatch_hours": 4,  "cost": 500,  "rates": {"R":0.45,"E":0.35,"L":0.20}},
    "medium": {"name": "Medium Egg", "emoji": "🥚", "hatch_hours": 6,  "cost": 1000, "rates": {"R":0.40,"E":0.32,"L":0.27,"God":0.01}},
    "large":  {"name": "Large Egg",  "emoji": "🥚", "hatch_hours": 2,  "cost": 2000, "rates": {"L":0.90,"God":0.10}},
}

def get_player(user_id):
    conn = db.get_conn()
    p = conn.execute("SELECT * FROM players WHERE user_id=?", (str(user_id),)).fetchone()
    conn.close()
    return p

class Items(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── jay!items ─────────────────────────────────────────────────────
    @commands.command(name="items", aliases=["item", "inventory_items"])
    async def items_cmd(self, ctx, page: int = 1):
        """View your item inventory. Usage: jay!items"""
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        conn = db.get_conn()
        rows = conn.execute(
            """SELECT pi.id, pi.level, pi.is_equipped, pi.is_favorite,
                      i.name, i.type, i.rarity, i.atk_bonus, i.def_bonus, i.hp_bonus
               FROM player_items pi JOIN items i ON pi.item_id = i.id
               WHERE pi.user_id = ?
               ORDER BY i.rarity DESC, i.type""",
            (str(ctx.author.id),)
        ).fetchall()
        conn.close()

        if not rows:
            await ctx.send("🎒 You have no items yet! Buy from `jay!shop` or earn from missions.")
            return

        PER_PAGE = 10
        total = len(rows)
        total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
        page = max(1, min(page, total_pages))
        chunk = rows[(page-1)*PER_PAGE : page*PER_PAGE]

        embed = discord.Embed(title=f"🎒 {ctx.author.name}'s Item Inventory", color=config.COLOR_MAIN)
        for item in chunk:
            r  = RARITY_EMOJI.get(item["rarity"], "")
            t  = ITEM_TYPE_EMOJI.get(item["type"], "📦")
            eq = " **[EQUIPPED]**" if item["is_equipped"] else ""
            fv = " ⭐" if item["is_favorite"] else ""
            stats = []
            if item["atk_bonus"]: stats.append(f"ATK+{item['atk_bonus']}")
            if item["def_bonus"]: stats.append(f"DEF+{item['def_bonus']}")
            if item["hp_bonus"]:  stats.append(f"HP+{item['hp_bonus']}")
            embed.add_field(
                name=f"{t} {r} {item['name']} (ID:{item['id']}){eq}{fv}",
                value=f"Lv.{item['level']} | {' | '.join(stats)}",
                inline=False
            )
        embed.set_footer(text=f"Page [{page}/{total_pages}] • jay!iinfo <ID> • jay!iequip <charID> <itemID>")
        await ctx.send(embed=embed)

    # ── jay!iinfo ─────────────────────────────────────────────────────
    @commands.command(name="iinfo", aliases=["iteminfo", "ii"])
    async def iinfo(self, ctx, item_id: int = None):
        """View item details. Usage: jay!iinfo <ID>"""
        if not item_id:
            await ctx.send("❌ Usage: `jay!iinfo <item ID>`")
            return
        conn = db.get_conn()
        row = conn.execute(
            """SELECT pi.id, pi.level, pi.is_equipped, i.*
               FROM player_items pi JOIN items i ON pi.item_id=i.id
               WHERE pi.id=? AND pi.user_id=?""",
            (item_id, str(ctx.author.id))
        ).fetchone()
        conn.close()
        if not row:
            await ctx.send(f"❌ No item with ID `{item_id}` in your inventory.")
            return

        r = RARITY_EMOJI.get(row["rarity"], "")
        t = ITEM_TYPE_EMOJI.get(row["type"], "📦")
        color = RARITY_COLOR.get(row["rarity"], config.COLOR_MAIN)
        lv = row["level"]
        atk = int(row["atk_bonus"] * (1 + 0.1*(lv-1)))
        def_ = int(row["def_bonus"] * (1 + 0.1*(lv-1)))
        hp  = int(row["hp_bonus"]  * (1 + 0.1*(lv-1)))

        embed = discord.Embed(
            title=f"{t} {r} {row['name']}",
            description=row["description"],
            color=color
        )
        embed.add_field(name="Type",    value=row["type"].capitalize(), inline=True)
        embed.add_field(name="Rarity",  value=RARITY_LABEL.get(row["rarity"],"?"), inline=True)
        embed.add_field(name="Level",   value=str(lv), inline=True)
        if atk:  embed.add_field(name="⚔️ ATK Bonus", value=f"+{atk}", inline=True)
        if def_: embed.add_field(name="🛡️ DEF Bonus", value=f"+{def_}", inline=True)
        if hp:   embed.add_field(name="❤️ HP Bonus",  value=f"+{hp}",  inline=True)
        embed.add_field(name="Status", value="**EQUIPPED**" if row["is_equipped"] else "In inventory", inline=True)
        embed.set_footer(text=f"Item ID: {item_id} • jay!iequip <charID> {item_id}")
        await ctx.send(embed=embed)

    # ── jay!iequip ────────────────────────────────────────────────────
    @commands.command(name="iequip", aliases=["itemequip", "ie"])
    async def iequip(self, ctx, char_id: int = None, item_id: int = None):
        """Equip an item to a warrior. Usage: jay!iequip <charID> <itemID>"""
        if not char_id or not item_id:
            await ctx.send("❌ Usage: `jay!iequip <warrior ID> <item ID>`")
            return

        conn = db.get_conn()
        # Verify warrior belongs to player
        pc = conn.execute(
            "SELECT pc.id, ch.name FROM player_characters pc JOIN characters ch ON pc.char_id=ch.id WHERE pc.id=? AND pc.user_id=?",
            (char_id, str(ctx.author.id))
        ).fetchone()
        if not pc:
            conn.close()
            await ctx.send(f"❌ No warrior with ID `{char_id}` in your inventory.")
            return

        # Verify item belongs to player
        pi = conn.execute(
            "SELECT pi.id, i.name, i.type FROM player_items pi JOIN items i ON pi.item_id=i.id WHERE pi.id=? AND pi.user_id=?",
            (item_id, str(ctx.author.id))
        ).fetchone()
        if not pi:
            conn.close()
            await ctx.send(f"❌ No item with ID `{item_id}` in your inventory.")
            return

        # Unequip any existing item of same type on this warrior
        conn.execute(
            """UPDATE player_items SET is_equipped=0, equipped_to=NULL
               WHERE user_id=? AND equipped_to=? AND item_id IN
               (SELECT id FROM items WHERE type=?)""",
            (str(ctx.author.id), char_id, pi["type"])
        )
        # Equip new item
        conn.execute(
            "UPDATE player_items SET is_equipped=1, equipped_to=? WHERE id=?",
            (char_id, item_id)
        )
        conn.commit()
        conn.close()

        t = ITEM_TYPE_EMOJI.get(pi["type"], "📦")
        await ctx.send(f"✅ {t} **{pi['name']}** equipped to **{pc['name']}**!")

    # ── jay!iunequip ──────────────────────────────────────────────────
    @commands.command(name="iunequip", aliases=["itemunequip", "iue"])
    async def iunequip(self, ctx, item_id: int = None):
        """Unequip an item. Usage: jay!iunequip <itemID>"""
        if not item_id:
            await ctx.send("❌ Usage: `jay!iunequip <item ID>`")
            return
        conn = db.get_conn()
        pi = conn.execute(
            "SELECT pi.id, i.name FROM player_items pi JOIN items i ON pi.item_id=i.id WHERE pi.id=? AND pi.user_id=? AND pi.is_equipped=1",
            (item_id, str(ctx.author.id))
        ).fetchone()
        if not pi:
            conn.close()
            await ctx.send(f"❌ Item `{item_id}` not found or not equipped.")
            return
        conn.execute("UPDATE player_items SET is_equipped=0, equipped_to=NULL WHERE id=?", (item_id,))
        conn.commit()
        conn.close()
        await ctx.send(f"✅ **{pi['name']}** unequipped!")

    # ── jay!shop ──────────────────────────────────────────────────────
    @commands.command(name="shop")
    async def shop(self, ctx, page: str = "1"):
        """Browse the shop. Usage: jay!shop or jay!shop 2 (eggs)"""
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        if page == "2":
            # Egg shop
            embed = discord.Embed(title="🥚 War Animal Egg Shop", color=config.COLOR_GOLD)
            for key, egg in EGG_TYPES.items():
                embed.add_field(
                    name=f"{egg['emoji']} {egg['name']}",
                    value=(
                        f"Cost: **{egg['cost']} 🪙 Hon**\n"
                        f"Hatch Time: **{egg['hatch_hours']}h**\n"
                        f"Rates: " + " | ".join([f"{r}:{int(v*100)}%" for r,v in egg['rates'].items()])
                        + f"\n`jay!buyegg {key}`"
                    ),
                    inline=True
                )
            embed.set_footer(text="jay!eggs — View your eggs • jay!pets — View your war animals")
            await ctx.send(embed=embed)
            return

        # Item shop
        conn = db.get_conn()
        all_items = conn.execute("SELECT * FROM items ORDER BY rarity DESC, type").fetchall()
        conn.close()

        embed = discord.Embed(title="🏪 Swarajya Armoury — Items Shop", color=config.COLOR_MAIN)
        for item in all_items:
            r = RARITY_EMOJI.get(item["rarity"], "")
            t = ITEM_TYPE_EMOJI.get(item["type"], "📦")
            stats = []
            if item["atk_bonus"]: stats.append(f"ATK+{item['atk_bonus']}")
            if item["def_bonus"]: stats.append(f"DEF+{item['def_bonus']}")
            if item["hp_bonus"]:  stats.append(f"HP+{item['hp_bonus']}")
            embed.add_field(
                name=f"{t} {r} {item['name']}",
                value=f"{' | '.join(stats)}\n**{item['cost_hon']:,} 🪙 Hon**\n`jay!buyitem {item['id']}`",
                inline=True
            )
        embed.set_footer(text="jay!shop 2 — Egg Shop • jay!bal — Check balance")
        await ctx.send(embed=embed)

    # ── jay!buyitem ───────────────────────────────────────────────────
    @commands.command(name="buyitem")
    async def buyitem(self, ctx, item_id: int = None):
        """Buy an item from the shop. Usage: jay!buyitem <ID>"""
        if not item_id:
            await ctx.send("❌ Usage: `jay!buyitem <item ID>` — check `jay!shop`")
            return
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        conn = db.get_conn()
        item = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        if not item:
            conn.close()
            await ctx.send(f"❌ Item `{item_id}` not found! Check `jay!shop`.")
            return
        if player["hon"] < item["cost_hon"]:
            conn.close()
            await ctx.send(f"❌ Not enough Hon! Need **{item['cost_hon']:,} 🪙** but you have **{player['hon']:,} 🪙**.")
            return

        conn.execute("UPDATE players SET hon=hon-? WHERE user_id=?", (item["cost_hon"], str(ctx.author.id)))
        conn.execute("INSERT INTO player_items (user_id, item_id) VALUES (?,?)", (str(ctx.author.id), item_id))
        conn.commit()
        new_hon = conn.execute("SELECT hon FROM players WHERE user_id=?", (str(ctx.author.id),)).fetchone()["hon"]
        conn.close()

        r = RARITY_EMOJI.get(item["rarity"], "")
        t = ITEM_TYPE_EMOJI.get(item["type"], "📦")
        embed = discord.Embed(
            title="🛒 Item Purchased!",
            description=f"{t} {r} **{item['name']}** added to your inventory!\n\nRemaining Hon: `{new_hon:,} 🪙`",
            color=config.COLOR_SUCCESS
        )
        embed.set_footer(text=f"Use jay!items to view • jay!iequip <charID> <itemID> to equip")
        await ctx.send(embed=embed)

    # ── jay!buyegg ────────────────────────────────────────────────────
    @commands.command(name="buyegg")
    async def buyegg(self, ctx, egg_type: str = None):
        """Buy a War Animal egg. Usage: jay!buyegg small/medium/large"""
        if not egg_type or egg_type not in EGG_TYPES:
            await ctx.send("❌ Usage: `jay!buyegg small` / `jay!buyegg medium` / `jay!buyegg large`")
            return
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        egg = EGG_TYPES[egg_type]
        if player["hon"] < egg["cost"]:
            await ctx.send(f"❌ Need **{egg['cost']:,} 🪙 Hon**. You have **{player['hon']:,} 🪙**.")
            return

        # Max 4 eggs
        conn = db.get_conn()
        egg_count = conn.execute(
            "SELECT COUNT(*) FROM player_eggs WHERE user_id=? AND hatched=0", (str(ctx.author.id),)
        ).fetchone()[0]
        if egg_count >= 4:
            conn.close()
            await ctx.send("❌ You can only hold **4 eggs** at once! Hatch some first with `jay!eggs`.")
            return

        hatch_time = (datetime.utcnow() + timedelta(hours=egg["hatch_hours"])).isoformat()
        conn.execute("UPDATE players SET hon=hon-? WHERE user_id=?", (egg["cost"], str(ctx.author.id)))
        conn.execute(
            "INSERT INTO player_eggs (user_id, egg_type, hatch_time) VALUES (?,?,?)",
            (str(ctx.author.id), egg_type, hatch_time)
        )
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title=f"🥚 {egg['name']} Purchased!",
            description=(
                f"Your egg is incubating...\n"
                f"**Hatches in:** {egg['hatch_hours']} hours\n"
                f"Check with `jay!eggs` when it's ready!"
            ),
            color=config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

    # ── jay!eggs ──────────────────────────────────────────────────────
    @commands.command(name="eggs", aliases=["egg"])
    async def eggs(self, ctx):
        """View your eggs and hatch ready ones. Usage: jay!eggs"""
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        conn = db.get_conn()
        eggs = conn.execute(
            "SELECT * FROM player_eggs WHERE user_id=? AND hatched=0 ORDER BY hatch_time",
            (str(ctx.author.id),)
        ).fetchall()
        conn.close()

        if not eggs:
            await ctx.send("🥚 No eggs! Buy eggs from `jay!shop 2`.")
            return

        now = datetime.utcnow()
        embed = discord.Embed(title="🥚 Your War Animal Eggs", color=config.COLOR_GOLD)

        for egg in eggs:
            egg_data = EGG_TYPES.get(egg["egg_type"], EGG_TYPES["small"])
            hatch_dt = datetime.fromisoformat(egg["hatch_time"])
            ready = now >= hatch_dt

            if ready:
                status = "🟢 **READY TO HATCH!** → `jay!hatch`"
            else:
                remaining = hatch_dt - now
                hrs = int(remaining.total_seconds() // 3600)
                mins = int((remaining.total_seconds() % 3600) // 60)
                status = f"⏳ Hatches in **{hrs}h {mins}m**"

            embed.add_field(
                name=f"{egg_data['emoji']} {egg_data['name']} (ID:{egg['id']})",
                value=status,
                inline=False
            )
        embed.set_footer(text="jay!hatch — Hatch a ready egg!")
        await ctx.send(embed=embed)

    # ── jay!hatch ─────────────────────────────────────────────────────
    @commands.command(name="hatch")
    async def hatch(self, ctx):
        """Hatch a ready egg! Usage: jay!hatch"""
        import asyncio
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        conn = db.get_conn()
        now = datetime.utcnow()
        ready_egg = conn.execute(
            "SELECT * FROM player_eggs WHERE user_id=? AND hatched=0 AND hatch_time <= ? LIMIT 1",
            (str(ctx.author.id), now.isoformat())
        ).fetchone()

        if not ready_egg:
            conn.close()
            await ctx.send("🥚 No eggs are ready to hatch yet! Check `jay!eggs`.")
            return

        # Pick pet rarity
        egg_data = EGG_TYPES.get(ready_egg["egg_type"], EGG_TYPES["small"])
        rates = egg_data["rates"]
        roll = random.random()
        cumulative = 0
        chosen_rarity = "R"
        for r, rate in rates.items():
            cumulative += rate
            if roll <= cumulative:
                chosen_rarity = r
                break

        # Map "God" rarity to "L" for DB lookup
        db_rarity = "L" if chosen_rarity == "God" else chosen_rarity
        pets = conn.execute("SELECT * FROM pets WHERE rarity=?", (db_rarity,)).fetchall()

        if not pets:
            conn.close()
            await ctx.send("❌ No pets found for this rarity. Try again!")
            return

        pet = random.choice(pets)
        conn.close()

        # Taming mini-game
        actions = ["🤝 Pet it", "⚔️ Fight it"]
        correct = random.choice(["pet", "fight"])
        correct_emoji = "🤝" if correct == "pet" else "⚔️"

        embed = discord.Embed(
            title="🥚 A Wild War Animal Appears!",
            description=(
                f"{pet['emoji']} **{pet['name']}** emerged from the egg!\n\n"
                f"*{pet['description']}*\n\n"
                f"**Quick! How do you tame it?**\n"
                f"Type `pet` to **pet it** 🤝 or `fight` to **fight it** ⚔️\n"
                f"_(10 seconds to decide!)_"
            ),
            color=config.COLOR_GOLD
        )
        await ctx.send(embed=embed)

        def check(m):
            return m.author.id == ctx.author.id and m.channel == ctx.channel and m.content.lower() in ["pet","fight"]

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=10.0)
            chosen = msg.content.lower()
        except asyncio.TimeoutError:
            chosen = None

        # Mark egg as hatched
        conn = db.get_conn()
        conn.execute("UPDATE player_eggs SET hatched=1 WHERE id=?", (ready_egg["id"],))

        if chosen == correct:
            conn.execute("INSERT INTO player_pets (user_id, pet_id) VALUES (?,?)", (str(ctx.author.id), pet["id"]))
            conn.commit()
            conn.close()
            win = discord.Embed(
                title=f"🎉 {pet['name']} Tamed!",
                description=(
                    f"{pet['emoji']} **{pet['name']}** joined your army!\n\n"
                    f"ATK+{pet['atk_bonus']} | DEF+{pet['def_bonus']} | HP+{pet['hp_bonus']}\n\n"
                    f"Use `jay!pets` to view and `jay!petequip <ID>` to activate!"
                ),
                color=config.COLOR_SUCCESS
            )
            await ctx.send(embed=win)
        else:
            conn.commit()
            conn.close()
            lose = discord.Embed(
                title=f"💨 {pet['name']} Escaped!",
                description=(
                    f"Wrong choice! The correct action was **{correct_emoji} {correct}**.\n"
                    f"{pet['emoji']} **{pet['name']}** ran away into the Sahyadri hills...\n\n"
                    f"Try buying another egg from `jay!shop 2`!"
                ),
                color=config.COLOR_ERROR
            )
            await ctx.send(embed=lose)

    # ── jay!pets ──────────────────────────────────────────────────────
    @commands.command(name="pets", aliases=["waranimals"])
    async def pets(self, ctx):
        """View your War Animals. Usage: jay!pets"""
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        conn = db.get_conn()
        rows = conn.execute(
            """SELECT pp.id, pp.nickname, pp.is_active, p.*
               FROM player_pets pp JOIN pets p ON pp.pet_id=p.id
               WHERE pp.user_id=?""",
            (str(ctx.author.id),)
        ).fetchall()
        conn.close()

        if not rows:
            await ctx.send(f"🐾 No war animals yet! Buy eggs from `jay!shop 2` and hatch them.")
            return

        embed = discord.Embed(title=f"🐾 {ctx.author.name}'s War Animals", color=config.COLOR_GOLD)
        for pet in rows:
            r = RARITY_EMOJI.get(pet["rarity"], "")
            active = " **[ACTIVE]**" if pet["is_active"] else ""
            name = pet["nickname"] or pet["name"]
            embed.add_field(
                name=f"{pet['emoji']} {r} {name} (ID:{pet['id']}){active}",
                value=f"ATK+{pet['atk_bonus']} | DEF+{pet['def_bonus']} | HP+{pet['hp_bonus']}",
                inline=False
            )
        embed.set_footer(text="jay!petequip <ID> — Activate a war animal")
        await ctx.send(embed=embed)

    # ── jay!petequip ──────────────────────────────────────────────────
    @commands.command(name="petequip", aliases=["petactivate"])
    async def petequip(self, ctx, pet_id: int = None):
        """Activate a war animal. Usage: jay!petequip <ID>"""
        if not pet_id:
            await ctx.send("❌ Usage: `jay!petequip <pet ID>`")
            return
        conn = db.get_conn()
        pet_row = conn.execute(
            "SELECT pp.id, p.name, p.emoji FROM player_pets pp JOIN pets p ON pp.pet_id=p.id WHERE pp.id=? AND pp.user_id=?",
            (pet_id, str(ctx.author.id))
        ).fetchone()
        if not pet_row:
            conn.close()
            await ctx.send(f"❌ No war animal with ID `{pet_id}`.")
            return
        # Deactivate all, activate selected
        conn.execute("UPDATE player_pets SET is_active=0 WHERE user_id=?", (str(ctx.author.id),))
        conn.execute("UPDATE player_pets SET is_active=1 WHERE id=?", (pet_id,))
        conn.commit()
        conn.close()
        await ctx.send(f"✅ {pet_row['emoji']} **{pet_row['name']}** is now your active War Animal!")

async def setup(bot):
    await bot.add_cog(Items(bot))
