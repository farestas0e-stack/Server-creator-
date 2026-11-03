# Server Creator

A Python 3.10+ Discord bot that creates the **THE REVEALS PLAYBOOK V1** community layout.

## Stack

- Python 3.10+
- discord.py 2.x
- asyncio
- aiosqlite (stores the main course-server invite)
- python-dotenv

## Features in this first version

- `/setupserver` creates or updates the agreed categories and channels.
- Creates the roles `Admin/Host`, `VIP/Member`, and `Guest/Unverified` if they do not already exist.
- Creates text, announcement, and forum channels with starter topics and forum tags.
- Applies channel visibility and posting permissions.
- `/setcourseinvite` saves the invite to the main course server.
- `/postcourseinvite` posts the saved invite in `#course-modules`.
- Setup is non-destructive: it does not delete existing channels or messages.

## Server layout

- 🚀 START HERE: `#start-here`, `#announcements`, `#introductions`
- 📚 THE REVEALS PLAYBOOK V1: `#course-modules`, `#doubts`
- 💬 COMMUNITY: `#inner-circle-chat`, `#wins`
- 🎬 FEEDBACK: `#clip-reviews`
- 🧰 RESOURCES: `#assets`, `#tools-and-deals`
- 💰 EARN: `#campaigns`, `#opportunities`
- ⚙️ COMMUNITY MANAGEMENT: `#suggestions`

`#wins` and `#course-modules` are text channels. Lessons remain in the separate main course server.

## Discord Developer Portal

1. Create an application and add a Bot user.
2. Copy the bot token. Never share it in chat or commit it to GitHub.
3. In OAuth2 URL Generator, select scopes `bot` and `applications.commands`.
4. Grant the bot these permissions: Manage Channels, Manage Roles, View Channels, Send Messages, Send Messages in Threads, Read Message History, Embed Links, Attach Files.
5. Invite the bot to your community server.
6. In Server Settings → Roles, move the bot's role above the roles it needs to manage.

No privileged Gateway intents are required for this first version.

## Run on Termux

```bash
pkg update
pkg install python
git clone https://github.com/farestas0e-stack/Server-creator-.git
cd Server-creator-
python -m pip install -r requirements.txt
cp .env.example .env
nano .env
python main.py
```

Paste your bot token into `.env` as the value of `DISCORD_TOKEN`.

## First run

1. Start the bot with `python main.py`.
2. In your target Discord server, run `/setupserver` as an administrator.
3. Run `/setcourseinvite` with the invite link to your main course server.
4. Run `/postcourseinvite` to publish the link in `#course-modules`.
5. Assign members to `VIP/Member` and new/unverified users to `Guest/Unverified`. Assign trusted staff to `Admin/Host`.

## Important permission note

The bot creates the role names but does not automatically assign them to users. The `Admin/Host` role receives moderation and server-management permissions but not the full Administrator permission. Review role permissions and channel visibility before opening the server to members.
