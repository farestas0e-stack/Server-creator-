from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_PATH = os.getenv("DATABASE_PATH", "server_creator.sqlite3")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("server_creator")


@dataclass(frozen=True)
class ChannelSpec:
    name: str
    kind: str
    topic: str
    tags: tuple[str, ...] = ()
    read_only: bool = False


SERVER_LAYOUT: tuple[tuple[str, tuple[ChannelSpec, ...]], ...] = (
    (
        "🚀 START HERE",
        (
            ChannelSpec("start-here", "text", "Start here: read the welcome guide, rules, and how to access the community.", read_only=True),
            ChannelSpec("announcements", "announcement", "Official updates and important announcements.", read_only=True),
            ChannelSpec("introductions", "forum", "Introduce yourself to the community. One post per member.", ("New Member", "Introduced")),
        ),
    ),
    (
        "📚 THE REVEALS PLAYBOOK V1",
        (
            ChannelSpec("course-modules", "text", "Course access hub. The lessons and modules are hosted in the main course server.", read_only=True),
            ChannelSpec("doubts", "forum", "Ask course-related questions. Create one post per question.", ("Beginner", "Intermediate", "Advanced", "Solved")),
        ),
    ),
    (
        "💬 COMMUNITY",
        (
            ChannelSpec("inner-circle-chat", "text", "Chat, connect, and support other members."),
            ChannelSpec("wins", "text", "Share your milestones, results, screenshots, and progress. Celebrate each other's wins."),
        ),
    ),
    (
        "🎬 FEEDBACK",
        (
            ChannelSpec("clip-reviews", "forum", "Post a clip for constructive feedback. Include your goal and the audience you want to reach.", ("Reel", "Short", "Advertisement", "Review Needed")),
        ),
    ),
    (
        "🧰 RESOURCES",
        (
            ChannelSpec("assets", "forum", "Share useful files, templates, guides, and other resources.", ("Template", "Guide", "File", "Other")),
            ChannelSpec("tools-and-deals", "forum", "Share useful tools, discounts, and deals with the community.", ("Free", "Paid", "Discount", "Tool")),
        ),
    ),
    (
        "💰 EARN",
        (
            ChannelSpec("campaigns", "forum", "Official earning campaigns and campaign application discussions.", ("Open", "Closing Soon", "Closed", "Completed")),
            ChannelSpec("opportunities", "forum", "Share or find collaborations, partnerships, hiring, and business opportunities.", ("Collaboration", "Partnership", "Hiring", "Looking For", "Offering")),
        ),
    ),
    (
        "⚙️ COMMUNITY MANAGEMENT",
        (
            ChannelSpec("suggestions", "forum", "Suggest improvements and ideas for the community. The team reviews submissions here.", ("New Idea", "Improvement", "Bug Report", "Under Review", "Implemented")),
        ),
    ),
)


class ServerCreator(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            await db.commit()
        synced = await self.tree.sync()
        log.info("Synced %s application commands", len(synced))


bot = ServerCreator()


async def get_setting(key: str) -> str | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def set_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


def base_overwrites(
    guild: discord.Guild,
    host_role: discord.Role,
    member_role: discord.Role,
    guest_role: discord.Role,
) -> dict:
    return {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        host_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            create_forum_threads=True,
            send_messages_in_threads=True,
            attach_files=True,
            embed_links=True,
            manage_messages=True,
            manage_channels=True,
        ),
        member_role: discord.PermissionOverwrite(view_channel=True, read_message_history=True),
        guest_role: discord.PermissionOverwrite(view_channel=False),
    }


async def get_or_create_role(
    guild: discord.Guild, name: str, permissions: discord.Permissions | None = None
) -> discord.Role:
    role = discord.utils.get(guild.roles, name=name)
    if role:
        return role
    return await guild.create_role(
        name=name,
        permissions=permissions or discord.Permissions.none(),
        mentionable=False,
        reason="Created by Server Creator setup",
    )


async def get_or_create_category(
    guild: discord.Guild, name: str, overwrites: dict
) -> discord.CategoryChannel:
    category = discord.utils.get(guild.categories, name=name)
    if category:
        await category.edit(overwrites=overwrites, reason="Apply Server Creator permissions")
        return category
    return await guild.create_category(
        name=name, overwrites=overwrites, reason="Created by Server Creator"
    )


def channel_overwrites(
    guild: discord.Guild,
    host_role: discord.Role,
    member_role: discord.Role,
    guest_role: discord.Role,
    spec: ChannelSpec,
    category_name: str,
) -> dict:
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        host_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            create_forum_threads=True,
            send_messages_in_threads=True,
            attach_files=True,
            embed_links=True,
            manage_messages=True,
            manage_channels=True,
        ),
        member_role: discord.PermissionOverwrite(view_channel=True, read_message_history=True),
        guest_role: discord.PermissionOverwrite(view_channel=(category_name == "🚀 START HERE" and spec.name in {"start-here", "announcements"}), read_message_history=True),
    }

    if spec.name in {"start-here", "announcements", "course-modules"}:
        overwrites[member_role].send_messages = False
        overwrites[guest_role].send_messages = False
    elif spec.kind == "forum":
        overwrites[member_role].create_forum_threads = True
        overwrites[member_role].send_messages_in_threads = True
        overwrites[member_role].attach_files = True
        overwrites[guest_role].create_forum_threads = False
        overwrites[guest_role].send_messages_in_threads = False
    else:
        overwrites[member_role].send_messages = True
        overwrites[member_role].attach_files = True
        overwrites[member_role].embed_links = True
        overwrites[guest_role].send_messages = False

    if spec.read_only:
        overwrites[member_role].send_messages = False
        overwrites[member_role].create_forum_threads = False
        overwrites[member_role].send_messages_in_threads = False
    return overwrites


async def create_or_update_channel(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    spec: ChannelSpec,
    overwrites: dict,
) -> tuple[discord.abc.GuildChannel | None, str]:
    existing = discord.utils.get(category.channels, name=spec.name)
    expected = {
        "text": discord.TextChannel,
        "announcement": discord.TextChannel,
        "forum": discord.ForumChannel,
    }[spec.kind]

    if existing:
        if not isinstance(existing, expected):
            return None, f"Skipped #{spec.name}: a channel with that name exists but has the wrong type."
        await existing.edit(topic=spec.topic, overwrites=overwrites, reason="Update Server Creator channel")
        if isinstance(existing, discord.ForumChannel):
            await existing.edit(available_tags=[discord.ForumTag(name=tag) for tag in spec.tags])
        return existing, f"Updated #{spec.name}"

    if spec.kind == "forum":
        channel = await guild.create_forum(
            spec.name,
            category=category,
            topic=spec.topic,
            available_tags=[discord.ForumTag(name=tag) for tag in spec.tags],
            overwrites=overwrites,
            reason="Created by Server Creator",
        )
    else:
        channel = await guild.create_text_channel(
            spec.name,
            category=category,
            topic=spec.topic,
            news=(spec.kind == "announcement"),
            overwrites=overwrites,
            reason="Created by Server Creator",
        )
    return channel, f"Created #{spec.name}"


async def publish_course_invite(channel: discord.TextChannel) -> bool:
    invite = await get_setting("course_invite")
    if not invite:
        return False
    embed = discord.Embed(
        title="THE REVEALS PLAYBOOK V1",
        description=f"Access the course modules in the main server using the link below.\n\n[Open the course server]({invite})",
        color=discord.Color.blurple(),
    )
    embed.set_footer(text="Official course access")
    await channel.send(embed=embed)
    return True


@bot.tree.command(name="setupserver", description="Create or update The Reveals Playbook community layout.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def setupserver(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild

    try:
        host_permissions = discord.Permissions(
            manage_channels=True,
            manage_messages=True,
            manage_roles=True,
            kick_members=True,
            moderate_members=True,
            view_audit_log=True,
        )
        host_role = await get_or_create_role(guild, "Admin/Host", host_permissions)
        member_role = await get_or_create_role(guild, "VIP/Member")
        guest_role = await get_or_create_role(guild, "Guest/Unverified")

        summary: list[str] = []
        for category_name, channel_specs in SERVER_LAYOUT:
            category_perms = base_overwrites(guild, host_role, member_role, guest_role)
            if category_name == "🚀 START HERE":
                category_perms[guest_role].view_channel = True
            category = await get_or_create_category(guild, category_name, category_perms)
            for spec in channel_specs:
                overwrites = channel_overwrites(
                    guild, host_role, member_role, guest_role, spec, category_name
                )
                channel, status = await create_or_update_channel(
                    guild, category, spec, overwrites
                )
                summary.append(status)
                if channel and spec.name == "course-modules" and isinstance(channel, discord.TextChannel):
                    if not channel.last_message_id:
                        posted = await publish_course_invite(channel)
                        if posted:
                            summary.append("Posted the saved main-server invite in #course-modules")

        report = "\n".join(summary)
        if len(report) > 1900:
            report = report[:1890] + "\n…"
        await interaction.followup.send(
            f"**Server setup finished.**\n{report}\n\nRoles were created if missing; assign members to VIP/Member or Guest/Unverified manually.",
            ephemeral=True,
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "I don't have enough permissions. Give the bot Manage Channels and Manage Roles, and move its role above the roles it needs to manage.",
            ephemeral=True,
        )
    except Exception:
        log.exception("Server setup failed")
        await interaction.followup.send(
            "Setup hit an error. Check the bot console for details; no existing channels were intentionally deleted.",
            ephemeral=True,
        )


@bot.tree.command(name="setcourseinvite", description="Save the main course server invite link.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@app_commands.describe(invite_url="Permanent or non-expiring invite link to the main course server")
async def setcourseinvite(interaction: discord.Interaction, invite_url: str) -> None:
    if not (invite_url.startswith("https://discord.gg/") or invite_url.startswith("https://discord.com/invite/")):
        await interaction.response.send_message(
            "Please provide a valid Discord invite URL (discord.gg or discord.com/invite).",
            ephemeral=True,
        )
        return
    await set_setting("course_invite", invite_url)
    await interaction.response.send_message(
        "Saved. Run /setupserver again to publish it in #course-modules if that channel is empty.",
        ephemeral=True,
    )


@bot.tree.command(name="postcourseinvite", description="Post the saved main course server link in #course-modules.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def postcourseinvite(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        return
    channel = discord.utils.get(interaction.guild.text_channels, name="course-modules")
    if channel is None:
        await interaction.response.send_message("I couldn't find #course-modules. Run /setupserver first.", ephemeral=True)
        return
    invite = await get_setting("course_invite")
    if not invite:
        await interaction.response.send_message("Set the invite first with /setcourseinvite.", ephemeral=True)
        return
    await publish_course_invite(channel)
    await interaction.response.send_message("Posted the main course server link in #course-modules.", ephemeral=True)


@bot.event
async def on_ready() -> None:
    log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id if bot.user else "unknown")


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing. Copy .env.example to .env and add your bot token.")
    bot.run(TOKEN)
