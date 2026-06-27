import discord
from discord.ext import commands
import asyncio
import random
import config
import database as db

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
        "name":    row["name"], "rarity": row["rarity"], "element": row["element"], "level": lv,
        "hp":      int(row["base_hp"] * scale),
        "atk":     int(row["base_atk"] * scale),
        "def":     int(row["base_def"] * scale),
        "moves": [
            {"name": row["move1_name"], "power": int(row["move1_power"] * scale)},
            {"name": row["move2_name"], "power": int(row["move2_power"] * scale)},
            {"name": row["move3_name"], "power": int(row["move3_power"] * scale)},
            {"name": row["move4_name"], "power": int(row["move4_power"] * scale)},
        ]
    }

def power_bar(power, max_power=800):
    filled = min(10, int((power / max_power) * 10))
    return "█" * filled + "░" * (10 - filled)

def element_mult(atk_el, def_el):
    adv = {"Fire":"Wind","Wind":"Earth","Earth":"Water","Water":"Fire","Light":"Dark","Dark":"Light"}
    if adv.get(atk_el) == def_el: return 1.25
    if adv.get(def_el) == atk_el: return 0.80
    return 1.0

class Saga(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_battles = {}  # channel_id -> battle state

    # ── jay!saga ──────────────────────────────────────────────────────
    @commands.command(name="saga", aliases=["sagas"])
    async def saga(self, ctx, saga_num: int = None):
        """View or select a saga. Usage: jay!saga or jay!saga 1"""
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        conn = db.get_conn()
        sagas = conn.execute("SELECT * FROM sagas ORDER BY id").fetchall()
        conn.close()

        if saga_num is None:
            # Show saga list
            embed = discord.Embed(
                title="📜 Available Sagas in Swarajya",
                description="Play a saga by entering the saga number\nExample: `jay!saga 1` for Swarajya Saga\n",
                color=config.COLOR_MAIN
            )
            from cogs.general import level_from_xp
            player_level = level_from_xp(player["xp"])

            lines = []
            for s in sagas:
                locked = player_level < s["unlock_level"]
                icon = "🔒" if locked else "📖"
                lines.append(f"{icon} **{s['name']}** (`jay!saga {s['id']}`)" +
                             (f" _(Unlocks at Lv.{s['unlock_level']})_" if locked else ""))
            embed.description += "\n".join(lines)
            embed.set_footer(text="Complete missions to earn Boss Keys 🗝️!")
            await ctx.send(embed=embed)
            return

        # Select a saga
        conn = db.get_conn()
        saga = conn.execute("SELECT * FROM sagas WHERE id=%s", (saga_num,)).fetchone()
        conn.close()

        if not saga:
            await ctx.send(f"❌ Saga {saga_num} doesn't exist! Use `jay!saga` to see all.")
            return

        from cogs.general import level_from_xp
        player_level = level_from_xp(player["xp"])
        if player_level < saga["unlock_level"]:
            await ctx.send(f"🔒 **{saga['name']}** unlocks at Level {saga['unlock_level']}. You are Lv.{player_level}.")
            return

        # Set active saga
        conn = db.get_conn()
        conn.execute("UPDATE players SET active_saga=%s WHERE user_id=%s", (saga_num, str(ctx.author.id)))
        conn.commit()
        conn.close()

        await ctx.send(
            f"✅ You chose **{saga['name']}**\n"
            f"_{saga['description']}_\n\n"
            f"Complete missions using `jay!mi` or `jay!mission`\n"
            f"Use `jay!mi <number>` to fight a specific mission."
        )

    # ── jay!mi ────────────────────────────────────────────────────────
    @commands.command(name="mi", aliases=["mission"])
    async def mission(self, ctx, mission_num: int = None):
        """View or fight a mission. Usage: jay!mi or jay!mi 1"""
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        saga_id = player["active_saga"]
        if not saga_id:
            await ctx.send("❌ Select a saga first with `jay!saga <number>`!")
            return

        conn = db.get_conn()
        saga    = conn.execute("SELECT * FROM sagas WHERE id=%s", (saga_id,)).fetchone()
        missions = conn.execute("SELECT * FROM missions WHERE saga_id=%s ORDER BY mission_num", (saga_id,)).fetchall()
        completed = {
            row["mission_num"]
            for row in conn.execute(
                "SELECT mission_num FROM player_missions WHERE user_id=%s AND saga_id=%s AND completed=1",
                (str(ctx.author.id), saga_id)
            ).fetchall()
        }
        conn.close()

        if mission_num is None:
            # Show mission list
            embed = discord.Embed(
                title=f"☐ {saga['name']}",
                description=f"Choose a mission using `jay!mi <number>`\nExample: `jay!mi 1`\n",
                color=config.COLOR_MAIN
            )
            lines = []
            for m in missions:
                done = m["mission_num"] in completed
                icon = "✅" if done else "🔒"
                key_note = " 🗝️" if m["reward_keys"] > 0 else ""
                lines.append(f"{icon} **{m['name']}** (`jay!mi {m['mission_num']}`){key_note}")
            embed.description += "\n".join(lines)
            embed.set_footer(text="🗝️ = Rewards a Boss Key on completion!")
            await ctx.send(embed=embed)
            return

        # Fight a mission
        conn = db.get_conn()
        mission = conn.execute(
            "SELECT * FROM missions WHERE saga_id=%s AND mission_num=%s", (saga_id, mission_num)
        ).fetchone()
        conn.close()

        if not mission:
            await ctx.send(f"❌ Mission {mission_num} not found in this saga!")
            return

        fighter = get_fighter(str(ctx.author.id))
        if not fighter:
            await ctx.send("❌ Select a warrior first with `jay!select <ID>`!")
            return

        # Start interactive battle
        await self._run_mission_battle(ctx, player, fighter, mission, saga)

    async def _run_mission_battle(self, ctx, player, fighter, mission, saga):
        """Interactive turn-based mission battle."""
        channel_id = ctx.channel.id
        if channel_id in self.active_battles:
            await ctx.send("⚠️ A battle is already active in this channel!")
            return

        fr = config.RARITY_EMOJI.get(fighter["rarity"], "")
        fe = config.ELEMENT_EMOJI.get(fighter["element"], "")
        ee = config.ELEMENT_EMOJI.get(mission["enemy_element"], "")

        # Opening embed
        embed = discord.Embed(
            title=f"⚔️ {saga['name']} — {mission['name']}",
            description=(
                f"*{mission['description']}*\n\n"
                f"**Enemy:** {ee} **{mission['enemy_name']}**\n"
                f"HP: `{mission['enemy_hp']:,}` | ATK: `{mission['enemy_atk']}` | DEF: `{mission['enemy_def']}`\n\n"
                f"**Your Warrior:** {fr} {fighter['name']} {fe} Lv.{fighter['level']}\n"
                f"HP: `{fighter['hp']:,}` | ATK: `{fighter['atk']}` | DEF: `{fighter['def']}`\n\n"
                f"⚔️ Battle starting in 2 seconds..."
            ),
            color=config.COLOR_ERROR
        )
        await ctx.send(embed=embed)
        await asyncio.sleep(2)

        # Battle state
        player_hp  = fighter["hp"]
        enemy_hp   = mission["enemy_hp"]
        max_phm    = fighter["hp"]
        max_ehp    = mission["enemy_hp"]
        total_dmg  = 0
        turn       = 0

        self.active_battles[channel_id] = True

        def hp_bar(current, maximum):
            filled = max(0, int((current / maximum) * 12))
            return "🟩" * filled + "⬛" * (12 - filled)

        def move_check(m):
            return (m.author.id == ctx.author.id and
                    m.channel == ctx.channel and
                    m.content in ["1", "2", "3", "4"])

        try:
            while player_hp > 0 and enemy_hp > 0 and turn < 30:
                turn += 1

                # Show move selection
                moves = fighter["moves"]
                move_lines = []
                for i, mv in enumerate(moves, 1):
                    bar = power_bar(mv["power"])
                    move_lines.append(
                        f"**{i}.** {mv['name']}\n"
                        f"Power: `{bar}` {mv['power']}\n"
                        f"Usage: `{i}`"
                    )

                battle_embed = discord.Embed(
                    title=f"Turn {turn} — Choose your move!",
                    color=config.COLOR_MAIN
                )
                battle_embed.add_field(
                    name=f"{fr} {fighter['name']} {fe}",
                    value=f"HP: {hp_bar(player_hp, max_phm)} `{player_hp:,}`",
                    inline=False
                )
                battle_embed.add_field(
                    name=f"{ee} {mission['enemy_name']}",
                    value=f"HP: {hp_bar(enemy_hp, max_ehp)} `{enemy_hp:,}`",
                    inline=False
                )
                for i, mv in enumerate(moves, 1):
                    bar = power_bar(mv["power"])
                    battle_embed.add_field(
                        name=f"`{i}` {mv['name']}",
                        value=f"`{bar}` Pow:{mv['power']}",
                        inline=True
                    )
                battle_embed.set_footer(text="Type 1, 2, 3, or 4 to attack • 20 seconds")
                await ctx.send(embed=battle_embed)

                # Wait for move
                try:
                    msg = await self.bot.wait_for("message", check=move_check, timeout=20.0)
                    move_idx = int(msg.content) - 1
                except asyncio.TimeoutError:
                    self.active_battles.pop(channel_id, None)
                    await ctx.send("⏰ **Battle timed out!** You took too long to choose a move.")
                    return

                chosen_move = moves[move_idx]

                # Player attacks
                mult = element_mult(fighter["element"], mission["enemy_element"])
                dmg  = int(max(1, chosen_move["power"] - mission["enemy_def"] // 3) * mult * random.uniform(0.9, 1.15))
                enemy_hp -= dmg
                total_dmg += dmg
                crit_txt = " 💥 **Element Advantage!**" if mult > 1.0 else ""

                # Enemy attacks back
                if enemy_hp > 0:
                    mult2  = element_mult(mission["enemy_element"], fighter["element"])
                    edm    = int(max(1, mission["enemy_atk"] - fighter["def"] // 3) * mult2 * random.uniform(0.9, 1.15))
                    player_hp -= edm
                    enemy_txt = f"\n{ee} **{mission['enemy_name']}** counterattacks for `{edm}` dmg!"
                else:
                    enemy_txt = ""

                result_embed = discord.Embed(
                    title=f"Turn {turn} Result",
                    description=(
                        f"⚔️ **{fighter['name']}** uses **{chosen_move['name']}**!{crit_txt}\n"
                        f"Dealt `{dmg}` damage!{enemy_txt}"
                    ),
                    color=config.COLOR_GOLD if enemy_hp <= 0 else config.COLOR_INFO
                )
                result_embed.add_field(
                    name=f"{fr} Your HP",
                    value=f"{hp_bar(max(0,player_hp), max_phm)} `{max(0,player_hp):,}`",
                    inline=True
                )
                result_embed.add_field(
                    name=f"{ee} Enemy HP",
                    value=f"{hp_bar(max(0,enemy_hp), max_ehp)} `{max(0,enemy_hp):,}`",
                    inline=True
                )
                await ctx.send(embed=result_embed)
                await asyncio.sleep(1)

        finally:
            self.active_battles.pop(channel_id, None)

        # Battle over
        if player_hp > 0 and enemy_hp <= 0:
            # Victory!
            conn = db.get_conn()
            conn.execute(
                "INSERT INTO player_missions (user_id, saga_id, mission_num, completed) VALUES (%s,%s,%s,1) ON CONFLICT (user_id, saga_id, mission_num) DO UPDATE SET completed=1",
                (str(ctx.author.id), saga["id"], mission["mission_num"])
            )
            conn.execute(
                "UPDATE players SET hon=hon+%s, xp=xp+%s, boss_keys=boss_keys+%s WHERE user_id=%s",
                (mission["reward_hon"], mission["reward_xp"], mission["reward_keys"], str(ctx.author.id))
            )
            conn.commit()
            conn.close()

            key_txt = f"\n🗝️ **+{mission['reward_keys']} Boss Key** earned!" if mission["reward_keys"] > 0 else ""
            win_embed = discord.Embed(
                title=f"🏆 Victory! {mission['enemy_name']} defeated!",
                description=(
                    f"**{fighter['name']}** won in {turn} turns!\n"
                    f"Total Damage: `{total_dmg:,}`\n\n"
                    f"**Rewards:**\n"
                    f"+{mission['reward_hon']} 🪙 Hon\n"
                    f"+{mission['reward_xp']} ✨ XP{key_txt}\n\n"
                    f"Use `jay!mi` to see next missions!"
                ),
                color=config.COLOR_SUCCESS
            )
            await ctx.send(embed=win_embed)
        else:
            lose_embed = discord.Embed(
                title=f"💀 Defeated by {mission['enemy_name']}!",
                description=(
                    f"You lasted {turn} turns and dealt `{total_dmg:,}` damage.\n\n"
                    f"**Tips:**\n"
                    f"• Use `jay!summon` to get stronger warriors\n"
                    f"• Pick a warrior with element advantage\n"
                    f"• Try `jay!daily` and `jay!roll` for more Hon"
                ),
                color=config.COLOR_ERROR
            )
            await ctx.send(embed=lose_embed)


async def setup(bot):
    await bot.add_cog(Saga(bot))
