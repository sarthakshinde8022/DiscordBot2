import discord
from discord.ext import commands
import asyncio
import random
from datetime import datetime, timedelta
import config
import database as db

TOWER_LEVELS = {
    1: {"name": "Chaukidar",  "label": "Easy",    "enemies": [
            ("Bijapur Footman",  1500, 120, 90,  "Earth"),
            ("Adilshahi Guard",  2000, 150, 110, "Dark"),
            ("Senior Guard",     2800, 190, 140, "Earth"),
        ], "reward_hon": 150, "reward_xp": 60,  "reward_keys": 0},
    2: {"name": "Havaldar",   "label": "Medium",  "enemies": [
            ("Mughal Soldier",   2500, 180, 130, "Dark"),
            ("Mughal Cavalry",   3200, 220, 160, "Wind"),
            ("Mughal Sardar",    4000, 270, 190, "Dark"),
        ], "reward_hon": 280, "reward_xp": 110, "reward_keys": 0},
    3: {"name": "Sardar",     "label": "Hard",    "enemies": [
            ("Rajput Warrior",   4000, 260, 180, "Fire"),
            ("Rajput Commander", 5500, 320, 220, "Fire"),
            ("Rajput General",   7000, 390, 270, "Fire"),
        ], "reward_hon": 500, "reward_xp": 200, "reward_keys": 1},
    4: {"name": "Senapati",   "label": "Extreme", "enemies": [
            ("Imperial Guard",   6000, 380, 260, "Dark"),
            ("Mughal Champion",  8000, 460, 310, "Dark"),
            ("Aurangzeb's Elite",10000,550, 380, "Dark"),
        ], "reward_hon": 900, "reward_xp": 350, "reward_keys": 2},
}

TOWER_COOLDOWN_HOURS = 6

def get_player(user_id):
    conn = db.get_conn()
    p = conn.execute("SELECT * FROM players WHERE user_id=%s", (str(user_id),)).fetchone()
    conn.close()
    return p

def get_fighter(user_id):
    conn = db.get_conn()
    row = conn.execute(
        """SELECT pc.id, pc.level, ch.name, ch.rarity, ch.element,
                  ch.base_hp, ch.base_atk, ch.base_def,
                  ch.move1_name, ch.move1_power, ch.move2_name, ch.move2_power,
                  ch.move3_name, ch.move3_power, ch.move4_name, ch.move4_power
           FROM players p
           JOIN player_characters pc ON pc.id = p.selected_char
           JOIN characters ch ON pc.char_id = ch.id
           WHERE p.user_id = %s""", (str(user_id),)
    ).fetchone()
    conn.close()
    if not row:
        return None
    lv = row["level"]
    scale = 1 + 0.05 * (lv - 1)
    return {
        "name": row["name"], "rarity": row["rarity"], "element": row["element"], "level": lv,
        "hp":   int(row["base_hp"] * scale),
        "atk":  int(row["base_atk"] * scale),
        "def":  int(row["base_def"] * scale),
        "moves": [
            {"name": row["move1_name"], "power": int(row["move1_power"] * scale)},
            {"name": row["move2_name"], "power": int(row["move2_power"] * scale)},
            {"name": row["move3_name"], "power": int(row["move3_power"] * scale)},
            {"name": row["move4_name"], "power": int(row["move4_power"] * scale)},
        ]
    }

def element_mult(a, d):
    adv = {"Fire":"Wind","Wind":"Earth","Earth":"Water","Water":"Fire","Light":"Dark","Dark":"Light"}
    if adv.get(a) == d: return 1.25
    if adv.get(d) == a: return 0.80
    return 1.0

def hp_bar(current, maximum):
    filled = max(0, int((current / maximum) * 12))
    return "🟩" * filled + "⬛" * (12 - filled)

def power_bar(power, max_power=800):
    filled = min(10, int((power / max_power) * 10))
    return "█" * filled + "░" * (10 - filled)

class Tower(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = set()

    @commands.command(name="tc", aliases=["tower", "towerchallenge"])
    async def tower(self, ctx, difficulty: int = None):
        """Tower Challenge. Usage: jay!tc or jay!tc <1-4>"""
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        if difficulty is None:
            embed = discord.Embed(title="🏰 Gadkille Tower — Choose Difficulty", color=config.COLOR_MAIN)
            for lvl, data in TOWER_LEVELS.items():
                key_txt = f" + {data['reward_keys']} 🗝️ Boss Key" if data["reward_keys"] else ""
                embed.add_field(
                    name=f"`jay!tc {lvl}` — {data['name']} ({data['label']})",
                    value=f"3 enemies | Rewards: {data['reward_hon']} 🪙 + {data['reward_xp']} XP{key_txt}",
                    inline=False
                )
            embed.set_footer(text="Tower resets every 6 hours! 🗝️ Keys needed for jay!boss")
            await ctx.send(embed=embed)
            return

        if difficulty not in TOWER_LEVELS:
            await ctx.send("❌ Choose difficulty 1 (Easy) to 4 (Extreme).")
            return

        # Cooldown check
        conn = db.get_conn()
        attempt = conn.execute("SELECT last_attempt FROM tower_attempts WHERE user_id=%s", (str(ctx.author.id),)).fetchone()
        conn.close()

        if attempt and attempt["last_attempt"]:
            last = datetime.fromisoformat(attempt["last_attempt"])
            diff = datetime.utcnow() - last
            if diff < timedelta(hours=TOWER_COOLDOWN_HOURS):
                remaining = timedelta(hours=TOWER_COOLDOWN_HOURS) - diff
                hrs = int(remaining.total_seconds() // 3600)
                mins = int((remaining.total_seconds() % 3600) // 60)
                await ctx.send(f"🏰 Tower resets in **{hrs}h {mins}m**. Come back later!")
                return

        fighter = get_fighter(str(ctx.author.id))
        if not fighter:
            await ctx.send("❌ Select a warrior with `jay!select <ID>`!")
            return

        level_data = TOWER_LEVELS[difficulty]
        channel_id = ctx.channel.id

        if channel_id in self.active:
            await ctx.send("⚠️ A tower battle is already running here!")
            return

        self.active.add(channel_id)

        fr = config.RARITY_EMOJI.get(fighter["rarity"], "")
        fe = config.ELEMENT_EMOJI.get(fighter["element"], "")

        embed = discord.Embed(
            title=f"🏰 Gadkille Tower — {level_data['name']} ({level_data['label']})",
            description=(
                f"3 enemies stand between you and glory!\n\n"
                f"**Your Warrior:** {fr} {fighter['name']} {fe} Lv.{fighter['level']}\n"
                f"HP: `{fighter['hp']:,}` | ATK: `{fighter['atk']}` | DEF: `{fighter['def']}`\n\n"
                f"⚔️ Starting in 2 seconds..."
            ),
            color=config.COLOR_MAIN
        )
        await ctx.send(embed=embed)
        await asyncio.sleep(2)

        player_hp = fighter["hp"]
        max_php   = fighter["hp"]
        total_dmg = 0
        won_all   = True

        def move_check(m):
            return (m.author.id == ctx.author.id and
                    m.channel == ctx.channel and
                    m.content in ["1","2","3","4"])

        try:
            for stage, (ename, ehp, eatk, edef, eel) in enumerate(level_data["enemies"], 1):
                if player_hp <= 0:
                    won_all = False
                    break

                max_ehp   = ehp
                ee        = config.ELEMENT_EMOJI.get(eel, "")

                await ctx.send(embed=discord.Embed(
                    title=f"🏰 Stage {stage}/3 — {ename}",
                    description=f"{ee} **{ename}** | HP:`{ehp:,}` ATK:`{eatk}` DEF:`{edef}`\n\nChoose your move!",
                    color=config.COLOR_ERROR
                ))

                stage_turn = 0
                while player_hp > 0 and ehp > 0 and stage_turn < 20:
                    stage_turn += 1

                    # Move selection UI
                    battle_embed = discord.Embed(
                        title=f"Stage {stage} — Turn {stage_turn}",
                        color=config.COLOR_MAIN
                    )
                    battle_embed.add_field(
                        name=f"{fr} {fighter['name']}",
                        value=f"{hp_bar(player_hp, max_php)} `{player_hp:,}`",
                        inline=True
                    )
                    battle_embed.add_field(
                        name=f"{ee} {ename}",
                        value=f"{hp_bar(ehp, max_ehp)} `{ehp:,}`",
                        inline=True
                    )
                    for i, mv in enumerate(fighter["moves"], 1):
                        battle_embed.add_field(
                            name=f"`{i}` {mv['name']}",
                            value=f"`{power_bar(mv['power'])}` {mv['power']}",
                            inline=True
                        )
                    battle_embed.set_footer(text="Type 1, 2, 3 or 4 • 20 seconds")
                    await ctx.send(embed=battle_embed)

                    try:
                        msg = await self.bot.wait_for("message", check=move_check, timeout=20.0)
                        move_idx = int(msg.content) - 1
                    except asyncio.TimeoutError:
                        self.active.discard(channel_id)
                        await ctx.send("⏰ Battle timed out!")
                        return

                    chosen = fighter["moves"][move_idx]
                    mult   = element_mult(fighter["element"], eel)
                    dmg    = int(max(1, chosen["power"] - edef // 3) * mult * random.uniform(0.9, 1.15))
                    ehp   -= dmg
                    total_dmg += dmg
                    crit_t = " 💥 **Advantage!**" if mult > 1 else ""

                    edesc = f"⚔️ **{chosen['name']}** hits `{dmg}`!{crit_t}"
                    if ehp > 0:
                        mult2  = element_mult(eel, fighter["element"])
                        edmg   = int(max(1, eatk - fighter["def"] // 3) * mult2 * random.uniform(0.9, 1.15))
                        player_hp -= edmg
                        edesc += f"\n{ee} **{ename}** counters for `{edmg}`!"

                    res = discord.Embed(
                        title=f"Stage {stage} — Turn {stage_turn}",
                        description=edesc,
                        color=config.COLOR_GOLD if ehp <= 0 else config.COLOR_INFO
                    )
                    res.add_field(name=f"{fr} Your HP", value=f"{hp_bar(max(0,player_hp), max_php)} `{max(0,player_hp):,}`", inline=True)
                    res.add_field(name=f"{ee} Enemy HP", value=f"{hp_bar(max(0,ehp), max_ehp)} `{max(0,ehp):,}`", inline=True)
                    await ctx.send(embed=res)
                    await asyncio.sleep(0.8)

                if ehp > 0:
                    won_all = False
                    break
                elif stage < len(level_data["enemies"]):
                    await ctx.send(f"✅ **{ename} defeated!** Next enemy incoming...")
                    await asyncio.sleep(1.5)

        finally:
            self.active.discard(channel_id)

        # Record attempt
        conn = db.get_conn()
        conn.execute(
            "INSERT INTO tower_attempts (user_id, last_attempt) VALUES (%s,%s) ON CONFLICT (user_id) DO UPDATE SET last_attempt=EXCLUDED.last_attempt",
            (str(ctx.author.id), datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

        if won_all:
            conn = db.get_conn()
            conn.execute(
                "UPDATE players SET hon=hon+%s, xp=xp+%s, boss_keys=boss_keys+%s WHERE user_id=%s",
                (level_data["reward_hon"], level_data["reward_xp"], level_data["reward_keys"], str(ctx.author.id))
            )
            conn.commit()
            new_keys = conn.execute("SELECT boss_keys FROM players WHERE user_id=%s", (str(ctx.author.id),)).fetchone()["boss_keys"]
            conn.close()

            key_txt = f"\n🗝️ **+{level_data['reward_keys']} Boss Key!** (Total: {new_keys})" if level_data["reward_keys"] else ""
            win = discord.Embed(
                title=f"🏆 Tower Cleared — {level_data['name']} ({level_data['label']})!",
                description=(
                    f"All 3 enemies defeated! Swarajya prevails!\n"
                    f"Total Damage: `{total_dmg:,}`\n\n"
                    f"**Rewards:**\n"
                    f"+{level_data['reward_hon']} 🪙 Hon\n"
                    f"+{level_data['reward_xp']} ✨ XP{key_txt}\n\n"
                    f"Tower resets in **{TOWER_COOLDOWN_HOURS} hours**!"
                ),
                color=config.COLOR_SUCCESS
            )
            await ctx.send(embed=win)
        else:
            lose = discord.Embed(
                title="💀 Tower Failed!",
                description=(
                    f"You were defeated before clearing all stages.\n"
                    f"Total Damage: `{total_dmg:,}`\n\n"
                    f"Try a lower difficulty or summon stronger warriors!"
                ),
                color=config.COLOR_ERROR
            )
            await ctx.send(embed=lose)

    @commands.command(name="keys", aliases=["bosskeys"])
    async def keys(self, ctx):
        """Check your Boss Keys."""
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return
        await ctx.send(
            f"🗝️ **{ctx.author.name}** has **{player['boss_keys']} Boss Key(s)**.\n"
            f"Use `jay!boss` to fight a boss (costs 1 key).\n"
            f"Earn keys by completing `jay!tc 3` or `jay!tc 4`!"
        )

async def setup(bot):
    await bot.add_cog(Tower(bot))
