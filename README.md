# Server Creator

A Python Discord bot that builds and updates the approved **The Reveals Playbook V1** community server.

## What it creates

- Categories and text, announcement, forum, and voice channels from the approved layout.
- Starter channel topics and forum tags.
- Roles: `Admin/Host`, `VIP/Member`, `Guest/Unverified`, plus selectable interest roles.
- Channel/category visibility and posting permissions.
- Persistent interest-role buttons in `#get-roles`.
- Main course-server invite storage and publishing.

## Server layout

- 🚀 START HERE: `#announcements`, `#get-roles`
- 📚 THE REVEALS PLAYBOOK V1: `#course-modules`, `#doubts`, `#learning-resources`, `#homework-and-tasks`
- 💬 COMMUNITY: `#inner-circle-chat`, `#wins`, `#daily-accountability`
- 🎬 FEEDBACK: `#clip-reviews`, `#content-ideas`, `#feedback-discussion`
- 🧰 RESOURCES: `#assets`, `#tools-and-deals`, `#ai-resources`
- 💰 EARN: `#campaigns`, `#opportunities`, `#success-stories`
- ⚙️ COMMUNITY MANAGEMENT: `#suggestions`, `#support`, `#report-an-issue`
- 🔊 VOICE ROOMS: `Community Lounge`, `Study Room`

Removed as requested: `#welcome`, `#rules`, `#start-here`, and `#introductions`.

## Commands

- `/setupserver` — create or update the server layout. It does not delete existing channels or messages.
- `/setcourseinvite` — save the main course-server invite.
- `/postcourseinvite` — post the saved invite in `#course-modules`.
- `/postrolepicker` — repost the interest-role buttons in `#get-roles`.

## Requirements

- Python 3.10+
- discord.py 2.x
- aiosqlite
- python-dotenv

## Discord setup

1. Create an application and Bot user in the Discord Developer Portal.
2. Copy the bot token privately. Never paste it into chat or commit it to GitHub.
3. Invite the bot with the `bot` and `applications.commands` OAuth scopes.
4. Grant: Manage Channels, Manage Roles, View Channels, Send Messages, Send Messages in Threads, Read Message History, Embed Links, Attach Files, and Connect/Speak if voice management requires them.
5. Move the bot's role above the roles it needs to manage.

No privileged Gateway intents are required.

## Run in Termux

```bash
pkg update
pkg install python git
git clone https://github.com/farestas0e-stack/Server-creator-.git
cd Server-creator-
python -m pip install -r requirements.txt
cp .env.example .env
nano .env
python main.py
```

Put your token in `.env` as `DISCORD_TOKEN=your_token_here`. Keep `.env` private.

## First setup

1. Start the bot.
2. Run `/setupserver` in the target server as an administrator.
3. Run `/setcourseinvite` with the main course-server invite.
4. Run `/postcourseinvite` to publish it.
5. Assign members to `VIP/Member` and unverified users to `Guest/Unverified`. The role picker lets members toggle interest roles.

## Important notes

- The bot creates roles but does not automatically assign the membership roles.
- Interest-role buttons are persistent across bot restarts.
- Existing channels with an unexpected type are reported as skipped rather than deleted or replaced.
- Re-running setup updates matching channels and permissions. Review the result before opening the server.
- `#report-an-issue` is a server-visible text channel, not a private ticket system.
