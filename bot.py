import os
import sqlite3
import asyncio
from datetime import datetime, timezone, timedelta

import aiohttp
import discord
from discord.ext import commands, tasks


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.environ["DISCORD_TOKEN"]

GUILD_ID = 1529456498319687680

TICKET_CATEGORY_ID = 1529456499414270124

ROLE_1_DAY = 1529460427518382080
ROLE_7_DAY = 1536786837249597440

MANAGER_ROLE_ID = 1553531664494231623
STAFF_ROLE_ID = 1529460720708747314

TRANSCRIPT_CHANNEL_ID = 1531076856646733894
WELCOME_LEAVE_CHANNEL_ID = 1531076725142978731

LTC_ADDRESS = "ltc1qd9d0n24kfw63647nsq9y4fs5xj7v4d793q4s3a"

PRICE_1_DAY_EUR = 12
PRICE_7_DAY_EUR = 70

PRICE_1_DAY_LTC = 0.19721329
PRICE_7_DAY_LTC = 1.15000000

REQUIRED_CONFIRMATIONS = 2
BLOCKCHAIN_POLL_SECONDS = 20
PAYMENT_TOLERANCE_LITOSHI = 20_000

DB_FILE = "buy_access.sqlite3"

BANNER_URL = (
    "https://cdn.discordapp.com/attachments/"
    "1554182048204460032/1554205879291879424/"
    "5c9782332a2344cb.png"
    "?ex=6abc0a85&is=6abab905"
    "&hm=49cb056df75050167521453223f1e376357a10109"
    "bef4de0fb4a9cfffc7d45c5"
)


# =========================================================
# BOT
# =========================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# DATABASE
# =========================================================

def db():
    return sqlite3.connect(DB_FILE)


def init_db():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            plan TEXT NOT NULL,
            amount_litoshi INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            paid INTEGER DEFAULT 0,
            txid TEXT,
            confirmations INTEGER DEFAULT 0,
            role_granted INTEGER DEFAULT 0,
            closed INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

    print("DATABASE READY")


# =========================================================
# HELPERS
# =========================================================

def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat()


def parse_dt(value):

    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def user_has_ticket(user_id):

    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT channel_id
        FROM orders
        WHERE user_id = ?
        AND closed = 0
        LIMIT 1
        """,
        (user_id,)
    )

    result = cur.fetchone()

    conn.close()

    return result[0] if result else None


# =========================================================
# ROLE SYSTEM
# =========================================================

async def give_access_role(member, role):

    if not member:
        print("ROLE ERROR: member not found")
        return False

    if not role:
        print("ROLE ERROR: role not found")
        return False

    if role in member.roles:

        print(
            f"ROLE INFO: {member} already has {role.name}"
        )

        return True

    guild = member.guild

    if not guild.me:
        print("ROLE ERROR: bot member not found")
        return False

    if not guild.me.guild_permissions.manage_roles:

        print(
            "ROLE ERROR: BOT DOES NOT HAVE MANAGE ROLES"
        )

        return False

    if guild.me.top_role.position <= role.position:

        print(
            "ROLE ERROR: BOT ROLE IS NOT ABOVE TARGET ROLE"
        )

        print(
            f"Bot role position: "
            f"{guild.me.top_role.position}"
        )

        print(
            f"Target role position: "
            f"{role.position}"
        )

        return False

    try:

        await member.add_roles(
            role,
            reason="Tropik Studios payment confirmed"
        )

        print(
            f"ROLE SUCCESS: {role.name} -> {member}"
        )

        return True

    except discord.Forbidden:

        print(
            "ROLE ERROR: Discord denied Manage Roles."
        )

        return False

    except Exception as e:

        print(
            f"ROLE ERROR: {repr(e)}"
        )

        return False


async def remove_access_role(member, role):

    if not member or not role:
        return False

    if role not in member.roles:
        return True

    try:

        await member.remove_roles(
            role,
            reason="Tropik Studios access expired"
        )

        print(
            f"ROLE REMOVED: {role.name} -> {member}"
        )

        return True

    except Exception as e:

        print(
            f"ROLE REMOVE ERROR: {repr(e)}"
        )

        return False


# =========================================================
# BUY PANEL
# =========================================================

def buy_panel_embed():

    embed = discord.Embed(
        title="Tropik Studios — Buy Access",
        description=(
            "**Choose your access, select the duration and complete "
            "your payment. Your access will be delivered automatically "
            "after confirmation.**\n\n"

            "📌 **HOW IT WORKS**\n\n"

            "> **01 — CHOOSE**\n"
            "> Select your access package.\n\n"

            "> **02 — ORDER**\n"
            "> Your private ticket is created.\n\n"

            "> **03 — PAY**\n"
            "> Send the exact amount shown.\n\n"

            "> **04 — ACCESS**\n"
            "> Receive your access after confirmation.\n\n"

            "━━━━━━━━━━━━━━━━━━━━\n\n"

            "-# Premium access • Fast checkout • Automated delivery\n"
            "-# © 2026 Tropik Studios — All Rights Reserved"
        ),
        color=discord.Color.purple()
    )

    embed.set_image(url=BANNER_URL)

    return embed


# =========================================================
# SUPPORT PANEL
# =========================================================

def support_panel_embed():

    embed = discord.Embed(
        title="Tropik Studios — Support",
        description=(
            "**Select a category below to open a ticket. "
            "A staff member will assist you shortly.**\n\n"

            "━━━━━━━━━━━━━━━━━━━━\n\n"

            "💬 **Support**\n"
            "🚨 **Report an Issue**\n"
            "📌 **Other**\n\n"

            "━━━━━━━━━━━━━━━━━━━━\n\n"

            "-# 24/7 Support • Fast • Reliable\n"
            "-# © 2026 Tropik Studios — All Rights Reserved"
        ),
        color=discord.Color.purple()
    )

    embed.set_image(url=BANNER_URL)

    return embed


# =========================================================
# BUY MENU
# =========================================================

class BuyAccessSelect(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(
                label="Access 1 Day",
                description="€12 — 1 day access",
                emoji="🕐",
                value="1day"
            ),

            discord.SelectOption(
                label="Access 7 Days",
                description="€70 — 7 days access",
                emoji="📅",
                value="7day"
            )
        ]

        super().__init__(
            placeholder="Choose Access",
            options=options,
            custom_id="buy_access_select"
        )

    async def callback(self, interaction):

        if self.values[0] == "1day":

            plan = "1 Day"
            price_eur = 12
            price_ltc = PRICE_1_DAY_LTC
            role_id = ROLE_1_DAY

        else:

            plan = "7 Days"
            price_eur = 70
            price_ltc = PRICE_7_DAY_LTC
            role_id = ROLE_7_DAY

        await create_access_ticket(
            interaction,
            plan,
            price_eur,
            price_ltc,
            role_id
        )


class BuyView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(
            BuyAccessSelect()
        )


# =========================================================
# SUPPORT MENU
# =========================================================

class SupportSelect(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(
                label="Support",
                description="Get help from staff",
                emoji="💬",
                value="support"
            ),

            discord.SelectOption(
                label="Report an Issue",
                description="Report a problem",
                emoji="🚨",
                value="report"
            ),

            discord.SelectOption(
                label="Other",
                description="Something else",
                emoji="📌",
                value="other"
            )
        ]

        super().__init__(
            placeholder="Choose a Category",
            options=options,
            custom_id="support_select"
        )

    async def callback(self, interaction):

        names = {
            "support": "support",
            "report": "report-an-issue",
            "other": "other"
        }

        await create_support_ticket(
            interaction,
            names[self.values[0]]
        )


class SupportView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(
            SupportSelect()
        )


# =========================================================
# ACCESS TICKET
# =========================================================

async def create_access_ticket(
    interaction,
    plan,
    price_eur,
    price_ltc,
    role_id
):

    guild = interaction.guild

    existing = user_has_ticket(
        interaction.user.id
    )

    if existing:

        channel = guild.get_channel(
            existing
        )

        if channel:

            await interaction.response.send_message(
                f"You already have an open ticket: {channel.mention}",
                ephemeral=True
            )

            return

    category = guild.get_channel(
        TICKET_CATEGORY_ID
    )

    if not category:

        await interaction.response.send_message(
            "Ticket category was not found.",
            ephemeral=True
        )

        return

    manager_role = guild.get_role(
        MANAGER_ROLE_ID
    )

    overwrites = {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        interaction.user:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),

        guild.me:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )
    }

    if manager_role:

        overwrites[manager_role] = (
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            )
        )

    channel = await guild.create_text_channel(
        name=f"access-{interaction.user.name}",
        category=category,
        overwrites=overwrites
    )

    amount_litoshi = int(
        round(price_ltc * 100000000)
    )

    created = now_utc()

    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO orders
        (
            user_id,
            channel_id,
            plan,
            amount_litoshi,
            role_id,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            interaction.user.id,
            channel.id,
            plan,
            amount_litoshi,
            role_id,
            iso(created)
        )
    )

    conn.commit()
    conn.close()

    embed = discord.Embed(
        title="💳 PAYMENT",
        description=(
            f"**Access:** {plan}\n"
            f"**Price:** €{price_eur}\n\n"

            f"**LTC Amount**\n"
            f"`{price_ltc:.8f} LTC`\n\n"

            f"**Litecoin Address**\n"
            f"`{LTC_ADDRESS}`\n\n"

            "━━━━━━━━━━━━━━━━━━━━\n\n"

            "**Confirmations:** `0/2`\n\n"

            "Send the exact amount to the address above.\n"
            "The bot will automatically detect your payment."
        ),
        color=discord.Color.purple()
    )

    embed.set_footer(
        text="Invoice expires after 60 minutes."
    )

    await channel.send(
        content=interaction.user.mention,
        embed=embed,
        view=TicketView()
    )

    await interaction.response.send_message(
        f"Ticket created: {channel.mention}",
        ephemeral=True
    )


# =========================================================
# SUPPORT TICKET
# =========================================================

async def create_support_ticket(
    interaction,
    ticket_type
):

    guild = interaction.guild

    category = guild.get_channel(
        TICKET_CATEGORY_ID
    )

    if not category:

        await interaction.response.send_message(
            "Ticket category was not found.",
            ephemeral=True
        )

        return

    manager_role = guild.get_role(
        MANAGER_ROLE_ID
    )

    staff_role = guild.get_role(
        STAFF_ROLE_ID
    )

    overwrites = {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        interaction.user:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),

        guild.me:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )
    }

    if manager_role:

        overwrites[manager_role] = (
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            )
        )

    if staff_role:

        overwrites[staff_role] = (
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            )
        )

    channel = await guild.create_text_channel(
        name=f"{ticket_type}-{interaction.user.name}",
        category=category,
        overwrites=overwrites
    )

    embed = discord.Embed(
        title="🎫 Support Ticket",
        description=(
            f"Hello {interaction.user.mention},\n\n"

            "A member of our support team will be with you "
            "as soon as possible. Please remain respectful "
            "and patient while waiting.\n\n"

            "📌 **Need To Know**\n\n"

            "- Please be patient while waiting for a response.\n"
            "- Provide all relevant information and proof when necessary.\n"
            "- Please do not ping staff repeatedly while waiting.\n"
            "- Respectful behavior helps us assist you more quickly."
        ),
        color=discord.Color.purple()
    )

    await channel.send(
        content=(
            f"<@&{STAFF_ROLE_ID}> "
            f"{interaction.user.mention}"
        ),
        embed=embed,
        view=SupportTicketView()
    )

    await interaction.response.send_message(
        f"Ticket created: {channel.mention}",
        ephemeral=True
    )


# =========================================================
# CLOSE TICKET
# =========================================================

async def create_transcript(channel):

    lines = []

    async for message in channel.history(
        limit=None,
        oldest_first=True
    ):

        timestamp = message.created_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        content = message.content or ""

        lines.append(
            f"[{timestamp}] "
            f"{message.author} "
            f"({message.author.id}): "
            f"{content}"
        )

    return "\n".join(lines)


async def close_ticket(interaction):

    channel = interaction.channel

    transcript = await create_transcript(
        channel
    )

    filename = (
        f"transcript-{channel.id}.txt"
    )

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(transcript)

    transcript_channel = bot.get_channel(
        TRANSCRIPT_CHANNEL_ID
    )

    if transcript_channel:

        await transcript_channel.send(
            content=(
                f"📄 Transcript: `{channel.name}`\n"
                f"Closed by {interaction.user.mention}"
            ),
            file=discord.File(filename)
        )

    try:
        os.remove(filename)
    except Exception:
        pass

    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE orders
        SET closed = 1
        WHERE channel_id = ?
        """,
        (channel.id,)
    )

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        "Ticket closed.",
        ephemeral=True
    )

    await asyncio.sleep(1)

    await channel.delete(
        reason="Ticket closed"
    )


class TicketView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="close_access_ticket"
    )
    async def close(
        self,
        interaction,
        button
    ):

        await close_ticket(
            interaction
        )


class SupportTicketView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="close_support_ticket"
    )
    async def close(
        self,
        interaction,
        button
    ):

        await close_ticket(
            interaction
        )


# =========================================================
# LITECOIN
# =========================================================

async def get_ltc_tip_height(session):

    url = (
        "https://litecoinspace.org/"
        "api/blocks/tip/height"
    )

    try:

        async with session.get(url) as response:

            if response.status != 200:
                return None

            return int(
                (await response.text()).strip()
            )

    except Exception:

        return None


async def find_payment(
    required_litoshi,
    created_at
):

    url = (
        f"https://litecoinspace.org/"
        f"api/address/{LTC_ADDRESS}/txs"
    )

    try:

        timeout = aiohttp.ClientTimeout(
            total=15
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(url) as response:

                if response.status != 200:
                    return None

                data = await response.json()

            if isinstance(data, list):

                txs = data

            elif isinstance(data, dict):

                txs = data.get(
                    "txs",
                    []
                )

            else:

                return None

            tip_height = await get_ltc_tip_height(
                session
            )

            for tx in txs:

                if not isinstance(
                    tx,
                    dict
                ):
                    continue

                txid = tx.get("txid")

                if not txid:
                    continue

                status = tx.get(
                    "status",
                    {}
                )

                if not isinstance(
                    status,
                    dict
                ):
                    status = {}

                block_height = status.get(
                    "block_height"
                )

                block_time = status.get(
                    "block_time"
                )

                if block_time:

                    try:

                        tx_time = datetime.fromtimestamp(
                            int(block_time),
                            tz=timezone.utc
                        )

                        if tx_time < (
                            created_at
                            - timedelta(minutes=5)
                        ):
                            continue

                    except Exception:
                        pass

                confirmations = 0

                if (
                    status.get("confirmed")
                    and block_height
                    and tip_height is not None
                ):

                    confirmations = max(
                        0,
                        tip_height
                        - int(block_height)
                        + 1
                    )

                for output in tx.get(
                    "vout",
                    []
                ):

                    if not isinstance(
                        output,
                        dict
                    ):
                        continue

                    value = int(
                        output.get(
                            "value",
                            0
                        ) or 0
                    )

                    if abs(
                        value - required_litoshi
                    ) > PAYMENT_TOLERANCE_LITOSHI:
                        continue

                    address = output.get(
                        "scriptpubkey_address"
                    )

                    if (
                        address
                        and address.lower()
                        == LTC_ADDRESS.lower()
                    ):

                        return (
                            txid,
                            confirmations,
                            value
                        )

    except Exception as e:

        print(
            "BLOCKCHAIN ERROR:",
            repr(e)
        )

    return None


# =========================================================
# PAYMENT WATCHER
# =========================================================

@tasks.loop(
    seconds=BLOCKCHAIN_POLL_SECONDS
)
async def payment_watcher():

    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            user_id,
            channel_id,
            plan,
            amount_litoshi,
            role_id,
            created_at
        FROM orders
        WHERE paid = 0
        AND closed = 0
        """
    )

    orders = cur.fetchall()

    conn.close()

    for order in orders:

        (
            order_id,
            user_id,
            channel_id,
            plan,
            amount_litoshi,
            role_id,
            created_at
        ) = order

        channel = bot.get_channel(
            channel_id
        )

        if not channel:
            continue

        created_dt = parse_dt(
            created_at
        )

        if not created_dt:
            continue

        payment = await find_payment(
            amount_litoshi,
            created_dt
        )

        if not payment:
            continue

        txid, confirmations, value = payment

        conn = db()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE orders
            SET txid = ?,
                confirmations = ?
            WHERE id = ?
            """,
            (
                txid,
                confirmations,
                order_id
            )
        )

        conn.commit()
        conn.close()

        if confirmations < REQUIRED_CONFIRMATIONS:

            print(
                f"PAYMENT FOUND: {txid} "
                f"({confirmations}/2)"
            )

            continue

        # =================================================
        # CONFIRMED - FETCH MEMBER
        # =================================================

        member = channel.guild.get_member(
            user_id
        )

        if not member:

            try:

                member = await channel.guild.fetch_member(
                    user_id
                )

            except Exception as e:

                print(
                    "MEMBER FETCH ERROR:",
                    repr(e)
                )

                continue

        role = channel.guild.get_role(
            role_id
        )

        if not role:

            try:

                role = await channel.guild.fetch_role(
                    role_id
                )

            except Exception as e:

                print(
                    "ROLE FETCH ERROR:",
                    repr(e)
                )

                continue

        # =================================================
        # GIVE ROLE
        # =================================================

        success = await give_access_role(
            member,
            role
        )

        # IMPORTANT:
        # If role failed, DON'T mark the order paid.
        # The bot will retry on the next cycle.

        if not success:

            print(
                f"ROLE NOT GRANTED. "
                f"Will retry order #{order_id}"
            )

            continue

        # =================================================
        # EXPIRATION
        # =================================================

        if plan == "1 Day":

            expires = now_utc() + timedelta(
                days=1
            )

        else:

            expires = now_utc() + timedelta(
                days=7
            )

        conn = db()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE orders
            SET paid = 1,
                txid = ?,
                confirmations = ?,
                expires_at = ?,
                role_granted = 1
            WHERE id = ?
            """,
            (
                txid,
                confirmations,
                iso(expires),
                order_id
            )
        )

        conn.commit()
        conn.close()

        print(
            f"PAYMENT CONFIRMED: {txid}"
        )

        print(
            f"ROLE SUCCESS: {role.name}"
        )

        # =================================================
        # CONFIRMED MESSAGE
        # =================================================

        embed = discord.Embed(
            title="✅ PAYMENT CONFIRMED",
            description=(
                f"**Access:** {plan}\n\n"

                f"**Transaction:**\n"
                f"`{txid}`\n\n"

                f"**Confirmations:** `2/2`\n\n"

                f"**Role:** {role.mention}\n\n"

                f"**Expiration:** "
                f"<t:{int(expires.timestamp())}:F>"
            ),
            color=discord.Color.green()
        )

        await channel.send(
            content=member.mention,
            embed=embed
        )


# =========================================================
# EXPIRATION
# =========================================================

@tasks.loop(
    minutes=1
)
async def expiry_watcher():

    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            user_id,
            role_id,
            expires_at
        FROM orders
        WHERE paid = 1
        AND role_granted = 1
        AND expires_at IS NOT NULL
        """
    )

    orders = cur.fetchall()

    conn.close()

    for order in orders:

        order_id, user_id, role_id, expires_at = order

        expiry = parse_dt(
            expires_at
        )

        if not expiry:
            continue

        if now_utc() < expiry:
            continue

        guild = bot.get_guild(
            GUILD_ID
        )

        if not guild:
            continue

        member = guild.get_member(
            user_id
        )

        role = guild.get_role(
            role_id
        )

        if member and role:

            await remove_access_role(
                member,
                role
            )

        conn = db()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE orders
            SET role_granted = 0
            WHERE id = ?
            """,
            (order_id,)
        )

        conn.commit()
        conn.close()


# =========================================================
# COMMANDS
# =========================================================

@bot.command(name="buyaccess")
async def buyaccess(ctx):

    await ctx.send(
        embed=buy_panel_embed(),
        view=BuyView()
    )


@bot.command(name="support")
async def support(ctx):

    await ctx.send(
        embed=support_panel_embed(),
        view=SupportView()
    )


# =========================================================
# WELCOME / LEAVE
# =========================================================

@bot.event
async def on_member_join(member):

    channel = member.guild.get_channel(
        WELCOME_LEAVE_CHANNEL_ID
    )

    if not channel:
        return

    embed = discord.Embed(
        title="👋 Welcome to Tropik Studios",
        description=(
            f"Welcome {member.mention}!\n\n"
            "We are happy to have you here."
        ),
        color=discord.Color.purple()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    await channel.send(
        embed=embed
    )


@bot.event
async def on_member_remove(member):

    channel = member.guild.get_channel(
        WELCOME_LEAVE_CHANNEL_ID
    )

    if not channel:
        return

    embed = discord.Embed(
        title="👋 Member Left",
        description=(
            f"**{member}** has left Tropik Studios."
        ),
        color=discord.Color.red()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    await channel.send(
        embed=embed
    )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print(
        f"Logged in as {bot.user}"
    )

    init_db()

    bot.add_view(
        BuyView()
    )

    bot.add_view(
        SupportView()
    )

    bot.add_view(
        TicketView()
    )

    bot.add_view(
        SupportTicketView()
    )

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild and guild.me:

        print(
            f"BOT TOP ROLE: "
            f"{guild.me.top_role.name}"
        )

        print(
            f"BOT TOP ROLE POSITION: "
            f"{guild.me.top_role.position}"
        )

        role1 = guild.get_role(
            ROLE_1_DAY
        )

        role7 = guild.get_role(
            ROLE_7_DAY
        )

        if role1:

            print(
                f"1 DAY ROLE POSITION: "
                f"{role1.position}"
            )

        if role7:

            print(
                f"7 DAY ROLE POSITION: "
                f"{role7.position}"
            )

        if not guild.me.guild_permissions.manage_roles:

            print(
                "WARNING: BOT DOES NOT HAVE MANAGE ROLES!"
            )

    if not payment_watcher.is_running():

        payment_watcher.start()

    if not expiry_watcher.is_running():

        expiry_watcher.start()

    print(
        "BOT IS ONLINE"
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    bot.run(TOKEN)