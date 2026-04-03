import disnake
from disnake.ext import commands, tasks
import datetime
import sqlite3
import math
import random
import asyncio
from typing import Optional


class LevelSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = 1488615641178181843  # ID канала для логов
        self.allowed_channel_id = 1488811577330368572  # ID разрешенного канала для команд
        self.init_database()
        self.start_voice_tracking.start()

        # Роли за уровни (новые уровни)
        self.level_roles = {
            0: {"name": "🥉 Bronze", "color": disnake.Color.from_rgb(205, 127, 50), "description": "Начинающий боец",
                "level_required": 0},
            2: {"name": "🥈 Silver", "color": disnake.Color.from_rgb(192, 192, 192), "description": "Серебряный воин",
                "level_required": 2},
            5: {"name": "🥇 Gold", "color": disnake.Color.from_rgb(255, 215, 0), "description": "Золотой защитник",
                "level_required": 5},
            7: {"name": "💎 Diamond", "color": disnake.Color.from_rgb(185, 242, 255),
                "description": "Бриллиантовый ассасин", "level_required": 7},
            10: {"name": "🔥 Mythic", "color": disnake.Color.from_rgb(255, 105, 180),
                 "description": "Мифический целитель", "level_required": 10},
            15: {"name": "🌟 Legend", "color": disnake.Color.from_rgb(255, 69, 0), "description": "Легендарный боец",
                 "level_required": 15},
            17: {"name": "👑 Master", "color": disnake.Color.from_rgb(0, 255, 255), "description": "Мастер всех стихий",
                 "level_required": 17},
            20: {"name": "⚡ Pro Rank", "color": disnake.Color.from_rgb(255, 215, 0),
                 "description": "Профессиональный ранг", "level_required": 20},
            25: {"name": "🌍 Planet", "color": disnake.Color.from_rgb(138, 43, 226), "description": "Хранитель планеты",
                 "level_required": 25},
            30: {"name": "☀️ Sun", "color": disnake.Color.from_rgb(255, 140, 0), "description": "Солнечный воин",
                 "level_required": 30},
            35: {"name": "🌌 Galaxy", "color": disnake.Color.from_rgb(147, 112, 219),
                 "description": "Защитник галактики", "level_required": 35},
            40: {"name": "✨ Fantasy", "color": disnake.Color.from_rgb(255, 20, 147),
                 "description": "Фантастический воин", "level_required": 40},
            45: {"name": "👼 God", "color": disnake.Color.from_rgb(255, 215, 0), "description": "Божественное существо",
                 "level_required": 45},
            50: {"name": "🐉 Dragon", "color": disnake.Color.from_rgb(255, 0, 0), "description": "Драконий воин",
                 "level_required": 50},
            60: {"name": "👑 Absolute", "color": disnake.Color.from_rgb(255, 215, 0),
                 "description": "Абсолютный чемпион", "level_required": 60}
        }

    def init_database(self):
        """Инициализация базы данных"""
        self.db = sqlite3.connect('levels.db')
        cursor = self.db.cursor()

        # Таблица для уровней пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_levels (
                user_id INTEGER,
                guild_id INTEGER,
                level INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                total_xp INTEGER DEFAULT 0,
                messages_count INTEGER DEFAULT 0,
                voice_time INTEGER DEFAULT 0,
                last_message_time TIMESTAMP,
                current_voice_session_start TIMESTAMP,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')

        # Таблица для голосовых сессий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS voice_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration INTEGER,
                xp_earned INTEGER
            )
        ''')

        self.db.commit()

    def get_current_time(self):
        """Получить текущее время с часовым поясом"""
        return datetime.datetime.now(datetime.timezone.utc)

    async def send_log(self, guild: disnake.Guild, embed: disnake.Embed):
        """Отправка лога в указанный канал"""
        try:
            channel = self.bot.get_channel(self.log_channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(self.log_channel_id)
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Ошибка при отправке лога: {e}")

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

    async def get_or_create_role(self, guild: disnake.Guild, level: int, role_data: dict):
        """Получить или создать роль"""
        role_name = role_data["name"]
        role = disnake.utils.get(guild.roles, name=role_name)

        if not role:
            try:
                # Создаем роль
                role = await guild.create_role(
                    name=role_name,
                    color=role_data["color"],
                    reason=f"Создание роли для {level} уровня",
                    mentionable=True
                )
                print(f"✅ Создана роль: {role_name}")
            except Exception as e:
                print(f"❌ Ошибка создания роли {role_name}: {e}")
                return None

        return role

    async def create_all_roles(self, guild: disnake.Guild):
        """Создание всех ролей на сервере"""
        for level, role_data in self.level_roles.items():
            await self.get_or_create_role(guild, level, role_data)

    async def check_and_assign_bronze(self, member: disnake.Member):
        """Проверка и выдача роли Bronze"""
        # Создаем все роли если их нет
        await self.create_all_roles(member.guild)

        # Получаем роль Bronze
        bronze_role = disnake.utils.get(member.guild.roles, name="🥉 Bronze")

        if bronze_role and bronze_role not in member.roles:
            try:
                await member.add_roles(bronze_role, reason="Выдача начальной роли Bronze")
                print(f"✅ Выдана роль Bronze пользователю {member.name}")
                return True
            except Exception as e:
                print(f"❌ Ошибка выдачи роли Bronze {member.name}: {e}")
        return False

    @commands.Cog.listener()
    async def on_ready(self):
        """При запуске бота создаем роли и выдаем Bronze всем существующим участникам"""
        await self.bot.wait_until_ready()

        for guild in self.bot.guilds:
            print(f"🔧 Проверка ролей на сервере {guild.name}...")

            # Создаем все роли
            await self.create_all_roles(guild)

            # Проверяем права бота
            if not guild.me.guild_permissions.manage_roles:
                print(f"❌ У бота нет прав на управление ролями на сервере {guild.name}!")
                continue

            # Проверяем и выдаем роли всем участникам
            print(f"🎭 Проверяем участников...")
            for member in guild.members:
                if not member.bot:
                    # Получаем уровень из базы
                    cursor = self.db.cursor()
                    cursor.execute('SELECT level FROM user_levels WHERE user_id = ? AND guild_id = ?',
                                   (member.id, guild.id))
                    result = cursor.fetchone()

                    if result:
                        level = result[0]
                        await self.update_roles(member, level)
                    else:
                        # Если нет в базе, выдаем Bronze
                        await self.check_and_assign_bronze(member)

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        """Когда новый участник заходит на сервер, выдаем ему Bronze роль"""
        if not member.bot:
            await self.check_and_assign_bronze(member)

    def calculate_xp_for_level(self, level):
        """Расчет XP для достижения уровня"""
        if level == 0:
            return 0
        return int(100 * level + 50 * (level ** 1.5))

    def calculate_level_from_xp(self, xp):
        """Расчет уровня из XP"""
        level = 0
        while self.calculate_xp_for_level(level + 1) <= xp:
            level += 1
        return level

    async def add_xp(self, user_id: int, guild_id: int, xp_gain: int, source: str = "message"):
        """Добавление XP пользователю"""
        cursor = self.db.cursor()

        # Получаем текущие данные
        cursor.execute('SELECT level, xp, total_xp FROM user_levels WHERE user_id = ? AND guild_id = ?',
                       (user_id, guild_id))
        result = cursor.fetchone()

        if not result:
            # Если пользователя нет в базе, создаем с нулевыми значениями
            level = 0
            current_xp = 0
            total_xp = 0
            # Создаем запись
            cursor.execute('''
                INSERT INTO user_levels (user_id, guild_id, level, xp, total_xp, messages_count, voice_time)
                VALUES (?, ?, ?, ?, ?, 0, 0)
            ''', (user_id, guild_id, level, current_xp, total_xp))
            self.db.commit()
        else:
            level, current_xp, total_xp = result

        new_total_xp = total_xp + xp_gain
        new_level = self.calculate_level_from_xp(new_total_xp)
        new_current_xp = new_total_xp - self.calculate_xp_for_level(new_level)

        # Обновляем только XP и уровень
        cursor.execute('''
            UPDATE user_levels 
            SET level = ?, xp = ?, total_xp = total_xp + ?
            WHERE user_id = ? AND guild_id = ?
        ''', (new_level, new_current_xp, xp_gain, user_id, guild_id))
        self.db.commit()

        # Проверяем повышение уровня
        if new_level > level:
            return True, level, new_level
        return False, level, new_level

    async def update_roles(self, member: disnake.Member, new_level: int):
        """Обновление ролей пользователя при повышении уровня"""
        guild = member.guild

        # Проверяем права бота
        if not guild.me.guild_permissions.manage_roles:
            print(f"❌ У бота нет прав на управление ролями на сервере {guild.name}!")
            return

        print(f"\n🎯 Обновление ролей для {member.name} (уровень {new_level})")

        # Создаем все недостающие роли
        await self.create_all_roles(guild)

        # Получаем все роли для этого уровня
        roles_to_add = []

        # Сортируем уровни ролей
        sorted_levels = sorted(self.level_roles.items())

        # Проверяем все роли, которые должны быть у пользователя
        for level, role_data in sorted_levels:
            role = disnake.utils.get(guild.roles, name=role_data["name"])

            if not role:
                print(f"⚠️ Роль {role_data['name']} не найдена!")
                continue

            # Проверяем, может ли бот выдавать эту роль
            if role >= guild.me.top_role:
                print(f"⚠️ Роль {role.name} выше или равна роли бота, не могу управлять!")
                continue

            # Если уровень пользователя >= требуемого уровня для роли
            if new_level >= level:
                if role not in member.roles:
                    roles_to_add.append((level, role))
                    print(f"📝 Нужно добавить роль: {role.name} (требуется уровень {level})")
                else:
                    print(f"✅ Роль {role.name} уже есть у пользователя")

        # Добавляем роли
        for level, role in sorted(roles_to_add, key=lambda x: x[0]):
            try:
                await member.add_roles(role, reason=f"Достигнут уровень {new_level}")
                print(f"✅ Добавлена роль: {role.name}")
            except Exception as e:
                print(f"❌ Ошибка добавления роли {role.name}: {e}")

    @tasks.loop(minutes=5)
    async def start_voice_tracking(self):
        """Отслеживание времени в голосовых каналах"""
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.voice and member.voice.channel:
                    cursor = self.db.cursor()
                    cursor.execute(
                        'SELECT current_voice_session_start FROM user_levels WHERE user_id = ? AND guild_id = ?',
                        (member.id, guild.id))
                    result = cursor.fetchone()

                    if not result or not result[0]:
                        current_time = self.get_current_time().isoformat()
                        cursor.execute('''
                            UPDATE user_levels 
                            SET current_voice_session_start = ?
                            WHERE user_id = ? AND guild_id = ?
                        ''', (current_time, member.id, guild.id))

                        if cursor.rowcount == 0:
                            cursor.execute('''
                                INSERT INTO user_levels (user_id, guild_id, current_voice_session_start, level, xp, total_xp, messages_count, voice_time)
                                VALUES (?, ?, ?, 0, 0, 0, 0, 0)
                            ''', (member.id, guild.id, current_time))

                        self.db.commit()

    @start_voice_tracking.before_loop
    async def before_tracking(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState,
                                    after: disnake.VoiceState):
        """Начисление XP за нахождение в голосовом канале (10 XP в час)"""
        cursor = self.db.cursor()

        if after.channel and not before.channel:
            current_time = self.get_current_time().isoformat()
            cursor.execute('''
                UPDATE user_levels 
                SET current_voice_session_start = ?
                WHERE user_id = ? AND guild_id = ?
            ''', (current_time, member.id, member.guild.id))

            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO user_levels (user_id, guild_id, current_voice_session_start, level, xp, total_xp, messages_count, voice_time)
                    VALUES (?, ?, ?, 0, 0, 0, 0, 0)
                ''', (member.id, member.guild.id, current_time))

            self.db.commit()

        elif before.channel and not after.channel:
            cursor.execute('SELECT current_voice_session_start FROM user_levels WHERE user_id = ? AND guild_id = ?',
                           (member.id, member.guild.id))
            result = cursor.fetchone()

            if result and result[0]:
                start_time = datetime.datetime.fromisoformat(result[0])
                end_time = self.get_current_time()
                duration = int((end_time - start_time).total_seconds())

                if duration >= 60:  # Минимум 1 минута
                    # 10 XP в час = 10/3600 XP в секунду
                    # Округляем до целых, минимум 1 XP за сессию
                    xp_gain = max(1, int(duration * 10 / 60))
                    
                    # Ограничиваем максимум 100 XP за одну сессию
                    xp_gain = min(xp_gain, 1000)

                    leveled_up, old_level, new_level = await self.add_xp(
                        member.id, member.guild.id, xp_gain, "голосовой канал"
                    )

                    cursor.execute('''
                        INSERT INTO voice_sessions (user_id, guild_id, start_time, end_time, duration, xp_earned)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (member.id, member.guild.id, start_time.isoformat(), end_time.isoformat(), duration, xp_gain))

                    cursor.execute('''
                        UPDATE user_levels 
                        SET voice_time = COALESCE(voice_time, 0) + ?, current_voice_session_start = NULL
                        WHERE user_id = ? AND guild_id = ?
                    ''', (duration, member.id, member.guild.id))

                    self.db.commit()

                    if leveled_up:
                        await self.handle_level_up(member, old_level, new_level, "голосовую активность")

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        """Начисление XP за сообщения (15 XP за сообщение)"""
        if message.author.bot or not message.guild:
            return

        cursor = self.db.cursor()

        cursor.execute('SELECT user_id FROM user_levels WHERE user_id = ? AND guild_id = ?',
                       (message.author.id, message.guild.id))
        exists = cursor.fetchone()

        if not exists:
            cursor.execute('''
                INSERT INTO user_levels (user_id, guild_id, level, xp, total_xp, messages_count, voice_time)
                VALUES (?, ?, 0, 0, 0, 0, 0)
            ''', (message.author.id, message.guild.id))
            self.db.commit()
            await self.check_and_assign_bronze(message.author)

        cursor.execute('SELECT last_message_time, messages_count FROM user_levels WHERE user_id = ? AND guild_id = ?',
                       (message.author.id, message.guild.id))
        result = cursor.fetchone()

        # Защита от спама: не чаще 1 сообщения в 60 секунд
        is_in_voice = message.author.voice and message.author.voice.channel

        if not is_in_voice and result and result[0]:
            last_time = datetime.datetime.fromisoformat(result[0])
            if (self.get_current_time() - last_time).total_seconds() < 60:
                return

        if is_in_voice and result and result[0]:
            last_time = datetime.datetime.fromisoformat(result[0])
            if (self.get_current_time() - last_time).total_seconds() < 30:
                return

        # 15 XP за сообщение (фиксированное значение)
        xp_gain = 15

        leveled_up, old_level, new_level = await self.add_xp(
            message.author.id,
            message.guild.id,
            xp_gain,
            "сообщение в чате"
        )

        cursor.execute('''
            UPDATE user_levels 
            SET last_message_time = ?, messages_count = COALESCE(messages_count, 0) + 1
            WHERE user_id = ? AND guild_id = ?
        ''', (self.get_current_time().isoformat(), message.author.id, message.guild.id))
        self.db.commit()

        if leveled_up:
            await self.handle_level_up(message.author, old_level, new_level, "общение в чате")

    async def handle_level_up(self, member: disnake.Member, old_level: int, new_level: int, source: str):
        """Обработка повышения уровня"""
        print(f"\n🎉 ПОВЫШЕНИЕ УРОВНЯ! {member.name}: {old_level} -> {new_level}")

        # Обновляем роли
        await self.update_roles(member, new_level)

        role_info = None
        for lvl, info in self.level_roles.items():
            if new_level >= lvl:
                role_info = info

        try:
            dm_embed = disnake.Embed(
                title=f"🎉 ПОВЫШЕНИЕ УРОВНЯ! 🎉",
                description=f"**Поздравляем!** Вы достигли **{new_level} уровня** в системе уровней {member.guild.name}!",
                color=disnake.Color.gold(),
                timestamp=self.get_current_time()
            )

            dm_embed.add_field(
                name="📊 Статистика",
                value=f"**Предыдущий уровень:** {old_level}\n"
                      f"**Новый уровень:** {new_level}\n"
                      f"**Источник XP:** {source}",
                inline=False
            )

            if role_info:
                dm_embed.add_field(
                    name="🏆 Новая роль!",
                    value=f"Вы получили роль: **{role_info['name']}**\n"
                          f"*{role_info['description']}*",
                    inline=False
                )

            dm_embed.set_footer(text="Продолжайте быть активными! 🚀")

            await member.send(embed=dm_embed)
        except:
            pass

        log_embed = disnake.Embed(
            title="🎉 ПОВЫШЕНИЕ УРОВНЯ",
            color=disnake.Color.gold(),
            timestamp=self.get_current_time()
        )
        log_embed.add_field(name="👤 Пользователь", value=f"{member.name}#{member.discriminator}\n({member.mention})",
                            inline=True)
        log_embed.add_field(name="🆔 ID", value=member.id, inline=True)
        log_embed.add_field(name="📊 Уровни", value=f"{old_level} → **{new_level}**", inline=True)
        log_embed.add_field(name="📝 Источник", value=source, inline=True)
        if role_info:
            log_embed.add_field(name="🏆 Новая роль", value=role_info['name'], inline=True)
        log_embed.set_thumbnail(url=member.display_avatar.url)

        await self.send_log(member.guild, log_embed)

    @commands.slash_command(name="level", description="Показать ваш уровень или уровень другого пользователя")
    async def level(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            user: Optional[disnake.Member] = commands.Param(default=None, description="Пользователь (по умолчанию вы)")
    ):
        """Показать уровень пользователя"""

        # Проверяем канал
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        target_user = user or interaction.author
        cursor = self.db.cursor()

        cursor.execute('''
            SELECT level, xp, total_xp, messages_count, voice_time 
            FROM user_levels 
            WHERE user_id = ? AND guild_id = ?
        ''', (target_user.id, interaction.guild.id))

        result = cursor.fetchone()

        if not result:
            level = 0
            current_xp = 0
            total_xp = 0
            messages = 0
            voice_time = 0
        else:
            level, current_xp, total_xp, messages, voice_time = result

        if level < 100:
            xp_needed = self.calculate_xp_for_level(level + 1)
            xp_current = total_xp - self.calculate_xp_for_level(level)
            if xp_needed > self.calculate_xp_for_level(level):
                progress = (xp_current / (xp_needed - self.calculate_xp_for_level(level))) * 100
            else:
                progress = 100
        else:
            progress = 100
            xp_current = 0

        voice_hours = voice_time // 3600
        voice_minutes = (voice_time % 3600) // 60

        embed = disnake.Embed(
            title=f"📊 Уровень {target_user.display_name}",
            color=target_user.color if target_user.color != disnake.Color.default() else disnake.Color.blue(),
            timestamp=self.get_current_time()
        )

        embed.set_thumbnail(url=target_user.display_avatar.url)

        bar_length = 20
        filled = int(bar_length * progress / 100)
        bar = "▓" * filled + "░" * (bar_length - filled)

        xp_for_next = self.calculate_xp_for_level(level + 1) - self.calculate_xp_for_level(level)

        embed.add_field(
            name="🎯 Текущий уровень",
            value=f"**Уровень {level}**\n{bar} {progress:.1f}%\n"
                  f"XP: {xp_current:,} / {xp_for_next:,}",
            inline=False
        )

        embed.add_field(
            name="📈 Статистика активности",
            value=f"**💬 Сообщений:** {messages:,}\n"
                  f"**🎙️ В голосовых каналах:** {voice_hours}ч {voice_minutes}м\n"
                  f"**⭐ Всего XP:** {total_xp:,}",
            inline=False
        )

        role_info = None
        for lvl, info in sorted(self.level_roles.items(), reverse=True):
            if level >= lvl:
                role_info = info
                break

        if role_info:
            embed.add_field(
                name="🏆 Текущая роль",
                value=f"**{role_info['name']}**\n*{role_info['description']}*",
                inline=False
            )

        next_role_info = None
        next_role_level = None
        for lvl, info in sorted(self.level_roles.items()):
            if lvl > level and lvl != 0:
                next_role_info = info
                next_role_level = lvl
                break

        if next_role_info and level < 100:
            xp_remaining = max(0, self.calculate_xp_for_level(next_role_level) - total_xp)
            embed.add_field(
                name="🎯 Следующая роль",
                value=f"**{next_role_info['name']}**\n"
                      f"Нужно еще XP: {xp_remaining:,}",
                inline=False
            )

        embed.set_footer(text=f"ID: {target_user.id}")

        await interaction.followup.send(embed=embed)

    @commands.slash_command(name="fix_roles", description="Восстановить роли у всех участников (только для админов)")
    @commands.has_permissions(administrator=True)
    async def fix_roles(self, interaction: disnake.ApplicationCommandInteraction):
        """Восстановить роли у всех участников"""

        # Проверяем канал
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        await self.create_all_roles(interaction.guild)

        fixed_count = 0
        error_count = 0
        roles_given = {}

        for member in interaction.guild.members:
            if member.bot:
                continue

            cursor = self.db.cursor()
            cursor.execute('SELECT level FROM user_levels WHERE user_id = ? AND guild_id = ?',
                           (member.id, interaction.guild.id))
            result = cursor.fetchone()

            if result:
                level = result[0]
                try:
                    await self.update_roles(member, level)
                    fixed_count += 1

                    # Считаем выданные роли
                    for lvl, role_data in self.level_roles.items():
                        if level >= lvl:
                            role_name = role_data['name']
                            roles_given[role_name] = roles_given.get(role_name, 0) + 1

                except Exception as e:
                    error_count += 1
                    print(f"Ошибка при фиксе ролей для {member.name}: {e}")

        # Создаем отчет
        report = f"✅ Проверено и обновлено ролей у {fixed_count} участников!\n❌ Ошибок: {error_count}\n\n"
        report += "**Выдано ролей:**\n"
        for role_name, count in sorted(roles_given.items(), key=lambda x: x[1], reverse=True):
            report += f"• {role_name}: {count} участников\n"

        await interaction.followup.send(report[:2000], ephemeral=True)

    @commands.slash_command(name="give_roles", description="Принудительно выдать роли всем участникам по их уровню")
    @commands.has_permissions(administrator=True)
    async def give_roles(self, interaction: disnake.ApplicationCommandInteraction):
        """Принудительно выдать роли всем участникам"""

        # Проверяем канал
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        await self.create_all_roles(interaction.guild)

        success_count = 0
        error_count = 0

        for member in interaction.guild.members:
            if member.bot:
                continue

            cursor = self.db.cursor()
            cursor.execute('SELECT level FROM user_levels WHERE user_id = ? AND guild_id = ?',
                           (member.id, interaction.guild.id))
            result = cursor.fetchone()

            if result:
                level = result[0]
                try:
                    await self.update_roles(member, level)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    print(f"Ошибка при выдаче ролей {member.name}: {e}")

        await interaction.followup.send(f"✅ Успешно выданы роли {success_count} участникам!\n❌ Ошибок: {error_count}",
                                        ephemeral=True)


def setup(bot):
    bot.add_cog(LevelSystem(bot))
