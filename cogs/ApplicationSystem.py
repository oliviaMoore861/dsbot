import disnake
from disnake.ext import commands, tasks
from typing import Optional
import datetime
import asyncio

# ========== НАСТРОЙКИ ==========
CHANNEL_ID = 1489235492213100605  # ID канала для отправки
INTERVAL_MINUTES = 5  # Интервал в минутах


# =================================


class ApplicationSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.applications_channel_id = 1488203458329968730  # ID канала для заявок
        self.vacancy_channel_id = CHANNEL_ID  # ID канала для вакансий
        self.last_message_id = None  # ID последнего отправленного сообщения
        self.auto_vacancy.start()  # Запускаем автоматическую отправку

    def cog_unload(self):
        """Остановка задачи при выгрузке кога"""
        self.auto_vacancy.cancel()

    async def send_vacancy_message(self):
        """Отправляет сообщение с вакансиями"""
        channel = self.bot.get_channel(self.vacancy_channel_id)

        if channel is None:
            print(f"❌ Канал с ID {self.vacancy_channel_id} не найден!")
            return

        # Удаляем предыдущее сообщение, если оно есть
        if self.last_message_id:
            try:
                old_message = await channel.fetch_message(self.last_message_id)
                await old_message.delete()
                print(f"🗑️ Удалено старое сообщение: {self.last_message_id}")
            except:
                print(f"⚠️ Не удалось удалить сообщение {self.last_message_id}")

        # Создаем embed с вакансиями
        embed = disnake.Embed(
            title="🌟 ВАКАНСИИ! 🌟",
            description="У нас ведется набор в персонал и есть такие должности!",
            color=disnake.Color.gold(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(
            name="🛡️ **Модератор**",
            value="Человек который следит за порядком и поддерживает правила сервера",
            inline=False
        )
        embed.add_field(
            name="📋 **Ивентер**",
            value="Человек который проводит интересные ивенты",
            inline=False
        )
        embed.add_field(
            name="📰 **Новостимейкер**",
            value="Человек который пишет новости по игре Brawl Stars",
            inline=False
        )

        embed.set_footer(
            text=f"Подавайте заявку ниже| Всех ждем")

        # Создаем селект-меню для выбора должности
        class RoleSelectView(disnake.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=None)
                self.cog = cog

                select = disnake.ui.Select(
                    placeholder="Выберите должность...",
                    options=[
                        disnake.SelectOption(
                            label="Модератор",
                            description="Модератор - следит за порядком",
                            emoji="🛡️",
                            value="moderator"
                        ),
                        disnake.SelectOption(
                            label="Ивентер",
                            description="Ивентер - проводит мероприятия",
                            emoji="📋",
                            value="eventer"
                        ),
                        disnake.SelectOption(
                            label="Новостимейкер",
                            description="Новостимейкер - пишет новости",
                            emoji="📰",
                            value="newsmaker"
                        )
                    ],
                    custom_id="role_select"
                )
                select.callback = self.role_select_callback
                self.add_item(select)

            async def role_select_callback(self, inter: disnake.MessageInteraction):
                """Обработка выбора должности"""
                selected_role = inter.values[0]

                role_names = {
                    "moderator": "Модератор",
                    "eventer": "Ивентер",
                    "newsmaker": "Новостимейкер"
                }

                role_name = role_names[selected_role]

                modal = ApplicationModal(self.cog, role_name)
                await inter.response.send_modal(modal)

        view = RoleSelectView(self)

        # Отправляем новое сообщение
        message = await channel.send(embed=embed, view=view)
        self.last_message_id = message.id
        print(f"✅ Отправлено новое сообщение в канал {channel.name} (ID: {message.id})")

    @tasks.loop(minutes=INTERVAL_MINUTES)
    async def auto_vacancy(self):
        """Автоматическая отправка вакансий каждые 5 минут"""
        await self.send_vacancy_message()

    @auto_vacancy.before_loop
    async def before_auto_vacancy(self):
        """Ожидание готовности бота перед запуском задачи"""
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)  # Ждём 10 секунд после запуска
        # Отправляем первое сообщение при запуске
        await self.send_vacancy_message()

    # Команда для ручной отправки (для администраторов)
    @commands.slash_command(name="send_vacancy", description="Отправить сообщение с вакансиями вручную")
    @commands.has_permissions(administrator=True)
    async def send_vacancy(self, inter: disnake.ApplicationCommandInteraction):
        """Вручную отправить сообщение с вакансиями"""
        await inter.response.defer(ephemeral=True)
        await self.send_vacancy_message()
        await inter.followup.send("✅ Сообщение с вакансиями отправлено!", ephemeral=True)

    # Команда для очистки последнего сообщения
    @commands.slash_command(name="clear_vacancy", description="Удалить последнее сообщение с вакансиями")
    @commands.has_permissions(administrator=True)
    async def clear_vacancy(self, inter: disnake.ApplicationCommandInteraction):
        """Удалить последнее сообщение с вакансиями"""
        if self.last_message_id:
            channel = self.bot.get_channel(self.vacancy_channel_id)
            if channel:
                try:
                    msg = await channel.fetch_message(self.last_message_id)
                    await msg.delete()
                    self.last_message_id = None
                    await inter.response.send_message("✅ Последнее сообщение удалено!", ephemeral=True)
                except:
                    await inter.response.send_message("❌ Не удалось удалить сообщение!", ephemeral=True)
            else:
                await inter.response.send_message("❌ Канал не найден!", ephemeral=True)
        else:
            await inter.response.send_message("❌ Нет сохраненного сообщения для удаления!", ephemeral=True)

    async def send_application_to_channel(self, guild: disnake.Guild, user: disnake.User, role: str, answers: dict):
        """Отправить заявку в указанный канал"""

        channel = self.bot.get_channel(self.applications_channel_id)
        if not channel:
            channel = await self.bot.fetch_channel(self.applications_channel_id)

        embed = disnake.Embed(
            title=f"📝 Новая заявка на должность {role}",
            color=disnake.Color.gold(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="👤 Пользователь", value=f"{user.name}#{user.discriminator}", inline=True)
        embed.add_field(name="🆔 ID", value=user.id, inline=True)
        embed.add_field(name="📌 Должность", value=role, inline=True)
        embed.add_field(name="📝 Имя", value=answers['name'], inline=False)
        embed.add_field(name="🎂 Возраст", value=answers['age'], inline=True)
        embed.add_field(name="⏰ Время серверу", value=answers['time'], inline=True)
        embed.add_field(name="⭐ Знание правил", value=f"{answers['rules_knowledge']}/10", inline=True)
        embed.add_field(name="📖 О себе", value=answers['about'][:1024], inline=False)

        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"ID: {user.id}")

        class ApplicationView(disnake.ui.View):
            def __init__(self, cog, user_id: int, role: str, user_name: str):
                super().__init__(timeout=None)
                self.cog = cog
                self.user_id = user_id
                self.role = role
                self.user_name = user_name

            @disnake.ui.button(label="✅", style=disnake.ButtonStyle.green, custom_id="approve_button")
            async def approve_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                if not inter.user.guild_permissions.ban_members:
                    await inter.response.send_message("❌ У вас нет прав для этого действия!", ephemeral=True)
                    return

                user = await self.cog.bot.fetch_user(self.user_id)

                try:
                    dm_embed = disnake.Embed(
                        title="✅ Ваша заявка одобрена!",
                        description=f"Поздравляем! Ваша заявка на должность **{self.role}** была **ОДОБРЕНА**!\n\n"
                                    f"Модератор: {inter.user.mention}",
                        color=disnake.Color.green()
                    )
                    await user.send(embed=dm_embed)
                except:
                    pass

                embed.color = disnake.Color.green()
                embed.add_field(name="✅ Статус", value=f"Одобрено администратором {inter.user.mention}", inline=False)

                await inter.response.edit_message(embed=embed, view=None)
                await inter.followup.send("✅ Заявка успешно одобрена!", ephemeral=True)

            @disnake.ui.button(label="❌", style=disnake.ButtonStyle.red, custom_id="reject_button")
            async def reject_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                if not inter.user.guild_permissions.ban_members:
                    await inter.response.send_message("❌ У вас нет прав для этого действия!", ephemeral=True)
                    return

                modal = RejectModal(self.cog, self.user_id, self.role, self.user_name)
                await inter.response.send_modal(modal)

        view = ApplicationView(self, user.id, role, user.name)
        await channel.send(embed=embed, view=view)


class ApplicationModal(disnake.ui.Modal):
    """Модальное окно с вопросами для заявки"""

    def __init__(self, cog, role: str):
        components = [
            disnake.ui.TextInput(
                label="Как вас зовут?",
                placeholder="Введите ваше имя",
                custom_id="name",
                style=disnake.TextInputStyle.short,
                max_length=100,
                required=True
            ),
            disnake.ui.TextInput(
                label="Сколько вам лет?",
                placeholder="Введите ваш возраст",
                custom_id="age",
                style=disnake.TextInputStyle.short,
                max_length=3,
                required=True
            ),
            disnake.ui.TextInput(
                label="Сколько времени готовы уделять серверу?",
                placeholder="Пример: 2-3 часа",
                custom_id="time",
                style=disnake.TextInputStyle.short,
                max_length=100,
                required=True
            ),
            disnake.ui.TextInput(
                label="Расскажите немного о себе",
                placeholder="Ваши сильные и слабые стороны, чем занимаетесь...",
                custom_id="about",
                style=disnake.TextInputStyle.paragraph,
                max_length=1000,
                required=True
            ),
            disnake.ui.TextInput(
                label="Ваше знание правил (от 1 до 10)",
                placeholder="Пример: 8",
                custom_id="rules_knowledge",
                style=disnake.TextInputStyle.short,
                max_length=2,
                required=True
            )
        ]
        super().__init__(title=f"📝 Заявка на должность {role}", components=components)
        self.cog = cog
        self.role = role

    async def callback(self, interaction: disnake.ModalInteraction):
        answers = {
            'name': interaction.text_values['name'],
            'age': interaction.text_values['age'],
            'time': interaction.text_values['time'],
            'about': interaction.text_values['about'],
            'rules_knowledge': interaction.text_values['rules_knowledge']
        }

        try:
            rules_score = int(answers['rules_knowledge'])
            if rules_score < 1 or rules_score > 10:
                await interaction.response.send_message("❌ Пожалуйста, укажите число от 1 до 10!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Пожалуйста, укажите число от 1 до 10!", ephemeral=True)
            return

        await self.cog.send_application_to_channel(
            interaction.guild,
            interaction.user,
            self.role,
            answers
        )

        try:
            dm_embed = disnake.Embed(
                title="📝 Заявка отправлена!",
                description=f"Ваша заявка на должность **{self.role}** успешно отправлена!\n\n"
                            f"Ожидайте решения администрации. Уведомление придет в личные сообщения.",
                color=disnake.Color.blue()
            )
            await interaction.user.send(embed=dm_embed)
        except:
            pass

        await interaction.response.send_message(
            f"✅ Ваша заявка на должность **{self.role}** успешно отправлена! Ожидайте решения администрации.",
            ephemeral=True
        )


class RejectModal(disnake.ui.Modal):
    """Модальное окно для указания причины отказа"""

    def __init__(self, cog, user_id: int, role: str, user_name: str):
        components = [
            disnake.ui.TextInput(
                label="Причина отказа",
                placeholder="Укажите причину отказа",
                custom_id="reason",
                style=disnake.TextInputStyle.paragraph,
                max_length=500,
                required=True
            )
        ]
        super().__init__(title="❌ Отказ в заявке", components=components)
        self.cog = cog
        self.user_id = user_id
        self.role = role
        self.user_name = user_name

    async def callback(self, interaction: disnake.ModalInteraction):
        reason = interaction.text_values['reason']

        user = await self.cog.bot.fetch_user(self.user_id)

        try:
            dm_embed = disnake.Embed(
                title="❌ Ваша заявка отклонена",
                description=f"К сожалению, ваша заявка на должность **{self.role}** была **ОТКЛОНЕНА**!\n\n"
                            f"**Причина:** {reason}\n\n"
                            f"Модератор: {interaction.user.mention}",
                color=disnake.Color.red()
            )
            await user.send(embed=dm_embed)
        except:
            pass

        try:
            channel = self.cog.bot.get_channel(self.cog.applications_channel_id)
            if channel:
                async for message in channel.history(limit=50):
                    if message.embeds and message.embeds[0].fields:
                        for field in message.embeds[0].fields:
                            if field.name == "🆔 ID" and str(self.user_id) in field.value:
                                embed = message.embeds[0]
                                embed.color = disnake.Color.red()
                                embed.add_field(name="❌ Статус",
                                                value=f"Отклонено администратором {interaction.user.mention}\nПричина: {reason}",
                                                inline=False)
                                await message.edit(embed=embed, view=None)
                                break
        except:
            pass

        await interaction.response.send_message("✅ Заявка отклонена!", ephemeral=True)


def setup(bot):
    bot.add_cog(ApplicationSystem(bot))