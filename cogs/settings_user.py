# settings_user.py
"""Contains user settings commands"""

import asyncio
from datetime import datetime

import discord
from discord.ext import commands
from discord.raw_models import RawReactionClearEmojiEvent

from database import clans, guilds, reminders, users
from resources import emojis, functions, exceptions, settings, strings


class SettingsUserCog(commands.Cog):
    """Cog with user settings commands"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=('me',))
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def settings(self, ctx: commands.Context) -> None:
        """Returns current user progress settings"""
        if ctx.prefix.lower() == 'rpg ': return
        embed = await embed_user_settings(self.bot, ctx)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name='list')
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def list_reminders(self, ctx: commands.Context, *args: tuple) -> None:
        """Lists all active reminders"""
        if ctx.prefix.lower() == 'rpg ': return
        if args:
            arg = args[0].lower().replace('<@!','').replace('<@','').replace('>','')
            if arg.isnumeric():
                try:
                    user_id = int(arg)
                except:
                    user_id = ctx.author.id
            else:
                user_id = ctx.author.id
        elif ctx.message.mentions:
            mentioned_user = ctx.message.mentions[0]
            if mentioned_user.bot:
                await ctx.reply(
                    'Why would you check the reminders of a bot :face_with_raised_eyebrow:',
                    mention_author=False
                )
                return
            user_id = mentioned_user.id
        else:
            user_id = ctx.author.id
        try:
            user: users.User = await users.get_user(user_id)
        except exceptions.FirstTimeUserError:
            if user_id == ctx.author.id:
                raise
            else:
                await ctx.reply('This user is not registered with this bot.', mention_author=False)
                return
        await self.bot.wait_until_ready()
        user_discord = self.bot.get_user(user_id)
        current_time = datetime.utcnow().replace(microsecond=0)
        user_reminders = await reminders.get_active_user_reminders(user.user_id)
        try:
            clan_reminders = await reminders.get_active_clan_reminders(user.clan_name)
        except:
            clan_reminders = ()
        reminders_commands_list = []
        reminders_events_list = []
        reminders_pets_list = []
        reminders_custom_list = []
        for reminder in user_reminders:
            if 'pets' in reminder.activity:
                reminders_pets_list.append(reminder)
            elif reminder.activity == 'custom':
                reminders_custom_list.append(reminder)
            elif reminder.activity in strings.ACTIVITIES_EVENTS:
                reminders_events_list.append(reminder)
            else:
                reminders_commands_list.append(reminder)

        # Sort pets with same time left together
        if reminders_pets_list:
            counter = -1
            field_pets_list = {}
            for index, reminder in enumerate(reminders_pets_list):
                reminder_last = reminders_pets_list[index-1] if index != 0 else None
                pet_id = reminder.activity.replace('pets-','')
                time_left = current_time - reminder.end_time
                if reminder_last is None:
                    field_pets_list[time_left.total_seconds()] = pet_id
                    counter += 1
                    continue
                if reminder_last.end_time == reminder.end_time:
                    last_pet_id = field_pets_list[time_left.total_seconds()]
                    field_pets_list[time_left.total_seconds()] = f'{last_pet_id}, {pet_id}'
                else:
                    field_pets_list[time_left.total_seconds()] = pet_id
                    counter += 1

        embed = discord.Embed(
            color = settings.EMBED_COLOR,
            title = f'{user_discord.name}\'S REMINDERS'.upper()
        )
        if not user_reminders and not clan_reminders:
            embed.description = f'{emojis.BP} You have no active reminders'
        if reminders_commands_list:
            field_command_reminders = ''
            for reminder in reminders_commands_list:
                time_left = reminder.end_time - current_time
                timestring = await functions.parse_seconds_to_timestring(time_left.total_seconds())
                activity = reminder.activity.replace('-',' ').capitalize()
                field_command_reminders = (
                    f'{field_command_reminders}\n'
                    f'{emojis.BP} **`{activity}`** (**{timestring}**)'
                )
            embed.add_field(name='COMMANDS', value=field_command_reminders.strip())
        if reminders_events_list:
            field_event_reminders = ''
            for reminder in reminders_events_list:
                time_left = reminder.end_time - current_time
                timestring = await functions.parse_seconds_to_timestring(time_left.total_seconds())
                if activity == 'dungeon-miniboss': activity = 'Dungeon / Miniboss'
                activity = reminder.activity.replace('-',' ').capitalize()
                field_event_reminders = (
                    f'{field_event_reminders}\n'
                    f'{emojis.BP} **`{activity}`** (**{timestring}**)'
                )
            embed.add_field(name='EVENTS', value=field_event_reminders.strip())
        if reminders_pets_list:
            field_pets_reminders = ''
            for time_left, pet_ids in field_pets_list.items():
                timestring = await functions.parse_seconds_to_timestring(time_left)
                if ',' in pet_ids:
                    field_pets_reminders = (
                        f'{field_pets_reminders}\n'
                        f'{emojis.BP} **`Pets {pet_ids}`** (**{timestring}**)'
                    )
                else:
                    field_pets_reminders = (
                        f'{field_pets_reminders}\n'
                        f'{emojis.BP} **`Pet {pet_ids}`** (**{timestring}**)'
                    )
            embed.add_field(name='PETS', value=field_pets_reminders.strip())
        if clan_reminders:
            reminder = clan_reminders[0]
            time_left = reminder.end_time - current_time
            timestring = await functions.parse_seconds_to_timestring(time_left.total_seconds())
            embed.add_field(name='GUILD', value=f'{emojis.BP} **`{reminder.clan_name}`** (**{timestring}**)')
        if reminders_custom_list:
            field_custom_reminders = ''
            for reminder in reminders_custom_list:
                time_left = reminder.end_time - current_time
                timestring = await functions.parse_seconds_to_timestring(time_left.total_seconds())
                custom_id = f'0{reminder.custom_id}' if reminder.custom_id <= 9 else reminder.custom_id
                field_custom_reminders = (
                    f'{field_custom_reminders}\n'
                    f'{emojis.BP} **`{custom_id}`** (**{timestring}**)'
                )
            embed.add_field(name='CUSTOM', value=field_custom_reminders.strip())
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=('start',))
    @commands.bot_has_permissions(send_messages=True)
    async def on(self, ctx: commands.Context) -> None:
        """Enables reminders (main activation)"""
        prefix = ctx.prefix
        if prefix.lower() == 'rpg ': return
        try:
            user: users.User = await users.get_user(ctx.author.id)
            if user.reminders_enabled:
                await ctx.reply(f'**{ctx.author.name}**, your reminders are already turned on.', mention_author=False)
                return
        except exceptions.FirstTimeUserError:
            user = await users.insert_user(ctx.author.id)
        if not user.reminders_enabled: await user.update(reminders_enabled=True)
        if not user.reminders_enabled:
            await ctx.reply(strings.MSG_ERROR, mention_author=False)
            return
        await ctx.reply(
            f'Hey! **{ctx.author.name}**! Hello! Your reminders are now turned on.\n'
            f'Don\'t forget to set your donor tier with `{prefix}donor` and - if you are married - '
            f'the donor tier of your partner with `{prefix}partner donor`.\n'
            f'You can check all of your settings with `{prefix}settings`.',
            mention_author=False
        )

    @commands.command(aliases=('stop',))
    @commands.bot_has_permissions(send_messages=True)
    async def off(self, ctx: commands.Context) -> None:
        """Disables reminders (main deactivation)"""
        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        prefix = ctx.prefix
        if prefix.lower() == 'rpg ': return
        user: users.User = await users.get_user(ctx.author.id)
        if not user.reminders_enabled:
            await ctx.reply(f'**{ctx.author.name}**, your reminders are already turned off.', mention_author=False)
            return
        await ctx.reply(
            f'**{ctx.author.name}**, turning off the bot will delete all of your active reminders. '
            f'Are you sure? `[yes/no]`',
            mention_author=False
        )
        try:
            answer = await self.bot.wait_for('message', check=check, timeout=30)
            if answer.content.lower() not in ['yes','y']:
                await ctx.send('Aborted.')
                return
        except asyncio.TimeoutError:
            await ctx.send(f'**{ctx.author.name}**, you didn\'t answer in time.')
            return
        await user.update(reminders_enabled=False)
        if user.reminders_enabled:
            await ctx.reply(strings.MSG_ERROR, mention_author=False)
            return
        active_reminders = await reminders.get_active_user_reminders(ctx.author.id)
        for reminder in active_reminders:
            await reminder.delete()
        await ctx.reply(
            f'**{ctx.author.name}**, your reminders are now turned off.\n'
            f'All active reminders were deleted.',
            mention_author=False
        )

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def dnd(self, ctx: commands.Context, *args: tuple) -> None:
        """Enables/disables dnd mode"""
        prefix = ctx.prefix
        if prefix.lower() == 'rpg ': return
        syntax = strings.MSG_SYNTAX.format(syntax=f'{prefix}dnd [on|off]')

        if not args:
            await ctx.reply(syntax, mention_author=False)
        if args:
            action = args[0].lower()
            if action in ('on', 'enable', 'start'):
                enabled = True
                action = 'enabled'
            elif action in ('off', 'disable', 'stop'):
                enabled = False
                action = 'disabled'
            else:
                await ctx.reply(syntax, mention_author=False)
                return
            user: users.User = await users.get_user(ctx.author.id)
            if user.dnd_mode_enabled == enabled:
                await ctx.reply(
                    f'**{ctx.author.name}**, DND mode is already {action}.',
                    mention_author=False
                )
                return
            await user.update(dnd_mode_enabled=enabled)
            if user.dnd_mode_enabled == enabled:
                await ctx.reply(
                    f'**{ctx.author.name}**, DND mode is now **{action}**.',
                    mention_author=False
                )
            else:
                await ctx.reply(strings.MSG_ERROR, mention_author=False)

    @commands.command(aliases=('donator',))
    @commands.bot_has_permissions(send_messages=True)
    async def donor(self, ctx: commands.Context, *args: tuple) -> None:
        """Sets user donor tier"""
        prefix = ctx.prefix
        if prefix.lower() == 'rpg ': return
        msg_syntax = strings.MSG_SYNTAX.format(syntax=f'`{prefix}donor [tier]`')
        user: users.User = await users.get_user(ctx.author.id)
        possible_tiers = f'Possible tiers:'
        for index, donor_tier in enumerate(strings.DONOR_TIERS):
            possible_tiers = f'{possible_tiers}\n{emojis.BP}`{index}` : {donor_tier}\n'
        if not args:
            await ctx.reply(
                f'**{ctx.author.name}**, your current EPIC RPG donor tier is **{user.user_donor_tier}** '
                f'({strings.DONOR_TIERS[user.user_donor_tier]}).\n'
                f'If you want to change this, use `{prefix}{ctx.invoked_with} [tier]`.\n\n{possible_tiers}',
                mention_author=False
            )
            return
        if args:
            try:
                donor_tier = int(args[0])
            except:
                await ctx.reply(f'{msg_syntax}\n\n{possible_tiers}')
                return
            if donor_tier > len(strings.DONOR_TIERS) - 1:
                await ctx.reply(f'{msg_syntax}\n\n{possible_tiers}')
                return
            await user.update(user_donor_tier=donor_tier)
            await ctx.reply(
                f'**{ctx.author.name}**, your EPIC RPG donor tier is now set to **{user.user_donor_tier}** '
                f'({strings.DONOR_TIERS[user.user_donor_tier]}).\n\n'
                f'Please note that the `hunt together` cooldown can only be accurately calculated if '
                f'`{prefix}partner donor [tier]` is set correctly as well.',
                mention_author=False
            )

    @commands.command(aliases=('disable',))
    @commands.bot_has_permissions(send_messages=True)
    async def enable(self, ctx: commands.Context, *args: tuple) -> None:
        """Enables/disables specific reminders"""
        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        prefix = ctx.prefix
        if prefix.lower() == 'rpg ': return
        action = ctx.invoked_with.lower()
        enabled = True if action == 'enable' else False
        user: users.User = await users.get_user(ctx.author.id)
        syntax = strings.MSG_SYNTAX(syntax=f'{prefix}{action} [activity]')
        possible_activities = 'Possible activities:'
        for activity in strings.ACTIVITIES_ALL:
            possible_activities = f'{possible_activities}\n{emojis.BP} `{activity}`'
        if not args:
            await ctx.reply(f'{syntax}\n\n{possible_activities}', mention_author=False)
            return
        if args[0].lower() == 'all':
            if not enabled:
                try:
                    await ctx.reply(
                        f'**{ctx.author.name}**, turning off all reminders will delete all of your active reminders. '
                        f'Are you sure? `[yes/no]`',
                        mention_author=False
                    )
                    answer = await self.bot.wait_for('message', check=check, timeout=30)
                except asyncio.TimeoutError:
                    await ctx.send(f'**{ctx.author.name}**, you didn\'t answer in time.')
                    return
                if answer.content.lower() not in ['yes','y']:
                    await ctx.send('Aborted')
                    return
            args = strings.ACTIVITIES
        updated_activities = []
        ignored_activites = []
        for activity in args:
            if activity in strings.ACTIVITIES_ALIASES: activity = strings.ACTIVITIES_ALIASES[activity]
            updated_activities.append(activity) if activity in strings.ACTIVITIES else ignored_activites.append(activity)
        if updated_activities:
            kwargs = {}
            answer = f'{action.capitalize()}d activities:'
            for activity in updated_activities:
                kwargs[f'{strings.ACTIVITIES_COLUMNS[activity]}_enabled'] = enabled
                answer = f'{answer}\n{emojis.BP}`{activity}`'
                if not enabled:
                    try:
                        reminder: reminders.Reminder = await reminders.get_user_reminder(ctx.author.id, activity)
                        await reminder.delete()
                    except exceptions.NoDataFoundError:
                        pass
            await user.update(**kwargs)
        if ignored_activites:
            answer = f'{answer}\n\nCouldn\'t find the following activities:'
            for activity in ignored_activites:
                answer = f'{answer}\n{emojis.BP}`{activity}`'
        await ctx.reply(answer, mention_author=False)

    @commands.command(aliases=('hm',))
    @commands.bot_has_permissions(send_messages=True)
    async def hardmode(self, ctx: commands.Context, *args: tuple) -> None:
        """Enables/disables hardmode mode"""
        prefix = ctx.prefix
        if prefix.lower() == 'rpg ': return
        syntax = strings.MSG_SYNTAX.format(syntax=f'{prefix}{ctx.invoked_with} [on|off]')

        if not args:
            await ctx.reply(syntax, mention_author=False)
            return
        action = args[0].lower()
        if action in ('on', 'enable', 'start'):
            enabled = True
            action = 'enabled'
        elif action in ('off', 'disable', 'stop'):
            enabled = False
            action = 'disabled'
        else:
            await ctx.reply(syntax, mention_author=False)
            return
        user: users.User = await users.get_user(ctx.author.id)
        if user.hardmode_mode_enabled == enabled:
            await ctx.reply(
                f'**{ctx.author.name}**, hardmode mode is already {action}.',
                mention_author=False
            )
            return
        await user.update(hardmode_mode_enabled=enabled)
        if user.hardmode_mode_enabled == enabled:
            await ctx.reply(
                f'**{ctx.author.name}**, hardmode mode is now **{action}**.',
                mention_author=False
            )
        else:
            await ctx.reply(strings.MSG_ERROR, mention_author=False)

    @commands.command(aliases=('rubies',))
    @commands.bot_has_permissions(send_messages=True)
    async def ruby(self, ctx: commands.Context, *args: tuple) -> None:
        """Enables/disables ruby counter and shows rubies"""
        prefix = ctx.prefix
        if prefix.lower() == 'rpg ': return
        syntax = strings.MSG_SYNTAX.format(syntax=f'{prefix}{ctx.invoked_with} [on|off]')

        user: users.User = await users.get_user(ctx.author.id)

        if not args:
            await ctx.reply(
                f'**{ctx.author.name}**, you have {user.rubies} {emojis.RUBY} rubies.',
                mention_author=False
            )
            return
        action = args[0].lower()
        if action in ('on', 'enable', 'start'):
            enabled = True
            action = 'enabled'
        elif action in ('off', 'disable', 'stop'):
            enabled = False
            action = 'disabled'
        else:
            await ctx.reply(syntax, mention_author=False)
            return
        if user.ruby_counter_enabled == enabled:
            await ctx.reply(
                f'**{ctx.author.name}**, the ruby counter is already {action}.',
                mention_author=False
            )
            return
        await user.update(ruby_counter_enabled=enabled)
        if user.ruby_counter_enabled == enabled:
            answer = f'**{ctx.author.name}**, the ruby counter is now **{action}**.'
            if enabled:
                answer = (
                    f'{answer}\n'
                    f'If your training reminder is turned on, I will automatically tell you your ruby count when '
                    f'the ruby training comes along.\n'
                    f'If you want to manually check your ruby count, use `{prefix}ruby`.'
                )
            await ctx.reply(answer, mention_author=False)
        else:
            await ctx.reply(strings.MSG_ERROR, mention_author=False)

    @commands.command(aliases=('tr-helper','traininghelper','training-helper'))
    @commands.bot_has_permissions(send_messages=True)
    async def trhelper(self, ctx: commands.Context, *args: tuple) -> None:
        """Enables/disables training helper"""
        prefix = ctx.prefix
        if prefix.lower() == 'rpg ': return
        syntax = strings.MSG_SYNTAX.format(syntax=f'{prefix}{ctx.invoked_with} [on|off]')
        if not args:
            await ctx.reply(syntax, mention_author=False)
            return
        action = args[0].lower()
        if action in ('on', 'enable', 'start'):
            enabled = True
            action = 'enabled'
        elif action in ('off', 'disable', 'stop'):
            enabled = False
            action = 'disabled'
        else:
            await ctx.reply(syntax, mention_author=False)
            return
        user: users.User = await users.get_user(ctx.author.id)
        if user.training_helper_enabled == enabled:
            await ctx.reply(
                f'**{ctx.author.name}**, the training helper is already {action}.',
                mention_author=False
            )
            return
        await user.update(training_helper_enabled=enabled)
        if user.training_helper_enabled == enabled:
            answer = f'**{ctx.author.name}**, the training helper is now **{action}**.'
            if enabled:
                answer = (
                    f'{answer}\n'
                    f'If your training reminder is turned on, I will automatically tell you the answer to all '
                    f'training questions.\n'
                    f'Note that the ruby question is controlled separately with `{prefix}ruby [on|off]`.'
                )
            await ctx.reply(answer, mention_author=False)
        else:
            await ctx.reply(strings.MSG_ERROR, mention_author=False)


# Initialization
def setup(bot):
    bot.add_cog(SettingsUserCog(bot))


# --- Embeds ---
async def embed_user_settings(bot: commands.Bot, ctx: commands.Context) -> discord.Embed:
    """User settings embed"""
    async def bool_to_text(boolean: bool):
        return 'Enabled' if boolean else 'Disabled'

    # Get user settings
    partner_channel_name = 'N/A'
    user_settings: users.User = await users.get_user(ctx.author.id)
    if user_settings.partner_channel_id is not None:
        await bot.wait_until_ready()
        partner_channel = bot.get_channel(user_settings.partner_channel_id)
        partner_channel_name = partner_channel.name

    # Get partner settings
    partner_name = partner_hardmode_status = 'N/A'
    if user_settings.partner_id is not None:
        partner_settings: users.User = await users.get_user(user_settings.partner_id)
        await bot.wait_until_ready()
        partner = bot.get_user(user_settings.partner_id)
        partner_name = f'{partner.name}#{partner.discriminator}'
        partner_hardmode_status = await bool_to_text(partner_settings.hardmode_mode_enabled)

    # Get clan settings
    clan_name = clan_alert_status = stealth_threshold = clan_channel_name = 'N/A'
    try:
        clan_settings: clans.Clan = await clans.get_clan_by_user_id(ctx.author.id)
        clan_name = clan_settings.clan_name
        clan_alert_status = await bool_to_text(clan_settings.alert_enabled)
        stealth_threshold = clan_settings.stealth_threshold
        if clan_settings.channel_id is not None:
            await bot.wait_until_ready()
            clan_channel = bot.get_channel(clan_settings.channel_id)
            clan_channel_name = clan_channel.name
    except exceptions.NoDataFoundError:
        pass

    # Fields
    field_user = (
        f'{emojis.bp} Reminders: `{await bool_to_text(user_settings.reminders_enabled)}`\n'
        f'{emojis.bp} Donor tier: `{user_settings.user_donor_tier}` '
        f'({settings.DONOR_TIERS[strings.user_donor_tier]})\n'
        f'{emojis.bp} DND mode: `{await bool_to_text(user_settings.dnd_mode_enabled)}`\n'
        f'{emojis.bp} Hardmode mode: `{await bool_to_text(user_settings.hardmode_mode_enabled)}`\n'
        f'{emojis.bp} Ruby counter: `{await bool_to_text(user_settings.ruby_counter_enabled)}`\n'
        f'{emojis.bp} Training helper: `{await bool_to_text(user_settings.training_helper_enabled)}`\n'
        f'{emojis.bp} Partner alert channel: `{partner_channel_name}`'
    )
    field_partner = (
        f'{emojis.bp} Name: `{partner_name}`\n'
        f'{emojis.bp} Hardmode mode: `{partner_hardmode_status}`\n'
        f'{emojis.bp} Donor tier: `{user_settings.partner_donor_tier}` '
        f'({strings.DONOR_TIERS[user_settings.partner_donor_tier]})\n'
    )
    field_clan = (
        f'{emojis.bp} Name: `{clan_name}`\n'
        f'{emojis.bp} Reminders: `{clan_alert_status}`\n'
        f'{emojis.bp} Alert channel: `{clan_channel_name}`\n'
        f'{emojis.bp} Stealth threshold: `{stealth_threshold}`'
    )
    field_reminders = (
        f'{emojis.bp} Adventure: `{await bool_to_text(user_settings.alert_adventure.enabled)}`\n'
        f'{emojis.bp} Arena: `{await bool_to_text(user_settings.alert_arena.enabled)}`\n'
        f'{emojis.bp} Daily: `{await bool_to_text(user_settings.alert_daily.enabled)}`\n'
        f'{emojis.bp} Duel: `{await bool_to_text(user_settings.alert_duel.enabled)}`\n'
        f'{emojis.bp} Dungeon / Miniboss: `{await bool_to_text(user_settings.alert_dungeon_miniboss.enabled)}`\n'
        f'{emojis.bp} Farm: `{await bool_to_text(user_settings.alert_farm.enabled)}`\n'
        f'{emojis.bp} Horse: `{await bool_to_text(user_settings.alert_horse_breed.enabled)}`\n'
        f'{emojis.bp} Hunt: `{await bool_to_text(user_settings.alert_hunt.enabled)}`\n'
        f'{emojis.bp} Lootbox: `{await bool_to_text(user_settings.alert_lootbox.enabled)}`\n'
        f'{emojis.bp} Lottery: `{await bool_to_text(user_settings.alert_lottery.enabled)}`\n'
        f'{emojis.bp} Partner alert: `{await bool_to_text(user_settings.alert_partner.enabled)}`\n'
        f'{emojis.bp} Pets: `{await bool_to_text(user_settings.alert_pets.enabled)}`\n'
        f'{emojis.bp} Quest: `{await bool_to_text(user_settings.alert_quest.enabled)}`\n'
        f'{emojis.bp} Training: `{await bool_to_text(user_settings.alert_training.enabled)}`\n'
        f'{emojis.bp} Vote: `{await bool_to_text(user_settings.alert_vote.enabled)}`\n'
        f'{emojis.bp} Weekly: `{await bool_to_text(user_settings.alert_weekly.enabled)}`\n'
        f'{emojis.bp} Work: `{await bool_to_text(user_settings.alert_work.enabled)}`'
    )
    field_event_reminders = (
        f'{emojis.bp} Big arena: `{await bool_to_text(user_settings.alert_big_arena.enabled)}`\n'
        f'{emojis.bp} Horse race: `{await bool_to_text(user_settings.alert_horse_race.enabled)}`\n'
        f'{emojis.bp} Not so mini boss: `{await bool_to_text(user_settings.alert_not_so_mini_boss.enabled)}`\n'
        f'{emojis.bp} Pet tournament: `{await bool_to_text(user_settings.alert_pet_tournament.enabled)}`\n'
    )
    if not user_settings.reminders_enabled:
        field_reminders = f'**These settings are ignored because your reminders are off.**\n{field_reminders}'

    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{ctx.author.name}\'s settings'.upper(),
    )
    embed.add_field(name='USER', value=field_user, inline=False)
    embed.add_field(name='PARTNER', value=field_partner, inline=False)
    embed.add_field(name='GUILD', value=field_clan, inline=False)
    embed.add_field(name='COOLDOWN REMINDERS', value=field_reminders, inline=False)
    embed.add_field(name='EVENT REMINDERS', value=field_event_reminders, inline=False)

    return embed