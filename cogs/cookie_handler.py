import random
import typing

import discord
from discord.ext import commands

from cogs import utils


class CookieHandler(utils.Cog):

    ADJECTIVES_URL = "https://raw.githubusercontent.com/a-type/adjective-adjective-animal/master/lib/lists/adjectives.js"

    def __init__(self, bot:utils.Bot):
        super().__init__(bot)
        self.cached_adjectives = None

    async def load_adjective_cache(self):
        """Loads the cache from wherever innit mate"""

        async with self.bot.session.get(self.ADJECTIVES_URL) as r:
            text = await r.text()
        self.cached_adjectives = [i.strip(',"').lower() for i in text.split('\n')[1:-1]]

    @utils.Cog.listener()
    async def on_guild_join(self, guild:discord.Guild):
        """Adds adjectives to the guild when they join a server"""

        if self.cached_adjectives is None:
            await self.load_adjective_cache()
        choice = random.choices(self.cached_adjectives, k=2)
        async with self.bot.database() as db:
            await db(
                """INSERT INTO guild_cookie_prefixes (guild_id, adjective1, adjective2) 
                VALUES ($1, $2, $3) ON CONFLICT (guild_id) DO NOTHING""", 
                guild.id, choice[0], choice[1]
            )

    @commands.command(cls=utils.Command, aliases=['gc', 'give'])
    async def givecookie(self, ctx:utils.Context, user:discord.Member, amount:typing.Optional[int]=1, *cookie_type:str):
        """Gives one cookie to another person"""

        # Remove "cookie" from list
        while cookie_type[-1].lower() in ['cookie', 'cookies']:
            cookie_type = cookie_type[:-1]

        # Fix up cookie type
        if len(cookie_type) == 0:
            return await ctx.send("You need to provide a cookie type.")
        elif len(cookie_type) > 2:
            return await ctx.send(f"You have no `{' '.join(cookie_type)} cookies`.")
        if len(cookie_type) == 1:
            cookie_type = cookie_type[0], None,
        cookie_type = [i.lower() if i else i for i in cookie_type]

        # Eh it's valid enough
        db = await self.bot.database.get_connection()

        # Check the author's inventory
        inv = await db(
            f"""SELECT user_cookies.amount, user_cookies.cookie_guild_id FROM user_cookies 
            WHERE user_cookies.cookie_guild_id IN
            (SELECT guild_id FROM guild_cookie_prefixes WHERE adjective1=$2 AND adjective2{'=$3' if cookie_type[-1] else ' IS NULL'})
            AND user_cookies.user_id=$1""",
            ctx.author.id, *[i for i in cookie_type if i]
        )

        # Check inventory
        if not inv or inv[0]['amount'] < amount or inv[0]['cookie_guild_id'] is None:
            await ctx.send(inv)
            await db.disconnect()
            return await ctx.send(f"You don't have `{amount}x {' '.join([i for i in cookie_type if i])} cookies`.")

        # They have enough - transfer
        await db.start_transaction()
        await db(
            """INSERT INTO user_cookies (user_id, cookie_guild_id, amount) 
            VALUES ($1, $2, $3) ON CONFLICT (user_id, cookie_guild_id) DO UPDATE 
            SET amount=user_cookies.amount+EXCLUDED.amount""",
            user.id, inv[0]['cookie_guild_id'], amount
        )
        await db(
            """UPDATE user_cookies SET amount=amount-$1 WHERE user_id=$2 AND cookie_guild_id=$3""",
            amount, ctx.author.id, inv[0]['cookie_guild_id']
        )
        await db.commit_transaction()
        await db.disconnect()

        # And output
        await ctx.send(f"You've successfully sent `{amount}x {' '.join([i for i in cookie_type if i])} cookies` to {user.mention}.")

    @commands.command(cls=utils.Command, aliases=['daily'])
    @utils.cooldown.cooldown(1, 60 * 60, commands.BucketType.member)
    @commands.guild_only()
    async def mine(self, ctx:utils.Context):
        """Gives you a sexy ol daily amount of cookies"""

        amount = random.randint(10, 30)
        async with self.bot.database() as db:
            await db(
                """INSERT INTO user_cookies (user_id, cookie_guild_id, amount) 
                VALUES ($1, $2, $3) ON CONFLICT (user_id, cookie_guild_id) DO UPDATE 
                SET amount=user_cookies.amount+EXCLUDED.amount""",
                ctx.author.id, ctx.guild.id, amount
            )
            cookie_type = await db("SELECT adjective1, adjective2 FROM guild_cookie_prefixes WHERE guild_id=$1", ctx.guild.id)
        adj1, adj2 = cookie_type[0]['adjective1'], cookie_type[0]['adjective2']
        if adj2:
            adjective = f"{adj1} {adj2}"
        else:
            adjective = adj1
        await ctx.send(f"You just gained `{amount}x {adjective} cookies`.")

    @commands.command(cls=utils.Command, aliases=['inv', 'i'])
    @utils.cooldown.cooldown(1, 120, commands.BucketType.member)
    async def inventory(self, ctx:utils.Context):
        """Shows you your cookie inventory"""

        async with self.bot.database() as db:
            data = await db(
                """SELECT guild_cookie_prefixes.adjective1, guild_cookie_prefixes.adjective2, user_cookies.amount FROM
                user_cookies LEFT JOIN guild_cookie_prefixes ON user_cookies.cookie_guild_id=guild_cookie_prefixes.guild_id
                WHERE user_cookies.user_id=$1""",
                ctx.author.id
            )
        lines = []
        for row in data:
            adj1, adj2 = row['adjective1'], row['adjective2']
            if adj2:
                adjective = f"{adj1} {adj2}"
            else:
                adjective = adj1
            lines.append(f"{row['amount']}x {adjective} cookies")
        await ctx.send('\n'.join(lines))


def setup(bot:utils.Bot):
    x = CookieHandler(bot)
    bot.add_cog(x)
