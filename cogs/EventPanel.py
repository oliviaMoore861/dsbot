import disnake
from disnake.ext import commands
from disnake.ui import Button, View, Modal, TextInput, Select
from typing import Optional
import datetime
import asyncio


class EventPanel(commands.Cog):
    """Ког для управления ивентами"""

    def __init__(self, bot):
        self.bot = bot
        # ID роли, которая имеет право использовать команду
        self.event_manager_role_id = 1488807586512896141
        # ID категории для создания каналов
        self.category_id = 1489211112321843210
        # ID канала для логов мероприятий
        self.log_channel_id = 1488908365147930808
        # ID канала для уведомлений о завершении мероприятия
        self.completion_channel_id = 1486023952714432634
        # ID разрешенного канала для использования команды
        self.allowed_channel_id = 1488811577330368572
        # Хранилище активных мероприятий
        self.active_events = {}  # {voice_channel_id: {"text_channel_id": int, "owner_id": int, "banned_users": []}}
        # ID сообщения с панелью управления
        self.panel_message_id = None

    def has_event_manager_role(self, member: disnake.Member) -> bool:
        """Проверка наличия роли ивент-менеджера"""
        role = member.guild.get_role(self.event_manager_role_id)
        if not role:
            return False
        return role in member.roles

    async def check_channel(self, interaction: disnake.ApplicationCommandInteraction) -> bool:
        """Проверка, что команда вызвана в разрешенном канале"""
        if interaction.channel_id != self.allowed_channel_id:
            embed = disnake.Embed(
                title="❌ Неправильный канал",
                description=f"Пожалуйста, используйте эту команду только в <#{self.allowed_channel_id}>",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    # --- Модальное окно для создания мероприятия ---
    class CreateEventModal(Modal):
        def __init__(self, cog):
            # Создаем компоненты для модального окна
            components = [
                TextInput(
                    label="Название мероприятия",
                    placeholder="Введите название мероприятия...",
                    min_length=3,
                    max_length=100,
                    required=True,
                    custom_id="event_name"
                ),
                TextInput(
                    label="Описание мероприятия",
                    placeholder="Введите описание мероприятия...",
                    style=disnake.TextInputStyle.paragraph,
                    min_length=5,
                    max_length=500,
                    required=True,
                    custom_id="event_description"
                ),
                TextInput(
                    label="Лимит участников",
                    placeholder="Введите число (например: 10)",
                    min_length=1,
                    max_length=3,
                    required=True,
                    custom_id="user_limit"
                )
            ]
            super().__init__(title="📅 Создание мероприятия", components=components, timeout=600)
            self.cog = cog

        async def callback(self, interaction: disnake.ModalInteraction):
            # Проверяем, есть ли уже активное мероприятие
            if self.cog.active_events:
                await interaction.response.send_message(
                    "❌ Невозможно создать новое мероприятие!\n"
                    "Сначала завершите текущее активное мероприятие.",
                    ephemeral=True
                )
                return

            # Получаем данные из модального окна
            event_name = interaction.text_values["event_name"]
            event_description = interaction.text_values["event_description"]

            try:
                user_limit = int(interaction.text_values["user_limit"])
                if user_limit < 1:
                    user_limit = 0  # 0 означает безлимит
                elif user_limit > 99:
                    user_limit = 99
            except ValueError:
                await interaction.response.send_message(
                    "❌ Лимит участников должен быть числом!",
                    ephemeral=True
                )
                return

            # Получаем категорию
            category = interaction.guild.get_channel(self.cog.category_id)
            if not category:
                await interaction.response.send_message(
                    "❌ Категория для создания каналов не найдена!",
                    ephemeral=True
                )
                return

            # Создаем голосовой канал
            try:
                voice_channel = await interaction.guild.create_voice_channel(
                    name=f"🎤 {event_name}",
                    category=category,
                    user_limit=user_limit if user_limit > 0 else None,
                    reason=f"Мероприятие создано пользователем {interaction.user}"
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Ошибка при создании голосового канала: {e}",
                    ephemeral=True
                )
                return

            # Создаем текстовый канал
            try:
                text_channel = await interaction.guild.create_text_channel(
                    name=f"💬 {event_name}",
                    category=category,
                    reason=f"Мероприятие создано пользователем {interaction.user}"
                )

                # Устанавливаем права доступа для текстового канала
                await text_channel.set_permissions(interaction.guild.default_role, send_messages=False)
                await text_channel.set_permissions(interaction.user, send_messages=True, read_messages=True)

            except Exception as e:
                # Если не удалось создать текстовый канал, удаляем голосовой
                await voice_channel.delete()
                await interaction.response.send_message(
                    f"❌ Ошибка при создании текстового канала: {e}",
                    ephemeral=True
                )
                return

            # Сохраняем информацию о мероприятии
            self.cog.active_events[voice_channel.id] = {
                "text_channel_id": text_channel.id,
                "owner_id": interaction.user.id,
                "banned_users": [],
                "event_name": event_name,
                "event_description": event_description,
                "created_at": datetime.datetime.utcnow()
            }

            # Отправляем сообщение в лог-канал
            log_channel = interaction.guild.get_channel(self.cog.log_channel_id)
            if log_channel:
                embed = disnake.Embed(
                    title="🎉 НОВОЕ МЕРОПРИЯТИЕ @everyone!",
                    description=f"**{event_name}**",
                    color=disnake.Color.green(),
                    timestamp=datetime.datetime.utcnow()
                )
                embed.add_field(
                    name="📝 Описание",
                    value=event_description,
                    inline=False
                )
                embed.add_field(
                    name="👤 Организатор",
                    value=f"{interaction.user.mention}",
                    inline=True
                )
                embed.add_field(
                    name="🎙️ Голосовой канал",
                    value=voice_channel.mention,
                    inline=True
                )
                embed.add_field(
                    name="💬 Текстовый канал",
                    value=text_channel.mention,
                    inline=True
                )
                embed.add_field(
                    name="👥 Лимит участников",
                    value=f"{user_limit if user_limit > 0 else 'Безлимит'}",
                    inline=True
                )
                embed.set_footer(text="Присоединяйтесь к мероприятию!")

                await log_channel.send(embed=embed)

            # Отправляем сообщение в текстовый канал мероприятия
            await text_channel.send(
                f"🎉 **Мероприятие началось!**\n\n"
                f"**Название:** {event_name}\n"
                f"**Описание:** {event_description}\n"
                f"**Организатор:** {interaction.user.mention}\n"
                f"**Голосовой канал:** {voice_channel.mention}\n"
                f"**Лимит участников:** {user_limit if user_limit > 0 else 'Безлимит'}\n\n"
                f"Присоединяйтесь к голосовому каналу чтобы участвовать!"
            )

            await interaction.response.send_message(
                f"✅ Мероприятие **{event_name}** успешно создано!\n"
                f"Голосовой канал: {voice_channel.mention}\n"
                f"Текстовый канал: {text_channel.mention}",
                ephemeral=True
            )

    # --- Модальное окно для выгона участника ---
    class KickMemberModal(Modal):
        def __init__(self, cog, voice_channel, text_channel, owner_id):
            # Создаем компоненты для модального окна
            components = [
                TextInput(
                    label="ID участника",
                    placeholder="Введите ID пользователя...",
                    min_length=17,
                    max_length=20,
                    required=True,
                    custom_id="member_id"
                ),
                TextInput(
                    label="Причина (необязательно)",
                    placeholder="Введите причину выгона...",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    max_length=200,
                    custom_id="reason"
                )
            ]
            super().__init__(title="🚫 Выгнать участника", components=components, timeout=300)
            self.cog = cog
            self.voice_channel = voice_channel
            self.text_channel = text_channel
            self.owner_id = owner_id

        async def callback(self, interaction: disnake.ModalInteraction):
            # Проверяем, что пользователь является создателем мероприятия
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message(
                    "❌ Только создатель мероприятия может выгонять участников!",
                    ephemeral=True
                )
                return

            try:
                member_id = int(interaction.text_values["member_id"])
                member = interaction.guild.get_member(member_id)

                if not member:
                    await interaction.response.send_message(
                        "❌ Пользователь не найден на сервере!",
                        ephemeral=True
                    )
                    return

                # Проверяем, что не пытаемся выгнать создателя
                if member.id == self.owner_id:
                    await interaction.response.send_message(
                        "❌ Вы не можете выгнать самого себя!",
                        ephemeral=True
                    )
                    return

                # Проверяем, находится ли участник в голосовом канале
                if not member.voice or member.voice.channel != self.voice_channel:
                    await interaction.response.send_message(
                        f"❌ {member.mention} не находится в голосовом канале {self.voice_channel.mention}!",
                        ephemeral=True
                    )
                    return

                # Добавляем в список забаненных
                event_data = self.cog.active_events.get(self.voice_channel.id)
                if event_data and member.id not in event_data["banned_users"]:
                    event_data["banned_users"].append(member.id)

                # Выгоняем из голосового канала
                await member.move_to(None, reason=f"Выгнан организатором {interaction.user}")

                # Запрещаем писать в текстовый канал
                await self.text_channel.set_permissions(
                    member,
                    send_messages=False,
                    read_messages=True
                )

                reason_text = f"\n**Причина:** {interaction.text_values['reason']}" if interaction.text_values.get(
                    'reason') else ""

                # Отправляем уведомления
                await self.text_channel.send(
                    f"🚫 {member.mention} был выгнан из мероприятия организатором {interaction.user.mention}!{reason_text}"
                )

                try:
                    await member.send(
                        f"⚠️ Вы были выгнаны из мероприятия **{event_data['event_name']}** организатором {interaction.user.name}.\n"
                        f"Вы больше не можете заходить в голосовой канал и писать в чат мероприятия.{reason_text}"
                    )
                except:
                    pass

                await interaction.response.send_message(
                    f"✅ {member.mention} был выгнан из мероприятия!",
                    ephemeral=True
                )

            except ValueError:
                await interaction.response.send_message(
                    "❌ Неверный формат ID пользователя!",
                    ephemeral=True
                )

    # --- Панель управления ивентами ---
    class EventPanelView(View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @disnake.ui.button(label="📅 Создать мероприятие", style=disnake.ButtonStyle.success, emoji="📅")
        async def create_event(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
            """Создать новое мероприятие"""
            if not self.cog.has_event_manager_role(interaction.user):
                await interaction.response.send_message(
                    "❌ У вас нет прав на создание мероприятий!",
                    ephemeral=True
                )
                return

            # Проверяем, есть ли уже активное мероприятие
            if self.cog.active_events:
                await interaction.response.send_message(
                    "❌ Невозможно создать новое мероприятие!\n"
                    "Сначала завершите текущее активное мероприятие.",
                    ephemeral=True
                )
                return

            modal = self.cog.CreateEventModal(self.cog)
            await interaction.response.send_modal(modal)

        @disnake.ui.button(label="✅ Завершить мероприятие", style=disnake.ButtonStyle.danger, emoji="✅")
        async def end_event(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
            """Завершить мероприятие"""
            if not self.cog.has_event_manager_role(interaction.user):
                await interaction.response.send_message(
                    "❌ У вас нет прав на завершение мероприятий!",
                    ephemeral=True
                )
                return

            # Получаем все активные мероприятия
            if not self.cog.active_events:
                await interaction.response.send_message(
                    "❌ Нет активных мероприятий для завершения!",
                    ephemeral=True
                )
                return

            # Создаем выбор мероприятия
            options = []
            for vc_id, event_data in self.cog.active_events.items():
                voice_channel = interaction.guild.get_channel(vc_id)
                if voice_channel:
                    options.append(
                        disnake.SelectOption(
                            label=event_data['event_name'],
                            description=f"Голосовой канал: {voice_channel.name}",
                            value=str(vc_id)
                        )
                    )

            if not options:
                await interaction.response.send_message(
                    "❌ Нет активных мероприятий для завершения!",
                    ephemeral=True
                )
                return

            select = Select(
                placeholder="Выберите мероприятие для завершения...",
                options=options[:25]
            )

            async def select_callback(select_interaction: disnake.MessageInteraction):
                await select_interaction.response.defer()

                vc_id = int(select.values[0])
                event_data = self.cog.active_events.get(vc_id)

                if not event_data:
                    await select_interaction.followup.send(
                        "❌ Мероприятие не найдено!",
                        ephemeral=True
                    )
                    return

                # Проверяем, что пользователь является создателем мероприятия
                if select_interaction.user.id != event_data["owner_id"]:
                    await select_interaction.followup.send(
                        "❌ Только создатель мероприятия может его завершить!",
                        ephemeral=True
                    )
                    return

                voice_channel = interaction.guild.get_channel(vc_id)
                text_channel = interaction.guild.get_channel(event_data["text_channel_id"])

                # Сохраняем информацию о мероприятии для уведомления
                event_name = event_data['event_name']
                event_description = event_data['event_description']
                organizer = interaction.guild.get_member(event_data['owner_id'])
                created_at = event_data['created_at']

                # Удаляем каналы
                try:
                    if voice_channel:
                        await voice_channel.delete(reason=f"Мероприятие завершено {interaction.user}")
                    if text_channel:
                        await text_channel.delete(reason=f"Мероприятие завершено {interaction.user}")

                    # Удаляем из активных
                    del self.cog.active_events[vc_id]

                    # Отправляем сообщение в канал завершения
                    completion_channel = interaction.guild.get_channel(self.cog.completion_channel_id)
                    if completion_channel:
                        embed = disnake.Embed(
                            title="✅ МЕРОПРИЯТИЕ ЗАВЕРШЕНО",
                            description=f"**{event_name}**",
                            color=disnake.Color.orange(),
                            timestamp=datetime.datetime.utcnow()
                        )
                        embed.add_field(
                            name="📝 Описание",
                            value=event_description,
                            inline=False
                        )
                        embed.add_field(
                            name="👤 Организатор",
                            value=organizer.mention if organizer else "Неизвестен",
                            inline=True
                        )
                        embed.add_field(
                            name="👑 Завершил",
                            value=interaction.user.mention,
                            inline=True
                        )
                        embed.add_field(
                            name="📅 Дата создания",
                            value=created_at.strftime("%d.%m.%Y %H:%M"),
                            inline=True
                        )
                        embed.add_field(
                            name="📊 Продолжительность",
                            value=f"{(datetime.datetime.utcnow() - created_at).seconds // 60} минут",
                            inline=True
                        )
                        embed.set_footer(text="Мероприятие успешно завершено")

                        await completion_channel.send(embed=embed)

                    # Отправляем лог в лог-канал
                    log_channel = interaction.guild.get_channel(self.cog.log_channel_id)
                    if log_channel:
                        embed = disnake.Embed(
                            title="✅ Мероприятие завершено",
                            description=f"**{event_name}**",
                            color=disnake.Color.orange(),
                            timestamp=datetime.datetime.utcnow()
                        )
                        embed.add_field(
                            name="👤 Завершил",
                            value=interaction.user.mention,
                            inline=True
                        )
                        await log_channel.send(embed=embed)

                    await select_interaction.followup.send(
                        f"✅ Мероприятие **{event_name}** успешно завершено и каналы удалены!",
                        ephemeral=True
                    )

                except Exception as e:
                    await select_interaction.followup.send(
                        f"❌ Ошибка при завершении мероприятия: {e}",
                        ephemeral=True
                    )

            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.response.send_message(
                "Выберите мероприятие для завершения:",
                view=view,
                ephemeral=True
            )

        @disnake.ui.button(label="🚫 Выгнать участника", style=disnake.ButtonStyle.secondary, emoji="🚫")
        async def kick_member(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
            """Выгнать участника из мероприятия"""
            if not self.cog.has_event_manager_role(interaction.user):
                await interaction.response.send_message(
                    "❌ У вас нет прав на выгон участников!",
                    ephemeral=True
                )
                return

            # Получаем все активные мероприятия
            if not self.cog.active_events:
                await interaction.response.send_message(
                    "❌ Нет активных мероприятий!",
                    ephemeral=True
                )
                return

            # Создаем выбор мероприятия
            options = []
            for vc_id, event_data in self.cog.active_events.items():
                voice_channel = interaction.guild.get_channel(vc_id)
                if voice_channel:
                    options.append(
                        disnake.SelectOption(
                            label=event_data['event_name'],
                            description=f"Голосовой канал: {voice_channel.name}",
                            value=str(vc_id)
                        )
                    )

            select = Select(
                placeholder="Выберите мероприятие...",
                options=options[:25]
            )

            async def select_callback(select_interaction: disnake.MessageInteraction):
                vc_id = int(select.values[0])
                event_data = self.cog.active_events.get(vc_id)

                if not event_data:
                    await select_interaction.response.send_message(
                        "❌ Мероприятие не найдено!",
                        ephemeral=True
                    )
                    return

                voice_channel = interaction.guild.get_channel(vc_id)
                text_channel = interaction.guild.get_channel(event_data["text_channel_id"])

                if not voice_channel or not text_channel:
                    await select_interaction.response.send_message(
                        "❌ Каналы мероприятия не найдены!",
                        ephemeral=True
                    )
                    return

                modal = self.cog.KickMemberModal(self.cog, voice_channel, text_channel, event_data["owner_id"])
                await select_interaction.response.send_modal(modal)

            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.response.send_message(
                "Выберите мероприятие:",
                view=view,
                ephemeral=True
            )

    # --- Команда для создания панели ивентов ---
    @commands.slash_command(name="event_panel", description="Создать панель управления мероприятиями")
    async def event_panel(self, interaction: disnake.ApplicationCommandInteraction):
        """Создать панель управления мероприятиями"""

        # Проверяем, что команда вызвана в разрешенном канале
        if not await self.check_channel(interaction):
            return

        # Проверяем наличие роли ивент-менеджера
        if not self.has_event_manager_role(interaction.user):
            embed = disnake.Embed(
                title="❌ Ошибка доступа",
                description="У вас нет прав на использование этой команды!\n"
                            "Требуется специальная роль ивент-менеджера.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Создаем панель
        embed = disnake.Embed(
            title="🎉 Панель управления мероприятиями",
            description="Добро пожаловать в панель управления мероприятиями!\n\n"
                        "Здесь вы можете создавать, управлять и завершать мероприятия.\n\n"
                        f"**Активных мероприятий:** {len(self.active_events)}/1",
            color=disnake.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(
            name="📅 Создать мероприятие",
            value="Создает новое мероприятие с голосовым и текстовым каналом.\n"
                  "Вы сможете указать название, описание и лимит участников.\n"
                  "**Можно создать только 1 мероприятие одновременно!**",
            inline=False
        )

        embed.add_field(
            name="✅ Завершить мероприятие",
            value="Завершает выбранное мероприятие и удаляет все связанные каналы.\n"
                  "**Только создатель мероприятия может его завершить!**\n"
                  "Уведомление о завершении отправляется в специальный канал.",
            inline=False
        )

        embed.add_field(
            name="🚫 Выгнать участника",
            value="Выгоняет участника из голосового канала и запрещает ему писать в текстовый чат мероприятия.\n"
                  "**Только создатель мероприятия может выгонять участников!**",
            inline=False
        )

        # Если есть активное мероприятие, показываем его
        if self.active_events:
            for vc_id, event_data in self.active_events.items():
                voice_channel = interaction.guild.get_channel(vc_id)
                text_channel = interaction.guild.get_channel(event_data["text_channel_id"])
                embed.add_field(
                    name="📌 Текущее мероприятие",
                    value=f"**Название:** {event_data['event_name']}\n"
                          f"**Голосовой канал:** {voice_channel.mention if voice_channel else 'Не найден'}\n"
                          f"**Текстовый канал:** {text_channel.mention if text_channel else 'Не найден'}\n"
                          f"**Организатор:** <@{event_data['owner_id']}>",
                    inline=False
                )

        embed.set_footer(text="Используйте кнопки ниже для управления мероприятиями")

        view = self.EventPanelView(self)

        # Сохраняем ID сообщения панели
        message = await interaction.response.send_message(embed=embed, view=view)
        if isinstance(message, disnake.Message):
            self.panel_message_id = message.id


def setup(bot):
    """Загрузка кога"""
    bot.add_cog(EventPanel(bot))