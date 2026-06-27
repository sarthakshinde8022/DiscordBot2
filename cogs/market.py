import discord
from discord.ext import commands
import asyncio
import config
import database as db

def get_player(user_id):
    conn = db.get_conn()
    p = conn.execute("SELECT * FROM players WHERE user_id=%s", (str(user_id),)).fetchone()
    conn.close()
    return p

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── jay!market ────────────────────────────────────────────────────
    @commands.command(name="market", aliases=["ma"])
    async def market(self, ctx, page: int = 1):
        """Browse the player market. Usage: jay!market"""
        conn = db.get_conn()
        listings = conn.execute(
            """SELECT m.id, m.seller_id, m.item_type, m.item_ref_id, m.price_hon, m.listed_at,
                      p.username as seller_name
               FROM market m JOIN players p ON m.seller_id=p.user_id
               WHERE m.sold=0 ORDER BY m.listed_at DESC LIMIT 20"""
        ).fetchall()
        conn.close()

        if not listings:
            await ctx.send("🏪 Market is empty! List items with `jay!mlist char/item <ID> <price>`.")
            return

        PER_PAGE = 8
        total_pages = max(1, (len(listings) + PER_PAGE - 1) // PER_PAGE)
        page = max(1, min(page, total_pages))
        chunk = listings[(page-1)*PER_PAGE : page*PER_PAGE]

        embed = discord.Embed(title="🏪 Swarajya Market", color=config.COLOR_GOLD)
        for listing in chunk:
            item_label = await self._get_item_label(listing["item_type"], listing["item_ref_id"])
            embed.add_field(
                name=f"#{listing['id']} — {item_label}",
                value=(
                    f"Seller: **{listing['seller_name']}**\n"
                    f"Price: **{listing['price_hon']:,} 🪙 Hon**\n"
                    f"`jay!mbuy {listing['id']}`"
                ),
                inline=True
            )
        embed.set_footer(text=f"Page [{page}/{total_pages}] • jay!mlist char/item <ID> <price> to sell")
        await ctx.send(embed=embed)

    async def _get_item_label(self, item_type, ref_id):
        conn = db.get_conn()
        if item_type == "char":
            row = conn.execute(
                "SELECT ch.name, ch.rarity FROM player_characters pc JOIN characters ch ON pc.char_id=ch.id WHERE pc.id=%s",
                (ref_id,)
            ).fetchone()
            conn.close()
            if row:
                r = config.RARITY_EMOJI.get(row["rarity"], "")
                return f"⚔️ {r} {row['name']}"
        elif item_type == "item":
            row = conn.execute(
                "SELECT i.name, i.rarity FROM player_items pi JOIN items i ON pi.item_id=i.id WHERE pi.id=%s",
                (ref_id,)
            ).fetchone()
            conn.close()
            if row:
                r = config.RARITY_EMOJI.get(row["rarity"], "")
                return f"🎒 {r} {row['name']}"
        conn.close()
        return f"{item_type} #{ref_id}"

    # ── jay!mlist ─────────────────────────────────────────────────────
    @commands.command(name="mlist", aliases=["ma_list", "marketlist"])
    async def mlist(self, ctx, item_type: str = None, item_id: int = None, price: int = None):
        """List an item on market. Usage: jay!mlist char/item <ID> <price>"""
        if not item_type or not item_id or not price:
            await ctx.send("❌ Usage: `jay!mlist char <ID> <price>` or `jay!mlist item <ID> <price>`")
            return

        item_type = item_type.lower()
        if item_type not in ["char", "item"]:
            await ctx.send("❌ Type must be `char` or `item`.")
            return
        if price < 1:
            await ctx.send("❌ Price must be at least 1 Hon.")
            return

        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        conn = db.get_conn()
        if item_type == "char":
            row = conn.execute(
                "SELECT pc.id, ch.name, ch.rarity FROM player_characters pc JOIN characters ch ON pc.char_id=ch.id WHERE pc.id=%s AND pc.user_id=%s",
                (item_id, str(ctx.author.id))
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT pi.id, i.name, i.rarity FROM player_items pi JOIN items i ON pi.item_id=i.id WHERE pi.id=%s AND pi.user_id=%s",
                (item_id, str(ctx.author.id))
            ).fetchone()

        if not row:
            conn.close()
            await ctx.send(f"❌ No {item_type} with ID `{item_id}` in your inventory.")
            return

        conn.execute(
            "INSERT INTO market (seller_id, item_type, item_ref_id, price_hon) VALUES (%s,%s,%s,%s)",
            (str(ctx.author.id), item_type, item_id, price)
        )
        conn.commit()
        conn.close()

        r = config.RARITY_EMOJI.get(row["rarity"], "")
        await ctx.send(
            f"✅ **{r} {row['name']}** listed on market for **{price:,} 🪙 Hon**!\n"
            f"Use `jay!market` to see all listings."
        )

    # ── jay!mbuy ──────────────────────────────────────────────────────
    @commands.command(name="mbuy", aliases=["marketbuy"])
    async def mbuy(self, ctx, listing_id: int = None):
        """Buy from market. Usage: jay!mbuy <listing ID>"""
        if not listing_id:
            await ctx.send("❌ Usage: `jay!mbuy <listing ID>`")
            return

        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return

        conn = db.get_conn()
        listing = conn.execute(
            "SELECT m.*, p.username as seller_name FROM market m JOIN players p ON m.seller_id=p.user_id WHERE m.id=%s AND m.sold=0",
            (listing_id,)
        ).fetchone()

        if not listing:
            conn.close()
            await ctx.send(f"❌ Listing `#{listing_id}` not found or already sold!")
            return
        if listing["seller_id"] == str(ctx.author.id):
            conn.close()
            await ctx.send("❌ You can't buy your own listing!")
            return
        if player["hon"] < listing["price_hon"]:
            conn.close()
            await ctx.send(f"❌ Not enough Hon! Need **{listing['price_hon']:,} 🪙** but have **{player['hon']:,} 🪙**.")
            return

        # Transfer item
        if listing["item_type"] == "char":
            conn.execute(
                "UPDATE player_characters SET user_id=%s WHERE id=%s",
                (str(ctx.author.id), listing["item_ref_id"])
            )
        else:
            conn.execute(
                "UPDATE player_items SET user_id=%s, is_equipped=0, equipped_to=NULL WHERE id=%s",
                (str(ctx.author.id), listing["item_ref_id"])
            )

        # Transfer Hon
        conn.execute("UPDATE players SET hon=hon-%s WHERE user_id=%s", (listing["price_hon"], str(ctx.author.id)))
        conn.execute("UPDATE players SET hon=hon+%s WHERE user_id=%s", (listing["price_hon"], listing["seller_id"]))
        conn.execute("UPDATE market SET sold=1 WHERE id=%s", (listing_id,))
        conn.commit()

        item_label = await self._get_item_label(listing["item_type"], listing["item_ref_id"])
        conn.close()

        embed = discord.Embed(
            title="🛒 Purchase Successful!",
            description=(
                f"You bought **{item_label}** from **{listing['seller_name']}**\n"
                f"for **{listing['price_hon']:,} 🪙 Hon**!"
            ),
            color=config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

    # ── jay!mremove ───────────────────────────────────────────────────
    @commands.command(name="mremove", aliases=["marketremove"])
    async def mremove(self, ctx, listing_id: int = None):
        """Remove your market listing. Usage: jay!mremove <listing ID>"""
        if not listing_id:
            await ctx.send("❌ Usage: `jay!mremove <listing ID>`")
            return

        conn = db.get_conn()
        listing = conn.execute(
            "SELECT * FROM market WHERE id=%s AND seller_id=%s AND sold=0",
            (listing_id, str(ctx.author.id))
        ).fetchone()
        if not listing:
            conn.close()
            await ctx.send(f"❌ Listing `#{listing_id}` not found or not yours!")
            return

        conn.execute("DELETE FROM market WHERE id=%s", (listing_id,))
        conn.commit()
        conn.close()
        await ctx.send(f"✅ Listing `#{listing_id}` removed from market.")

    # ── jay!mylistings ────────────────────────────────────────────────
    @commands.command(name="mylistings", aliases=["mmine"])
    async def mylistings(self, ctx):
        """View your active market listings."""
        conn = db.get_conn()
        listings = conn.execute(
            "SELECT * FROM market WHERE seller_id=%s AND sold=0", (str(ctx.author.id),)
        ).fetchall()
        conn.close()

        if not listings:
            await ctx.send("📭 No active listings. Use `jay!mlist` to sell!")
            return

        embed = discord.Embed(title=f"📋 {ctx.author.name}'s Market Listings", color=config.COLOR_GOLD)
        for l in listings:
            item_label = await self._get_item_label(l["item_type"], l["item_ref_id"])
            embed.add_field(
                name=f"#{l['id']} — {item_label}",
                value=f"Price: **{l['price_hon']:,} 🪙** | `jay!mremove {l['id']}`",
                inline=False
            )
        await ctx.send(embed=embed)

    # ── jay!trade ─────────────────────────────────────────────────────
    @commands.command(name="trade")
    async def trade(self, ctx, opponent: discord.Member = None, hon: int = 0):
        """Offer a Hon trade to another player. Usage: jay!trade @user <hon amount>"""
        if not opponent:
            await ctx.send("❌ Usage: `jay!trade @user <hon>` — offer Hon to trade")
            return
        if opponent.bot or opponent.id == ctx.author.id:
            await ctx.send("❌ Invalid trade target!")
            return

        player = get_player(str(ctx.author.id))
        if not player:
            await ctx.send("❌ Use `jay!start` first!")
            return
        if hon > 0 and player["hon"] < hon:
            await ctx.send(f"❌ Not enough Hon! You have **{player['hon']:,} 🪙**.")
            return

        target = get_player(str(opponent.id))
        if not target:
            await ctx.send(f"❌ {opponent.name} hasn't started yet!")
            return

        embed = discord.Embed(
            title="🤝 Trade Offer!",
            description=(
                f"{ctx.author.mention} offers **{hon:,} 🪙 Hon** to {opponent.mention}!\n\n"
                f"{opponent.mention} type `accept` or `decline` within 30 seconds."
            ),
            color=config.COLOR_MAIN
        )
        await ctx.send(embed=embed)

        def check(m):
            return m.author.id == opponent.id and m.channel == ctx.channel and m.content.lower() in ["accept","decline"]

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Trade offer expired.")
            return

        if msg.content.lower() == "decline":
            await ctx.send(f"❌ {opponent.name} declined the trade.")
            return

        if hon > 0:
            conn = db.get_conn()
            conn.execute("UPDATE players SET hon=hon-%s WHERE user_id=%s", (hon, str(ctx.author.id)))
            conn.execute("UPDATE players SET hon=hon+%s WHERE user_id=%s", (hon, str(opponent.id)))
            conn.commit()
            conn.close()

        embed = discord.Embed(
            title="✅ Trade Complete!",
            description=f"**{ctx.author.name}** sent **{hon:,} 🪙 Hon** to **{opponent.name}**!",
            color=config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Market(bot))
