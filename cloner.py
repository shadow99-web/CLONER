import discord
import asyncio
import os
import sys
import logging
import time
from flask import Flask
from threading import Thread

# ───────────────────────────────────────────────────────────────────
# 🛠️ LOGGING
# ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("ClonerEngine")

# ───────────────────────────────────────────────────────────────────
# 🔥 CRITICAL GATEWAY PATCH
# ───────────────────────────────────────────────────────────────────
from discord.state import ConnectionState

def patched_parse_ready_supplemental(self, data):
    try:
        self.pending_payments = {
            int(p['id']): p for p in data.get('pending_payments') or []
        }
    except Exception:
        self.pending_payments = {}

ConnectionState.parse_ready_supplemental = patched_parse_ready_supplemental
# ───────────────────────────────────────────────────────────────────

# =======================================================================
# ⚙️ CONFIGURATION
# =======================================================================
ACCOUNT_TOKEN = os.getenv("TOKEN1") 
SOURCE_SERVER_ID = 1443875856803168360  
TARGET_SERVER_ID = 1517588614459031723   

DRY_RUN = False
MAX_CONCURRENT_EMOJI_CREATIONS = 3
# =======================================================================

# --- FLASK KEEP ALIVE ---
app = Flask('')

@app.route('/')
def home():
    return "Cloning Engine is active!"

def run():
    port = int(os.environ.get("PORT", 7860))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run, daemon=True).start()
# ───────────────────────────────────────────────────────────────────

cloner_client = discord.Client(
    self_bot=True,
    browser="chrome",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    compress=False
)

# ───────────────────────────────────────────────────────────────────
# 🧠 HELPER PROGRESS
# ───────────────────────────────────────────────────────────────────
def print_progress(current, total, label="Progress"):
    if total == 0:
        logger.info(f"{label}: 0/0 (100%)")
        return
    percent = (current / total) * 100
    bar = "[" + "=" * int(percent // 5) + ">" + "." * (20 - int(percent // 5)) + "]"
    logger.info(f"{label}: {bar} {current}/{total} ({percent:.1f}%)")

# ───────────────────────────────────────────────────────────────────
# 🚀 CLONING ENGINE
# ───────────────────────────────────────────────────────────────────
async def start_cloning_engine():
    # Wait for cache to be filled
    logger.info("⏳ Waiting for Discord cache to populate...")
    await asyncio.sleep(8)

    source_guild = cloner_client.get_guild(SOURCE_SERVER_ID)
    target_guild = cloner_client.get_guild(TARGET_SERVER_ID)

    # Retry up to 6 times (30 seconds total)
    for attempt in range(1, 7):
        if source_guild and target_guild:
            break
        await asyncio.sleep(5)
        source_guild = cloner_client.get_guild(SOURCE_SERVER_ID)
        target_guild = cloner_client.get_guild(TARGET_SERVER_ID)
        logger.info(f"Attempt {attempt}/6 – Source: {source_guild is not None}, Target: {target_guild is not None}")

    if not source_guild:
        logger.error(f"❌ Source server [{SOURCE_SERVER_ID}] not found. Account must be in it.")
        logger.error(f"📋 Guilds in cache: {[g.id for g in cloner_client.guilds]}")
        return

    if not target_guild:
        logger.error(f"❌ Target server [{TARGET_SERVER_ID}] not found. Account must be in it.")
        logger.error(f"📋 Guilds in cache: {[g.id for g in cloner_client.guilds]}")
        return

    if DRY_RUN:
        logger.warning("⚠️ DRY RUN – No changes will be made.")
    else:
        logger.info("🔴 LIVE MODE – Changes will be applied.")

    logger.info("\n" + "="*50)
    logger.info(f"🚀 CLONING INITIALIZED")
    logger.info(f"📁 Source: {source_guild.name} ({source_guild.id})")
    logger.info(f"🎯 Target: {target_guild.name} ({target_guild.id})")
    logger.info("="*50 + "\n")

    # ───────────────────────────────────────────────────────────────
    # STEP 1: Purge target channels
    # ───────────────────────────────────────────────────────────────
    logger.info("🧹 [1/4] Clearing target server channels...")
    if not DRY_RUN:
        for channel in target_guild.channels:
            try:
                await channel.delete()
                logger.info(f"  🗑️ Deleted: {channel.name}")
                await asyncio.sleep(0.2)
            except Exception as e:
                logger.warning(f"  ⚠️ Could not delete {channel.name}: {e}")
    else:
        logger.info("ℹ️ DRY RUN – Skipping channel deletion.")

    # ───────────────────────────────────────────────────────────────
    # STEP 2: Roles
    # ───────────────────────────────────────────────────────────────
    logger.info("\n🎭 [2/4] Duplicating roles...")
    role_mapping = {}

    sorted_roles = sorted(source_guild.roles, key=lambda r: r.position, reverse=True)

    for role in sorted_roles:
        if role.is_default():
            if not DRY_RUN:
                try:
                    await target_guild.default_role.edit(permissions=role.permissions)
                    logger.info("✅ @everyone permissions synced.")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to edit @everyone: {e}")
            else:
                logger.info("ℹ️ DRY RUN – Would sync @everyone permissions.")
            continue

        if role.managed:
            logger.info(f"⏩ Skipping managed role: {role.name}")
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
        else:
            logger.info(f"ℹ️ DRY RUN – Would create role: {role.name}")

    # ───────────────────────────────────────────────────────────────
    # STEP 3: Categories & Channels
    # ───────────────────────────────────────────────────────────────
    logger.info("\n📁 [3/4] Building categories and channels...")
    
    total_channels = sum(len(cat.text_channels) + len(cat.voice_channels) for cat in source_guild.categories)
    processed = 0

    for category in source_guild.categories:
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
                logger.error(f"❌ Failed to create category {category.name}: {e}")
                continue
        else:
            logger.info(f"ℹ️ DRY RUN – Would create category: {category.name}")
            new_category = None

        # Text channels
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
                    processed += 1
                    print_progress(processed, total_channels, "Channels")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"  ├── ⚠️ Failed text channel {txt_chan.name}: {e}")
                    processed += 1
            else:
                logger.info(f"  ├── ℹ️ DRY RUN – Would create text: {txt_chan.name}")

        # Voice channels
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
                    processed += 1
                    print_progress(processed, total_channels, "Channels")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"  ├── ⚠️ Failed voice channel {vc_chan.name}: {e}")
                    processed += 1
            else:
                logger.info(f"  ├── ℹ️ DRY RUN – Would create voice: {vc_chan.name}")

    # Uncategorized channels
    for channel in source_guild.channels:
        if channel.category is None and not isinstance(channel, discord.CategoryChannel):
            if not DRY_RUN:
                try:
                    await target_guild.create_text_channel(
                        name=channel.name,
                        topic=getattr(channel, 'topic', None),
                        nsfw=getattr(channel, 'nsfw', False),
                        slowmode_delay=getattr(channel, 'slowmode_delay', 0)
                    )
                    logger.info(f"📝 Uncategorized: {channel.name}")
                    processed += 1
                    print_progress(processed, total_channels, "Channels")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"⚠️ Failed uncategorized channel {channel.name}: {e}")
            else:
                logger.info(f"ℹ️ DRY RUN – Would create uncategorized: {channel.name}")

    # ───────────────────────────────────────────────────────────────
    # STEP 4: Emojis
    # ───────────────────────────────────────────────────────────────
    logger.info("\n👾 [4/4] Syncing custom emojis...")
    
    if not source_guild.emojis:
        logger.info("ℹ️ No custom emojis in source.")
    else:
        max_slots = target_guild.emoji_limit
        used_slots = len(target_guild.emojis)
        available = max_slots - used_slots
        logger.info(f"📊 Emoji slots: {used_slots}/{max_slots} used, {available} available.")

        emojis_to_copy = source_guild.emojis[:available]
        total_emojis = len(emojis_to_copy)
        if total_emojis == 0:
            logger.info("ℹ️ No emoji slots available.")
        else:
            sem = asyncio.Semaphore(MAX_CONCURRENT_EMOJI_CREATIONS)

            async def copy_one_emoji(emoji, idx):
                async with sem:
                    if DRY_RUN:
                        logger.info(f"  ℹ️ DRY RUN – Would copy emoji :{emoji.name}:")
                        return
                    try:
                        emoji_bytes = await emoji.read()
                        await target_guild.create_custom_emoji(
                            name=emoji.name,
                            image=emoji_bytes
                        )
                        logger.info(f"  ✅ Copied emoji :{emoji.name}: ({idx+1}/{total_emojis})")
                    except discord.HTTPException as e:
                        if e.status == 429:
                            retry_after = getattr(e, 'retry_after', 5)
                            logger.warning(f"  ⏳ Rate limited on :{emoji.name}: waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            try:
                                emoji_bytes = await emoji.read()
                                await target_guild.create_custom_emoji(
                                    name=emoji.name,
                                    image=emoji_bytes
                                )
                                logger.info(f"  ✅ Retry succeeded :{emoji.name}:")
                            except Exception as e2:
                                logger.error(f"  ❌ Failed to copy emoji :{emoji.name}: {e2}")
                        else:
                            logger.error(f"  ❌ Failed to copy emoji :{emoji.name}: {e}")
                    except Exception as e:
                        logger.error(f"  ❌ Failed to copy emoji :{emoji.name}: {e}")

            tasks = []
            for idx, emoji in enumerate(emojis_to_copy):
                tasks.append(copy_one_emoji(emoji, idx))
                await asyncio.sleep(0.1)

            await asyncio.gather(*tasks)

    # ───────────────────────────────────────────────────────────────
    # FINISH
    # ───────────────────────────────────────────────────────────────
    logger.info("\n" + "="*50)
    logger.info("🎉 CLONING COMPLETED!")
    logger.info(f"📊 Channels processed: {processed}/{total_channels}")
    logger.info(f"🎭 Roles created: {len(role_mapping)}")
    logger.info(f"👾 Emojis attempted: {total_emojis}")
    logger.info("="*50 + "\n")

# ───────────────────────────────────────────────────────────────────
# EVENT HANDLERS
# ───────────────────────────────────────────────────────────────────
@cloner_client.event
async def on_connect():
    logger.info("✨ Connected to Discord gateway. Waiting for cache...")
    # Start the cloning after a short delay to allow cache to fill
    await asyncio.sleep(5)
    await start_cloning_engine()

# ───────────────────────────────────────────────────────────────────
# BOOT
# ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not ACCOUNT_TOKEN or ACCOUNT_TOKEN == "None":
        logger.error("❌ Error: TOKEN1 environment variable is not set.")
        sys.exit(1)

    keep_alive()

    try:
        cloner_client.run(ACCOUNT_TOKEN)
    except Exception as e:
        logger.error(f"🛑 Execution Terminated: {e}")
