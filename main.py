import os
from datetime import datetime
import json
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks, commands
from discord.ui import View
from discord.utils import format_dt

from secrets import TOKEN, GUILD_ID, REMINDER_CHANNEL_ID, PRINCESS_ID


intents = discord.Intents.default()
intents.typing = False
intents.message_content = True

bot = commands.Bot(command_prefix=commands.when_mentioned_or("hair", "🧼"), case_insensitive=True,
                   strip_after_prefix=True, intents=intents,
                   activity=discord.CustomActivity(type=3, name="✨ sparkle like me gurl"))

server_timezone = ZoneInfo('America/New_York')  # same as your timezone

"""
database.json schematics
{
    "shampoo": [
        int timestamp, ...
    ]
    "reminder_count": {
        "shampoo": int
    }
}
"""
# Initialize db
if not os.path.exists('database.json'):
    initial_data = {'shampoo': [], "reminder_count": {"shampoo": 5}}
    with open('database.json', 'w') as fp:
        json.dump(initial_data, fp, indent=4)


@bot.event
async def on_ready():
    print("Online to make you jealous of my hair!")


@bot.command()
async def ping(ctx):
    await ctx.send('🌊 Pong!')


@commands.is_owner()
@bot.command()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send('Synced successfully')


async def add_to_history(interaction):
    with open("database.json", "r") as f:
        data = json.load(f)

    if data["shampoo"]:
        last_timestamp = data["shampoo"][-1]
        free_to_shower = last_timestamp + 10 * 60 * 60  # keep a 10 hour safety net
        if free_to_shower > datetime.now(server_timezone).timestamp():
            return await interaction.response.send_message(
                'You shampooed your hair less than 10 hours ago!? Try after 10 hours have passed..')

    data["shampoo"].append(int(datetime.now(server_timezone).timestamp()))
    data["reminder_count"]["shampoo"] = 5  # reset count
    with open("database.json", "w") as f:
        json.dump(data, f, indent=4)

    await interaction.response.send_message('Added to your history! Type `hair shampoo` or `hair history` to view!')


class DidShampooView(View):
    @discord.ui.button(emoji="🧴", label="I shampooed my hair today!")
    async def callback(self, interaction, btn):
        await add_to_history(interaction)

    async def interaction_check(self, interaction):
        return interaction.user.id == PRINCESS_ID


@bot.hybrid_command(aliases=("history", ))
async def shampoo(ctx):
    """This command will show a history of showering your hair, with shampoo"""
    with open("database.json", "r") as f:
        data = json.load(f)

    if data["shampoo"]:
        history = "\n".join([f"- {format_dt(datetime.fromtimestamp(timestamp, server_timezone), 'F')} ({format_dt(datetime.fromtimestamp(timestamp, server_timezone), 'R')})" for timestamp in data["shampoo"][-5:]])
    else:
        history = 'Start tracking already... click the button!'

    emb = discord.Embed(
        color=discord.Color.magenta(),
        title="🫧 Your shampoo history",
        description=history
    )
    await ctx.send(
        'The door to perfect hair is a very soapy road!',
        embed=emb,
        view=DidShampooView()
    )


class ShampooReminderView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="✨", label="Yay! My hair is silky now!!")
    async def callback(self, interaction, btn):
        await add_to_history(interaction)

    async def interaction_check(self, interaction):
        return interaction.user.id == PRINCESS_ID


async def send_reminder():
    guild = bot.get_guild(GUILD_ID)
    channel = guild.get_channel(REMINDER_CHANNEL_ID)
    user_mention = f"<@{PRINCESS_ID}>"
    await channel.send(f"{user_mention} time to shampoo your hair!! It's been 3 days!!!", view=ShampooReminderView())


@tasks.loop(seconds=300)
async def reminder():
    """
    This task will loop through your history and remind you once 3 days have passed since most recent shampoo
    after which it will remind once every 5 hours for 5 times (reminder_count)
    """
    with open("database.json", "r") as f:
        data = json.load(f)

    try:
        most_recent = data["shampoo"][-1]
    except IndexError:  # no recorded data yet
        return

    current_time = datetime.now(server_timezone).timestamp()
    three_days = 3 * 24 * 60 * 60  # in seconds

    if current_time - most_recent >= three_days:  # 36h have passed
        count = data["reminder_count"]["shampoo"]
        if count > 0:
            five_hours = 5 * 60 * 60  # in seconds
            # every 5 hours reminder after 3 days upto 5 times
            extra_wait_time = five_hours * (5 - count)  # 0 additional wait time when 5 is the count, 5h when 4, so on..
            if current_time - most_recent >= three_days + extra_wait_time:
                await send_reminder()
                data["reminder_count"]["shampoo"] -= 1
                with open('database.json', 'w') as f:
                    json.dump(data, f, indent=4)


@reminder.before_loop
async def before_reminder():
    await bot.wait_until_ready()


@bot.event
async def setup_hook():
    # Start the task
    reminder.start()


bot.run(TOKEN)
