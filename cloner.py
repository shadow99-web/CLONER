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
TARGET_SERVER_ID = 1517635362862661763
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

# ─── CLONING ENGINE (fixed: fetch channels explicitly) ───
async def start_cloning_engine(client, source_guild, target_guild):
    logger.info(f"\n{'='*50}\n🚀 CLONING INITIALIZED\n📁 Source: {source_guild.name}\n🎯 Target: {target_guild.name}\n{'='*50}")

    # ─── Check permissions using fetch_member ───
    try:
        self_member = await target_guild.fetch_member(client.user.id)
    except discord.NotFound:
        logger.error("❌ Could not find yourself in the target guild.")
        return
    except discord.Forbidden:
        logger.error("❌ Bot does not have permission to view members in the target guild.")
        return

    if not self_member.guild_permissions.manage_channels:
        logger.error("❌ Account does not have 'Manage Channels' permission in the target server.")
        return
    logger.info("✅ Permission check passed.")

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

    # ─── THE FIX: Fetch channels explicitly ───
    logger.info("⏳ Fetching channels from source guild...")
    try:
        source_channels = await source_guild.fetch_channels()
        logger.info(f"✅ Fetched {len(source_channels)} channels from source.")
    except Exception as e:
        logger.error(f"❌ Failed to fetch channels: {e}")
        return

    # Separate categories and non-category channels
    source_categories = [ch for ch in source_channels if isinstance(ch, discord.CategoryChannel)]
    source_text_channels = [ch for ch in source_channels if isinstance(ch, discord.TextChannel)]
    source_voice_channels = [ch for ch in source_channels if isinstance(ch, discord.VoiceChannel)]

    logger.info(f"📊 Categories: {len(source_categories)}, Text: {len(source_text_channels)}, Voice: {len(source_voice_channels)}")

    # ─── Create Categories ───
    category_mapping = {}
    for category in sorted(source_categories, key=lambda c: c.position):
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
                category_mapping[category.id] = new_category
                logger.info(f"📂 Category: {category.name}")
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"❌ Failed category {category.name}: {e}")

    # ─── Create Text Channels ───
    for txt_chan in sorted(source_text_channels, key=lambda c: c.position):
        chan_overwrites = {}
        for role_or_member, overwrite in txt_chan.overwrites.items():
            if isinstance(role_or_member, discord.Role):
                mapped_role = role_mapping.get(role_or_member.id)
                if mapped_role:
                    chan_overwrites[mapped_role] = overwrite

        parent_category = category_mapping.get(txt_chan.category_id) if txt_chan.category_id else None

        if not DRY_RUN:
            try:
                await target_guild.create_text_channel(
                    name=txt_chan.name,
                    category=parent_category,
                    topic=txt_chan.topic,
                    nsfw=txt_chan.nsfw,
                    slowmode_delay=txt_chan.slowmode_delay,
                    overwrites=chan_overwrites
                )
                logger.info(f"  ├── 📝 Text: {txt_chan.name}")
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"  ├── ❌ Failed text channel {txt_chan.name}: {e}")

    # ─── Create Voice Channels ───
    for vc_chan in sorted(source_voice_channels, key=lambda c: c.position):
        chan_overwrites = {}
        for role_or_member, overwrite in vc_chan.overwrites.items():
            if isinstance(role_or_member, discord.Role):
                mapped_role = role_mapping.get(role_or_member.id)
                if mapped_role:
                    chan_overwrites[mapped_role] = overwrite

        parent_category = category_mapping.get(vc_chan.category_id) if vc_chan.category_id else None

        if not DRY_RUN:
            try:
                max_bitrate = target_guild.bitrate_limit
                bitrate = max(8000, min(vc_chan.bitrate, max_bitrate))
                await target_guild.create_voice_channel(
                    name=vc_chan.name,
                    category=parent_category,
                    user_limit=vc_chan.user_limit,
                    bitrate=bitrate,
                    overwrites=chan_overwrites
                )
                logger.info(f"  ├── 🔊 Voice: {vc_chan.name}")
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"  ├── ❌ Failed voice channel {vc_chan.name}: {e}")

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
    logger.info(f"📊 Categories created: {len(category_mapping)}")
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
