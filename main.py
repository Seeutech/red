import asyncio
import os
import time
from uuid import uuid4

import redis
import telethon
import telethon.tl.types
from telethon import TelegramClient, events
from telethon.tl.functions.messages import ForwardMessagesRequest
from telethon.types import Message, UpdateNewMessage

from cansend import CanSend
from config import *
from terabox import get_data
from tools import (
    convert_seconds,
    download_file,
    download_image_to_bytesio,
    extract_code_from_url,
    get_formatted_size,
    get_urls_from_string,
    is_user_on_chat,
)

bot = TelegramClient("tele", API_ID, API_HASH)

db = redis.Redis(
    host=HOST,
    port=PORT,
    password=PASSWORD,
    decode_responses=True,
)


async def is_premium_user(user_id):
    return str(user_id) in PREMIUM_USERS


@bot.on(events.NewMessage(pattern="/start$", incoming=True, outgoing=False))
async def start(m: UpdateNewMessage):
    reply_text = f"""
𝐇𝐞𝐥𝐥𝐨! 𝐈 𝐚𝐦 𝐓𝐞𝐫𝐚𝐛𝐨𝐱 𝐕𝐢𝐝𝐞𝐨 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐫 𝐁𝐨𝐭.
𝐒𝐞𝐧𝐝 𝐦𝐞 𝐭𝐞𝐫𝐚𝐛𝐨𝐱 𝐯𝐢𝐝𝐞𝐨 𝐥𝐢𝐧𝐤 & 𝐈 𝐰𝐢𝐥𝐥 𝐬𝐞𝐧𝐝 𝐕𝐢𝐝𝐞𝐨.

𝐈𝐟 𝐘𝐨𝐮 𝐖𝐚𝐧𝐭 𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐋𝐢𝐤𝐞.
𝟏. 𝐰𝐢𝐭𝐡𝐨𝐮𝐭 𝟏 𝐦𝐢𝐧𝐮𝐭𝐞 𝐚𝐧𝐭𝐢 𝐬𝐩𝐚𝐦
𝟐. 𝐰𝐢𝐭𝐡𝐨𝐮𝐭 𝟐 𝐡𝐨𝐮𝐫𝐬 𝐨𝐟 𝐰𝐚𝐢𝐭 𝐭𝐢𝐦𝐞
𝟑. 𝐍𝐨 𝐋𝐢𝐦𝐢𝐭𝐬

 𝐂𝐡𝐞𝐜𝐤 𝐏𝐥𝐚𝐧'𝐬 : /plans"""
    check_if = await is_user_on_chat(bot, "@TechyMaskBots", m.peer_id)
    if not check_if:
        return await m.reply("Please join @TechyMaskBots then send me the link again.")
    check_if = await is_user_on_chat(bot, "@TechyMaskBots", m.peer_id)
    if not check_if:
        return await m.reply(
            "Please join @TechyMaskBots then send me the link again."
        )
    await m.reply(reply_text, link_preview=False, parse_mode="markdown")


@bot.on(events.NewMessage(pattern="/start (.*)", incoming=True, outgoing=False))
async def start(m: UpdateNewMessage):
    text = m.pattern_match.group(1)
    fileid = db.get(str(text))
    check_if = await is_user_on_chat(bot, "@TechyMaskBots", m.peer_id)
    if not check_if:
        return await m.reply("Please join @TechyMaskBots then send me the link again.")
    check_if = await is_user_on_chat(bot, "@TechyMaskBots", m.peer_id)
    if not check_if:
        return await m.reply(
            "Please join @TechyMaskBots then send me the link again."
        )
    await bot(
        ForwardMessagesRequest(
            from_peer=PRIVATE_CHAT_ID,
            id=[int(fileid)],
            to_peer=m.chat.id,
            drop_author=True,
            noforwards=True,
            background=True,
            drop_media_captions=False,
            with_my_score=True,
        )
    )

@bot.on(events.NewMessage(pattern="/plans", incoming=True, outgoing=False))
async def show_plans(m: UpdateNewMessage):
    plans_text = "𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐏𝐥𝐚𝐧𝐬:"
    
    for plan_name, plan_details in PREMIUM_PLANS.items():
        amount = plan_details["amount"]
        validity_days = plan_details["validity_days"]
        plans_text += f"\n{plan_name} - 𝐀𝐦𝐨𝐮𝐧𝐭: ₹{amount} - 𝐕𝐚𝐥𝐢𝐝𝐢𝐭𝐲: {validity_days} 𝐝𝐚𝐲𝐬"

     # Create an inline keyboard with a pay button
    keyboard = [
        [telethon.tl.types.KeyboardButtonUrl(
            text="𝐂𝐨𝐧𝐭𝐚𝐜𝐭 𝐭𝐨 𝐀𝐝𝐦𝐢𝐧",
            url=f"https://t.me/{YOUR_ADMIN_USERNAME}",
        )],
    ]

    await m.reply(plans_text, buttons=keyboard, parse_mode="markdown")

@bot.on(
    events.NewMessage(
        pattern="/remove (.*)", incoming=True, outgoing=False, from_users=ADMINS
    )
)
async def remove(m: UpdateNewMessage):
    user_id = m.pattern_match.group(1)
    if db.get(f"check_{user_id}"):
        db.delete(f"check_{user_id}")
        await m.reply(f"Removed {user_id} from the list.")
    else:
        await m.reply(f"{user_id} is not in the list.")


@bot.on(
    events.NewMessage(
        pattern="/add_premium (.*)",
        incoming=True,
        outgoing=False,
        from_users=ADMINS,
    )
)
async def add_premium_user(m: UpdateNewMessage):
    user_id = m.pattern_match.group(1)
    
    # Check if the user ID is a 10-digit number
    if not user_id.isdigit() or len(user_id) != 10:
        return await m.reply("Invalid user ID. Please enter a 10-digit numerical user ID.")

    user_id = int(user_id)

    if user_id in PREMIUM_USERS:
        return await m.reply(f"{user_id} is already in the premium users list.")

    PREMIUM_USERS.append(user_id)

    # Read existing content
    with open("config.py", "r") as f:
        lines = f.readlines()

    # Find the line where PREMIUM_USERS is defined
    for i, line in enumerate(lines):
        if "PREMIUM_USERS" in line:
            lines[i] = f"PREMIUM_USERS = {PREMIUM_USERS}\n"
            break

    # Write back the modified content
    with open("config.py", "w") as f:
        f.writelines(lines)

    await m.reply(f"{user_id} has been added to the premium users list.")


@bot.on(
    events.NewMessage(
        incoming=True,
        outgoing=False,
        func=lambda message: message.text
        and get_urls_from_string(message.text)
        and message.is_private,
    )
)
async def get_message(m: Message):
    asyncio.create_task(handle_message(m))


async def handle_message(m: Message):
    url = get_urls_from_string(m.text)
    if not url:
        return await m.reply("Please enter a valid URL.")
    check_if = await is_user_on_chat(bot, "@TechyMaskBots", m.peer_id)
    if not check_if:
        return await m.reply("Please join @TechyMaskBots then send me the link again.")
    check_if = await is_user_on_chat(bot, "@TechyMaskBots", m.peer_id)
    if not check_if:
        return await m.reply(
            "Please join @TechyMaskBots then send me the link again."
        )
    is_spam = db.get(m.sender_id)
    if is_spam and m.sender_id not in PREMIUM_USERS:
        return await m.reply("You are spamming. Please wait 1 minute and try again.")
    hm = await m.reply("Sending you the media. Please wait...")
    is_premium_user = m.sender_id in PREMIUM_USERS

if not is_premium_user:
    count = db.get(f"check_{m.sender_id}")
    if count and int(count) > 5:
        return await hm.edit("You are limited now. Please come back after 2 hours or use another account.")

    shorturl = extract_code_from_url(url)
    if not shorturl:
        return await hm.edit("Seems like your link is invalid.")
    fileid = db.get(shorturl)
    if fileid:
        try:
            await hm.delete()
        except:
            pass

        await bot(
            ForwardMessagesRequest(
                from_peer=PRIVATE_CHAT_ID,
                id=[int(fileid)],
                to_peer=m.chat.id,
                drop_author=True,
                noforwards=True,
                background=True,
                drop_media_captions=False,
                with_my_score=True,
            )
        )
        db.set(m.sender_id, time.monotonic(), ex=60)
        db.set(
            f"check_{m.sender_id}",
            int(count) + 1 if count else 1,
            ex=7200,
        )
        return

    data = get_data(url)
    if not data:
        return await hm.edit("Sorry! API is dead or maybe your link is broken.")
    db.set(m.sender_id, time.monotonic(), ex=60)
    if (
        not data["file_name"].endswith(".mp4")
        and not data["file_name"].endswith(".mkv")
        and not data["file_name"].endswith(".Mkv")
        and not data["file_name"].endswith(".webm")
    ):
        return await hm.edit(
            "Sorry! File is not supported for now. I can download only .mp4, .mkv, and .webm files."
        )
    if int(data["sizebytes"]) > 2054448565 and m.sender_id not in PREMIUM_USERS:
        return await hm.edit(
            f"Sorry! File is too big. I can download only 500MB and this file is of {data['size']} ."
        )

    start_time = time.time()
    cansend = CanSend()

    async def progress_bar(current_downloaded, total_downloaded, state="Sending"):
        if not cansend.can_send():
            return

        bar_length = 20
        percent = current_downloaded / total_downloaded
        arrow = "█" * int(percent * bar_length)
        spaces = "░" * (bar_length - len(arrow))

        elapsed_time = time.time() - start_time

        head_text = f"{state} `{data['file_name']}`"
        progress_bar = f"[{arrow + spaces}] {percent:.2%}"
        upload_speed = current_downloaded / elapsed_time if elapsed_time > 0 else 0
        speed_line = f"Speed: **{get_formatted_size(upload_speed)}/s**"

        time_remaining = (
            (total_downloaded - current_downloaded) / upload_speed
            if upload_speed > 0
            else 0
        )
        time_line = f"Time Remaining: `{convert_seconds(time_remaining)}`"

        size_line = f"Size: **{get_formatted_size(current_downloaded)}** / **{get_formatted_size(total_downloaded)}**"

        await hm.edit(
            f"{head_text}\n{progress_bar}\n{speed_line}\n{time_line}\n{size_line}",
            parse_mode="markdown",
        )

    uuid = str(uuid4())
    thumbnail = download_image_to_bytesio(data["thumb"], "thumbnail.png")

    try:
        file = await bot.send_file(
            PRIVATE_CHAT_ID,
            file=data["direct_link"],
            thumb=thumbnail if thumbnail else None,
            progress_callback=progress_bar,
            caption=f"""
File Name: `{data['file_name']}`
Size: **{data["size"]}** 
Direct Link: [Click Here](https://t.me/teraboxbro_bot?start={uuid})

@TechyMaskBots
""",
            supports_streaming=True,
            spoiler=True,
        )
    except telethon.errors.rpcerrorlist.WebpageCurlFailedError:
        download = await download_file(
            data["direct_link"], data["file_name"], progress_bar
        )
        if not download:
            return await hm.edit(
                f"Sorry! Download Failed but you can download it from [here]({data['direct_link']}).",
                parse_mode="markdown",
            )
        file = await bot.send_file(
            PRIVATE_CHAT_ID,
            download,
            caption=f"""
File Name: `{data['file_name']}`
Size: **{data["size"]}** 
Direct Link: [Click Here](https://t.me/teraboxdown_bot?start={uuid})

@TechyMaskBots
""",
            progress_callback=progress_bar,
            thumb=thumbnail if thumbnail else None,
            supports_streaming=True,
            spoiler=True,
        )
        try:
            os.unlink(download)
        except Exception as e:
            print(e)
    except Exception:
        return await hm.edit(
            f"Sorry! Download Failed but you can download it from [here]({data['direct_link']}).",
            parse_mode="markdown",
        )
    try:
        os.unlink(download)
    except Exception as e:
        pass
    try:
        await hm.delete()
    except Exception as e:
        print(e)

    if shorturl:
        db.set(shorturl, file.id)
    if file:
        db.set(uuid, file.id)

        await bot(
            ForwardMessagesRequest(
                from_peer=PRIVATE_CHAT_ID,
                id=[file.id],
                to_peer=m.chat.id,
                top_msg_id=m.id,
                drop_author=True,
                noforwards=True,
                background=True,
                drop_media_captions=False,
                with_my_score=True,
            )
        )
        db.set(m.sender_id, time.monotonic(), ex=60)
        db.set(
            f"check_{m.sender_id}",
            int(count) + 1 if count else 1,
            ex=7200,
        )


bot.start(bot_token=BOT_TOKEN)
bot.run_until_disconnected()
