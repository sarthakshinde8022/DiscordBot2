import discord
from discord.ext import commands
import random
import asyncio
import config
import database as db
from cogs.views import BattleAcceptView, run_interactive_battle

def get_player(user_id):
    conn = db.get_conn()
    p = conn.execute("SELECT * FROM players WHERE user_id=%s", (str(user_id),)).fetchone()
    conn.close()
    return p

def get_fighter(user_id):
    conn = db.get_conn()
    row = conn.execute(
        """SELECT pc.id, pc.level, pc.tier, ch.name, ch.rarity, ch.element,
                  ch.base_hp, ch.base_atk, ch.base_def
           FROM players p
           JOIN player_characters pc ON pc.id = p.selected_char
           JOIN characters ch ON pc.char_id = ch.id
           WHERE p.user_id = %s""",
        (str(user_id),)
    ).fetchone()
    conn.close()
    if not row:
        return None
    lv = row["level"]
    return {
        "name":    row["name"],
        "rarity":  row["rarity"],
        "element": row["element"],
        "level":   lv,
        "hp":      int(row["base_hp"]  * (1 + 0.05 * (lv - 1))),
        "atk":     int(row["base_atk"] * (1 + 0.05 * (lv - 1))),
        "def":     int(row["base_def"] * (1 + 0.05 * (lv - 1))),
    }

def ensure_battle_stats(user_id):
    conn = db.get_conn()
    conn.execute("INSERT INTO battle_stats (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (str(user_id),))
    conn.commit()
    conn.close()

def element_multiplier(atk_el, def_el):
    advantages = {
        "Fire": "Wind", "Wind": "Earth", "Earth": "Water",
        "Water": "Fire", "Light": "Dark", "Dark": "Light",
    }
    if advantages.get(atk_el) == def_el:
        return 1.25
    if advantages.get(def_el) == atk_el:
        return 0.80
    return 1.0

def simulate_battle(f1, f2):
    hp1, hp2 = f1["hp"], f2["hp"]
    log = []
    for turn in range(1, 21):
        mult = element_multiplier(f1["element"], f2["element"])
        dmg1 = int(max(1, f1["atk"] - f2["def"]//2) * mult * random.uniform(0.85, 1.15))
        hp2 -= dmg1
        crit = "💥" if mult > 1 else ""
        log.append(f"T{turn}: **{f1['name']}** hits `{dmg1}` {crit} | {f2['name']} HP:`{max(0,hp2)}`")
        if hp2 <= 0:
            return 1, log
        mult2 = element_multiplier(f2["element"], f1["element"])
        dmg2  = int(max(1, f2["atk"] - f1["def"]//2) * mult2 * random.uniform(0.85, 1.15))
        hp1  -= dmg2
        crit2 = "💥" if mult2 > 1 else ""
        log.append(f"T{turn}: **{f2['name']}** hits `{dmg2}` {crit2} | {f1['name']} HP:`{max(0,hp1)}`")
        if hp1 <= 0:
            return 2, log
    return (1 if hp1 > hp2 else (2 if hp2 > hp1 else 0)), log

class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_pvp = set()

    @commands.command(name="fight", aliases=["ch", "challenge"])
    async def fight(self, ctx, opponent: discord.Member = None):
        """Challenge another player. Usage: jay!fight @user"""
        if not opponent:
            await ctx.send("❌ Tag someone! Usage: `jay!fight @user`")
            return
        if opponent.bot or opponent.id == ctx.author.id:
            await ctx.send("❌ Invalid opponent!")
            return

        p1 = get_player(str(ctx.author.id))
        p2 = get_player(str(opponent.id))
        if not p1:
            await ctx.send("❌ Use `jay!start` first!")
            return
        if not p2:
            await ctx.send(f"❌ {opponent.name} hasn't started yet!")
            return

        f1 = get_fighter(str(ctx.author.id))
        f2 = get_fighter(str(opponent.id))
        if not f1:
            await ctx.send(f"❌ {ctx.author.mention} select a warrior with `jay!select <ID>`!")
            return
        if not f2:
            await ctx.send(f"❌ {opponent.mention} hasn't selected a warrior yet!")
            return

        if ctx.channel.id in self.active_pvp:
            await ctx.send("⚠️ A battle is already happening here!")
            return

        r1 = config.RARITY_EMOJI.get(f1["rarity"], "")
        r2 = config.RARITY_EMOJI.get(f2["rarity"], "")
        e1 = config.ELEMENT_EMOJI.get(f1["element"], "")
        e2 = config.ELEMENT_EMOJI.get(f2["element"], "")

        embed = discord.Embed(
            title="⚔️ Battle Challenge!",
            description=(
                f"{ctx.author.mention} challenges {opponent.mention}!\n\n"
                f"**{ctx.author.name}** → {r1} {f1['name']} {e1} Lv.{f1['level']}\n"
                f"**{opponent.name}** → {r2} {f2['name']} {e2} Lv.{f2['level']}\n\n"
                f"{opponent.mention} type `accept` or `decline` within 30s!"
            ),
            color=config.COLOR_MAIN
        )
        view = BattleAcceptView(ctx.author.id, opponent.id)
msg = await ctx.send(embed=embed, view=view)
await view.wait()
if not view.accepted:
    return await ctx.send(f"🛡️ {opponent.mention} declined.")

        def check(m):
            return m.author.id == opponent.id and m.channel == ctx.channel and m.content.lower() in ["accept","decline"]

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ {opponent.mention} didn't respond. Challenge expired.")
            return

        if msg.content.lower() == "decline":
            await ctx.send(f"🛡️ {opponent.mention} declined the battle.")
            return

        self.active_pvp.add(ctx.channel.id)
        await ctx.send("⚔️ **Battle begins!**")
        await asyncio.sleep(1.5)

        winner_idx, log = simulate_battle(f1, f2)
        log_text = "\n".join(log[-6:])
        hon_reward = random.randint(80, 150)
        xp_reward  = random.randint(30, 60)

        if winner_idx == 1:
            winner, loser, wf, lf, wr, lr = ctx.author, opponent, f1, f2, r1, r2
        elif winner_idx == 2:
            winner, loser, wf, lf, wr, lr = opponent, ctx.author, f2, f1, r2, r1
        else:
            winner = None

        if winner:
            ensure_battle_stats(str(winner.id))
            ensure_battle_stats(str(loser.id))
            conn = db.get_conn()
            conn.execute("UPDATE battle_stats SET pvp_wins=pvp_wins+1, total_dmg=total_dmg+%s WHERE user_id=%s", (wf["atk"], str(winner.id)))
            conn.execute("UPDATE battle_stats SET pvp_losses=pvp_losses+1 WHERE user_id=%s", (str(loser.id),))
            conn.execute("UPDATE players SET hon=hon+%s, xp=xp+%s WHERE user_id=%s", (hon_reward, xp_reward, str(winner.id)))
            conn.commit()
            conn.close()
            result = discord.Embed(
                title=f"🏆 {winner.name} wins!",
                description=(
                    f"**Battle Log:**\n{log_text}\n\n"
                    f"🎖️ **{winner.name}** ({wr} {wf['name']}) defeated **{loser.name}** ({lr} {lf['name']})\n\n"
                    f"**Rewards:** +{hon_reward} 🪙 Hon | +{xp_reward} ✨ XP"
                ),
                color=config.COLOR_GOLD
            )
        else:
            result = discord.Embed(
                title="🤝 Draw!",
                description=f"**Battle Log:**\n{log_text}\n\nBoth warriors fought valiantly!",
                color=config.COLOR_INFO
            )

        self.active_pvp.discard(ctx.channel.id)
        await ctx.send(embed=result)

    @commands.command(name="boss")
    async def boss(self, ctx, *, boss_name: str = None):
        """Fight a boss (requires Boss Key). Usage: jay!boss or jay!boss Afzal Khan"""
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return
        if (player["boss_keys"] or 0) < 1:
            await ctx.send(
                "You don't have a Boss Key! Earn keys by completing jay!tc 3 or jay!tc 4. "
                "You can challenge the tower every 6 hours."
            )
            return
        fighter = get_fighter(str(ctx.author.id))
        if not fighter:
            await ctx.send("❌ Select a warrior with `jay!select <ID>`!")
            return

        conn = db.get_conn()
        boss = conn.execute(
            "SELECT * FROM bosses WHERE name LIKE %s" if boss_name else "SELECT * FROM bosses ORDER BY RANDOM() LIMIT 1",
            (f"%{boss_name}%",) if boss_name else ()
        ).fetchone()
        conn.close()

        if not boss:
            conn = db.get_conn()
            names = ", ".join([b["name"] for b in conn.execute("SELECT name FROM bosses").fetchall()])
            conn.close()
            await ctx.send(f"❌ Boss not found! Available: {names}")
            return

        # Deduct boss key
        conn = db.get_conn()
        conn.execute("UPDATE players SET boss_keys=boss_keys-1 WHERE user_id=%s", (str(ctx.author.id),))
        conn.commit()
        conn.close()

        be = config.ELEMENT_EMOJI.get(boss["element"], "")
        fe = config.ELEMENT_EMOJI.get(fighter["element"], "")
        fr = config.RARITY_EMOJI.get(fighter["rarity"], "")

        embed = discord.Embed(
            title=f"👹 Boss Battle — {boss['name']}",
            description=(
                f"*{boss['description']}*\n\n"
                f"**{boss['name']}** {be} — _{boss['title']}_\n"
                f"HP:`{boss['hp']:,}` | ATK:`{boss['atk']}` | DEF:`{boss['def']}`\n\n"
                f"Your warrior: {fr} **{fighter['name']}** {fe} Lv.{fighter['level']}\n"
                f"HP:`{fighter['hp']:,}` | ATK:`{fighter['atk']}` | DEF:`{fighter['def']}`\n\n"
                f"⚔️ Charging into battle..."
            ),
            color=config.COLOR_ERROR
        )
        await ctx.send(embed=embed)
        await asyncio.sleep(2)

        player_hp = fighter["hp"]
        boss_hp   = boss["hp"]
        log       = []
        won       = False

        for turn in range(1, 26):
            mult = element_multiplier(fighter["element"], boss["element"])
            dmg  = int(max(1, fighter["atk"] - boss["def"]//3) * mult * random.uniform(0.9, 1.2))
            boss_hp -= dmg
            crit = "💥" if mult > 1 else ""
            log.append(f"T{turn}: **{fighter['name']}** → `{dmg}` {crit} | Boss HP:`{max(0,boss_hp):,}`")
            if boss_hp <= 0:
                won = True
                break
            mult2 = element_multiplier(boss["element"], fighter["element"])
            dmg2  = int(max(1, boss["atk"] - fighter["def"]//3) * mult2 * random.uniform(0.9, 1.2))
            player_hp -= dmg2
            log.append(f"T{turn}: **{boss['name']}** → `{dmg2}` | Your HP:`{max(0,player_hp):,}`")
            if player_hp <= 0:
                break

        log_text = "\n".join(log[-8:])
        ensure_battle_stats(str(ctx.author.id))

        if won:
            conn = db.get_conn()
            conn.execute("UPDATE battle_stats SET boss_wins=boss_wins+1 WHERE user_id=%s", (str(ctx.author.id),))
            conn.execute("UPDATE players SET hon=hon+%s, xp=xp+%s WHERE user_id=%s", (boss["reward_hon"], boss["reward_xp"], str(ctx.author.id)))
            conn.commit()
            conn.close()
            result = discord.Embed(
                title=f"🏆 Victory! {boss['name']} defeated!",
                description=(
                    f"**Battle Log:**\n{log_text}\n\n"
                    f"**Swarajya prevails!** {fr} {fighter['name']} vanquished {boss['name']}!\n\n"
                    f"**Rewards:** +{boss['reward_hon']} 🪙 Hon | +{boss['reward_xp']} ✨ XP"
                ),
                color=config.COLOR_SUCCESS
            )
        else:
            result = discord.Embed(
                title=f"💀 Defeated by {boss['name']}!",
                description=(
                    f"**Battle Log:**\n{log_text}\n\n"
                    f"**{boss['name']}** was too powerful! Train harder and try again.\n"
                    f"Use `jay!select` to pick a stronger warrior."
                ),
                color=config.COLOR_ERROR
            )
        await ctx.send(embed=result)

    @commands.command(name="bosses")
    async def bosses(self, ctx):
        """View all available bosses."""
        conn = db.get_conn()
        rows = conn.execute("SELECT * FROM bosses ORDER BY hp ASC").fetchall()
        conn.close()
        embed = discord.Embed(title="👹 Enemies of Swarajya", color=config.COLOR_ERROR)
        for b in rows:
            be = config.ELEMENT_EMOJI.get(b["element"], "")
            embed.add_field(
                name=f"{be} {b['name']} — {b['title']}",
                value=f"HP:`{b['hp']:,}` ATK:`{b['atk']}` DEF:`{b['def']}` | Reward: `{b['reward_hon']} Hon` + `{b['reward_xp']} XP`",
                inline=False
            )
        embed.set_footer(text="jay!boss <name> to fight • jay!boss for random")
        await ctx.send(embed=embed)

    @commands.command(name="stats", aliases=["battlestats"])
    async def stats(self, ctx, member: discord.Member = None):
        """View battle stats. Usage: jay!stats"""
        target = member or ctx.author
        player = get_player(str(target.id))
        if not player:
            await ctx.send("❌ Player hasn't started yet!")
            return
        ensure_battle_stats(str(target.id))
        conn = db.get_conn()
        bs = conn.execute("SELECT * FROM battle_stats WHERE user_id=%s", (str(target.id),)).fetchone()
        conn.close()
        total   = (bs["pvp_wins"] or 0) + (bs["pvp_losses"] or 0)
        winrate = f"{int(bs['pvp_wins']/total*100)}%" if total > 0 else "N/A"
        fighter = get_fighter(str(target.id))
        fs = f"{config.RARITY_EMOJI.get(fighter['rarity'],'')} {fighter['name']}" if fighter else "None"
        embed = discord.Embed(title=f"⚔️ {target.name}'s Battle Stats", color=config.COLOR_MAIN)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🗡️ PvP Wins",      value=str(bs["pvp_wins"]),    inline=True)
        embed.add_field(name="🛡️ PvP Losses",    value=str(bs["pvp_losses"]),  inline=True)
        embed.add_field(name="📊 Win Rate",       value=winrate,                inline=True)
        embed.add_field(name="👹 Boss Wins",      value=str(bs["boss_wins"]),   inline=True)
        embed.add_field(name="💥 Total Damage",   value=f"{bs['total_dmg']:,}", inline=True)
        embed.add_field(name="🎯 Active Warrior", value=fs,                     inline=True)
        embed.set_footer(text="jay!fight @user | jay!boss | jay!bosses")
        await ctx.send(embed=embed)

    @commands.command(name="moves")
    async def moves(self, ctx):
        """View your warrior's moveset."""
        fighter = get_fighter(str(ctx.author.id))
        if not fighter:
            await ctx.send("❌ Select a warrior with `jay!select <ID>`!")
            return
        move_sets = {
            "Fire":  [("🔥 Agni Strike","Burns with fierce flames"),("💨 Saffron Fury","Powerful saffron charge"),("🌋 Volcanic Rage","Unleashes volcanic energy")],
            "Wind":  [("🌪️ Vayu Slash","Cuts like Sahyadri winds"),("⚡ Swift Charge","Lightning cavalry charge"),("🌀 Cyclone Blade","Spinning blade attack")],
            "Earth": [("🌿 Stone Crush","Crushes with earth's might"),("🪨 Fort Defense","Turtle stance, high DEF"),("💪 Mountain Fist","Strike like a mountain")],
            "Water": [("💧 River Rush","Flows like a mighty river"),("🌊 Flood Strike","Overwhelms with water"),("❄️ Konkan Mist","Blinds with coastal mist")],
            "Light": [("✨ Divine Aura","Blesses with holy light"),("🌟 Swarajya Beam","Beam of Swarajya's glory"),("💫 Bhavani Blessing","Channels the goddess")],
            "Dark":  [("🌑 Shadow Strike","Strikes from shadows"),("💀 Death Blow","Devastating dark blow"),("🖤 Void Slash","Cuts through reality")],
        }
        moves = move_sets.get(fighter["element"], move_sets["Fire"])
        r = config.RARITY_EMOJI.get(fighter["rarity"], "")
        e = config.ELEMENT_EMOJI.get(fighter["element"], "")
        embed = discord.Embed(
            title=f"⚔️ {r} {fighter['name']} {e} — Moveset",
            color=config.RARITY_COLOR.get(fighter["rarity"], config.COLOR_MAIN)
        )
        for i, (name, desc) in enumerate(moves, 1):
            embed.add_field(name=f"Move {i}: {name}", value=f"{desc}\nPower: `{fighter['atk'] + random.randint(-20,20)}`", inline=False)
        embed.set_footer(text="Moves are used automatically in battle!")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Battle(bot))
