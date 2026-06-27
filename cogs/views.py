import discord
from discord.ext import commands
import asyncio
import random
import config
import database as db

# ── Utility ───────────────────────────────────────────────────────────
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
    if not row: return None
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

# ── Move Selection View ───────────────────────────────────────────────
class MoveView(discord.ui.View):
    def __init__(self, fighter, author_id, timeout=25):
        super().__init__(timeout=timeout)
        self.chosen_move = None
        self.author_id   = author_id
        self.fighter     = fighter
        for i, mv in enumerate(fighter["moves"]):
            bar   = power_bar(mv["power"])
            label = f"{mv['name']} ({mv['power']})"[:80]
            btn   = discord.ui.Button(
                label=label, style=discord.ButtonStyle.primary,
                custom_id=f"move_{i}", row=i // 2
            )
            btn.callback = self._make_callback(i)
            self.add_item(btn)

    def _make_callback(self, idx):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("❌ This isn't your battle!", ephemeral=True)
                return
            self.chosen_move = idx
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)
            self.stop()
        return callback

    async def on_timeout(self):
        self.chosen_move = None
        self.stop()

# ── Summon Again View ─────────────────────────────────────────────────
class SummonAgainView(discord.ui.View):
    def __init__(self, author_id, banner="1"):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.banner    = banner

    @discord.ui.button(label="Summon Again", style=discord.ButtonStyle.primary, emoji="✨")
    async def summon_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This isn't your summon!", ephemeral=True)
            return
        button.disabled = True
        await interaction.response.edit_message(view=self)
        ctx_like = interaction.channel
        await interaction.followup.send(
            f"Use `jay!summon {self.banner}` to summon again!", ephemeral=True
        )
        self.stop()

    @discord.ui.button(label="View Warriors", style=discord.ButtonStyle.secondary, emoji="⚔️")
    async def view_chars(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This isn't your summon!", ephemeral=True)
            return
        await interaction.response.send_message("Use `jay!chars` to view your warriors!", ephemeral=True)

# ── Pagination View ───────────────────────────────────────────────────
class PaginationView(discord.ui.View):
    def __init__(self, pages, author_id, timeout=120):
        super().__init__(timeout=timeout)
        self.pages     = pages
        self.author_id = author_id
        self.current   = 0
        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.current == 0
        self.next_btn.disabled = self.current == len(self.pages) - 1
        self.page_btn.label    = f"{self.current+1}/{len(self.pages)}"

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This isn't your list!", ephemeral=True)
            return
        self.current -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True, custom_id="page")
    async def page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This isn't your list!", ephemeral=True)
            return
        self.current += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

# ── Battle Accept View ────────────────────────────────────────────────
class BattleAcceptView(discord.ui.View):
    def __init__(self, challenger_id, opponent_id):
        super().__init__(timeout=30)
        self.challenger_id = challenger_id
        self.opponent_id   = opponent_id
        self.accepted      = None

    @discord.ui.button(label="Accept ⚔️", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message("❌ This challenge isn't for you!", ephemeral=True)
            return
        self.accepted = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Decline 🛡️", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message("❌ This challenge isn't for you!", ephemeral=True)
            return
        self.accepted = False
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    async def on_timeout(self):
        self.accepted = False
        for item in self.children:
            item.disabled = True
        self.stop()

# ── Profile Quick Actions View ────────────────────────────────────────
class ProfileView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.author_id = author_id

    @discord.ui.button(label="Daily", style=discord.ButtonStyle.success, emoji="🎁")
    async def daily(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This isn't your profile!", ephemeral=True)
            return
        await interaction.response.send_message("Use `jay!daily` to claim your daily reward!", ephemeral=True)

    @discord.ui.button(label="Warriors", style=discord.ButtonStyle.primary, emoji="⚔️")
    async def warriors(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This isn't your profile!", ephemeral=True)
            return
        await interaction.response.send_message("Use `jay!chars` to view your warriors!", ephemeral=True)

    @discord.ui.button(label="Summon", style=discord.ButtonStyle.secondary, emoji="🏹")
    async def summon(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This isn't your profile!", ephemeral=True)
            return
        await interaction.response.send_message("Use `jay!summon` to summon a warrior!", ephemeral=True)

# ── Interactive Battle Engine ─────────────────────────────────────────
async def run_interactive_battle(ctx, fighter, enemy_name, enemy_hp, enemy_atk, enemy_def, enemy_element, on_win, on_lose):
    """Reusable interactive battle engine using Discord buttons."""
    player_hp = fighter["hp"]
    max_php   = fighter["hp"]
    max_ehp   = enemy_hp
    total_dmg = 0
    turn      = 0
    won       = False

    fr = config.RARITY_EMOJI.get(fighter["rarity"], "")
    fe = config.ELEMENT_EMOJI.get(fighter["element"], "")
    ee = config.ELEMENT_EMOJI.get(enemy_element, "")

    while player_hp > 0 and enemy_hp > 0 and turn < 30:
        turn += 1

        # Build battle embed
        battle_embed = discord.Embed(
            title=f"⚔️ Turn {turn} — Choose your move!",
            color=config.COLOR_MAIN
        )
        battle_embed.add_field(
            name=f"{fr} {fighter['name']} {fe}",
            value=f"{hp_bar(player_hp, max_php)} `{player_hp:,}`",
            inline=True
        )
        battle_embed.add_field(
            name=f"{ee} {enemy_name}",
            value=f"{hp_bar(enemy_hp, max_ehp)} `{enemy_hp:,}`",
            inline=True
        )
        battle_embed.set_footer(text="Click a move button below • 25 seconds")

        view = MoveView(fighter, ctx.author.id)
        msg  = await ctx.send(embed=battle_embed, view=view)

        await view.wait()

        if view.chosen_move is None:
            await msg.edit(content="⏰ **Battle timed out!**", embed=None, view=None)
            return False, total_dmg

        chosen = fighter["moves"][view.chosen_move]
        mult   = element_mult(fighter["element"], enemy_element)
        dmg    = int(max(1, chosen["power"] - enemy_def // 3) * mult * random.uniform(0.9, 1.15))
        enemy_hp  -= dmg
        total_dmg += dmg
        crit_txt = " 💥 **Element Advantage!**" if mult > 1 else ""

        result_embed = discord.Embed(
            title=f"Turn {turn} — Result",
            description=f"⚔️ **{chosen['name']}** hits `{dmg}`!{crit_txt}",
            color=config.COLOR_GOLD if enemy_hp <= 0 else config.COLOR_INFO
        )

        if enemy_hp > 0:
            mult2 = element_mult(enemy_element, fighter["element"])
            edmg  = int(max(1, enemy_atk - fighter["def"] // 3) * mult2 * random.uniform(0.9, 1.15))
            player_hp -= edmg
            result_embed.description += f"\n{ee} **{enemy_name}** counters for `{edmg}`!"

        result_embed.add_field(
            name=f"{fr} Your HP",
            value=f"{hp_bar(max(0,player_hp), max_php)} `{max(0,player_hp):,}`",
            inline=True
        )
        result_embed.add_field(
            name=f"{ee} Enemy HP",
            value=f"{hp_bar(max(0,enemy_hp), max_ehp)} `{max(0,enemy_hp):,}`",
            inline=True
        )
        await msg.edit(embed=result_embed, view=None)
        await asyncio.sleep(1.2)

    won = player_hp > 0 and enemy_hp <= 0
    return won, total_dmg
