import disnake
from disnake.ext import commands, tasks
import datetime
import sqlite3
from typing import Optional


class ProfileSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.allowed_channel_id = 1488811577330368572  # ID разрешенного канала
        self.init_database()
        self.start_tracking.start()

    def init_database(self):
        """Инициализация базы данных"""
        self.db = sqlite3.connect('user_stats.db')
        cursor = self.db.cursor()

        # Таблица для статистики пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER,
                guild_id INTEGER,
                messages_count INTEGER DEFAULT 0,
                voice_time INTEGER DEFAULT 0,
                last_voice_join TIMESTAMP,
                current_voice_session_start TIMESTAMP,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')

        # Таблица для отслеживания активности в голосовых каналах
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS voice_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                channel_id INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration INTEGER
            )
        ''')

        self.db.commit()

    def get_current_time(self):
        """Получить текущее время с часовым поясом"""
        return datetime.datetime.now(datetime.timezone.utc)

    async def check_allowed_channel(self, interaction: disnake.ApplicationCommandInteraction) -> bool:
        """Проверка, что команда используется в разрешенном канале"""
        if interaction.channel.id != self.allowed_channel_id:
            # Получаем разрешенный канал
            allowed_channel = self.bot.get_channel(self.allowed_channel_id)
            channel_mention = allowed_channel.mention if allowed_channel else f"<#{self.allowed_channel_id}>"

            embed = disnake.Embed(
                title="❌ Неверный канал",
                description=f"Эту команду можно использовать только в канале {channel_mention}!",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    @tasks.loop(seconds=30)
    async def start_tracking(self):
        """Отслеживание времени в голосовых каналах"""
        for guild in self.bot.guilds:
            # Получаем всех участников в голосовых каналах
            for member in guild.members:
                if member.voice and member.voice.channel:
                    cursor = self.db.cursor()
                    cursor.execute(
                        'SELECT current_voice_session_start FROM user_stats WHERE user_id = ? AND guild_id = ?',
                        (member.id, guild.id))
                    result = cursor.fetchone()

                    if not result or not result[0]:
                        # Начинаем новую сессию
                        current_time = self.get_current_time().isoformat()
                        cursor.execute('''
                            INSERT OR REPLACE INTO user_stats (user_id, guild_id, current_voice_session_start)
                            VALUES (?, ?, ?)
                        ''', (member.id, guild.id, current_time))
                        self.db.commit()
                else:
                    # Пользователь не в голосовом канале - проверяем и завершаем сессию
                    cursor = self.db.cursor()
                    cursor.execute(
                        'SELECT current_voice_session_start FROM user_stats WHERE user_id = ? AND guild_id = ?',
                        (member.id, guild.id))
                    result = cursor.fetchone()

                    if result and result[0]:
                        start_time = datetime.datetime.fromisoformat(result[0])
                        end_time = self.get_current_time()
                        duration = int((end_time - start_time).total_seconds())

                        if duration > 0:
                            # Обновляем общее время
                            cursor.execute('''
                                UPDATE user_stats 
                                SET voice_time = voice_time + ?, current_voice_session_start = NULL
                                WHERE user_id = ? AND guild_id = ?
                            ''', (duration, member.id, guild.id))

                            # Сохраняем сессию
                            cursor.execute('''
                                INSERT INTO voice_sessions (user_id, guild_id, channel_id, start_time, end_time, duration)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (member.id, guild.id, member.voice.channel.id if member.voice else None,
                                  start_time.isoformat(), end_time.isoformat(), duration))

                            self.db.commit()

    @start_tracking.before_loop
    async def before_tracking(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        """Счетчик сообщений"""
        if message.author.bot or not message.guild:
            return

        cursor = self.db.cursor()
        cursor.execute('''
            INSERT INTO user_stats (user_id, guild_id, messages_count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET
            messages_count = messages_count + 1
        ''', (message.author.id, message.guild.id))
        self.db.commit()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState,
                                    after: disnake.VoiceState):
        """Мгновенное обновление при входе/выходе из голосового канала"""
        cursor = self.db.cursor()

        # Пользователь зашел в голосовой канал
        if after.channel and not before.channel:
            current_time = self.get_current_time().isoformat()
            cursor.execute('''
                INSERT OR REPLACE INTO user_stats (user_id, guild_id, current_voice_session_start)
                VALUES (?, ?, ?)
            ''', (member.id, member.guild.id, current_time))
            self.db.commit()

        # Пользователь вышел из голосового канала
        elif before.channel and not after.channel:
            cursor.execute('SELECT current_voice_session_start FROM user_stats WHERE user_id = ? AND guild_id = ?',
                           (member.id, member.guild.id))
            result = cursor.fetchone()

            if result and result[0]:
                start_time = datetime.datetime.fromisoformat(result[0])
                end_time = self.get_current_time()
                duration = int((end_time - start_time).total_seconds())

                if duration > 0:
                    # Обновляем общее время
                    cursor.execute('''
                        UPDATE user_stats 
                        SET voice_time = voice_time + ?, current_voice_session_start = NULL
                        WHERE user_id = ? AND guild_id = ?
                    ''', (duration, member.id, member.guild.id))

                    # Сохраняем сессию
                    cursor.execute('''
                        INSERT INTO voice_sessions (user_id, guild_id, channel_id, start_time, end_time, duration)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (member.id, member.guild.id, before.channel.id,
                          start_time.isoformat(), end_time.isoformat(), duration))

                    self.db.commit()

        # Пользователь сменил канал
        elif before.channel and after.channel and before.channel.id != after.channel.id:
            # Завершаем старую сессию
            cursor.execute('SELECT current_voice_session_start FROM user_stats WHERE user_id = ? AND guild_id = ?',
                           (member.id, member.guild.id))
            result = cursor.fetchone()

            if result and result[0]:
                start_time = datetime.datetime.fromisoformat(result[0])
                end_time = self.get_current_time()
                duration = int((end_time - start_time).total_seconds())

                if duration > 0:
                    # Обновляем общее время и начинаем новую сессию
                    cursor.execute('''
                        UPDATE user_stats 
                        SET voice_time = voice_time + ?, current_voice_session_start = ?
                        WHERE user_id = ? AND guild_id = ?
                    ''', (duration, self.get_current_time().isoformat(), member.id, member.guild.id))

                    # Сохраняем старую сессию
                    cursor.execute('''
                        INSERT INTO voice_sessions (user_id, guild_id, channel_id, start_time, end_time, duration)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (member.id, member.guild.id, before.channel.id,
                          start_time.isoformat(), end_time.isoformat(), duration))

                    self.db.commit()

    @commands.slash_command(name="profile", description="Показать профиль пользователя")
    async def profile(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            user: Optional[disnake.Member] = commands.Param(default=None, description="Пользователь (по умолчанию вы)")
    ):
        """Показать профиль пользователя со статистикой"""

        # Проверяем, что команда используется в разрешенном канале
        if not await self.check_allowed_channel(interaction):
            return

        target_user = user or interaction.author
        guild = interaction.guild

        # Получаем статистику из базы данных
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT messages_count, voice_time 
            FROM user_stats 
            WHERE user_id = ? AND guild_id = ?
        ''', (target_user.id, guild.id))

        result = cursor.fetchone()
        messages_count = result[0] if result else 0
        voice_time_seconds = result[1] if result else 0

        # Получаем текущую голосовую сессию если есть
        current_voice_time = 0
        if target_user.voice and target_user.voice.channel:
            cursor.execute('SELECT current_voice_session_start FROM user_stats WHERE user_id = ? AND guild_id = ?',
                           (target_user.id, guild.id))
            session_start = cursor.fetchone()
            if session_start and session_start[0]:
                start_time = datetime.datetime.fromisoformat(session_start[0])
                current_voice_time = int((self.get_current_time() - start_time).total_seconds())

        total_voice_time = voice_time_seconds + current_voice_time

        # Форматируем время
        voice_formatted = self.format_time(total_voice_time)

        # Создаем профиль
        embed = disnake.Embed(
            title=f"📊 Профиль пользователя",
            color=target_user.color if target_user.color != disnake.Color.default() else disnake.Color.blue(),
            timestamp=self.get_current_time()
        )

        embed.set_author(
            name=f"{target_user.name}#{target_user.discriminator}",
            icon_url=target_user.display_avatar.url
        )

        embed.set_thumbnail(url=target_user.display_avatar.url)

        # Основная информация
        embed.add_field(
            name="👤 Основная информация",
            value=f"**Имя:** {target_user.display_name}\n"
                  f"**ID:** {target_user.id}\n"
                  f"**Аккаунт создан:** <t:{int(target_user.created_at.timestamp())}:R>\n"
                  f"**Присоединился:** <t:{int(target_user.joined_at.timestamp())}:R>",
            inline=False
        )

        # Статистика
        embed.add_field(
            name="📈 Статистика на сервере",
            value=f"**💬 Сообщений:** {messages_count:,}\n"
                  f"**🎙️ Время в голосовых каналах:** {voice_formatted}\n"
                  f"**📅 На сервере:** {self.get_member_days(target_user.joined_at)} дней",
            inline=False
        )

        # Роли
        roles = [role.mention for role in target_user.roles if role != guild.default_role]
        if roles:
            roles_text = ", ".join(roles[:10])  # Показываем первые 10 ролей
            if len(roles) > 10:
                roles_text += f" и еще {len(roles) - 10}"
            embed.add_field(
                name=f"🎭 Роли ({len(roles)})",
                value=roles_text,
                inline=False
            )

        # Статус
        status_emoji = {
            disnake.Status.online: "🟢",
            disnake.Status.idle: "🟡",
            disnake.Status.dnd: "🔴",
            disnake.Status.offline: "⚫"
        }

        status = status_emoji.get(target_user.status, "⚪")

        embed.add_field(
            name="🟢 Статус",
            value=f"{status} {str(target_user.status).capitalize()}",
            inline=True
        )

        # В голосовом канале?
        if target_user.voice and target_user.voice.channel:
            embed.add_field(
                name="🔊 В голосовом канале",
                value=f"В канале: {target_user.voice.channel.mention}\n"
                      f"Текущая сессия: {self.format_time(current_voice_time)}",
                inline=True
            )
        else:
            embed.add_field(
                name="🔇 Голосовой канал",
                value="Не в голосовом канале",
                inline=True
            )

        embed.set_footer(text=f"ID: {target_user.id}")

        # Добавляем кнопки для дополнительной информации
        class ProfileView(disnake.ui.View):
            def __init__(self, cog, user, guild, messages, voice_time):
                super().__init__(timeout=60)
                self.cog = cog
                self.user = user
                self.guild = guild
                self.messages = messages
                self.voice_time = voice_time

            @disnake.ui.button(label="📊 Детальная статистика", style=disnake.ButtonStyle.secondary, emoji="📈")
            async def detailed_stats(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                # Проверяем, что кнопка нажата в разрешенном канале
                if inter.channel.id != self.cog.allowed_channel_id:
                    allowed_channel = self.cog.bot.get_channel(self.cog.allowed_channel_id)
                    channel_mention = allowed_channel.mention if allowed_channel else f"<#{self.cog.allowed_channel_id}>"
                    await inter.response.send_message(
                        f"❌ Эту кнопку можно использовать только в канале {channel_mention}!", ephemeral=True)
                    return

                # Получаем последние 10 голосовых сессий
                cursor = self.cog.db.cursor()
                cursor.execute('''
                    SELECT channel_id, start_time, end_time, duration 
                    FROM voice_sessions 
                    WHERE user_id = ? AND guild_id = ?
                    ORDER BY start_time DESC LIMIT 10
                ''', (self.user.id, self.guild.id))

                voice_sessions = cursor.fetchall()

                # Считаем среднее сообщений в день
                days_on_server = self.cog.get_member_days(self.user.joined_at)
                avg_messages_per_day = round(self.messages / days_on_server, 1) if days_on_server > 0 else 0

                detailed_embed = disnake.Embed(
                    title=f"📊 Детальная статистика {self.user.display_name}",
                    color=self.user.color if self.user.color != disnake.Color.default() else disnake.Color.blue(),
                    timestamp=self.cog.get_current_time()
                )

                detailed_embed.set_thumbnail(url=self.user.display_avatar.url)

                detailed_embed.add_field(
                    name="📝 Сообщения",
                    value=f"**Всего:** {self.messages:,}\n"
                          f"**В среднем в день:** {avg_messages_per_day}\n"
                          f"**В среднем в час:** {round(self.messages / (days_on_server * 24), 1) if days_on_server > 0 else 0}",
                    inline=False
                )

                detailed_embed.add_field(
                    name="🎙️ Голосовые каналы",
                    value=f"**Общее время:** {self.cog.format_time(self.voice_time)}\n"
                          f"**Всего сессий:** {len(voice_sessions)}\n"
                          f"**Среднее время сессии:** {self.cog.format_time(self.voice_time // len(voice_sessions)) if voice_sessions else '0с'}",
                    inline=False
                )

                if voice_sessions:
                    detailed_embed.add_field(
                        name="🕒 Последние голосовые сессии",
                        value="\n".join([
                            f"• <t:{int(datetime.datetime.fromisoformat(session[1]).timestamp())}:R> — {self.cog.format_time(session[3])}"
                            for session in voice_sessions[:5]
                        ]),
                        inline=False
                    )

                await inter.response.send_message(embed=detailed_embed, ephemeral=True)

            @disnake.ui.button(label="🏆 Ранг активности", style=disnake.ButtonStyle.secondary, emoji="🏆")
            async def activity_rank(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                # Проверяем, что кнопка нажата в разрешенном канале
                if inter.channel.id != self.cog.allowed_channel_id:
                    allowed_channel = self.cog.bot.get_channel(self.cog.allowed_channel_id)
                    channel_mention = allowed_channel.mention if allowed_channel else f"<#{self.cog.allowed_channel_id}>"
                    await inter.response.send_message(
                        f"❌ Эту кнопку можно использовать только в канале {channel_mention}!", ephemeral=True)
                    return

                # Получаем топ пользователей по сообщениям
                cursor = self.cog.db.cursor()
                cursor.execute('''
                    SELECT user_id, messages_count 
                    FROM user_stats 
                    WHERE guild_id = ? 
                    ORDER BY messages_count DESC 
                    LIMIT 10
                ''', (self.guild.id,))

                top_messages = cursor.fetchall()

                # Получаем топ по голосовому времени
                cursor.execute('''
                    SELECT user_id, voice_time 
                    FROM user_stats 
                    WHERE guild_id = ? 
                    ORDER BY voice_time DESC 
                    LIMIT 10
                ''', (self.guild.id,))

                top_voice = cursor.fetchall()

                # Находим позицию пользователя
                messages_rank = None
                for i, (uid, _) in enumerate(top_messages, 1):
                    if uid == self.user.id:
                        messages_rank = i
                        break

                voice_rank = None
                for i, (uid, _) in enumerate(top_voice, 1):
                    if uid == self.user.id:
                        voice_rank = i
                        break

                rank_embed = disnake.Embed(
                    title=f"🏆 Рейтинг активности {self.user.display_name}",
                    color=disnake.Color.gold(),
                    timestamp=self.cog.get_current_time()
                )

                rank_embed.set_thumbnail(url=self.user.display_avatar.url)

                rank_embed.add_field(
                    name="💬 Сообщения",
                    value=f"**Ранг:** #{messages_rank if messages_rank else 'Не в топе'}\n"
                          f"**Всего сообщений:** {self.messages:,}",
                    inline=False
                )

                rank_embed.add_field(
                    name="🎙️ Голосовое время",
                    value=f"**Ранг:** #{voice_rank if voice_rank else 'Не в топе'}\n"
                          f"**Всего времени:** {self.cog.format_time(self.voice_time)}",
                    inline=False
                )

                # Топ 5 по сообщениям
                top_messages_text = ""
                for i, (uid, count) in enumerate(top_messages[:5], 1):
                    user = self.guild.get_member(uid)
                    if user:
                        top_messages_text += f"{i}. {user.display_name}: {count:,} сообщ.\n"

                if top_messages_text:
                    rank_embed.add_field(
                        name="📊 Топ 5 по сообщениям",
                        value=top_messages_text,
                        inline=False
                    )

                # Топ 5 по голосовому времени
                top_voice_text = ""
                for i, (uid, time_sec) in enumerate(top_voice[:5], 1):
                    user = self.guild.get_member(uid)
                    if user:
                        top_voice_text += f"{i}. {user.display_name}: {self.cog.format_time(time_sec)}\n"

                if top_voice_text:
                    rank_embed.add_field(
                        name="🎧 Топ 5 по голосовому времени",
                        value=top_voice_text,
                        inline=False
                    )

                await inter.response.send_message(embed=rank_embed, ephemeral=True)

        view = ProfileView(self, target_user, guild, messages_count, total_voice_time)
        await interaction.response.send_message(embed=embed, view=view)

    def format_time(self, seconds: int) -> str:
        """Форматирование времени из секунд в читаемый вид"""
        if seconds == 0:
            return "0с"

        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days}д")
        if hours > 0:
            parts.append(f"{hours}ч")
        if minutes > 0:
            parts.append(f"{minutes}м")
        if secs > 0 or not parts:
            parts.append(f"{secs}с")

        return " ".join(parts)

    def get_member_days(self, joined_at: datetime.datetime) -> int:
        """Получить количество дней с момента присоединения"""
        now = self.get_current_time()
        # joined_at уже имеет часовой пояс, так как это свойство Discord
        delta = now - joined_at
        return max(1, delta.days)  # Минимум 1 день для избежания деления на 0


def setup(bot):
    bot.add_cog(ProfileSystem(bot))