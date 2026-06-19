import discord
import asyncio
import os
import sys
import logging
from flask import Flask
from threading import Thread

# ─── LOGGING ───
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', stream=sys.stdout)
logger = logging.getLogger("ClonerEngine")

# ─── GATEWAY PATCH ───
from discord.state import ConnectionState
def patched_parse_ready_supplemental(self, data):
    try:
        self.pending_payments = {int(p['id']): p for p in data.get('pending_payments') or []}
    except Exception:
        self.pending_payments = {}
ConnectionState.parse_ready_supplemental = patched_parse_ready_supplemental

# ─── CONFIG ───
ACCOUNT_TOKEN = os.getenv("TOKEN1")
if not ACCOUNT_TOKEN:
    ACCOUNT_TOKEN = "YOUR_HARDCODED_TOKEN_HERE"

SOURCE_SERVER_ID = 1443875856803168360
TARGET_SERVER_ID = 1517627991369449623
DRY_RUN = False

# ─── FLASK KEEP-ALIVE ───
app = Flask('')
@app.route('/')
def home():
    return "Cloning Engine is active!"

def run():
    port = int(os.environ.get("PORT", 7860))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run, daemon=True).start()

# ─── CLONING ENGINE (with fixed permission check) ───
async def start_cloning_engine(client, source_guild, target_guild):
    logger.info(f"\n{'='*50}\n🚀 CLONING INITIALIZED\n📁 Source: {source_guild.name}\n🎯 Target: {target_guild.name}\n{'='*50}")

    # ─── Check permissions (fixed for self‑bots) ───
    self_member = target_guild.get_member(client.user.id)
    if not self_member:
        logger.error("❌ Could not find yourself in the target guild.")
        return
    if not self_member.guild_permissions.manage_channels:
        logger.error("❌ Account does not have 'Manage Channels' permission in the target server.")
        return

    # ─── STEP 1: Purge channels ───
    logger.info("🧹 [1/4] Clearing target channels...")
    if not DRY_RUN:
        for channel in target_guild.channels:
            try:
                await channel.delete()
                await asyncio.sleep(0.2)
            except Exception:
                pass

    # ─── STEP 2: Roles ───
    logger.info("\n🎭 [2/4] Duplicating roles...")
    role_mapping = {}
    for role in sorted(source_guild.roles, key=lambda r: r.position, reverse=True):
        if role.is_default():
            if not DRY_RUN:
                try:
                    await target_guild.default_role.edit(permissions=role.permissions)
                except Exception:
                    pass
            continue
        if role.managed:
            continue
        if not DRY_RUN:
            try:
                new_role = await target_guild.create_role(
                    name=role.name,
                    permissions=role.permissions,
                    color=role.color,
                    hoist=role.hoist,
                    mentionable=role.mentionable
                )
                role_mapping[role.id] = new_role
                logger.info(f"✅ Created role: {role.name}")
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"❌ Failed to create role {role.name}: {e}")

    # ─── STEP 3: Categories & Channels ───
    logger.info("\n📁 [3/4] Building categories and channels...")
    categories = source_guild.categories
    logger.info(f"📊 Found {len(categories)} categories in source.")

    for category in categories:
        cat_overwrites = {}
        for role_or_member, overwrite in category.overwrites.items():
            if isinstance(role_or_member, discord.Role):
                mapped_role = role_mapping.get(role_or_member.id)
                if mapped_role:
                    cat_overwrites[mapped_role] = overwrite

        if not DRY_RUN:
            try:
                new_category = await target_guild.create_category(
                    name=category.name,
                    overwrites=cat_overwrites
                )
                logger.info(f"📂 Category: {category.name}")
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"❌ Failed category {category.name}: {e}")
                continue
        else:
            new_category = None

        # Text channels in this category
        for txt_chan in sorted(category.text_channels, key=lambda c: c.position):
            chan_overwrites = {}
            for role_or_member, overwrite in txt_chan.overwrites.items():
                if isinstance(role_or_member, discord.Role):
                    mapped_role = role_mapping.get(role_or_member.id)
                    if mapped_role:
                        chan_overwrites[mapped_role] = overwrite

            if not DRY_RUN:
                try:
                    await target_guild.create_text_channel(
                        name=txt_chan.name,
                        category=new_category,
                        topic=txt_chan.topic,
                        nsfw=txt_chan.nsfw,
                        slowmode_delay=txt_chan.slowmode_delay,
                        overwrites=chan_overwrites
                    )
                    logger.info(f"  ├── 📝 Text: {txt_chan.name}")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"  ├── ❌ Failed text channel {txt_chan.name}: {e}")

        # Voice channels in this category
        for vc_chan in sorted(category.voice_channels, key=lambda c: c.position):
            chan_overwrites = {}
            for role_or_member, overwrite in vc_chan.overwrites.items():
                if isinstance(role_or_member, discord.Role):
                    mapped_role = role_mapping.get(role_or_member.id)
                    if mapped_role:
                        chan_overwrites[mapped_role] = overwrite

            if not DRY_RUN:
                try:
                    max_bitrate = target_guild.bitrate_limit
                    bitrate = max(8000, min(vc_chan.bitrate, max_bitrate))
                    await target_guild.create_voice_channel(
                        name=vc_chan.name,
                        category=new_category,
                        user_limit=vc_chan.user_limit,
                        bitrate=bitrate,
                        overwrites=chan_overwrites
                    )
                    logger.info(f"  ├── 🔊 Voice: {vc_chan.name}")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"  ├── ❌ Failed voice channel {vc_chan.name}: {e}")

    # ─── Handle uncategorized channels ───
    uncategorized = [ch for ch in source_guild.channels if ch.category is None and not isinstance(ch, discord.CategoryChannel)]
    logger.info(f"📊 Found {len(uncategorized)} uncategorized channels.")

    for channel in uncategorized:
        chan_overwrites = {}
        for role_or_member, overwrite in channel.overwrites.items():
            if isinstance(role_or_member, discord.Role):
                mapped_role = role_mapping.get(role_or_member.id)
                if mapped_role:
                    chan_overwrites[mapped_role] = overwrite

        if isinstance(channel, discord.TextChannel):
            if not DRY_RUN:
                try:
                    await target_guild.create_text_channel(
                        name=channel.name,
                        topic=channel.topic,
                        nsfw=channel.nsfw,
                        slowmode_delay=channel.slowmode_delay,
                        overwrites=chan_overwrites
                    )
                    logger.info(f"📝 Uncategorized Text: {channel.name}")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"❌ Failed uncategorized text channel {channel.name}: {e}")
        elif isinstance(channel, discord.VoiceChannel):
            if not DRY_RUN:
                try:
                    max_bitrate = target_guild.bitrate_limit
                    bitrate = max(8000, min(channel.bitrate, max_bitrate))
                    await target_guild.create_voice_channel(
                        name=channel.name,
                        user_limit=channel.user_limit,
                        bitrate=bitrate,
                        overwrites=chan_overwrites
                    )
                    logger.info(f"🔊 Uncategorized Voice: {channel.name}")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"❌ Failed uncategorized voice channel {channel.name}: {e}")

    # ─── STEP 4: Emojis ───
    logger.info("\n👾 [4/4] Syncing emojis...")
    if source_guild.emojis:
        available = target_guild.emoji_limit - len(target_guild.emojis)
        emojis_to_copy = source_guild.emojis[:available]
        logger.info(f"📊 Copying {len(emojis_to_copy)} emojis...")
        for i, emoji in enumerate(emojis_to_copy):
            if not DRY_RUN:
                try:
                    emoji_bytes = await emoji.read()
                    await target_guild.create_custom_emoji(
                        name=emoji.name,
                        image=emoji_bytes
                    )
                    logger.info(f"  ✅ Copied emoji :{emoji.name}: ({i+1}/{len(emojis_to_copy)})")
                    await asyncio.sleep(1.0)
                except discord.HTTPException as e:
                    if e.status == 429:
                        retry_after = getattr(e, 'retry_after', 5)
                        logger.warning(f"  ⏳ Rate limited on :{emoji.name}: waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        try:
                            emoji_bytes = await emoji.read()
                            await target_guild.create_custom_emoji(name=emoji.name, image=emoji_bytes)
                            logger.info(f"  ✅ Retry succeeded :{emoji.name}:")
                        except Exception as e2:
                            logger.error(f"  ❌ Failed to copy emoji :{emoji.name}: {e2}")
                    else:
                        logger.error(f"  ❌ Failed to copy emoji :{emoji.name}: {e}")
                except Exception as e:
                    logger.error(f"  ❌ Failed to copy emoji :{emoji.name}: {e}")

    logger.info("\n" + "="*50)
    logger.info("🎉 CLONING COMPLETED SUCCESSFULLY!")
    logger.info(f"📊 Roles created: {len(role_mapping)}")
    logger.info("="*50 + "\n")

# ─── MAIN BOOT ───
async def main_boot():
    keep_alive()
    logger.info("🚀 SYSTEM BOOT: DIRECT CONNECTION MODE")

    if not ACCOUNT_TOKEN or ACCOUNT_TOKEN == "YOUR_HARDCODED_TOKEN_HERE":
        logger.error("❌ TOKEN1 not set!")
        return

    client = discord.Client(
        self_bot=True,
        browser="chrome",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        compress=False
    )

    @client.event
    async def on_ready():
        logger.info(f"✨ [ON_READY] Authenticated as: {client.user}")

    # Start client in background
    asyncio.create_task(client.start(ACCOUNT_TOKEN.strip()))

    # Wait for authentication by polling client.user
    logger.info("⏳ Waiting for client to authenticate...")
    auth_attempts = 0
    while client.user is None and auth_attempts < 30:
        await asyncio.sleep(1)
        auth_attempts += 1

    if client.user is None:
        logger.error("❌ Authentication failed after 30 seconds.")
        return

    logger.info(f"✨ Authenticated as: {client.user}")

    # Wait for connection to stabilize
    logger.info("⏳ Waiting 10s for connection to stabilize...")
    await asyncio.sleep(10)

    logger.info("⏳ Fetching guilds directly from Discord API...")
    try:
        source_guild, target_guild = await asyncio.gather(
            client.fetch_guild(SOURCE_SERVER_ID),
            client.fetch_guild(TARGET_SERVER_ID)
        )
        logger.info(f"✅ Source guild found: {source_guild.name}")
        logger.info(f"✅ Target guild found: {target_guild.name}")
        await start_cloning_engine(client, source_guild, target_guild)
    except discord.NotFound:
        logger.error("❌ One or both guilds not found. Check the IDs.")
        logger.error(f"📋 Source ID: {SOURCE_SERVER_ID}, Target ID: {TARGET_SERVER_ID}")
    except discord.Forbidden:
        logger.error("❌ Bot does not have access to one or both guilds.")
    except Exception as e:
        logger.error(f"❌ Error fetching guilds: {e}")

    # Keep alive
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main_boot())
    except KeyboardInterrupt:
        logger.info("Stopping Cloner...")
    except Exception as e:
        logger.error(f"Fatal System Error: {e}")
