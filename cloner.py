import discord
import asyncio
import os
import sys

# =======================================================================
# ⚙️ CONFIGURATION BOUNDARY
# =======================================================================
# Put the account token you want to use to perform the clone here
ACCOUNT_TOKEN = os.getenv("TOKEN1") 

# The server ID you want to copy (where you are a member)
SOURCE_SERVER_ID = 1443875856803168360  

# Your empty destination server ID (where you have Admin/Owner control)
TARGET_SERVER_ID = 1517588614459031723   
# =======================================================================

cloner_client = discord.Client(
    self_bot=True,
    browser="chrome",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

async def start_cloning_engine():
    source_guild = cloner_client.get_guild(SOURCE_SERVER_ID)
    target_guild = cloner_client.get_guild(TARGET_SERVER_ID)

    if not source_guild:
        print(f"❌ Critical Error: Unable to locate source server [{SOURCE_SERVER_ID}]. Am I in it?")
        await cloner_client.close()
        return
    if not target_guild:
        print(f"❌ Critical Error: Unable to locate destination server [{TARGET_SERVER_ID}]. Am I an Admin there?")
        await cloner_client.close()
        return

    print("\n" + "="*50)
    print(f"🚀 DEEP CLONING AND EMOJI SYNC INITIALIZED")
    print(f"📁 Source Guild: {source_guild.name}")
    print(f"🎯 Target Guild: {target_guild.name}")
    print("="*50 + "\n")

    # ───────────────────────────────────────────────────────────────────
    # STEP 1: CLEANING INTERFACE LAYER
    # ───────────────────────────────────────────────────────────────────
    print("🧹 [1/4] Purging default channels from target server...")
    for channel in target_guild.channels:
        try:
            await channel.delete()
            await asyncio.sleep(0.4)  # Prevent early rate limits
        except Exception as e:
            pass

    # ───────────────────────────────────────────────────────────────────
    # STEP 2: REBUILDING THE ROLE MAP MATRIX
    # ───────────────────────────────────────────────────────────────────
    print("\n🎭 [2/4] Extracting and deploying global role permissions...")
    role_mapping = {}  # Old Role ID -> New Role Object

    # Sort roles from lowest to highest hierarchy order to avoid position conflicts
    sorted_roles = sorted(source_guild.roles, key=lambda r: r.position)

    for role in sorted_roles:
        if role.is_default():
            try:
                await target_guild.default_role.edit(permissions=role.permissions)
                role_mapping[role.id] = target_guild.default_role
                print(" ✅ Synced baseline @everyone permissions.")
            except Exception as e:
                print(f" ⚠️ Failed syncing @everyone perms: {e}")
            continue

        if role.managed:
            continue

        try:
            new_role = await target_guild.create_role(
                name=role.name,
                permissions=role.permissions,
                color=role.color,
                hoist=role.hoist,
                mentionable=role.mentionable
            )
            role_mapping[role.id] = new_role
            print(f" ✅ Duplicated Role: {role.name}")
            await asyncio.sleep(0.8)  # Anti-spam API delay
        except Exception as e:
            print(f" ❌ Failed creating role [{role.name}]: {e}")

    # ───────────────────────────────────────────────────────────────────
    # STEP 3: MAPPING STRUCTURAL CATEGORIES & CHANNELS
    # ───────────────────────────────────────────────────────────────────
    print("\n📁 [3/4] Engineering layout structures and local permission overrides...")

    for category in source_guild.categories:
        cat_overwrites = {}
        for role_or_member, overwrite in category.overwrites.items():
            if isinstance(role_or_member, discord.Role):
                mapped_role = role_mapping.get(role_or_member.id)
                if mapped_role:
                    cat_overwrites[mapped_role] = overwrite

        try:
            new_category = await target_guild.create_category(
                name=category.name,
                overwrites=cat_overwrites
            )
            print(f"📂 Category Built: {category.name}")
            await asyncio.sleep(1.0)
        except Exception as e:
            print(f" ❌ Skipping Category [{category.name}] due to failure: {e}")
            continue

        for txt_chan in category.text_channels:
            chan_overwrites = {}
            for role_or_member, overwrite in txt_chan.overwrites.items():
                if isinstance(role_or_member, discord.Role):
                    mapped_role = role_mapping.get(role_or_member.id)
                    if mapped_role:
                        chan_overwrites[mapped_role] = overwrite

            try:
                await target_guild.create_text_channel(
                    name=txt_chan.name,
                    category=new_category,
                    topic=txt_chan.topic,
                    nsfw=txt_chan.nsfw,
                    slowmode_delay=txt_chan.slowmode_delay,
                    overwrites=chan_overwrites
                )
                print(f"  ├── 📝 Text Channel: {txt_chan.name}")
                await asyncio.sleep(1.2)  
            except Exception as e:
                print(f"  ├── ⚠️ Skipped Text Channel [{txt_chan.name}]: {e}")

        for vc_chan in category.voice_channels:
            chan_overwrites = {}
            for role_or_member, overwrite in vc_chan.overwrites.items():
                if isinstance(role_or_member, discord.Role):
                    mapped_role = role_mapping.get(role_or_member.id)
                    if mapped_role:
                        chan_overwrites[mapped_role] = overwrite

            try:
                await target_guild.create_voice_channel(
                    name=vc_chan.name,
                    category=new_category,
                    user_limit=vc_chan.user_limit,
                    bitrate=max(8000, min(vc_chan.bitrate, 96000)),
                    overwrites=chan_overwrites
                )
                print(f"  ├── 🔊 Voice Channel: {vc_chan.name}")
                await asyncio.sleep(1.2)
            except Exception as e:
                print(f"  ├── ⚠️ Skipped Voice Channel [{vc_chan.name}]: {e}")

    # ───────────────────────────────────────────────────────────────────
    # STEP 4: DOWNLOADING & UPLOADING EMOTES PIPELINE
    # ───────────────────────────────────────────────────────────────────
    print("\n👾 [4/4] Extracting and importing server expressions (emojis)...")
    
    if not source_guild.emojis:
        print(" ℹ️ No custom emojis discovered on the source server.")
    else:
        # Check current tier layout capabilities of destination guild
        max_emojis = target_guild.emoji_limit
        current_emojis = len(target_guild.emojis)
        slots_available = max_emojis - current_emojis
        
        print(f" ℹ️ Target server emoji space capacity: {current_emojis}/{max_emojis} slots occupied.")
        
        emoji_count = 0
        for emoji in source_guild.emojis:
            if emoji_count >= slots_available:
                print(" ⚠️ Reached maximum emoji capacity slots available on your target server tier! Stopping.")
                break
                
            try:
                # Read the asset's binary payload data
                emoji_bytes = await emoji.read()
                
                # Re-upload asset stream onto your destination dashboard
                await target_guild.create_custom_emoji(
                    name=emoji.name,
                    image=emoji_bytes
                )
                emoji_count += 1
                print(f"  ├── ✨ Synced Emoji: :{emoji.name}: ({emoji_count})")
                
                # Emojis hit harsh rate limits. Pause to keep account profile operations safe.
                await asyncio.sleep(2.0)
            except Exception as e:
                print(f"  ├── ⚠️ Failed to mirror emoji :{emoji.name}: -> {e}")
                await asyncio.sleep(1.5)

    print("\n" + "="*50)
    print("🎉 DEPLOYMENT SUCCESSFUL! Structural layout and emoji banks mirrored completely.")
    print("="*50 + "\n")
    await cloner_client.close()

@cloner_client.event
async def on_ready():
    print(f"✨ Authenticated successfully as: {cloner_client.user}")
    cloner_client.loop.create_task(start_cloning_engine())

if __name__ == "__main__":
    if not ACCOUNT_TOKEN or ACCOUNT_TOKEN == "None":
        print("❌ Error: ACCOUNT_TOKEN variable is completely empty inside cloner.py!")
        sys.exit()
    try:
        cloner_client.run(ACCOUNT_TOKEN)
    except Exception as e:
        print(f"🛑 Execution Terminated: {e}")
                overwrites=cat_overwrites
            )
            print(f"📂 Category Built: {category.name}")
            await asyncio.sleep(1.0)
        except Exception as e:
            print(f" ❌ Skipping Category [{category.name}] due to failure: {e}")
            continue

        # Compile text channels nested inside this category
        for txt_chan in category.text_channels:
            chan_overwrites = {}
            for role_or_member, overwrite in txt_chan.overwrites.items():
                if isinstance(role_or_member, discord.Role):
                    mapped_role = role_mapping.get(role_or_member.id)
                    if mapped_role:
                        chan_overwrites[mapped_role] = overwrite

            try:
                await target_guild.create_text_channel(
                    name=txt_chan.name,
                    category=new_category,
                    topic=txt_chan.topic,
                    nsfw=txt_chan.nsfw,
                    slowmode_delay=txt_chan.slowmode_delay,
                    overwrites=chan_overwrites
                )
                print(f"  ├── 📝 Text Channel: {txt_chan.name}")
                await asyncio.sleep(1.2)  # Strict delay to prevent channel rate-limiting spikes
            except Exception as e:
                print(f"  ├── ⚠️ Skipped Text Channel [{txt_chan.name}]: {e}")

        # Compile voice channels nested inside this category
        for vc_chan in category.voice_channels:
            chan_overwrites = {}
            for role_or_member, overwrite in vc_chan.overwrites.items():
                if isinstance(role_or_member, discord.Role):
                    mapped_role = role_mapping.get(role_or_member.id)
                    if mapped_role:
                        chan_overwrites[mapped_role] = overwrite

            try:
                await target_guild.create_voice_channel(
                    name=vc_chan.name,
                    category=new_category,
                    user_limit=vc_chan.user_limit,
                    bitrate=max(8000, min(vc_chan.bitrate, 96000)),
                    overwrites=chan_overwrites
                )
                print(f"  ├── 🔊 Voice Channel: {vc_chan.name}")
                await asyncio.sleep(1.2)
            except Exception as e:
                print(f"  ├── ⚠️ Skipped Voice Channel [{vc_chan.name}]: {e}")

    print("\n" + "="*50)
    print("🎉 DEPLOYMENT SUCCESSFUL! Structural layout mirrored completely.")
    print("="*50 + "\n")
    await cloner_client.close()

@cloner_client.event
async def on_ready():
    print(f"✨ Authenticated successfully as: {cloner_client.user}")
    cloner_client.loop.create_task(start_cloning_engine())

if __name__ == "__main__":
    if not ACCOUNT_TOKEN or ACCOUNT_TOKEN == "None":
        print("❌ Error: ACCOUNT_TOKEN variable is completely empty inside cloner.py!")
        sys.exit()
    try:
        cloner_client.run(ACCOUNT_TOKEN)
    except Exception as e:
        print(f"🛑 Execution Terminated: {e}")
