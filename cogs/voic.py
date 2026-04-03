import disnake
from disnake.ext import commands, tasks
from disnake.ui import View, Modal, Button, TextInput, Select
from disnake import ButtonStyle, SelectOption

# ---------- КОНФИГУРАЦИЯ ----------
GUILD_ID = 1486013024048382153  # ID вашего сервера
TRIGGER_VOICE_CHANNEL_ID = 1489241977982550156
CATEGORY_ID = 1489238606714245251
CONTROL_TEXT_CHANNEL_ID = 1489242103841030234


class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_voice_channels = {}
        self.update_control_panels.start()

    def cog_unload(self):
        self.update_control_panels.cancel()

    @tasks.loop(minutes=5)
    async def update_control_panels(self):
        control_channel = self.bot.get_channel(CONTROL_TEXT_CHANNEL_ID)
        if not control_channel:
            return

        for owner_id in list(self.user_voice_channels.keys()):
            vc_id = self.user_voice_channels.get(owner_id)
            if not vc_id or not self.bot.get_channel(vc_id):
                continue

            async for msg in control_channel.history(limit=50):
                if msg.author == self.bot.user and msg.embeds:
                    embed = msg.embeds[0]
                    if embed.footer and str(owner_id) in embed.footer.text:
                        await msg.delete()
                        break

            embed = disnake.Embed(
                title="🎙️ Управление вашим голосовым каналом",
                description="Используйте кнопки ниже для управления вашим каналом.",
                color=disnake.Color.blurple()
            )
            embed.set_footer(text=f"owner_{owner_id}")

            view = ControlPanelView(owner_id, self)
            await control_channel.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState,
                                    after: disnake.VoiceState):
        if member.bot:
            return

        guild = member.guild
        if guild.id != GUILD_ID:
            return

        # СОЗДАНИЕ КАНАЛА
        if after.channel and after.channel.id == TRIGGER_VOICE_CHANNEL_ID:
            if member.id in self.user_voice_channels:
                await member.move_to(None)
                try:
                    await member.send("❌ У вас уже есть активный временный канал.")
                except:
                    pass
                return

            category = guild.get_channel(CATEGORY_ID)
            if not category:
                return

            vc = await guild.create_voice_channel(
                name=f"{member.display_name}",
                category=category,
                user_limit=0
            )
            self.user_voice_channels[member.id] = vc.id
            await member.move_to(vc)

            control_channel = self.bot.get_channel(CONTROL_TEXT_CHANNEL_ID)
            if control_channel:
                embed = disnake.Embed(
                    title="🎙️ Управление вашим голосовым каналом",
                    description="Используйте кнопки ниже для управления вашим каналом.",
                    color=disnake.Color.blurple()
                )
                embed.set_footer(text=f"owner_{member.id}")

                view = ControlPanelView(member.id, self)
                await control_channel.send(embed=embed, view=view)

        # УДАЛЕНИЕ КАНАЛА
        if before.channel and before.channel.id in self.user_voice_channels.values():
            vc = before.channel
            if len(vc.members) == 0:
                owner_id = None
                for uid, vid in self.user_voice_channels.items():
                    if vid == vc.id:
                        owner_id = uid
                        break

                if owner_id:
                    del self.user_voice_channels[owner_id]
                    await vc.delete()

                    control_channel = self.bot.get_channel(CONTROL_TEXT_CHANNEL_ID)
                    if control_channel:
                        async for msg in control_channel.history(limit=50):
                            if msg.author == self.bot.user and msg.embeds:
                                if msg.embeds[0].footer and str(owner_id) in msg.embeds[0].footer.text:
                                    await msg.delete()
                                    break


class ControlPanelView(View):
    def __init__(self, owner_id: int, cog: Voice):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.cog = cog

        # Основные кнопки
        self.add_item(Button(style=ButtonStyle.secondary, label="✏️ Название", custom_id=f"name_{owner_id}"))
        self.add_item(Button(style=ButtonStyle.danger, label="🚫 Забанить", custom_id=f"ban_{owner_id}"))
        self.add_item(Button(style=ButtonStyle.danger, label="👢 Кикнуть", custom_id=f"kick_{owner_id}"))
        self.add_item(Button(style=ButtonStyle.primary, label="🔢 Лимит", custom_id=f"limit_{owner_id}"))
        self.add_item(Button(style=ButtonStyle.danger, label="🔒 Закрыть для всех", custom_id=f"lock_{owner_id}"))
        self.add_item(Button(style=ButtonStyle.success, label="🔓 Открыть для всех", custom_id=f"unlock_{owner_id}"))
        self.add_item(Button(style=ButtonStyle.secondary, label="🎤 Замутить", custom_id=f"mute_{owner_id}"))
        self.add_item(Button(style=ButtonStyle.secondary, label="🔊 Размутить", custom_id=f"unmute_{owner_id}"))
        self.add_item(Button(style=ButtonStyle.secondary, label="🔇 Выкл. звук", custom_id=f"deafen_{owner_id}"))
        self.add_item(Button(style=ButtonStyle.secondary, label="🔊 Вкл. звук", custom_id=f"undeafen_{owner_id}"))
        self.add_item(Button(style=ButtonStyle.success, label="🔓 Разбанить", custom_id=f"unban_{owner_id}"))

    async def callback_handler(self, inter: disnake.MessageInteraction, action: str):
        """Обработчик всех кнопок - ТОЛЬКО ДЛЯ ВЛАДЕЛЬЦА"""

        # ⚠️ ГЛАВНАЯ ПРОВЕРКА: только владелец может управлять
        if inter.user.id != self.owner_id:
            await inter.response.send_message(
                "❌ Эта панель управления не для вас! Только владелец канала может управлять.", ephemeral=True)
            return

        vc_id = self.cog.user_voice_channels.get(self.owner_id)
        vc = inter.guild.get_channel(vc_id)

        if not vc:
            await inter.response.send_message("❌ Ваш голосовой канал больше не существует.", ephemeral=True)
            return

        # Действия без выбора пользователя
        if action == "name":
            await inter.response.send_modal(ChangeNameModal(self.owner_id, self.cog))

        elif action == "limit":
            await inter.response.send_modal(LimitModal(self.owner_id, self.cog))

        elif action == "lock":
            overwrite = vc.overwrites_for(inter.guild.default_role)
            overwrite.connect = False
            await vc.set_permissions(inter.guild.default_role, overwrite=overwrite)
            await inter.response.send_message("🔒 Канал закрыт для всех.", ephemeral=True)

        elif action == "unlock":
            overwrite = vc.overwrites_for(inter.guild.default_role)
            overwrite.connect = None
            await vc.set_permissions(inter.guild.default_role, overwrite=overwrite)
            await inter.response.send_message("🔓 Канал открыт для всех.", ephemeral=True)

        # Действия с выбором пользователя из голосового канала
        elif action == "kick":
            users = [m for m in vc.members if m.id != self.owner_id]
            if not users:
                await inter.response.send_message("❌ В вашем канале нет других пользователей.", ephemeral=True)
                return
            view = UserSelectView(self.owner_id, self.cog, "kick", users)
            await inter.response.send_message("👢 Выберите пользователя для кика:", view=view, ephemeral=True)

        elif action == "ban":
            users = [m for m in vc.members if m.id != self.owner_id]
            if not users:
                await inter.response.send_message("❌ В вашем канале нет других пользователей.", ephemeral=True)
                return
            view = UserSelectView(self.owner_id, self.cog, "ban", users)
            await inter.response.send_message("🚫 Выберите пользователя для бана:", view=view, ephemeral=True)

        elif action == "mute":
            users = [m for m in vc.members if m.id != self.owner_id]
            if not users:
                await inter.response.send_message("❌ В вашем канале нет других пользователей.", ephemeral=True)
                return
            view = UserSelectView(self.owner_id, self.cog, "mute", users)
            await inter.response.send_message("🎤 Выберите пользователя для мута:", view=view, ephemeral=True)

        elif action == "unmute":
            users = [m for m in vc.members if m.id != self.owner_id]
            if not users:
                await inter.response.send_message("❌ В вашем канале нет других пользователей.", ephemeral=True)
                return
            view = UserSelectView(self.owner_id, self.cog, "unmute", users)
            await inter.response.send_message("🔊 Выберите пользователя для размута:", view=view, ephemeral=True)

        elif action == "deafen":
            users = [m for m in vc.members if m.id != self.owner_id]
            if not users:
                await inter.response.send_message("❌ В вашем канале нет других пользователей.", ephemeral=True)
                return
            view = UserSelectView(self.owner_id, self.cog, "deafen", users)
            await inter.response.send_message("🔇 Выберите пользователя для выключения звука:", view=view,
                                              ephemeral=True)

        elif action == "undeafen":
            users = [m for m in vc.members if m.id != self.owner_id]
            if not users:
                await inter.response.send_message("❌ В вашем канале нет других пользователей.", ephemeral=True)
                return
            view = UserSelectView(self.owner_id, self.cog, "undeafen", users)
            await inter.response.send_message("🔊 Выберите пользователя для включения звука:", view=view, ephemeral=True)

        # Действия с выбором забаненных пользователей
        elif action == "unban":
            banned_users = []
            for overwrite in vc.overwrites:
                if isinstance(overwrite, disnake.Member):
                    perms = vc.overwrites_for(overwrite)
                    if perms.connect is False:
                        banned_users.append(overwrite)

            if not banned_users:
                await inter.response.send_message("❌ В вашем канале нет забаненных пользователей.", ephemeral=True)
                return
            view = UserSelectView(self.owner_id, self.cog, "unban", banned_users)
            await inter.response.send_message("🔓 Выберите пользователя для разбана:", view=view, ephemeral=True)


class UserSelectView(View):
    """View с выпадающим меню для выбора пользователя"""

    def __init__(self, owner_id: int, cog: Voice, action: str, users: list):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.cog = cog
        self.action = action

        # Создаем выпадающее меню
        options = []
        for user in users[:25]:  # Максимум 25 опций
            options.append(SelectOption(
                label=user.display_name[:100],  # Ограничиваем длину
                value=str(user.id),
                description=f"ID: {user.id}"[:100]  # Ограничиваем длину
            ))

        if options:  # Проверяем, что есть опции
            select = Select(
                placeholder=f"Выберите пользователя для {self.get_action_name()}",
                options=options,
                custom_id=f"user_select_{action}"
            )
            select.callback = self.select_callback
            self.add_item(select)

    def get_action_name(self):
        names = {
            "ban": "бана",
            "unban": "разбана",
            "kick": "кика",
            "mute": "мута",
            "unmute": "размута",
            "deafen": "выключения звука",
            "undeafen": "включения звука"
        }
        return names.get(self.action, "действия")

    async def select_callback(self, inter: disnake.MessageInteraction):
        # ⚠️ ПРОВЕРКА: только владелец может выбирать пользователей
        if inter.user.id != self.owner_id:
            await inter.response.send_message("❌ Это меню не для вас! Только владелец канала может управлять.",
                                              ephemeral=True)
            return

        user_id = int(inter.values[0])
        target = inter.guild.get_member(user_id)

        if not target:
            await inter.response.send_message("❌ Пользователь не найден.", ephemeral=True)
            return

        vc_id = self.cog.user_voice_channels.get(self.owner_id)
        vc = inter.guild.get_channel(vc_id)

        if not vc:
            await inter.response.send_message("❌ Канал не найден.", ephemeral=True)
            return

        # Выполняем действие
        if self.action == "ban":
            overwrite = vc.overwrites_for(target)
            overwrite.connect = False
            await vc.set_permissions(target, overwrite=overwrite)
            await inter.response.send_message(f"🚫 Пользователь {target.mention} забанен в вашем канале.",
                                              ephemeral=True)

            log_channel = self.cog.bot.get_channel(CONTROL_TEXT_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"🚫 **{inter.user.display_name}** забанил {target.mention} в канале `{vc.name}`")

        elif self.action == "unban":
            await vc.set_permissions(target, overwrite=None)
            await inter.response.send_message(f"🔓 Пользователь {target.mention} разбанен в вашем канале.",
                                              ephemeral=True)

            log_channel = self.cog.bot.get_channel(CONTROL_TEXT_CHANNEL_ID)
            if log_channel:
                await log_channel.send(
                    f"🔓 **{inter.user.display_name}** разбанил {target.mention} в канале `{vc.name}`")

        elif self.action == "kick":
            if target in vc.members:
                await target.move_to(None)
                await inter.response.send_message(f"👢 Пользователь {target.mention} кикнут из вашего канала.",
                                                  ephemeral=True)

                log_channel = self.cog.bot.get_channel(CONTROL_TEXT_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(
                        f"👢 **{inter.user.display_name}** кикнул {target.mention} из канала `{vc.name}`")
            else:
                await inter.response.send_message(f"❌ Пользователь {target.mention} не в вашем канале.", ephemeral=True)

        elif self.action == "mute":
            if target in vc.members:
                await target.edit(mute=True)
                await inter.response.send_message(f"🔇 Пользователь {target.mention} замучен в вашем канале.",
                                                  ephemeral=True)

                log_channel = self.cog.bot.get_channel(CONTROL_TEXT_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(
                        f"🔇 **{inter.user.display_name}** замутил {target.mention} в канале `{vc.name}`")
            else:
                await inter.response.send_message(f"❌ Пользователь {target.mention} не в вашем канале.", ephemeral=True)

        elif self.action == "unmute":
            if target in vc.members:
                await target.edit(mute=False)
                await inter.response.send_message(f"🔊 Пользователь {target.mention} размучен в вашем канале.",
                                                  ephemeral=True)

                log_channel = self.cog.bot.get_channel(CONTROL_TEXT_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(
                        f"🔊 **{inter.user.display_name}** размутил {target.mention} в канале `{vc.name}`")
            else:
                await inter.response.send_message(f"❌ Пользователь {target.mention} не в вашем канале.", ephemeral=True)

        elif self.action == "deafen":
            if target in vc.members:
                await target.edit(deafen=True)
                await inter.response.send_message(f"🔇 Пользователю {target.mention} выключен звук.", ephemeral=True)

                log_channel = self.cog.bot.get_channel(CONTROL_TEXT_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(
                        f"🔇 **{inter.user.display_name}** выключил звук {target.mention} в канале `{vc.name}`")
            else:
                await inter.response.send_message(f"❌ Пользователь {target.mention} не в вашем канале.", ephemeral=True)

        elif self.action == "undeafen":
            if target in vc.members:
                await target.edit(deafen=False)
                await inter.response.send_message(f"🔊 Пользователю {target.mention} включен звук.", ephemeral=True)

                log_channel = self.cog.bot.get_channel(CONTROL_TEXT_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(
                        f"🔊 **{inter.user.display_name}** включил звук {target.mention} в канале `{vc.name}`")
            else:
                await inter.response.send_message(f"❌ Пользователь {target.mention} не в вашем канале.", ephemeral=True)

        # Удаляем сообщение с выбором через 5 секунд
        await inter.message.delete(delay=5)


# ---------- МОДАЛЬНЫЕ ОКНА ----------
class ChangeNameModal(Modal):
    def __init__(self, owner_id: int, cog: Voice):
        self.owner_id = owner_id
        self.cog = cog
        super().__init__(
            title="Изменить название канала",
            components=[
                TextInput(
                    label="Новое название",
                    placeholder="Введите новое название для канала...",
                    custom_id="new_name",
                    max_length=100
                )
            ]
        )

    async def callback(self, inter: disnake.ModalInteraction):
        # Проверка на владельца
        if inter.user.id != self.owner_id:
            await inter.response.send_message("❌ Это окно не для вас!", ephemeral=True)
            return

        new_name = inter.text_values["new_name"]
        vc_id = self.cog.user_voice_channels.get(self.owner_id)
        vc = inter.guild.get_channel(vc_id)

        if vc:
            await vc.edit(name=new_name)
            await inter.response.send_message(f"✅ Название изменено на **{new_name}**", ephemeral=True)
        else:
            await inter.response.send_message("❌ Канал не найден.", ephemeral=True)


class LimitModal(Modal):
    def __init__(self, owner_id: int, cog: Voice):
        self.owner_id = owner_id
        self.cog = cog
        super().__init__(
            title="Лимит участников",
            components=[
                TextInput(
                    label="Лимит (0-99)",
                    placeholder="Введите число от 0 до 99",
                    custom_id="limit",
                    required=True
                )
            ]
        )

    async def callback(self, inter: disnake.ModalInteraction):
        # Проверка на владельца
        if inter.user.id != self.owner_id:
            await inter.response.send_message("❌ Это окно не для вас!", ephemeral=True)
            return

        limit = inter.text_values["limit"]
        vc_id = self.cog.user_voice_channels.get(self.owner_id)
        vc = inter.guild.get_channel(vc_id)

        if vc:
            try:
                new_limit = int(limit)
                if 0 <= new_limit <= 99:
                    await vc.edit(user_limit=new_limit)
                    await inter.response.send_message(f"✅ Лимит установлен на **{new_limit}**", ephemeral=True)
                else:
                    await inter.response.send_message("❌ Лимит должен быть от 0 до 99", ephemeral=True)
            except:
                await inter.response.send_message("❌ Введите корректное число", ephemeral=True)


def setup(bot):
    if not bot.get_cog("Voice"):
        bot.add_cog(Voice(bot))
        print("✅ Voice cog загружен")