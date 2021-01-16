import random
import typing

import discord
from discord.ext import commands
import voxelbotutils as utils


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
        async with self.bot.database() as db:
            while True:
                choice = random.choices(self.cached_adjectives, k=2)
                data = await db("SELECT guild_id FROM guild_cookie_prefixes WHERE adjective1=$1 AND adjective2=$2", choice[0], choice[1])
                if not data:
                    await db(
                        """INSERT INTO guild_cookie_prefixes (guild_id, adjective1, adjective2)
                        VALUES ($1, $2, $3) ON CONFLICT (guild_id) DO NOTHING""",
                        guild.id, choice[0], choice[1]
                    )
                    return

    @utils.command(aliases=['gc', 'give'])
    async def givecookie(self, ctx:utils.Context, user:discord.Member, amount:typing.Optional[int]=1, *cookie_type:str):
        """Gives one cookie to another person"""

        PROVIDE_COOKIE_TYPE = "You need to provide a cookie type."

        # Make sure they gave a cookie type
        if not cookie_type:
            return await ctx.send(PROVIDE_COOKIE_TYPE)

        # Remove "cookie" from list
        while cookie_type[-1].lower() in ['cookie', 'cookies']:
            cookie_type = cookie_type[:-1]

        # Fix up cookie type
        if amount <= 0:
            return await ctx.send("You need to give a number larger than 0.")
        if len(cookie_type) == 0:
            return await ctx.send(PROVIDE_COOKIE_TYPE)
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

    @utils.command(aliases=['daily'])
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

    @utils.command()
    @utils.cooldown.cooldown(1, 60 * 60 * 24, commands.BucketType.member)
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def setcookie(self, ctx:utils.Context, adj1:str, adj2:typing.Optional[str]=None):
        """Sets the cookie type for your server"""

        # Check adjectives
        if self.cached_adjectives is None:
            await self.load_adjective_cache()
        if adj1 not in self.cached_adjectives:
            return await ctx.send(f"`{adj1}` is not a valid adjective.")
        if adj2 and adj2 not in self.cached_adjectives:
            return await ctx.send(f"`{adj2}` is not a valid adjective.")

        # Save
        async with self.bot.database() as db:
            if adj2:
                data = await db("SELECT guild_id FROM guild_cookie_prefixes WHERE adjective1=$1 AND adjective2=$2", adj1, adj2)
                if data:
                    return await ctx.send(f"There's already a server with `{adj1} {adj2} cookies` - you must set a unique name.")
            else:
                data = await db("SELECT guild_id FROM guild_cookie_prefixes WHERE adjective1=$1 AND adjective2 is NULL", adj1)
                if data:
                    return await ctx.send(f"There's already a server with `{adj1} cookies` - you must set a unique name.")
            await db(
                """UPDATE guild_cookie_prefixes SET adjective1=$1, adjective2=$2 WHERE guild_id=$3""",
                adj1, adj2, ctx.guild.id
            )

        # Output
        if adj2:
            adj = f"{adj1} {adj2}"
        else:
            adj = adj1
        await ctx.send(f"Your server's cookie type has been updated to `{adj} cookies`.")

    @utils.command(aliases=['inv', 'i'])
    @utils.cooldown.cooldown(1, 120, commands.BucketType.member)
    async def inventory(self, ctx:utils.Context, user:typing.Optional[discord.User]=None):
        """Shows you your cookie inventory"""

        user = user or ctx.author

        # Get data
        async with self.bot.database() as db:
            data = await db(
                """SELECT guild_cookie_prefixes.adjective1, guild_cookie_prefixes.adjective2, user_cookies.amount, user_cookies.cookie_guild_id FROM
                user_cookies LEFT JOIN guild_cookie_prefixes ON user_cookies.cookie_guild_id=guild_cookie_prefixes.guild_id
                WHERE user_cookies.user_id=$1 ORDER BY user_cookies.amount DESC""",
                user.id
            )
            all_cookie_data = await db(
                """SELECT cookie_guild_id, SUM(amount) FROM user_cookies WHERE cookie_guild_id=ANY($1::BIGINT[]) GROUP BY cookie_guild_id""",
                [i['cookie_guild_id'] for i in data]
            )

        # Get total cookies
        total_cookies = {i['cookie_guild_id']: i['sum'] for i in all_cookie_data}

        # Format output
        lines = []
        for row in data:
            adj1, adj2 = row['adjective1'], row['adjective2']
            if adj2:
                adjective = f"{adj1} {adj2}"
            else:
                adjective = adj1
            lines.append(f"`{row['amount']}x {adjective} cookies` (`{100 * (row['amount'] / total_cookies[row['cookie_guild_id']]):.3f}%`)")

        # Output to user
        if not lines:
            return await ctx.send(f"{user.mention} has no cookies to their name.")
        await ctx.send('\n'.join(lines))


def setup(bot:utils.Bot):
    x = CookieHandler(bot)
    bot.add_cog(x)
