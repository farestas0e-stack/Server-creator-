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

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("server_creator")


@dataclass(frozen=True)
class ChannelSpec:
    name: str
    kind: str
    topic: str
    tags: tuple[str, ...] = ()
    read_only: bool = False


SERVER_LAYOUT: tuple[tuple[str, tuple[ChannelSpec, ...]], ...] = (
    ("🚀 START HERE", (
        ChannelSpec("announcements", "announcement", "Official community news, changes, and important updates.", read_only=True),
        ChannelSpec("get-roles", "text", "Use the buttons below to choose your interests and notification roles.", read_only=True),
    )),
    ("📚 THE REVEALS PLAYBOOK V1", (
        ChannelSpec("course-modules", "text", "The course lessons are hosted in the main course server. Use the official link posted here.", read_only=True),
        ChannelSpec("doubts", "forum", "Ask course-related questions. Create one post per question.", ("Beginner", "Intermediate", "Advanced", "Solved")),
        ChannelSpec("learning-resources", "forum", "Share and discover useful learning material.", ("Guide", "Tutorial", "Reference", "Other")),
        ChannelSpec("homework-and-tasks", "forum", "Practice tasks, assignments, and member submissions.", ("Task", "Submission", "Feedback Needed", "Completed")),
    )),
    ("💬 COMMUNITY", (
        ChannelSpec("inner-circle-chat", "text", "Everyday conversation and community networking."),
        ChannelSpec("wins", "text", "Share milestones, results, screenshots, and progress."),
        ChannelSpec("daily-accountability", "forum", "Post goals, daily progress, and accountability updates.", ("Daily Goal", "Weekly Goal", "Progress", "Completed")),
    )),
    ("🎬 FEEDBACK", (
        ChannelSpec("clip-reviews", "forum", "Post a clip for constructive feedback. Include your goal and target audience.", ("Reel", "Short", "Advertisement", "Review Needed")),
        ChannelSpec("content-ideas", "forum", "Share hooks, content concepts, and creative inspiration.", ("Hook", "Idea", "Script", "Reference")),
        ChannelSpec("feedback-discussion", "text", "Discuss feedback, reviews, and ways to improve."),
    )),
    ("🧰 RESOURCES", (
        ChannelSpec("assets", "forum", "Share templates, downloadable files, and useful assets.", ("Template", "Guide", "File", "Other")),
        ChannelSpec("tools-and-deals", "forum", "Useful tools, discounts, and deals.", ("Free", "Paid", "Discount", "Tool")),
        ChannelSpec("ai-resources", "forum", "AI tools, prompts, workflows, and automation resources.", ("Tool", "Prompt", "Workflow", "Tutorial")),
    )),
    ("💰 EARN", (
        ChannelSpec("campaigns", "forum", "Official earning campaigns and campaign applications.", ("Open", "Closing Soon", "Closed", "Completed")),
        ChannelSpec("opportunities", "forum", "Collaborations, partnerships, hiring, and business opportunities.", ("Collaboration", "Partnership", "Hiring", "Looking For", "Offering")),
        ChannelSpec("success-stories", "forum", "Share earning case studies, results, and lessons learned.", ("Case Study", "First Sale", "Milestone", "Lessons")),
    )),
    ("⚙️ COMMUNITY MANAGEMENT", (
        ChannelSpec("suggestions", "forum", "Suggest improvements and ideas for the community.", ("New Idea", "Improvement", "Bug Report", "Under Review", "Implemented")),
        ChannelSpec("support", "text", "Ask for help with community access or server issues."),
        ChannelSpec("report-an-issue", "text", "Report server issues to the team. Do not post passwords or sensitive personal information.", read_only=False),
    )),
)

VOICE_CHANNELS = (
    ("🔊 Community Lounge", "Casual voice conversations and member networking."),
    ("🔊 Study Room", "Quiet co-working and focused study sessions."),
)

INTEREST_ROLES = (
    ("Content Creator", "content_creator"),
    ("AI & Automation", "ai_automation"),
    ("Business & Earning", "business_earning"),
    ("Feedback & Networking", "feedback_networking"),
)


async def db_init() -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        await db.commit()


async def get_setting(key: str) -> str | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def set_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await db.commit()


class InterestRoleView(discord.ui.View):
    """Persistent role picker. Members can toggle their own interest roles."""

    def __init__(self) -> None:
        super().__init__(timeout=None)
        for label, key in INTEREST_ROLES:
            self.add_item(InterestRoleButton(label, key))


class InterestRoleButton(discord.ui.Button):
    def __init__(self, label: str, key: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.secondary, custom_id=f"interest_role:{key}")
        self.role_name = label

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Use this button inside the server.", ephemeral=True)
            return
        role = discord.utils.get(interaction.guild.roles, name=self.role_name)
        if role is None:
            await interaction.response.send_message("That interest role is not set up yet. Ask an admin to run /setupserver.", ephemeral=True)
            return
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role, reason="Member updated interest roles")
                message = f"Removed **{role.name}**."
            else:
                await interaction.user.add_roles(role, reason="Member selected an interest role")
                message = f"Added **{role.name}**."
            await interaction.response.send_message(message, ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I cannot manage that role. Move my bot role above the interest roles in Server Settings → Roles.", ephemeral=True)


class ServerCreator(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self) -> None:
        await db_init()
        self.add_view(InterestRoleView())
        synced = await self.tree.sync()
        log.info("Synced %s application commands", len(synced))


bot = ServerCreator()


async def get_or_create_role(guild: discord.Guild, name: str, permissions: discord.Permissions | None = None) -> discord.Role:
    role = discord.utils.get(guild.roles, name=name)
    if role:
        return role
    return await guild.create_role(name=name, permissions=permissions or discord.Permissions.none(),
                                   mentionable=False, reason="Created by Server Creator")


async def get_or_create_category(guild: discord.Guild, name: str, overwrites: dict) -> discord.CategoryChannel:
    category = discord.utils.get(guild.categories, name=name)
    if category:
        await category.edit(overwrites=overwrites, reason="Apply Server Creator permissions")
        return category
    return await guild.create_category(name=name, overwrites=overwrites, reason="Created by Server Creator")


def category_overwrites(guild: discord.Guild, host: discord.Role, member: discord.Role, guest: discord.Role,
                        guest_can_view: bool = False) -> dict:
    return {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        host: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True,
                                           manage_channels=True, create_public_threads=True,
                                           send_messages_in_threads=True, attach_files=True, embed_links=True),
        member: discord.PermissionOverwrite(view_channel=True, read_message_history=True),
        guest: discord.PermissionOverwrite(view_channel=guest_can_view, read_message_history=True),
    }


def channel_overwrites(guild: discord.Guild, host: discord.Role, member: discord.Role, guest: discord.Role,
                       spec: ChannelSpec, category_name: str) -> dict:
    guest_visible = category_name == "🚀 START HERE" and (spec.name == "announcements" or spec.name == "get-roles")
    ow = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        host: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True,
                                          create_public_threads=True, send_messages_in_threads=True,
                                          attach_files=True, embed_links=True),
        member: discord.PermissionOverwrite(view_channel=True, read_message_history=True),
        guest: discord.PermissionOverwrite(view_channel=guest_visible, read_message_history=True),
    }
    if spec.read_only:
        ow[member].send_messages = False
        ow[guest].send_messages = False
    elif spec.kind == "forum":
        ow[member].create_public_threads = True
        ow[member].send_messages_in_threads = True
        ow[member].attach_files = True
        ow[guest].create_public_threads = False
        ow[guest].send_messages_in_threads = False
    else:
        ow[member].send_messages = True
        ow[member].attach_files = True
        ow[member].embed_links = True
        ow[guest].send_messages = False
    return ow


async def create_or_update_channel(guild: discord.Guild, category: discord.CategoryChannel,
                                   spec: ChannelSpec, overwrites: dict) -> tuple[discord.abc.GuildChannel | None, str]:
    existing = discord.utils.get(category.channels, name=spec.name)
    expected = discord.ForumChannel if spec.kind == "forum" else discord.TextChannel
    if existing:
        if not isinstance(existing, expected):
            return None, f"Skipped #{spec.name}: existing channel has the wrong type."
        await existing.edit(topic=spec.topic, overwrites=overwrites, reason="Update Server Creator channel")
        if isinstance(existing, discord.ForumChannel):
            await existing.edit(available_tags=[discord.ForumTag(name=tag) for tag in spec.tags])
        return existing, f"Updated #{spec.name}"
    if spec.kind == "forum":
        channel = await guild.create_forum(spec.name, category=category, topic=spec.topic,
                                           available_tags=[discord.ForumTag(name=tag) for tag in spec.tags],
                                           overwrites=overwrites, reason="Created by Server Creator")
    else:
        channel = await guild.create_text_channel(spec.name, category=category, topic=spec.topic,
                                                  news=(spec.kind == "announcement"), overwrites=overwrites,
                                                  reason="Created by Server Creator")
    return channel, f"Created #{spec.name}"


async def create_voice_channels(guild: discord.Guild, category: discord.CategoryChannel,
                                host: discord.Role, member: discord.Role, guest: discord.Role) -> list[str]:
    results = []
    overwrites = category_overwrites(guild, host, member, guest)
    for name, topic in VOICE_CHANNELS:
        channel = discord.utils.get(category.voice_channels, name=name)
        if channel:
            await channel.edit(overwrites=overwrites, user_limit=0, reason="Update Server Creator voice channel")
            results.append(f"Updated voice: {name}")
        else:
            await guild.create_voice_channel(name, category=category, overwrites=overwrites,
                                             reason="Created by Server Creator")
            results.append(f"Created voice: {name}")
    return results


async def publish_course_invite(channel: discord.TextChannel) -> bool:
    invite = await get_setting("course_invite")
    if not invite:
        return False
    embed = discord.Embed(title="THE REVEALS PLAYBOOK V1",
                          description=f"The course modules are hosted in the main server.\n\n[Open the course server]({invite})",
                          color=discord.Color.blurple())
    embed.set_footer(text="Official course access")
    await channel.send(embed=embed)
    return True


async def publish_role_picker(channel: discord.TextChannel) -> None:
    embed = discord.Embed(title="Choose your interests",
                          description="Tap a button to add or remove the matching interest role. You can choose more than one.",
                          color=discord.Color.blurple())
    await channel.send(embed=embed, view=InterestRoleView())


@bot.tree.command(name="setupserver", description="Create or update the approved Reveals Playbook server layout.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def setupserver(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    try:
        host_perms = discord.Permissions(manage_channels=True, manage_messages=True, manage_roles=True,
                                         kick_members=True, moderate_members=True, view_audit_log=True)
        host = await get_or_create_role(guild, "Admin/Host", host_perms)
        member = await get_or_create_role(guild, "VIP/Member")
        guest = await get_or_create_role(guild, "Guest/Unverified")
        for role_name, _ in INTEREST_ROLES:
            await get_or_create_role(guild, role_name)

        report: list[str] = []
        for category_name, specs in SERVER_LAYOUT:
            guest_can_view = category_name == "🚀 START HERE"
            category = await get_or_create_category(
                guild, category_name, category_overwrites(guild, host, member, guest, guest_can_view)
            )
            for spec in specs:
                channel, status = await create_or_update_channel(
                    guild, category, spec, channel_overwrites(guild, host, member, guest, spec, category_name)
                )
                report.append(status)
                if channel and spec.name == "get-roles" and isinstance(channel, discord.TextChannel):
                    if not channel.last_message_id:
                        await publish_role_picker(channel)
                        report.append("Posted the interest-role buttons in #get-roles")
                if channel and spec.name == "course-modules" and isinstance(channel, discord.TextChannel):
                    if not channel.last_message_id and await publish_course_invite(channel):
                        report.append("Posted the saved course invite in #course-modules")

        voice_category = await get_or_create_category(
            guild, "🔊 VOICE ROOMS", category_overwrites(guild, host, member, guest)
        )
        report.extend(await create_voice_channels(guild, voice_category, host, member, guest))

        output = "\n".join(report)
        if len(output) > 1850:
            output = output[:1840] + "\n…"
        await interaction.followup.send(
            f"**Server setup completed.**\n{output}\n\nNo existing channels or messages were deleted. Assign members to VIP/Member or Guest/Unverified manually.",
            ephemeral=True,
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "I lack permissions. Give the bot Manage Channels and Manage Roles, then move its bot role above the roles it must manage.",
            ephemeral=True,
        )
    except Exception:
        log.exception("Server setup failed")
        await interaction.followup.send("Setup encountered an error. Check the bot console. Existing channels are not intentionally deleted.", ephemeral=True)


@bot.tree.command(name="setcourseinvite", description="Save the main course server invite link.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@app_commands.describe(invite_url="Discord invite to the main course server")
async def setcourseinvite(interaction: discord.Interaction, invite_url: str) -> None:
    if not (invite_url.startswith("https://discord.gg/") or invite_url.startswith("https://discord.com/invite/")):
        await interaction.response.send_message("Use a valid discord.gg or discord.com/invite URL.", ephemeral=True)
        return
    await set_setting("course_invite", invite_url)
    await interaction.response.send_message("Invite saved. Run /postcourseinvite to publish it in #course-modules.", ephemeral=True)


@bot.tree.command(name="postcourseinvite", description="Post the saved main course server link.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def postcourseinvite(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        return
    channel = discord.utils.get(interaction.guild.text_channels, name="course-modules")
    if channel is None:
        await interaction.response.send_message("Run /setupserver first.", ephemeral=True)
        return
    if not await publish_course_invite(channel):
        await interaction.response.send_message("Save the invite first with /setcourseinvite.", ephemeral=True)
        return
    await interaction.response.send_message("Posted the course invite.", ephemeral=True)


@bot.tree.command(name="postrolepicker", description="Post the interest-role selection buttons in #get-roles.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def postrolepicker(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        return
    channel = discord.utils.get(interaction.guild.text_channels, name="get-roles")
    if channel is None:
        await interaction.response.send_message("Run /setupserver first.", ephemeral=True)
        return
    await publish_role_picker(channel)
    await interaction.response.send_message("Posted the role picker.", ephemeral=True)


@bot.event
async def on_ready() -> None:
    log.info("Ready as %s (%s)", bot.user, bot.user.id if bot.user else "unknown")


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing. Copy .env.example to .env and add your bot token.")
    bot.run(TOKEN)
