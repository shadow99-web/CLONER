import discord
import asyncio
import os
import sys
import time
from flask import Flask
from threading import Thread

# ───────────────────────────────────────────────────────────────────
# 🔥 CRITICAL GATEWAY PATCH: FIXES 'NoneType' OBJECT IS NOT ITERABLE
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

# Optional: set to True for a trial run without making changes
DRY_RUN = False

# Concurrency limits (to avoid rate limits)
MAX_CONCURRENT_CHANNEL_CREATIONS = 5
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
# 🧠 HELPER: Progress Bar (optional, just prints dots)
# ───────────────────────────────────────────────────────────────────
def print_progress(current, total, label="Progress"):
    percent = (current / total) * 100
    bar = "[" + "=" * int(percent // 5) + ">" + "." * (20 - int(percent // 5)) + "]"
    print(f"\r{label}: {bar} {current}/{total} ({percent:.1f}%)", end="", flush=True)
    if current == total:
        print()  # newline after completion

# ───────────────────────────────────────────────────────────────────
# 🚀 MAIN CLONING ENGINE
# ───────────────────────────────────────────────────────────────────
async def start_cloning_engine():
    # Allow Discord to fully connect
    await asyncio.sleep(8)

    print(f"📡 Visible guilds: {len(cloner_client.guilds)}")
    print(f"📋 Guild IDs in cache: {[g.id for g in cloner_client.guilds]}")

    source_guild = cloner_client.get_guild(SOURCE_SERVER_ID)
    target_guild = cloner_client.get_guild(TARGET_SERVER_ID)

    if not source_guild:
        print(f"❌ Source server [{SOURCE_SERVER_ID}] not found.")
        return
    if not target_guild:
        print(f"❌ Target server [{TARGET_SERVER_ID}] not found.")
        return

    print("\n" + "="*50)
    print(f"🚀 CLONING INITIALIZED")
    print(f"📁 Source: {source_guild.name} ({source_guild.id})")
    print(f"🎯 Target: {target_guild.name} ({target_guild.id})")
    if DRY_RUN:
        print("⚠️ DRY RUN MODE: No changes will be made.")
    print("="*50 + "\n")

    # ───────────────────────────────────────────────────────────────
    # STEP 1: Purge target channels (optional – you may want to skip)
    # ───────────────────────────────────────────────────────────────
    print("🧹 [1/4] Clearing target server channels...")
    if not DRY_RUN:
        for channel in target_guild.channels:
            try:
                await channel.delete()
                await asyncio.sleep(0.2)  # brief delay
            except Exception as e:
                print(f"⚠️ Could not delete {channel.name}: {e}")
    else:
        print("ℹ️ DRY RUN: Skipping channel deletion.")

    # ───────────────────────────────────────────────────────────────
    # STEP 2: Role cloning (synchronous but fast enough)
    # ───────────────────────────────────────────────────────────────
    print("\n🎭 [2/4] Duplicating roles...")
    role_mapping = {}

    # Sort roles by position (highest first is safer)
    sorted_roles = sorted(source_guild.roles, key=lambda r: r.position, reverse=True)

    for i, role in enumerate(sorted_roles):
        if role.is_default():
            if not DRY_RUN:
                try:
                    await target_guild.default_role.edit(permissions=role.permissions)
                    print("✅ @everyone permissions synced.")
                except Exception as e:
                    print(f"⚠️ Failed to edit @everyone: {e}")
            else:
                print("ℹ️ DRY RUN: Would sync @everyone permissions.")
            continue

        if role.managed:
            print(f"⏩ Skipping managed role: {role.name}")
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
                print(f"✅ Created role: {role.name}")
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"❌ Failed to create role {role.name}: {e}")
        else:
            print(f"ℹ️ DRY RUN: Would create role: {role.name}")

    # ───────────────────────────────────────────────────────────────
    # STEP 3: Channels & Categories
    # ───────────────────────────────────────────────────────────────
    print("\n📁 [3/4] Building categories and channels...")
    
    # Count total channels for progress
    total_channels = sum(len(cat.text_channels) + len(cat.voice_channels) for cat in source_guild.categories)
    processed = 0

    for category in source_guild.categories:
        # Build category permission overrides
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
                print(f"📂 Category: {category.name}")
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"❌ Failed to create category {category.name}: {e}")
                continue
        else:
            print(f"ℹ️ DRY RUN: Would create category: {category.name}")
            new_category = None

        # Gather tasks for channels in this category
        channel_tasks = []

        # Text channels (sorted by position)
        for txt_chan in sorted(category.text_channels, key=lambda c: c.position):
            chan_overwrites = {}
            for role_or_member, overwrite in txt_chan.overwrites.items():
                if isinstance(role_or_member, discord.Role):
                    mapped_role = role_mapping.get(role_or_member.id)
                    if mapped_role:
                        chan_overwrites[mapped_role] = overwrite

            if not DRY_RUN:
                # We'll create directly here (or batch later)
                try:
                    await target_guild.create_text_channel(
                        name=txt_chan.name,
                        category=new_category,
                        topic=txt_chan.topic,
                        nsfw=txt_chan.nsfw,
                        slowmode_delay=txt_chan.slowmode_delay,
                        overwrites=chan_overwrites
                    )
                    print(f"  ├── 📝 Text: {txt_chan.name}")
                    processed += 1
                    print_progress(processed, total_channels, "Channels")
                    await asyncio.sleep(0.3)  # short delay to avoid ratelimit
                except Exception as e:
                    print(f"  ├── ⚠️ Failed text channel {txt_chan.name}: {e}")
                    processed += 1
            else:
                print(f"  ├── ℹ️ DRY RUN: Would create text channel: {txt_chan.name}")

        # Voice channels (sorted by position)
        for vc_chan in sorted(category.voice_channels, key=lambda c: c.position):
            chan_overwrites = {}
            for role_or_member, overwrite in vc_chan.overwrites.items():
                if isinstance(role_or_member, discord.Role):
                    mapped_role = role_mapping.get(role_or_member.id)
                    if mapped_role:
                        chan_overwrites[mapped_role] = overwrite

            if not DRY_RUN:
                try:
                    # Use target guild's max bitrate
                    max_bitrate = target_guild.bitrate_limit
                    bitrate = max(8000, min(vc_chan.bitrate, max_bitrate))
                    await target_guild.create_voice_channel(
                        name=vc_chan.name,
                        category=new_category,
                        user_limit=vc_chan.user_limit,
                        bitrate=bitrate,
                        overwrites=chan_overwrites
                    )
                    print(f"  ├── 🔊 Voice: {vc_chan.name}")
                    processed += 1
                    print_progress(processed, total_channels, "Channels")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    print(f"  ├── ⚠️ Failed voice channel {vc_chan.name}: {e}")
                    processed += 1
            else:
                print(f"  ├── ℹ️ DRY RUN: Would create voice channel: {vc_chan.name}")

    # If there are channels not in any category (shouldn't happen in modern servers)
    # but handle them as well.
    for channel in source_guild.channels:
        if channel.category is None:
            if not DRY_RUN:
                try:
                    await target_guild.create_text_channel(
                        name=channel.name,
                        topic=getattr(channel, 'topic', None),
                        nsfw=getattr(channel, 'nsfw', False),
                        slowmode_delay=getattr(channel, 'slowmode_delay', 0)
                    )
                    print(f"📝 Uncategorized: {channel.name}")
                    processed += 1
                    print_progress(processed, total_channels, "Channels")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    print(f"⚠️ Failed uncategorized channel {channel.name}: {e}")
            else:
                print(f"ℹ️ DRY RUN: Would create uncategorized channel: {channel.name}")

    # ───────────────────────────────────────────────────────────────
    # STEP 4: Emoji copying (with concurrency control)
    # ───────────────────────────────────────────────────────────────
    print("\n👾 [4/4] Syncing custom emojis...")
    
    if not source_guild.emojis:
        print("ℹ️ No custom emojis in source.")
    else:
        max_slots = target_guild.emoji_limit
        used_slots = len(target_guild.emojis)
        available = max_slots - used_slots
        print(f"📊 Emoji slots: {used_slots}/{max_slots} used, {available} available.")

        emojis_to_copy = source_guild.emojis[:available]  # only copy what fits
        total_emojis = len(emojis_to_copy)
        if total_emojis == 0:
            print("ℹ️ No emoji slots available or no emojis to copy.")
        else:
            # Use semaphore to limit concurrent uploads
            sem = asyncio.Semaphore(MAX_CONCURRENT_EMOJI_CREATIONS)

            async def copy_one_emoji(emoji, idx):
                async with sem:
                    if DRY_RUN:
                        print(f"  ℹ️ DRY RUN: Would copy emoji :{emoji.name}:")
                        return
                    try:
                        emoji_bytes = await emoji.read()
                        await target_guild.create_custom_emoji(
                            name=emoji.name,
                            image=emoji_bytes
                        )
                        print(f"  ✅ Copied emoji :{emoji.name}: ({idx+1}/{total_emojis})")
                    except discord.HTTPException as e:
                        if e.status == 429:
                            # Rate limited – wait and retry (optional)
                            retry_after = e.retry_after if hasattr(e, 'retry_after') else 5
                            print(f"  ⏳ Rate limited on emoji :{emoji.name}: waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            # Retry once
                            try:
                                emoji_bytes = await emoji.read()
                                await target_guild.create_custom_emoji(
                                    name=emoji.name,
                                    image=emoji_bytes
                                )
                                print(f"  ✅ Retry succeeded :{emoji.name}:")
                            except Exception as e2:
                                print(f"  ❌ Failed to copy emoji :{emoji.name}: {e2}")
                        else:
                            print(f"  ❌ Failed to copy emoji :{emoji.name}: {e}")
                    except Exception as e:
                        print(f"  ❌ Failed to copy emoji :{emoji.name}: {e}")

            # Create tasks for all emojis
            tasks = []
            for idx, emoji in enumerate(emojis_to_copy):
                tasks.append(copy_one_emoji(emoji, idx))
                await asyncio.sleep(0.1)  # small delay to spread requests

            # Wait for all emoji copies to finish
            await asyncio.gather(*tasks)

    # ───────────────────────────────────────────────────────────────
    # FINISHED
    # ───────────────────────────────────────────────────────────────
    print("\n" + "="*50)
    print("🎉 CLONING COMPLETED SUCCESSFULLY!")
    print(f"📊 Channels processed: {processed}/{total_channels}")
    print(f"🎭 Roles created: {len(role_mapping)}")
    print(f"👾 Emojis attempted: {total_emojis}")
    print("="*50 + "\n")

# ───────────────────────────────────────────────────────────────────
# DISCORD EVENT HANDLERS
# ───────────────────────────────────────────────────────────────────
@cloner_client.event
async def on_ready():
    print(f"✨ Authenticated as: {cloner_client.user}")
    cloner_client.loop.create_task(start_cloning_engine())

# ───────────────────────────────────────────────────────────────────
# BOOT
# ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not ACCOUNT_TOKEN or ACCOUNT_TOKEN == "None":
        print("❌ Error: TOKEN1 environment variable is not set.")
        sys.exit(1)

    keep_alive()

    try:
        cloner_client.run(ACCOUNT_TOKEN)
    except Exception as e:
        print(f"🛑 Execution Terminated: {e}")
