import discord
from discord.ext import commands
import config
import database as db

def get_player(user_id):
    conn = db.get_conn()
    p = conn.execute("SELECT * FROM players WHERE user_id=%s", (str(user_id),)).fetchone()
    conn.close()
    return p

def get_clan(clan_id):
    conn = db.get_conn()
    c = conn.execute("SELECT * FROM clans WHERE id=%s", (clan_id,)).fetchone()
    conn.close()
    return c

class Clans(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── jay!clancreate ────────────────────────────────────────────────
    @commands.command(name="clancreate")
    async def clancreate(self, ctx, tag: str = None, *, name: str = None):
        """Create a clan. Usage: jay!clancreate <TAG> <Name>"""
        if not tag or not name:
            await ctx.send("❌ Usage: `jay!clancreate <TAG> <Clan Name>`\nExample: `jay!clancreate MRT Maratha Warriors`")
            return

        tag = tag.upper()
        if len(tag) > 5:
            await ctx.send("❌ Tag must be 5 characters or less!")
            return

        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return
        if player["clan_id"]:
            await ctx.send("❌ You're already in a clan! Leave first with `jay!clanleave`.")
            return
        if player["hon"] < 1000:
            await ctx.send("❌ Creating a clan costs **1000 🪙 Hon**. You don't have enough!")
            return

        conn = db.get_conn()
        try:
            conn.execute(
                "INSERT INTO clans (name, tag, leader_id, description) VALUES (%s,%s,%s,%s)",
                (name, tag, str(ctx.author.id), f"A proud Maratha clan led by {ctx.author.name}!")
            )
            clan_id = conn.execute("SELECT id FROM clans WHERE tag=%s", (tag,)).fetchone()["id"]
            conn.execute(
                "UPDATE players SET clan_id=%s, clan_role='leader', hon=hon-1000 WHERE user_id=%s",
                (clan_id, str(ctx.author.id))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            conn.close()
            if "UNIQUE" in str(e):
                await ctx.send(f"❌ Clan name or tag **{tag}** already exists! Choose another.")
            else:
                await ctx.send(f"❌ Error: {e}")
            return

        embed = discord.Embed(
            title="🏰 Clan Created!",
            description=(
                f"**[{tag}] {name}** has been founded!\n\n"
                f"👑 Leader: {ctx.author.mention}\n"
                f"💰 Cost: 1000 🪙 Hon deducted\n\n"
                f"Invite members with `jay!claninvite @user`!"
            ),
            color=config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

    # ── jay!claninfo ──────────────────────────────────────────────────
    @commands.command(name="claninfo", aliases=["clan"])
    async def claninfo(self, ctx, *, clan_name: str = None):
        """View clan info. Usage: jay!claninfo or jay!claninfo <name>"""
        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        conn = db.get_conn()
        if clan_name:
            clan = conn.execute(
                "SELECT * FROM clans WHERE name LIKE %s OR tag LIKE %s",
                (f"%{clan_name}%", f"%{clan_name.upper()}%")
            ).fetchone()
        elif player["clan_id"]:
            clan = conn.execute("SELECT * FROM clans WHERE id=%s", (player["clan_id"],)).fetchone()
        else:
            conn.close()
            await ctx.send("❌ You're not in a clan! Join one with `jay!clanjoin <tag>` or create with `jay!clancreate`.")
            return

        if not clan:
            conn.close()
            await ctx.send("❌ Clan not found!")
            return

        members = conn.execute(
            "SELECT username, clan_role FROM players WHERE clan_id=%s", (clan["id"],)
        ).fetchall()
        conn.close()

        leader = next((m for m in members if m["clan_role"] == "leader"), None)
        member_lines = []
        for m in members:
            role_icon = "👑" if m["clan_role"] == "leader" else "⚔️"
            member_lines.append(f"{role_icon} {m['username']}")

        embed = discord.Embed(
            title=f"🏰 [{clan['tag']}] {clan['name']}",
            description=clan["description"],
            color=config.COLOR_MAIN
        )
        embed.add_field(name="👑 Leader",   value=leader["username"] if leader else "Unknown", inline=True)
        embed.add_field(name="⚔️ Members",  value=str(len(members)), inline=True)
        embed.add_field(name="🏆 Level",    value=str(clan["level"]), inline=True)
        embed.add_field(name="🗡️ Wins",     value=str(clan["wins"]),  inline=True)
        embed.add_field(name="🛡️ Losses",   value=str(clan["losses"]),inline=True)
        embed.add_field(name="🏦 Hon Bank", value=f"{clan['hon_bank']:,} 🪙", inline=True)
        embed.add_field(
            name=f"Members [{len(members)}]",
            value="\n".join(member_lines) or "None",
            inline=False
        )
        embed.set_footer(text="jay!clanleave • jay!clandonate <amount>")
        await ctx.send(embed=embed)

    # ── jay!clanjoin ──────────────────────────────────────────────────
    @commands.command(name="clanjoin")
    async def clanjoin(self, ctx, tag: str = None):
        """Join a clan by tag. Usage: jay!clanjoin <TAG>"""
        if not tag:
            await ctx.send("❌ Usage: `jay!clanjoin <TAG>`")
            return

        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return
        if player["clan_id"]:
            await ctx.send("❌ You're already in a clan! Leave first with `jay!clanleave`.")
            return

        conn = db.get_conn()
        clan = conn.execute("SELECT * FROM clans WHERE tag=%s", (tag.upper(),)).fetchone()
        if not clan:
            conn.close()
            await ctx.send(f"❌ No clan with tag **{tag.upper()}**! Use `jay!clanlist` to find clans.")
            return

        conn.execute(
            "UPDATE players SET clan_id=%s, clan_role='member' WHERE user_id=%s",
            (clan["id"], str(ctx.author.id))
        )
        conn.commit()
        conn.close()

        await ctx.send(
            f"✅ {ctx.author.mention} joined **[{clan['tag']}] {clan['name']}**! Jay Bhavani! ⚔️"
        )

    # ── jay!clanleave ─────────────────────────────────────────────────
    @commands.command(name="clanleave")
    async def clanleave(self, ctx):
        """Leave your clan. Usage: jay!clanleave"""
        player = get_player(str(ctx.author.id))
        if not player or not player["clan_id"]:
            await ctx.send("❌ You're not in a clan!")
            return
        if player["clan_role"] == "leader":
            await ctx.send("❌ You're the clan leader! Transfer leadership first or disband with `jay!clandisband`.")
            return

        conn = db.get_conn()
        clan = conn.execute("SELECT name, tag FROM clans WHERE id=%s", (player["clan_id"],)).fetchone()
        conn.execute("UPDATE players SET clan_id=NULL, clan_role=NULL WHERE user_id=%s", (str(ctx.author.id),))
        conn.commit()
        conn.close()
        await ctx.send(f"👋 You left **[{clan['tag']}] {clan['name']}**.")

    # ── jay!clandisband ───────────────────────────────────────────────
    @commands.command(name="clandisband")
    async def clandisband(self, ctx):
        """Disband your clan (leader only)."""
        player = get_player(str(ctx.author.id))
        if not player or not player["clan_id"]:
            await ctx.send("❌ You're not in a clan!")
            return
        if player["clan_role"] != "leader":
            await ctx.send("❌ Only the clan leader can disband the clan!")
            return

        conn = db.get_conn()
        clan_id = player["clan_id"]
        clan = conn.execute("SELECT name, tag FROM clans WHERE id=%s", (clan_id,)).fetchone()
        conn.execute("UPDATE players SET clan_id=NULL, clan_role=NULL WHERE clan_id=%s", (clan_id,))
        conn.execute("DELETE FROM clans WHERE id=%s", (clan_id,))
        conn.commit()
        conn.close()
        await ctx.send(f"💀 **[{clan['tag']}] {clan['name']}** has been disbanded.")

    # ── jay!clandonate ────────────────────────────────────────────────
    @commands.command(name="clandonate")
    async def clandonate(self, ctx, amount: int = None):
        """Donate Hon to clan bank. Usage: jay!clandonate <amount>"""
        if not amount or amount <= 0:
            await ctx.send("❌ Usage: `jay!clandonate <amount>`")
            return
        player = get_player(str(ctx.author.id))
        if not player or not player["clan_id"]:
            await ctx.send("❌ You're not in a clan!")
            return
        if player["hon"] < amount:
            await ctx.send(f"❌ Not enough Hon! You have **{player['hon']:,} 🪙**.")
            return

        conn = db.get_conn()
        conn.execute("UPDATE players SET hon=hon-%s WHERE user_id=%s", (amount, str(ctx.author.id)))
        conn.execute("UPDATE clans SET hon_bank=hon_bank+%s, xp=xp+%s WHERE id=%s",
                     (amount, amount//10, player["clan_id"]))
        clan = conn.execute("SELECT name, tag, hon_bank FROM clans WHERE id=%s", (player["clan_id"],)).fetchone()
        conn.commit()
        conn.close()

        await ctx.send(
            f"🏦 **{ctx.author.name}** donated **{amount:,} 🪙 Hon** to "
            f"**[{clan['tag']}] {clan['name']}**!\n"
            f"Clan Bank: `{clan['hon_bank']:,} 🪙`"
        )

    # ── jay!clanlist ──────────────────────────────────────────────────
    @commands.command(name="clanlist", aliases=["clans"])
    async def clanlist(self, ctx):
        """View all clans."""
        conn = db.get_conn()
        clans = conn.execute(
            "SELECT c.*, COUNT(p.user_id) as member_count FROM clans c "
            "LEFT JOIN players p ON p.clan_id=c.id "
            "GROUP BY c.id ORDER BY c.level DESC, c.xp DESC LIMIT 10"
        ).fetchall()
        conn.close()

        if not clans:
            await ctx.send("No clans yet! Create one with `jay!clancreate <TAG> <Name>`.")
            return

        embed = discord.Embed(title="🏰 Maratha Clan Rankings", color=config.COLOR_MAIN)
        medals = ["🥇","🥈","🥉"] + ["🔹"]*7
        for i, clan in enumerate(clans):
            embed.add_field(
                name=f"{medals[i]} [{clan['tag']}] {clan['name']} — Lv.{clan['level']}",
                value=f"👥 {clan['member_count']} members | 🗡️ {clan['wins']}W {clan['losses']}L",
                inline=False
            )
        embed.set_footer(text="jay!clanjoin <TAG> to join • jay!clancreate to start your own")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Clans(bot))
