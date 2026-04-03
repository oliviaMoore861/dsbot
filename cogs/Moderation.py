import disnake
from disnake.ext import commands, tasks
import datetime
import sqlite3
from typing import Optional


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = 1488227522536542300  # ID канала для логов
        self.allowed_channel_id = 1488811577330368572  # ID разрешенного канала для команд
        self.mute_role_name = "Muted"  # Название роли для мута
        self.init_database()
        self.check_temp_mutes.start()

    def check_allowed_channel(self, interaction: disnake.ApplicationCommandInteraction) -> bool:
        """Проверяет, что команда вызвана в разрешенном канале"""
        return interaction.channel_id == self.allowed_channel_id

    def init_database(self):
        """Инициализация базы данных"""
        self.db = sqlite3.connect('moderation.db')
        cursor = self.db.cursor()

        # Таблица для временных мутов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS temp_mutes (
                user_id INTEGER,
                guild_id INTEGER,
                end_time TEXT,
                reason TEXT,
                moderator_id INTEGER,
                mute_time TEXT,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')

        # Таблица для варнов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                reason TEXT,
                moderator_id INTEGER,
                warn_time TEXT
            )
        ''')

        # Таблица для конфигурации сервера
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                mute_role_id INTEGER,
                max_warns INTEGER DEFAULT 3,
                auto_ban BOOLEAN DEFAULT 0
            )
        ''')

        self.db.commit()

    async def send_log(self, guild: disnake.Guild, embed: disnake.Embed):
        """Отправка лога в указанный канал"""
        try:
            channel = self.bot.get_channel(self.log_channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(self.log_channel_id)
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Ошибка при отправке лога: {e}")

    async def get_or_create_mute_role(self, guild: disnake.Guild):
        """Получить или создать роль для мута"""
        cursor = self.db.cursor()
        cursor.execute('SELECT mute_role_id FROM guild_config WHERE guild_id = ?', (guild.id,))
        result = cursor.fetchone()

        if result and result[0]:
            role = guild.get_role(result[0])
            if role:
                return role

        # Создаем роль если не существует
        try:
            role = await guild.create_role(
                name=self.mute_role_name,
                color=disnake.Color.dark_gray(),
                reason="Создание роли для мута"
            )

            # Настраиваем права для роли
            for channel in guild.channels:
                try:
                    await channel.set_permissions(
                        role,
                        send_messages=False,
                        add_reactions=False,
                        speak=False,
                        connect=False
                    )
                except:
                    pass

            # Сохраняем ID роли
            cursor.execute('INSERT OR REPLACE INTO guild_config (guild_id, mute_role_id) VALUES (?, ?)',
                           (guild.id, role.id))
            self.db.commit()

            return role
        except:
            return None

    @tasks.loop(minutes=1)
    async def check_temp_mutes(self):
        """Проверка истекших мутов"""
        cursor = self.db.cursor()
        cursor.execute('SELECT user_id, guild_id, reason, moderator_id, mute_time FROM temp_mutes WHERE end_time <= ?',
                       (datetime.datetime.utcnow().isoformat(),))
        expired_mutes = cursor.fetchall()

        for user_id, guild_id, reason, moderator_id, mute_time in expired_mutes:
            guild = self.bot.get_guild(guild_id)
            if guild:
                member = guild.get_member(user_id)
                if member:
                    mute_role = await self.get_or_create_mute_role(guild)
                    if mute_role and mute_role in member.roles:
                        await member.remove_roles(mute_role, reason="Время мута истекло")

                        # Логируем снятие мута
                        moderator = await self.bot.fetch_user(moderator_id) if moderator_id else None
                        user = await self.bot.fetch_user(user_id)

                        embed = disnake.Embed(
                            title="🔊 Снятие мута",
                            description=f"Участник {member.mention} был автоматически размучен",
                            color=disnake.Color.green(),
                            timestamp=datetime.datetime.utcnow()
                        )
                        embed.add_field(name="👤 Пользователь", value=f"{user.name}#{user.discriminator}", inline=True)
                        embed.add_field(name="🆔 ID", value=user.id, inline=True)
                        embed.add_field(name="📝 Причина мута", value=reason, inline=False)
                        if moderator:
                            embed.add_field(name="👮 Замутил", value=f"{moderator.name}#{moderator.discriminator}",
                                            inline=True)
                        embed.add_field(name="⏱️ Время мута", value=mute_time, inline=True)
                        embed.set_thumbnail(url=user.display_avatar.url)

                        await self.send_log(guild, embed)

            # Удаляем из базы данных
            cursor.execute('DELETE FROM temp_mutes WHERE user_id = ? AND guild_id = ?',
                           (user_id, guild_id))
            self.db.commit()

    @check_temp_mutes.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # ==================== КОМАНДЫ МУТА ====================

    @commands.slash_command(name="mute", description="Замутить участника на определенное время")
    @commands.has_permissions(moderate_members=True)
    async def mute(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: disnake.Member,
            duration: str,
            reason: str = "Причина не указана"
    ):
        """Временный мут участника"""

        # Проверка канала
        if not self.check_allowed_channel(interaction):
            await interaction.response.send_message(
                f"❌ Команда `/mute` доступна только в канале <#{self.allowed_channel_id}>",
                ephemeral=True
            )
            return

        if not interaction.guild.me.guild_permissions.moderate_members:
            await interaction.response.send_message("❌ У меня нет прав на мут!", ephemeral=True)
            return

        # Проверки
        if member == interaction.author:
            await interaction.response.send_message("❌ Вы не можете замутить самого себя!", ephemeral=True)
            return

        if member.guild_permissions.administrator:
            await interaction.response.send_message("❌ Нельзя замутить администратора!", ephemeral=True)
            return

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message("❌ Нельзя замутить участника с ролью выше моей!", ephemeral=True)
            return

        # Парсинг времени
        try:
            mute_duration = self.parse_duration(duration)
            if not mute_duration:
                await interaction.response.send_message(
                    "❌ Неправильный формат времени! Используйте: 30s, 5m, 2h, 1d, 1w",
                    ephemeral=True
                )
                return
        except ValueError as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)
            return

        # Получаем или создаем роль мута
        mute_role = await self.get_or_create_mute_role(interaction.guild)
        if not mute_role:
            await interaction.response.send_message("❌ Не удалось создать роль для мута!", ephemeral=True)
            return

        end_time = datetime.datetime.utcnow() + mute_duration
        mute_time_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

        # Сохраняем в базу данных
        cursor = self.db.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO temp_mutes (user_id, guild_id, end_time, reason, moderator_id, mute_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (member.id, interaction.guild.id, end_time.isoformat(), reason, interaction.author.id, mute_time_str))
        self.db.commit()

        try:
            # Добавляем роль мута
            await member.add_roles(mute_role, reason=f"Мут на {self.format_duration(mute_duration)}. Причина: {reason}")

            # Embed для ответа в чат
            embed = disnake.Embed(
                title="🔇 Участник замучен",
                description=f"{member.mention} получил мут",
                color=disnake.Color.orange(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="👤 Пользователь", value=f"{member.name}#{member.discriminator}", inline=True)
            embed.add_field(name="🆔 ID", value=member.id, inline=True)
            embed.add_field(name="⏱️ Длительность", value=self.format_duration(mute_duration), inline=True)
            embed.add_field(name="📅 Истекает", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)
            embed.add_field(name="📝 Причина", value=reason, inline=False)
            embed.add_field(name="👮 Модератор", value=interaction.author.mention, inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)

            await interaction.response.send_message(embed=embed)

            # Лог в канал
            log_embed = disnake.Embed(
                title="🔇 МУТ",
                color=disnake.Color.orange(),
                timestamp=datetime.datetime.utcnow()
            )
            log_embed.add_field(name="👤 Пользователь",
                                value=f"{member.name}#{member.discriminator}\n({member.mention})", inline=True)
            log_embed.add_field(name="🆔 ID", value=member.id, inline=True)
            log_embed.add_field(name="⏱️ Длительность", value=self.format_duration(mute_duration), inline=True)
            log_embed.add_field(name="📅 Мут до", value=f"<t:{int(end_time.timestamp())}:F>", inline=False)
            log_embed.add_field(name="📝 Причина", value=reason, inline=False)
            log_embed.add_field(name="👮 Модератор",
                                value=f"{interaction.author.name}#{interaction.author.discriminator}\n({interaction.author.mention})",
                                inline=True)
            log_embed.add_field(name="🕒 Время мута", value=f"<t:{int(datetime.datetime.utcnow().timestamp())}:F>",
                                inline=False)
            log_embed.set_thumbnail(url=member.display_avatar.url)
            log_embed.set_footer(text=f"Временный мут | ID: {member.id}")

            await self.send_log(interaction.guild, log_embed)

            # Личное сообщение пользователю
            try:
                dm_embed = disnake.Embed(
                    title=f"🔇 Мут на {interaction.guild.name}",
                    description=f"Вы получили временный мут.",
                    color=disnake.Color.orange()
                )
                dm_embed.add_field(name="⏱️ Длительность", value=self.format_duration(mute_duration), inline=True)
                dm_embed.add_field(name="📅 Истекает", value=f"<t:{int(end_time.timestamp())}:F>", inline=True)
                dm_embed.add_field(name="📝 Причина", value=reason, inline=False)
                dm_embed.add_field(name="👮 Модератор", value=interaction.author.name, inline=True)
                await member.send(embed=dm_embed)
            except:
                pass

        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка при муте: {e}", ephemeral=True)

    @commands.slash_command(name="unmute", description="Снять мут с участника")
    @commands.has_permissions(moderate_members=True)
    async def unmute(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: disnake.Member,
            reason: str = "Причина не указана"
    ):
        """Снять мут с участника"""

        # Проверка канала
        if not self.check_allowed_channel(interaction):
            await interaction.response.send_message(
                f"❌ Команда `/unmute` доступна только в канале <#{self.allowed_channel_id}>",
                ephemeral=True
            )
            return

        mute_role = await self.get_or_create_mute_role(interaction.guild)

        if not mute_role or mute_role not in member.roles:
            await interaction.response.send_message(f"❌ Участник {member.mention} не замучен!", ephemeral=True)
            return

        try:
            await member.remove_roles(mute_role, reason=f"Снятие мута: {reason}")

            # Удаляем из базы данных
            cursor = self.db.cursor()
            cursor.execute('DELETE FROM temp_mutes WHERE user_id = ? AND guild_id = ?',
                           (member.id, interaction.guild.id))
            self.db.commit()

            # Embed для ответа
            embed = disnake.Embed(
                title="🔊 Снятие мута",
                description=f"{member.mention} был размучен",
                color=disnake.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="👤 Пользователь", value=f"{member.name}#{member.discriminator}", inline=True)
            embed.add_field(name="📝 Причина", value=reason, inline=False)
            embed.add_field(name="👮 Модератор", value=interaction.author.mention, inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)

            await interaction.response.send_message(embed=embed)

            # Лог в канал
            log_embed = disnake.Embed(
                title="🔊 СНЯТИЕ МУТА",
                color=disnake.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            log_embed.add_field(name="👤 Пользователь",
                                value=f"{member.name}#{member.discriminator}\n({member.mention})", inline=True)
            log_embed.add_field(name="🆔 ID", value=member.id, inline=True)
            log_embed.add_field(name="📝 Причина", value=reason, inline=False)
            log_embed.add_field(name="👮 Модератор",
                                value=f"{interaction.author.name}#{interaction.author.discriminator}\n({interaction.author.mention})",
                                inline=True)
            log_embed.set_thumbnail(url=member.display_avatar.url)

            await self.send_log(interaction.guild, log_embed)

            # Личное сообщение
            try:
                dm_embed = disnake.Embed(
                    title=f"🔊 Снятие мута на {interaction.guild.name}",
                    description=f"С вас снят мут.",
                    color=disnake.Color.green()
                )
                dm_embed.add_field(name="📝 Причина", value=reason, inline=False)
                await member.send(embed=dm_embed)
            except:
                pass

        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка при снятии мута: {e}", ephemeral=True)

    # ==================== КОМАНДЫ ВАРНОВ ====================

    @commands.slash_command(name="warn", description="Выдать предупреждение участнику")
    @commands.has_permissions(moderate_members=True)
    async def warn(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: disnake.Member,
            reason: str,
            auto_ban: bool = commands.Param(default=False, description="Автоматически забанить при превышении лимита?")
    ):
        """Выдать предупреждение участнику"""

        # Проверка канала
        if not self.check_allowed_channel(interaction):
            await interaction.response.send_message(
                f"❌ Команда `/warn` доступна только в канале <#{self.allowed_channel_id}>",
                ephemeral=True
            )
            return

        if member == interaction.author:
            await interaction.response.send_message("❌ Вы не можете выдать предупреждение себе!", ephemeral=True)
            return

        # Сохраняем варн
        cursor = self.db.cursor()
        warn_time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

        cursor.execute('''
            INSERT INTO warns (user_id, guild_id, reason, moderator_id, warn_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (member.id, interaction.guild.id, reason, interaction.author.id, warn_time))
        self.db.commit()

        # Получаем количество варнов
        cursor.execute('SELECT COUNT(*) FROM warns WHERE user_id = ? AND guild_id = ?',
                       (member.id, interaction.guild.id))
        warn_count = cursor.fetchone()[0]

        # Получаем настройки сервера
        cursor.execute('SELECT max_warns FROM guild_config WHERE guild_id = ?', (interaction.guild.id,))
        result = cursor.fetchone()
        max_warns = result[0] if result else 3

        # Embed для ответа
        embed = disnake.Embed(
            title="⚠️ Предупреждение",
            description=f"{member.mention} получил предупреждение",
            color=disnake.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="👤 Пользователь", value=f"{member.name}#{member.discriminator}", inline=True)
        embed.add_field(name="📊 Всего варнов", value=f"{warn_count}/{max_warns}", inline=True)
        embed.add_field(name="📝 Причина", value=reason, inline=False)
        embed.add_field(name="👮 Модератор", value=interaction.author.mention, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)

        await interaction.response.send_message(embed=embed)

        # Лог в канал
        log_embed = disnake.Embed(
            title="⚠️ ПРЕДУПРЕЖДЕНИЕ",
            color=disnake.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="👤 Пользователь", value=f"{member.name}#{member.discriminator}\n({member.mention})",
                            inline=True)
        log_embed.add_field(name="🆔 ID", value=member.id, inline=True)
        log_embed.add_field(name="📊 Всего варнов", value=f"{warn_count}/{max_warns}", inline=True)
        log_embed.add_field(name="📝 Причина", value=reason, inline=False)
        log_embed.add_field(name="👮 Модератор",
                            value=f"{interaction.author.name}#{interaction.author.discriminator}\n({interaction.author.mention})",
                            inline=True)
        log_embed.add_field(name="🕒 Время", value=f"<t:{int(datetime.datetime.utcnow().timestamp())}:F>", inline=False)
        log_embed.set_thumbnail(url=member.display_avatar.url)

        await self.send_log(interaction.guild, log_embed)

        # Личное сообщение
        try:
            dm_embed = disnake.Embed(
                title=f"⚠️ Предупреждение на {interaction.guild.name}",
                description=f"Вы получили предупреждение.",
                color=disnake.Color.orange()
            )
            dm_embed.add_field(name="📊 Всего варнов", value=f"{warn_count}/{max_warns}", inline=True)
            dm_embed.add_field(name="📝 Причина", value=reason, inline=False)
            dm_embed.add_field(name="👮 Модератор", value=interaction.author.name, inline=True)
            await member.send(embed=dm_embed)
        except:
            pass

        # Автоматический бан при превышении лимита
        if warn_count >= max_warns and auto_ban:
            try:
                await member.ban(reason=f"Превышение лимита предупреждений ({max_warns})")

                ban_embed = disnake.Embed(
                    title="🔨 Автоматический бан",
                    description=f"{member.mention} был забанен за превышение лимита предупреждений",
                    color=disnake.Color.red(),
                    timestamp=datetime.datetime.utcnow()
                )
                ban_embed.add_field(name="📊 Всего варнов", value=warn_count, inline=True)
                ban_embed.add_field(name="👮 Модератор", value=interaction.author.mention, inline=True)

                await interaction.followup.send(embed=ban_embed)

                # Лог бана
                ban_log = disnake.Embed(
                    title="🔨 АВТОМАТИЧЕСКИЙ БАН",
                    color=disnake.Color.red(),
                    timestamp=datetime.datetime.utcnow()
                )
                ban_log.add_field(name="👤 Пользователь",
                                  value=f"{member.name}#{member.discriminator}\n({member.mention})", inline=True)
                ban_log.add_field(name="🆔 ID", value=member.id, inline=True)
                ban_log.add_field(name="📊 Всего варнов", value=warn_count, inline=True)
                ban_log.add_field(name="📝 Причина", value="Превышение лимита предупреждений", inline=False)
                ban_log.add_field(name="👮 Модератор",
                                  value=f"{interaction.author.name}#{interaction.author.discriminator}", inline=True)

                await self.send_log(interaction.guild, ban_log)

            except:
                pass

    @commands.slash_command(name="warns", description="Показать предупреждения участника")
    @commands.has_permissions(moderate_members=True)
    async def warns(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: disnake.Member
    ):
        """Показать все предупреждения участника"""

        # Проверка канала
        if not self.check_allowed_channel(interaction):
            await interaction.response.send_message(
                f"❌ Команда `/warns` доступна только в канале <#{self.allowed_channel_id}>",
                ephemeral=True
            )
            return

        cursor = self.db.cursor()
        cursor.execute(
            'SELECT reason, moderator_id, warn_time FROM warns WHERE user_id = ? AND guild_id = ? ORDER BY warn_time DESC',
            (member.id, interaction.guild.id))
        warns_list = cursor.fetchall()

        if not warns_list:
            embed = disnake.Embed(
                title="📋 Предупреждения",
                description=f"У {member.mention} нет предупреждений",
                color=disnake.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            return

        embed = disnake.Embed(
            title=f"📋 Предупреждения {member.name}#{member.discriminator}",
            description=f"Всего: {len(warns_list)}",
            color=disnake.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )

        for i, (reason, moderator_id, warn_time) in enumerate(warns_list[:10], 1):
            moderator = await self.bot.fetch_user(moderator_id)
            embed.add_field(
                name=f"#{i} - {warn_time}",
                value=f"**Причина:** {reason}\n**Модератор:** {moderator.name}#{moderator.discriminator}",
                inline=False
            )

        embed.set_thumbnail(url=member.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    @commands.slash_command(name="clearwarns", description="Очистить предупреждения участника")
    @commands.has_permissions(administrator=True)
    async def clearwarns(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: disnake.Member
    ):
        """Очистить все предупреждения участника"""

        # Проверка канала
        if not self.check_allowed_channel(interaction):
            await interaction.response.send_message(
                f"❌ Команда `/clearwarns` доступна только в канале <#{self.allowed_channel_id}>",
                ephemeral=True
            )
            return

        cursor = self.db.cursor()
        cursor.execute('DELETE FROM warns WHERE user_id = ? AND guild_id = ?',
                       (member.id, interaction.guild.id))
        deleted = cursor.rowcount
        self.db.commit()

        embed = disnake.Embed(
            title="✅ Предупреждения очищены",
            description=f"У {member.mention} удалено {deleted} предупреждений",
            color=disnake.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="👮 Модератор", value=interaction.author.mention, inline=True)

        await interaction.response.send_message(embed=embed)

        # Лог в канал
        log_embed = disnake.Embed(
            title="✅ ОЧИСТКА ПРЕДУПРЕЖДЕНИЙ",
            color=disnake.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="👤 Пользователь", value=f"{member.name}#{member.discriminator}\n({member.mention})",
                            inline=True)
        log_embed.add_field(name="🆔 ID", value=member.id, inline=True)
        log_embed.add_field(name="📊 Удалено варнов", value=deleted, inline=True)
        log_embed.add_field(name="👮 Модератор",
                            value=f"{interaction.author.name}#{interaction.author.discriminator}\n({interaction.author.mention})",
                            inline=True)

        await self.send_log(interaction.guild, log_embed)

    @commands.slash_command(name="setwarnlimit", description="Установить лимит предупреждений")
    @commands.has_permissions(administrator=True)
    async def setwarnlimit(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            limit: int = commands.Param(ge=1, le=10, description="Максимальное количество предупреждений (1-10)")
    ):
        """Установить максимальное количество предупреждений"""

        # Проверка канала
        if not self.check_allowed_channel(interaction):
            await interaction.response.send_message(
                f"❌ Команда `/setwarnlimit` доступна только в канале <#{self.allowed_channel_id}>",
                ephemeral=True
            )
            return

        cursor = self.db.cursor()
        cursor.execute('INSERT OR REPLACE INTO guild_config (guild_id, max_warns) VALUES (?, ?)',
                       (interaction.guild.id, limit))
        self.db.commit()

        embed = disnake.Embed(
            title="✅ Лимит предупреждений установлен",
            description=f"Максимальное количество предупреждений: **{limit}**",
            color=disnake.Color.green()
        )

        await interaction.response.send_message(embed=embed)

        # Лог
        log_embed = disnake.Embed(
            title="⚙️ НАСТРОЙКА ЛИМИТА ВАРНОВ",
            color=disnake.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="📊 Новый лимит", value=str(limit), inline=True)
        log_embed.add_field(name="👮 Модератор", value=f"{interaction.author.name}#{interaction.author.discriminator}",
                            inline=True)

        await self.send_log(interaction.guild, log_embed)

    # ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

    def parse_duration(self, duration_str: str):
        """Парсинг строки длительности"""
        units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}

        try:
            value = int(duration_str[:-1])
            unit = duration_str[-1].lower()

            if unit not in units:
                raise ValueError("Неизвестная единица времени")

            if unit == 'w' and value > 2:
                raise ValueError("Максимум 2 недели")
            if unit == 'd' and value > 14:
                raise ValueError("Максимум 14 дней")

            return datetime.timedelta(seconds=value * units[unit])
        except (ValueError, IndexError):
            return None

    def format_duration(self, duration: datetime.timedelta):
        """Форматирование длительности"""
        seconds = int(duration.total_seconds())

        weeks = seconds // 604800
        days = (seconds % 604800) // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        parts = []
        if weeks: parts.append(f"{weeks}н")
        if days: parts.append(f"{days}д")
        if hours: parts.append(f"{hours}ч")
        if minutes: parts.append(f"{minutes}м")
        if secs: parts.append(f"{secs}с")

        return " ".join(parts)


def setup(bot):
    bot.add_cog(Moderation(bot))