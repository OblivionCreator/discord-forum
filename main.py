import json
import os
import random
import subprocess
import time

import aiohttp
import disnake
import sqlite3

import requests
from disnake.ext import commands

intents = disnake.Intents()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents,
                   allowed_mentions=disnake.AllowedMentions(everyone=False, users=False, replied_user=False,
                                                            roles=False))

channels = [1059241356159098991, 1089200413510742118]
forums = [1091479882476826674, 1027772036690497597]
signature_store = 1089454603369730058


# On Message Handling
# This gets any new messages in the specified channels, and reposts them as an embed.

@bot.event
async def on_message(message):

    if message.type != disnake.MessageType.default and message.type != disnake.MessageType.reply:
        return

    if message.channel.id in channels and not message.author.discriminator == '0000' and message.author.id != 594559806401019908 and message.author.id != 901483003912527912:
        await forum_prep(message)
    elif isinstance(message.channel, disnake.Thread) and not message.author.discriminator == '0000' and message.author.id != 594559806401019908 and message.author.id != 901483003912527912:
        if isinstance(message.channel.parent, disnake.ForumChannel):
            if message.channel.parent.id in forums and message.channel.total_message_sent > 0:
                await forum_prep(message)
    await bot.process_commands(message)


async def forum_prep(message):
    content = message.content
    author = message.author
    channel = message.channel
    files = message.attachments
    await generate_forum(content, author, channel, message.guild, files)
    try:
        await message.delete()
    except disnake.NotFound:
        pass


async def generate_forum(content, author, channel, guild, files):
    files_storage = []
    if len(files) > 0:
        for f in files:
            if isinstance(f, disnake.Attachment):
                response = requests.get(f.url)
                new_filename = f"{author.id}_{int(time.time() * 10000)}_{f.filename}"
                with open(f"temp/{new_filename}", 'wb') as file:
                    file.write(response.content)
                files_storage.append(new_filename)
            elif isinstance(f, str):
                files_storage.append(f)

    embed = disnake.Embed(description=None, color=author.color)
    image, text = await get_user_signature(author)
    if image: embed.set_image(image)
    if text: embed.title = text
    count = update_post_count(author.id)
    embed.set_footer(text=f'Message sent by {author.name} ({author.id})')
    await webhookManager(channel=channel, author=author, embed=embed, files=files_storage, guild=guild,
                         file_url='', count=count, content=content)


def random_signature(author):
    art_pick = random.choice(os.listdir("templates/"))
    with open(f"templates/{art_pick}", "r") as file:
        data = file.read()
    nick = author.nick
    if not nick:
        nick = author.name
    final_text = data.format(NICKNAME=nick, USERNAME=author.name, DISCRIM=author.discriminator)
    filename = f"{int(time.time())}_{art_pick}"
    final_filename = f"{int(time.time())}_generated.png"
    with open(f"temp/{filename}", "x", encoding='utf8') as file:
        file.write(final_text)
    subprocess.check_call(
        f"""\"C:\\Program Files\\Inkscape\\bin\\inkscape.exe\" --export-type=\"png\" --export-area-page temp/{filename} --export-filename C:\\Users\\Jared\\PycharmProjects\\discord-forum\\temp\\{final_filename}""")
    return final_filename


def generate_wordart(text):
    #
    # text_split = text.split(" ")
    # text_current = ""
    # text_lines = []
    # for tx in text_split:
    #     if len(text_current) > 40:
    #         text_lines.append(text_current)
    #         text_current = tx + " "
    #     else:
    #         text_current = text_current + tx + " "
    # if len(text_current) > 0:
    #     text_lines.append(text_current)

    # text_final = "\n\n".join(text_lines)

    text_final = text

    art_pick = random.choice(os.listdir("wordart/"))
    with open(f"wordart/{art_pick}", "r") as file:
        data = file.read()
    final_text = data.format(YOURTEXTHERE=text_final)
    filename = f"{int(time.time())}_{art_pick}"
    with open(f"temp/{filename}", "x", encoding='utf8') as file:
        file.write(final_text)

    final_filename = f"{time.strftime('%Y%m%d_%H%M%S')}_generated.png"
    subprocess.check_call(
        f"""\"C:\\Program Files\\Inkscape\\bin\\inkscape.exe\" --export-type=\"png\" --export-area-drawing temp/{filename} --export-filename C:\\Users\\Jared\\PycharmProjects\\discord-forum\\temp\\{final_filename}""")
    return final_filename


async def webhookManager(channel, author, embed, files, guild, file_url, count, content):
    if isinstance(author, disnake.User):
        user_id = author.id
        author = await guild.get_or_fetch_member(user_id)

    final_files = []

    if len(files) > 0:
        for f in files:
            final_files.append(disnake.File(f"temp/{f}"))

    if count < 10:
        rank = "[Rookie]"
    elif count < 100:
        rank = "[Member]"
    elif count < 200:
        rank = "[Member+]"
    elif count < 400:
        rank = "[VIP]"
    else:
        rank = "[VIP+]"

    moderator = ""

    roles = author.roles
    for r in roles:
        if r.name == 'Staff':
            moderator = "[Moderator] "
            break

    with open('webhooks.json') as file:
        data = file.read()
        webhooks = json.loads(data)

    username = f"{rank} {moderator}{author.nick or author.name}"

    webhook_url = None
    thread_parent = None

    if isinstance(channel, disnake.Thread):
        thread_parent = channel
        channel = channel.parent

    for c in webhooks:
        if int(c) == channel.id:  # Checks if the channel ID has a webhook, if so sets the webhook_url.
            webhook_url = webhooks[c]

    async with aiohttp.ClientSession() as session:  # Opens a session to create a webhook.
        if webhook_url:
            webhook = disnake.Webhook.from_url(webhook_url,
                                               session=session)  # Gets the existing webhook if it already exists.
            try:
                await webhook_sender(content.rstrip(), embed=embed, files=final_files, username=username,
                                     avatar_url=author.display_avatar, webhook=webhook, parent=thread_parent)
                return
            except disnake.NotFound as nf:
                webhook_url = False
            except Exception as e:
                content = ''
                if len(file_url) > 0:
                    for url in file_url:
                        content = f'{content}\n{url}'

                await webhook_sender(content.rstrip(), embed=embed, files=final_files, username=username,
                                     avatar_url=author.display_avatar, webhook=webhook, parent=thread_parent)
        if not webhook_url:
            webhook = await channel.create_webhook(name="Webhook Generated by AF-23")  # Generates the webhook and stores the webhook item if no webhook is found.
            webhooks[channel.id] = webhook.url
            with open('webhooks.json', 'w') as file:
                file.write(json.dumps(webhooks))
            await webhook_sender(content.rstrip(), embed=embed, files=final_files, username=username, avatar_url=author.display_avatar, webhook=webhook, parent=thread_parent)
            return


async def webhook_sender(content, embed, username, avatar_url, webhook, files=None, parent=None): # Moved Webhook sending out of the webhook function to make it easier.
        try:
            if parent:
                await webhook.send(content[0:2000], embed=embed, username=username, avatar_url=avatar_url, files=files, thread=parent, allowed_mentions=disnake.AllowedMentions(everyone=False, users=False, replied_user=False, roles=False))
            else:
                await webhook.send(content[0:2000], embed=embed, username=username, avatar_url=avatar_url, files=files, allowed_mentions=disnake.AllowedMentions(everyone=False, users=False, replied_user=False, roles=False))
        except disnake.NotFound as e:
            raise e


# Wordart Fuckery
@commands.cooldown(1, 60, disnake.ext.commands.BucketType.user)
@bot.slash_command(guild_ids=[770428394918641694, 120330239996854274])
async def wordart(inter, content: str):
    id = inter.channel.id
    if isinstance(inter.channel, disnake.Thread):
        id = inter.channel.parent.id

    if id not in channels and id not in forums:
        await inter.send("Wordart can only be sent in the Event Channels!", ephemeral=True)
        return
    if len(content) > 80:
        await inter.send("Wordart can only be 80 characters long!", ephemeral=True)
        return
    await inter.response.send_message("Wordart is being prepared!!", ephemeral=True)
    wordart = generate_wordart(content)
    await generate_forum(author=inter.author, channel=inter.channel, content="", guild=inter.guild, files=[wordart])


@wordart.error
async def on_wordart_errot(ctx, error):
    await ctx.send(f"This command is currently on cooldown. It may be used again in {int(error.retry_after)} seconds.",
                   ephemeral=True)


# Custom Forum Signature Section

@bot.slash_command(guild_ids=[770428394918641694, 120330239996854274])
async def signature(inter, image: disnake.Attachment = None, text: str = None):
    image_old, text_old = await get_user_signature(inter.author)
    embed = disnake.Embed(title=text_old)
    embed.set_image(image_old)

    if image:

        if text_old == 'No Signature has been set! Use `/signature` to set your signature' and text is None:
            text = ''

        if 'image' not in image.content_type:
            await inter.send("You have not uploaded a valid image, so your signature was unable to be set.",
                             ephemeral=True)
            return
        else:
            response = requests.get(image.url)
            with open(f"temp/{inter.author.id}_{image.filename}", 'wb') as file:
                file.write(response.content)

            try:
                message = await bot.get_channel(signature_store).send(
                    file=disnake.File(f"temp/{inter.author.id}_{image.filename}"))
                new_image = message.attachments[0]
            except Exception as e:
                await inter.send(
                    "Fatal error when uploading your signature. Please contact @OblivionCreator with the following exception.\n",
                    e.with_traceback())
                return

            set_user_signature(inter.author.id, new_image.url)

    if text:
        set_user_text(inter.author.id, text)
        embed.title = text
    if image:
        embed.set_image(new_image)
        failed_image = "If the image does not load, please make sure it is a filetype supported by Discord.\n"


    else:
        failed_image = ""
    await inter.send(f"Your signature has been set! {failed_image}Preview:", ephemeral=True, embed=embed)


async def get_user_signature(user):
    conn = sqlite3.connect('signatures.db')
    cur = conn.cursor()
    sql = '''SELECT url, text FROM sigtable WHERE user IS ?'''
    cur.execute(sql, [user.id])
    temp = cur.fetchone()
    image = None
    if temp:
        image, text = temp
        return image, text
    else:
        sql = '''INSERT INTO sigtable (user, url, postcount, text) VALUES(?, ?, ?, ?)'''
        cur.execute(sql, [user.id, "", 0, "No Signature has been set! Use `/signature` to set your signature"])
        conn.commit()
        temp_image = random_signature(user)
        message = await bot.get_channel(signature_store).send(file=disnake.File(f"temp/{temp_image}"))
        new_image = message.attachments[0]
        set_user_signature(user.id, new_image.url)
        return new_image.url, "No Signature has been set! Use `/signature` to set your signature"


def update_post_count(user):
    conn = sqlite3.connect('signatures.db')
    cur = conn.cursor()
    sql = '''SELECT postcount FROM sigtable WHERE user IS ?'''
    cur.execute(sql, [user])
    temp, = cur.fetchone()
    if isinstance(temp, int):
        count = temp
    else:
        count = 0

    count += 1

    sql = '''UPDATE sigtable SET postcount=? WHERE user=?'''
    cur.execute(sql, [count, user])
    conn.commit()
    return count


def set_user_signature(user, url):
    conn = sqlite3.connect('signatures.db')
    cur = conn.cursor()
    try:
        sql = '''INSERT INTO sigtable (user, url) VALUES(?, ?)'''
        cur.execute(sql, [user, url])
    except sqlite3.IntegrityError:
        sql = '''UPDATE sigtable SET url=? WHERE user=?'''
        cur.execute(sql, [url, user])
    conn.commit()


def set_user_text(user, text):
    conn = sqlite3.connect('signatures.db')
    cur = conn.cursor()
    try:
        sql = '''INSERT INTO sigtable (user, text) VALUES(?, ?)'''
        cur.execute(sql, [user, text])
    except sqlite3.IntegrityError:
        sql = '''UPDATE sigtable SET text=? WHERE user=?'''
        cur.execute(sql, [text, user])
    conn.commit()


with open('token.txt') as file:
    token = file.read()

bot.run(token)
