import disnake
from disnake.ext import commands, tasks
from disnake.ui import Button, View, Select
from typing import Optional, Dict
import time
import asyncio

# ========== НАСТРОЙКИ ==========
VOICE_CHANNELS = {

#==================================================================================
                    #DUO каналы
#==================================================================================


    1486048846013530132: {"name": "Дуо-1", "text_channel_id": 1486048846013530132},
    1486048899193110538: {"name": "Дуо-2", "text_channel_id": 1486048899193110538},
    1486048992142954527: {"name": "Дуо-3", "text_channel_id": 1486048992142954527},
    1486049023126274149: {"name": "Дуо-4", "text_channel_id": 1486049023126274149},
    1486049042898354318: {"name": "Дуо-5", "text_channel_id": 1486049042898354318},
    1486049062875562135: {"name": "Дуо-6", "text_channel_id": 1486049062875562135},
    1486049088402096290: {"name": "Дуо-7", "text_channel_id": 1486049088402096290},
    1486049113031049479: {"name": "Дуо-8", "text_channel_id": 1486049113031049479},
    1486049137622519900: {"name": "Дуо-9", "text_channel_id": 1486049137622519900},
    1486049165422104839: {"name": "Дуо-10", "text_channel_id": 1486049165422104839},

#==================================================================================
                    #TRIO каналы
#==================================================================================

    1486049297152606389: {"name": "Трио-1", "text_channel_id": 1486049297152606389},
    1486049372906193088: {"name": "Трио-2", "text_channel_id": 1486049372906193088},
    1486049400169038066: {"name": "Трио-3", "text_channel_id": 1486049400169038066},
    1486049419865624608: {"name": "Трио-4", "text_channel_id": 1486049419865624608},
    1486049437448147036: {"name": "Трио-5", "text_channel_id": 1486049437448147036},
    1486049453134839829: {"name": "Трио-6", "text_channel_id": 1486049453134839829},
    1486049473221230692: {"name": "Трио-7", "text_channel_id": 1486049473221230692},
    1486049494369046719: {"name": "Трио-8", "text_channel_id": 1486049494369046719},
    1486049529101946932: {"name": "Трио-9", "text_channel_id": 1486049529101946932},
    1486049549628739714: {"name": "Трио-10", "text_channel_id": 1486049549628739714},
    1486049578485547219: {"name": "Трио-11", "text_channel_id": 1486049578485547219},
    1486049599452872896: {"name": "Трио-12", "text_channel_id": 1486049599452872896},
    1486049617589043413: {"name": "Трио-13", "text_channel_id": 1486049617589043413},
    1486049635343536190: {"name": "Трио-14", "text_channel_id": 1486049635343536190},
    1486049657288392724: {"name": "Трио-15", "text_channel_id": 1486049657288392724},
    1486049678847115565: {"name": "Трио-16", "text_channel_id": 1486049678847115565},
    1486049693518532749: {"name": "Трио-17", "text_channel_id": 1486049693518532749},
    1486049719473148045: {"name": "Трио-18", "text_channel_id": 1486049719473148045},
    1486049738527866971: {"name": "Трио-19", "text_channel_id": 1486049738527866971},
    1486049758618452130: {"name": "Трио-20", "text_channel_id": 1486049758618452130},
    1486049779040518154: {"name": "Трио-21", "text_channel_id": 1486049779040518154},
    1486049800561492121: {"name": "Трио-22", "text_channel_id": 1486049800561492121},
    1486049825723257052: {"name": "Трио-23", "text_channel_id": 1486049825723257052},
    1486049843217567917: {"name": "Трио-24", "text_channel_id": 1486049843217567917},
    1486049868689571932: {"name": "Трио-25", "text_channel_id": 1486049868689571932},
    1486049884032335953: {"name": "Трио-26", "text_channel_id": 1486049884032335953},
    1486049917444165632: {"name": "Трио-27", "text_channel_id": 1486049917444165632},
    1486049934913437947: {"name": "Трио-28", "text_channel_id": 1486049934913437947},
    1486049952990757087: {"name": "Трио-29", "text_channel_id": 1486049952990757087},
    1486049975895851159: {"name": "Трио-30", "text_channel_id": 1486049975895851159},
}

CHECK_INTERVAL = 60


# =================================


class VoiceManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_sessions: Dict[int, dict] = {}
        self.voice_channels = VOICE_CHANNELS
        self.panel_messages: Dict[int, int] = {}
        self.leader_panels: Dict[int, int] = {}

        self.check_owner_presence.start()
        self.send_welcome_messages.start()

    def cog_unload(self):
        self.check_owner_presence.cancel()
        self.send_welcome_messages.cancel()

    def get_session(self, voice_channel_id: int) -> Optional[dict]:
        return self.active_sessions.get(voice_channel_id)

    def update_session(self, voice_channel_id: int, owner_id: Optional[int] = None,
                       banned_list: list = None, leave_time: float = None):
        if voice_channel_id not in self.active_sessions:
            self.active_sessions[voice_channel_id] = {
                "owner_id": None,
                "banned_users": [],
                "leave_time": None
            }

        if owner_id is not None:
            self.active_sessions[voice_channel_id]["owner_id"] = owner_id
        if banned_list is not None:
            self.active_sessions[voice_channel_id]["banned_users"] = banned_list
        if leave_time is not None:
            self.active_sessions[voice_channel_id]["leave_time"] = leave_time

    def delete_session(self, voice_channel_id: int):
        if voice_channel_id in self.active_sessions:
            del self.active_sessions[voice_channel_id]

    def is_moderator(self, member: disnake.Member) -> bool:
        return member.guild_permissions.administrator or member.guild_permissions.manage_channels

    async def get_text_channel(self, voice_channel_id: int, guild: disnake.Guild) -> Optional[disnake.TextChannel]:
        channel_info = self.voice_channels.get(voice_channel_id)
        if channel_info and channel_info.get("text_channel_id") and channel_info["text_channel_id"] != 0:
            return guild.get_channel(channel_info["text_channel_id"])
        return None

    async def ban_user(self, voice_channel: disnake.VoiceChannel, target: disnake.Member,
                       leader: disnake.Member, reason: str = "Забанен лидером"):
        try:
            overwrites = voice_channel.overwrites
            overwrites[target] = disnake.PermissionOverwrite(
                connect=False,
                speak=False
            )
            await voice_channel.edit(overwrites=overwrites)

            if target.voice and target.voice.channel == voice_channel:
                await target.move_to(None, reason=reason)

            text_channel = await self.get_text_channel(voice_channel.id, voice_channel.guild)
            if text_channel:
                embed = disnake.Embed(
                    title="🔨 УЧАСТНИК ЗАБАНЕН",
                    description=f"{target.mention} был забанен в канале {voice_channel.mention}",
                    color=disnake.Color.red()
                )
                embed.add_field(name="👑 Лидер", value=leader.mention, inline=True)
                await text_channel.send(embed=embed)
            return True
        except Exception as e:
            print(f"Ошибка бана: {e}")
            return False

    async def unban_user(self, voice_channel: disnake.VoiceChannel, target: disnake.Member, leader: disnake.Member):
        try:
            overwrites = voice_channel.overwrites
            if target in overwrites:
                del overwrites[target]
            await voice_channel.edit(overwrites=overwrites)

            text_channel = await self.get_text_channel(voice_channel.id, voice_channel.guild)
            if text_channel:
                embed = disnake.Embed(
                    title="🔓 УЧАСТНИК РАЗБАНЕН",
                    description=f"{target.mention} был разбанен в канале {voice_channel.mention}",
                    color=disnake.Color.green()
                )
                embed.add_field(name="👑 Лидер", value=leader.mention, inline=True)
                await text_channel.send(embed=embed)
            return True
        except Exception as e:
            print(f"Ошибка разбана: {e}")
            return False

    async def clear_all_bans(self, voice_channel: disnake.VoiceChannel):
        try:
            session = self.get_session(voice_channel.id)
            if session:
                banned_users = session.get("banned_users", [])
                overwrites = voice_channel.overwrites

                for user_id in banned_users:
                    user = voice_channel.guild.get_member(user_id)
                    if user and user in overwrites:
                        del overwrites[user]

                await voice_channel.edit(overwrites=overwrites)
                session["banned_users"] = []

                text_channel = await self.get_text_channel(voice_channel.id, voice_channel.guild)
                if text_channel:
                    embed = disnake.Embed(
                        title="🔓 ВСЕ БАНЫ СНЯТЫ",
                        description=f"Лидер покинул канал **{voice_channel.name}**, все баны сброшены!",
                        color=disnake.Color.green()
                    )
                    await text_channel.send(embed=embed)
        except Exception as e:
            print(f"Ошибка очистки банов: {e}")

    async def update_no_leader_panel(self, voice_channel: disnake.VoiceChannel):
        text_channel = await self.get_text_channel(voice_channel.id, voice_channel.guild)
        if not text_channel:
            return

        message_id = self.panel_messages.get(voice_channel.id)
        if message_id:
            try:
                old_msg = await text_channel.fetch_message(message_id)
                await old_msg.delete()
            except:
                pass

        embed = disnake.Embed(
            title="🔊 НЕТ АКТИВНОГО ЛИДЕРА",
            description=f"В голосовом канале **{voice_channel.name}** сейчас нет лидера.",
            color=disnake.Color.orange()
        )
        embed.add_field(
            name="🎤 КАК СТАТЬ ЛИДЕРОМ?",
            value=(
                "**1️⃣** Зайдите в голосовой канал\n"
                "**2️⃣** Нажмите на кнопку **🎤 Взять лидерство** ниже\n\n"
                "**✨ Возможности лидера:**\n"
                "• 🔨 Банить участников\n"
                "• 👑 Передавать лидерство\n"
                "• 🔓 Разбанивать участников"
            ),
            inline=False
        )
        embed.set_footer(text="⏰ Лидерство автоматически снимается через 60 секунд после выхода лидера")

        view = self.ClaimButtonView(self, voice_channel.id)
        msg = await text_channel.send(embed=embed, view=view)
        self.panel_messages[voice_channel.id] = msg.id

    async def update_leader_panel(self, voice_channel: disnake.VoiceChannel, owner: disnake.Member):
        text_channel = await self.get_text_channel(voice_channel.id, voice_channel.guild)
        if not text_channel:
            return

        old_panel_id = self.leader_panels.get(voice_channel.id)
        if old_panel_id:
            try:
                old_msg = await text_channel.fetch_message(old_panel_id)
                await old_msg.delete()
            except:
                pass

        session = self.get_session(voice_channel.id)
        banned_count = len(session.get("banned_users", [])) if session else 0

        embed = disnake.Embed(
            title="👑 АКТИВНЫЙ ЛИДЕР КАНАЛА",
            description=f"**{owner.mention}** является лидером канала **{voice_channel.name}**!",
            color=disnake.Color.green()
        )
        embed.add_field(
            name="📊 СТАТИСТИКА",
            value=(
                f"• Лидер: {owner.display_name}\n"
                f"• Забанено: {banned_count} пользователей"
            ),
            inline=False
        )
        embed.set_thumbnail(url=owner.display_avatar.url)

        view = self.LeaderControlView(self, voice_channel.id, owner.id)
        msg = await text_channel.send(embed=embed, view=view)
        self.leader_panels[voice_channel.id] = msg.id

    # --- Кнопка "Взять лидерство" ---
    class ClaimButtonView(View):
        def __init__(self, cog, voice_channel_id: int):
            super().__init__(timeout=None)
            self.cog = cog
            self.voice_channel_id = voice_channel_id

        @disnake.ui.button(label="🎤 Взять лидерство", style=disnake.ButtonStyle.success, emoji="🎤")
        async def claim_channel(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
            voice_channel = interaction.guild.get_channel(self.voice_channel_id)

            if not voice_channel:
                await interaction.response.send_message("❌ Голосовой канал не найден!", ephemeral=True)
                return

            if not interaction.user.voice or interaction.user.voice.channel != voice_channel:
                await interaction.response.send_message(
                    f"❌ Вы должны находиться в голосовом канале **{voice_channel.name}**!",
                    ephemeral=True
                )
                return

            session = self.cog.get_session(self.voice_channel_id)

            if session and session.get("owner_id"):
                owner = interaction.guild.get_member(session["owner_id"])
                if owner and owner.voice and owner.voice.channel == voice_channel:
                    await interaction.response.send_message(
                        f"❌ У канала уже есть лидер: {owner.display_name}",
                        ephemeral=True
                    )
                    return
                elif session.get("leave_time"):
                    time_left = 60 - (time.time() - session["leave_time"])
                    if time_left > 0:
                        await interaction.response.send_message(
                            f"⚠️ Подождите {int(time_left)} секунд",
                            ephemeral=True
                        )
                        return
                else:
                    self.cog.delete_session(self.voice_channel_id)
                    session = None

            overwrites = voice_channel.overwrites
            if interaction.user in overwrites and overwrites[interaction.user].connect is False:
                await interaction.response.send_message(
                    "❌ Вы забанены в этом канале!",
                    ephemeral=True
                )
                return

            banned_users = []
            for target, overwrite in overwrites.items():
                if isinstance(target, disnake.Member) and overwrite.connect is False:
                    banned_users.append(target.id)

            self.cog.update_session(
                self.voice_channel_id,
                interaction.user.id,
                banned_users,
                leave_time=None
            )

            msg_id = self.cog.panel_messages.get(self.voice_channel_id)
            if msg_id:
                try:
                    msg = await interaction.channel.fetch_message(msg_id)
                    await msg.delete()
                except:
                    pass
                del self.cog.panel_messages[self.voice_channel_id]

            await self.cog.update_leader_panel(voice_channel, interaction.user)
            await interaction.response.send_message(f"✅ Вы стали лидером!", ephemeral=True)

    # --- Панель управления лидера ---
    class LeaderControlView(View):
        def __init__(self, cog, voice_channel_id: int, owner_id: int):
            super().__init__(timeout=None)
            self.cog = cog
            self.voice_channel_id = voice_channel_id
            self.owner_id = owner_id

        async def interaction_check(self, interaction: disnake.MessageInteraction) -> bool:
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message(
                    "❌ Только лидер может использовать кнопки!",
                    ephemeral=True
                )
                return False
            return True

        @disnake.ui.button(label="🔨 Забанить", style=disnake.ButtonStyle.danger, emoji="🔨")
        async def ban_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
            voice_channel = interaction.guild.get_channel(self.voice_channel_id)
            if not voice_channel:
                await interaction.response.send_message("Канал не найден!", ephemeral=True)
                return

            members_in_vc = []
            for m in voice_channel.members:
                if m.id != self.owner_id and not self.cog.is_moderator(m):
                    members_in_vc.append(m)

            if not members_in_vc:
                await interaction.response.send_message("Нет участников для бана.", ephemeral=True)
                return

            select = Select(
                placeholder="Выберите участника...",
                options=[disnake.SelectOption(label=m.display_name, value=str(m.id)) for m in members_in_vc[:25]]
            )

            async def select_callback(select_interaction: disnake.MessageInteraction):
                await select_interaction.response.defer()
                target_id = int(select.values[0])
                target = select_interaction.guild.get_member(target_id)

                if not target:
                    await select_interaction.followup.send("Пользователь не найден!", ephemeral=True)
                    return

                if self.cog.is_moderator(target):
                    await select_interaction.followup.send("❌ Нельзя забанить модератора!", ephemeral=True)
                    return

                success = await self.cog.ban_user(voice_channel, target, interaction.user)

                if success:
                    session = self.cog.get_session(self.voice_channel_id)
                    if session and target.id not in session["banned_users"]:
                        session["banned_users"].append(target.id)
                    await self.cog.update_leader_panel(voice_channel, interaction.user)
                    await select_interaction.followup.send(f"✅ {target.display_name} забанен.", ephemeral=True)

                try:
                    await select_interaction.message.delete()
                except:
                    pass

            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.response.send_message("Выберите участника:", view=view, ephemeral=True)

        @disnake.ui.button(label="👑 Передать", style=disnake.ButtonStyle.primary, emoji="👑")
        async def transfer_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
            voice_channel = interaction.guild.get_channel(self.voice_channel_id)
            if not voice_channel:
                await interaction.response.send_message("Канал не найден!", ephemeral=True)
                return

            members_in_vc = [m for m in voice_channel.members if m.id != self.owner_id]
            if not members_in_vc:
                await interaction.response.send_message("Нет других участников.", ephemeral=True)
                return

            select = Select(
                placeholder="Кому передать?",
                options=[disnake.SelectOption(label=m.display_name, value=str(m.id)) for m in members_in_vc[:25]]
            )

            async def select_callback(select_interaction: disnake.MessageInteraction):
                await select_interaction.response.defer()
                new_owner_id = int(select.values[0])
                new_owner = select_interaction.guild.get_member(new_owner_id)
                if new_owner:
                    session = self.cog.get_session(self.voice_channel_id)
                    if session:
                        session["owner_id"] = new_owner.id
                        self.owner_id = new_owner.id

                        embed = disnake.Embed(
                            title="👑 ЛИДЕРСТВО ПЕРЕДАНО",
                            description=f"{new_owner.mention} стал новым лидером!",
                            color=disnake.Color.gold()
                        )
                        text_channel = await self.cog.get_text_channel(self.voice_channel_id, voice_channel.guild)
                        if text_channel:
                            await text_channel.send(embed=embed)

                        await self.cog.update_leader_panel(voice_channel, new_owner)
                        await select_interaction.followup.send(f"👑 Передано {new_owner.display_name}!", ephemeral=True)
                    try:
                        await select_interaction.message.delete()
                    except:
                        pass

            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.response.send_message("Выберите нового лидера:", view=view, ephemeral=True)

        @disnake.ui.button(label="🔓 Разбанить", style=disnake.ButtonStyle.secondary, emoji="🔓")
        async def unban_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
            voice_channel = interaction.guild.get_channel(self.voice_channel_id)
            if not voice_channel:
                await interaction.response.send_message("Канал не найден!", ephemeral=True)
                return

            overwrites = voice_channel.overwrites
            banned_members = []
            for target, overwrite in overwrites.items():
                if isinstance(target, disnake.Member) and overwrite.connect is False:
                    if target.id != self.owner_id and not self.cog.is_moderator(target):
                        banned_members.append(target)

            if not banned_members:
                await interaction.response.send_message("Нет забаненных.", ephemeral=True)
                return

            select = Select(
                placeholder="Выберите кого разбанить...",
                options=[disnake.SelectOption(label=m.display_name, value=str(m.id)) for m in banned_members[:25]]
            )

            async def select_callback(select_interaction: disnake.MessageInteraction):
                await select_interaction.response.defer()
                target_id = int(select.values[0])
                target = select_interaction.guild.get_member(target_id)

                if not target:
                    await select_interaction.followup.send("Пользователь не найден!", ephemeral=True)
                    return

                success = await self.cog.unban_user(voice_channel, target, interaction.user)

                if success:
                    session = self.cog.get_session(self.voice_channel_id)
                    if session and target.id in session["banned_users"]:
                        session["banned_users"].remove(target.id)
                    await self.cog.update_leader_panel(voice_channel, interaction.user)
                    await select_interaction.followup.send(f"✅ {target.display_name} разбанен.", ephemeral=True)

                try:
                    await select_interaction.message.delete()
                except:
                    pass

            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.response.send_message("Выберите кого разбанить:", view=view, ephemeral=True)

    # --- Задача: Проверка статуса владельца ---
    @tasks.loop(seconds=CHECK_INTERVAL)
    async def check_owner_presence(self):
        for vc_id, session in list(self.active_sessions.items()):
            owner_id = session.get("owner_id")
            leave_time_val = session.get("leave_time")

            if not owner_id:
                continue

            voice_channel = self.bot.get_channel(vc_id)
            if not voice_channel:
                self.delete_session(vc_id)
                continue

            owner = voice_channel.guild.get_member(owner_id)

            is_owner_valid = False
            if owner and owner.voice and owner.voice.channel == voice_channel:
                is_owner_valid = True

            if not is_owner_valid:
                if leave_time_val is None:
                    session["leave_time"] = time.time()

                    embed = disnake.Embed(
                        title="⚠️ ЛИДЕР ПОКИНУЛ КАНАЛ",
                        description=f"Лидер покинул канал **{voice_channel.name}**",
                        color=disnake.Color.orange()
                    )
                    embed.add_field(name="⏰ Осталось", value="60 секунд", inline=False)

                    text_channel = await self.get_text_channel(vc_id, voice_channel.guild)
                    if text_channel:
                        await text_channel.send(embed=embed)

                elif time.time() - leave_time_val >= 60:
                    await self.clear_all_bans(voice_channel)
                    self.delete_session(vc_id)

                    old_panel = self.leader_panels.get(vc_id)
                    if old_panel:
                        text_channel = await self.get_text_channel(vc_id, voice_channel.guild)
                        if text_channel:
                            try:
                                msg = await text_channel.fetch_message(old_panel)
                                await msg.delete()
                            except:
                                pass
                        del self.leader_panels[vc_id]

                    await self.update_no_leader_panel(voice_channel)
            else:
                if leave_time_val is not None:
                    session["leave_time"] = None
                    await self.update_leader_panel(voice_channel, owner)

    # --- Событие: проверка входа в канал (ИСПРАВЛЕНО) ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member,
                                    before: disnake.VoiceState,
                                    after: disnake.VoiceState):
        # Проверяем, что пользователь ИМЕННО ЗАШЁЛ в канал
        # after.channel - это канал, в который пользователь зашёл (если зашёл)
        # before.channel - это канал, из которого пользователь вышел (если вышел)

        # Если пользователь ВЫШЕЛ из канала (after.channel is None) - игнорируем
        if after.channel is None:
            return

        # Если пользователь ПЕРЕМЕСТИЛСЯ из одного канала в другой - обрабатываем
        # Проверяем права доступа в канале, в который он зашёл
        overwrites = after.channel.overwrites
        if member in overwrites and overwrites[member].connect is False:
            await asyncio.sleep(0.5)
            await member.move_to(None, reason="Пользователь забанен в этом канале")

            text_channel = await self.get_text_channel(after.channel.id, after.channel.guild)
            if text_channel:
                embed = disnake.Embed(
                    title="⚠️ ДОСТУП ЗАПРЕЩЕН",
                    description=f"{member.mention} попытался зайти в канал {after.channel.mention}, но он в бане!",
                    color=disnake.Color.red()
                )
                await text_channel.send(embed=embed)

    # --- Задача: Отправка приветственных сообщений ---
    @tasks.loop(count=1)
    async def send_welcome_messages(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)

        for voice_id, info in self.voice_channels.items():
            voice_channel = self.bot.get_channel(voice_id)
            if voice_channel:
                session = self.get_session(voice_id)
                if not session or not session.get("owner_id"):
                    await self.update_no_leader_panel(voice_channel)
                else:
                    owner = voice_channel.guild.get_member(session["owner_id"])
                    if owner:
                        await self.update_leader_panel(voice_channel, owner)

    @check_owner_presence.before_loop
    async def before_check_owner(self):
        await self.bot.wait_until_ready()

    @send_welcome_messages.before_loop
    async def before_send_welcome(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(VoiceManager(bot))