import disnake
from disnake.ext import commands, tasks
import datetime
import sqlite3
import random
import asyncio
from typing import Optional


class EconomySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = 1488615641178181843  # ID канала для логов
        self.riddle_channel_id = 1486253733926141992  # ID канала для загадок
        self.init_database()
        self.check_daily_reset.start()
        self.check_work_reset.start()
        self.active_riddle = None
        self.riddle_solved = False
        self.last_riddle_time = None
        
        # Запускаем таск для автоматической смены загадки каждые 30 минут
        self.auto_riddle.start()

    def init_database(self):
        """Инициализация базы данных"""
        self.db = sqlite3.connect('economy.db')
        cursor = self.db.cursor()

        # Таблица для баланса пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS economy (
                user_id INTEGER,
                guild_id INTEGER,
                balance INTEGER DEFAULT 0,
                daily_last_claim TIMESTAMP,
                work_last_claim TIMESTAMP,
                total_earned INTEGER DEFAULT 0,
                total_spent INTEGER DEFAULT 0,
                messages_count INTEGER DEFAULT 0,
                voice_time INTEGER DEFAULT 0,
                last_message_time TIMESTAMP,
                current_voice_session_start TIMESTAMP,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')

        # Таблица для купленных ролей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchased_roles (
                user_id INTEGER,
                guild_id INTEGER,
                role_name TEXT,
                purchase_date TIMESTAMP,
                PRIMARY KEY (user_id, guild_id, role_name)
            )
        ''')

        # Таблица для магазина ролей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shop_roles (
                role_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                role_name TEXT,
                role_price INTEGER,
                role_description TEXT,
                role_color TEXT
            )
        ''')

        self.db.commit()

        # Добавляем роли в магазин
        self.init_shop_roles()

    def init_shop_roles(self):
        """Инициализация магазина ролей"""
        cursor = self.db.cursor()

        cursor.execute('SELECT COUNT(*) FROM shop_roles')
        count = cursor.fetchone()[0]

        if count == 0:
            shop_roles = [
                ("Top4ik", 5000, "🏆 Элитная роль Top4ik - статус топового игрока", "0xFFD700"),
                ("Kaif", 3000, "😎 Роль Kaif - для тех, кто получает кайф от жизни", "0xFF69B4"),
                ("Kentik", 2000, "🤝 Роль Kentik - для настоящих кентов и друзей", "0x00FA9A")
            ]

            for name, price, desc, color in shop_roles:
                cursor.execute('''
                    INSERT INTO shop_roles (guild_id, role_name, role_price, role_description, role_color)
                    VALUES (0, ?, ?, ?, ?)
                ''', (name, price, desc, color))

            self.db.commit()

    def get_current_time(self):
        """Получить текущее время"""
        return datetime.datetime.now(datetime.timezone.utc)

    async def send_log(self, guild: disnake.Guild, embed: disnake.Embed):
        """Отправка лога"""
        try:
            channel = self.bot.get_channel(self.log_channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(self.log_channel_id)
            await channel.send(embed=embed)
        except:
            pass

    async def get_balance(self, user_id: int, guild_id: int) -> int:
        """Получить баланс пользователя"""
        cursor = self.db.cursor()
        cursor.execute('SELECT balance FROM economy WHERE user_id = ? AND guild_id = ?',
                       (user_id, guild_id))
        result = cursor.fetchone()
        return result[0] if result else 0

    async def update_balance(self, user_id: int, guild_id: int, amount: int):
        """Обновить баланс пользователя"""
        cursor = self.db.cursor()

        cursor.execute('''
            INSERT INTO economy (user_id, guild_id, balance, total_earned)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET
            balance = balance + ?,
            total_earned = total_earned + ?
        ''', (user_id, guild_id, amount, amount, amount, amount))

        self.db.commit()

    async def remove_balance(self, user_id: int, guild_id: int, amount: int):
        """Снять баланс пользователя"""
        cursor = self.db.cursor()

        cursor.execute('''
            INSERT INTO economy (user_id, guild_id, balance, total_spent)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET
            balance = balance - ?,
            total_spent = total_spent + ?
        ''', (user_id, guild_id, -amount, amount, amount, amount))

        self.db.commit()

    async def add_coins_for_activity(self, user_id: int, guild_id: int, coins: int, source: str):
        """Добавление монет за активность"""
        await self.update_balance(user_id, guild_id, coins)

        user = await self.bot.fetch_user(user_id)
        if user:
            log_embed = disnake.Embed(
                title="💰 Получение монет",
                description=f"{user.mention} получил {coins} 🪙",
                color=disnake.Color.green(),
                timestamp=self.get_current_time()
            )
            log_embed.add_field(name="📝 Источник", value=source, inline=True)
            await self.send_log(await self.bot.fetch_guild(guild_id), log_embed)

    @tasks.loop(minutes=30)
    async def auto_riddle(self):
        """Автоматическая публикация новой загадки каждые 30 минут"""
        await asyncio.sleep(5)  # Ждем запуска бота
        while True:
            try:
                channel = self.bot.get_channel(self.riddle_channel_id)
                if channel:
                    # Выбираем новую случайную загадку
                    self.active_riddle = random.choice(self.riddles)
                    self.riddle_solved = False
                    self.last_riddle_time = self.get_current_time()
                    
                    embed = disnake.Embed(
                        title="🎯 НОВАЯ ЗАГАДКА BRAWL STARS! 🎯",
                        description=f"**{self.active_riddle['question']}**\n\n💡 **Подсказка:** ||{self.active_riddle['hint']}||",
                        color=disnake.Color.purple()
                    )
                    embed.set_footer(text="Ответь правильно и получи 150 монет! | Следующая загадка через 30 минут")
                    await channel.send(embed=embed)
                    
                    # Логируем новую загадку
                    log_embed = disnake.Embed(
                        title="🎯 Новая загадка",
                        color=disnake.Color.blue(),
                        timestamp=self.get_current_time()
                    )
                    log_embed.add_field(name="❓ Вопрос", value=self.active_riddle['question'], inline=False)
                    await self.send_log(channel.guild, log_embed)
                    
            except Exception as e:
                print(f"Ошибка при отправке загадки: {e}")
            
            await asyncio.sleep(1800)  # 30 минут

    @tasks.loop(minutes=30)
    async def check_daily_reset(self):
        pass

    @tasks.loop(minutes=30)
    async def check_work_reset(self):
        pass

    # ==================== НОВЫЕ ЗАГАДКИ ПРО BRAWL STARS ====================
    
    @property
    def riddles(self):
        """Коллекция загадок о Brawl Stars"""
        return [
            # Вопросы о режимах
            {
                "question": "В каком режиме нужно собрать 10 кристаллов, появляющихся в центре карты?",
                "answer": "Захват кристаллов",
                "hint": "Gem Grab"
            },
            {
                "question": "Как называется режим, где нужно выбить всех врагов из зоны, которая постепенно сужается?",
                "answer": "шд",
                "hint": "Showdown"
            },
            {
                "question": "В каком режиме команда получает звезды за убийства, и побеждает та, у которой больше звезд?",
                "answer": "Баунти",
                "hint": "Bounty"
            },
            {
                "question": "Как называется режим, где нужно защищать свою базу от робота и разрушить вражескую?",
                "answer": "Осада",
                "hint": "Его удалили"
            },
            {
                "question": "В каком режиме нужно контролировать зону, которая приносит очки вашей команде?",
                "answer": "Горячая зона",
                "hint": "Горячая"
            },
            {
                "question": "Как называется режим, где команда должна выиграть 2 раунда из 3, без возрождения?",
                "answer": "Нокаут",
                "hint": "Нок***"
            },
            {
                "question": "В каком режиме нужно забить мяч в ворота соперника 2 раза?",
                "answer": "Футбол",
                "hint": "Brawl Ball"
            },
            {
                "question": "Как называется одиночный режим, где 10 игроков сражаются друг с другом?",
                "answer": "шд",
                "hint": "Solo Showdown"
            },
            {
                "question": "В каком режиме команда из 3 человек сражается с огромным роботом?",
                "answer": "роборубка",
                "hint": "Boss Fight"
            },
            {
                "question": "Как называется режим, где нужно пройти 5 этапов, уничтожая город?",
                "answer": "Город супергероев",
                "hint": "Super City Rampage"
            },
            
            # Вопросы о бойцах
            {
                "question": "Как зовут бойца, который имеет пса по имени Брюс?",
                "answer": "Нита",
                "hint": "Nita"
            },
            {
                "question": "Какой боец стреляет двумя пистолетами?",
                "answer": "Кольт",
                "hint": "Colt"
            },
            {
                "question": "Как зовут бойца, который кидает динамитные шашки и имеет сверхспособность 'Большая бомба'?",
                "answer": "Динамайк",
                "hint": "Dynamike"
            },
            {
                "question": "Какой боец может лечить союзников и имеет дочку Джесси?",
                "answer": "Пэм",
                "hint": "Pam"
            },
            {
                "question": "Как зовут бойца с чупиком, который телепортируется через свою сверхспособность?",
                "answer": "Леон",
                "hint": "Leon"
            },
            {
                "question": "Какой боец юзает карты и имеет сверхспособность, которая создает клонов?",
                "answer": "Тара",
                "hint": "Tara"
            },
            {
                "question": "Как зовут бойца с битой, который стреляет жевачками (кстати название нашего бота)?",
                "answer": "Биби",
                "hint": "Bibi"
            },
            {
                "question": "Какой боец использует гитару и лечит союзников?",
                "answer": "Поко",
                "hint": "Poco"
            },
            {
                "question": "Как зовут бойца ракетницой?",
                "answer": "Брок",
                "hint": "Brock"
            },
            {
                "question": "Какой боец выглядет как бочка и имеет 2 заряда ульты?",
                "answer": "Булл",
                "hint": "Bull"
            },
            
            # Вопросы об истории игры
            {
                "question": "В каком году вышла игра Brawl Stars в глобальном релизе?",
                "answer": "2018",
                "hint": "Год выхода 20XX"
            },
            {
                "question": "Как назывался первый режим в Brawl Stars, который был удален?",
                "answer": "осада",
                "hint": "легендарная ос**а"
            },
            {
                "question": "Какой легендарный боец был добавлен в игру первым?",
                "answer": "Спайк",
                "hint": "Кактус"
            },
            {
                "question": "В каком обновлении добавили режим 'Королевская битва'?",
                "answer": "Июль 2018",
                "hint": "месяц лета 2018"
            },
            {
                "question": "Как назывался первый скин для Шелли, добавленный в игру?",
                "answer": "Бандитка Шелли",
                "hint": "Бандит епта"
            },
            {
                "question": "Сколько трофеев нужно было для открытия эмз в трофейной дороге стар?",
                "answer": "8000",
                "hint": "меньше 10000"
            },
            {
                "question": "Какой боец был награжден за участие в бета-тесте Brawl Stars?",
                "answer": "звездная шелли",
                "hint": "Star Shelly"
            },
            {
                "question": "В каком году Brawl Stars вышла из бета-тестирования?",
                "answer": "2017",
                "hint": "Год, когда игра была доступна только в Канаде"
            },
            {
                "question": "Какой первый легендарный боец был добавлен в Brawl Stars после Спайка?",
                "answer": "Кроу",
                "hint": "Ворона"
            },
            {
                "question": "Как назывался ивент, где можно было получить эксклюзивного бойца Галеон?",
                "answer": "Ретро",
                "hint": "Ностальгический ивент"
            }
        ]

    # ==================== ОТСЛЕЖИВАНИЕ АКТИВНОСТИ ====================

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        """Начисление монет за сообщения и обработка загадок"""
        if message.author.bot:
            return

        # Обработка загадок в специальном канале
        if message.channel.id == self.riddle_channel_id:
            if not self.active_riddle or self.riddle_solved:
                # Если нет активной загадки, создаем новую
                self.active_riddle = random.choice(self.riddles)
                self.riddle_solved = False
                
                embed = disnake.Embed(
                    title="🎯 НОВАЯ ЗАГАДКА BRAWL STARS! 🎯",
                    description=f"**{self.active_riddle['question']}**\n\n💡 **Подсказка:** ||{self.active_riddle['hint']}||",
                    color=disnake.Color.purple()
                )
                embed.set_footer(text="Ответь правильно и получи 150 монет!")
                await message.channel.send(embed=embed)
                return

            # Проверяем ответ
            answer_lower = message.content.lower().strip()
            correct_answer_lower = self.active_riddle['answer'].lower()

            if answer_lower == correct_answer_lower or answer_lower in self.get_answer_variants(correct_answer_lower):
                if not self.riddle_solved:
                    self.riddle_solved = True

                    await self.update_balance(message.author.id, message.guild.id, 150)

                    embed = disnake.Embed(
                        title="✅ ПРАВИЛЬНЫЙ ОТВЕТ! ✅",
                        description=f"{message.author.mention} правильно ответил на загадку!\n\n"
                                   f"**Ответ:** {self.active_riddle['answer']}\n\n"
                                   f"🎉 Вы получили **150** 🪙!",
                        color=disnake.Color.green()
                    )
                    await message.channel.send(embed=embed)

                    log_embed = disnake.Embed(
                        title="🎯 Решена загадка",
                        color=disnake.Color.green(),
                        timestamp=self.get_current_time()
                    )
                    log_embed.add_field(name="👤 Пользователь", value=message.author.mention, inline=True)
                    log_embed.add_field(name="💰 Награда", value="150 🪙", inline=True)
                    log_embed.add_field(name="❓ Вопрос", value=self.active_riddle['question'], inline=False)
                    await self.send_log(message.guild, log_embed)

                    self.active_riddle = None
                return

        # Начисление монет за сообщения (только не в канале загадок)
        if not message.guild:
            return

        cursor = self.db.cursor()

        cursor.execute('SELECT last_message_time FROM economy WHERE user_id = ? AND guild_id = ?',
                       (message.author.id, message.guild.id))
        result = cursor.fetchone()

        if result and result[0]:
            last_time = datetime.datetime.fromisoformat(result[0])
            if (self.get_current_time() - last_time).total_seconds() < 60:
                return

        coins_gain = random.randint(5, 15)

        await self.add_coins_for_activity(message.author.id, message.guild.id, coins_gain, "сообщение в чате")

        cursor.execute('''
            UPDATE economy 
            SET last_message_time = ?, messages_count = COALESCE(messages_count, 0) + 1
            WHERE user_id = ? AND guild_id = ?
        ''', (self.get_current_time().isoformat(), message.author.id, message.guild.id))

        if cursor.rowcount == 0:
            cursor.execute('''
                INSERT INTO economy (user_id, guild_id, last_message_time, messages_count)
                VALUES (?, ?, ?, 1)
            ''', (message.author.id, message.guild.id, self.get_current_time().isoformat()))

        self.db.commit()

    def get_answer_variants(self, correct_answer: str):
        """Возвращает варианты ответов для разных режимов/бойцов"""
        variants = {
            "захват кристаллов": ["gem grab", "гем граб", "кристаллы"],
            "королевская битва": ["showdown", "шоудаун"],
            "охота на звезды": ["bounty", "баунти"],
            "осада": ["siege", "сидж"],
            "горячая зона": ["hot zone", "хот зон"],
            "нокаут": ["knockout", "нокдаун"],
            "футбол": ["brawl ball", "бравл бол"],
            "одиночный бой": ["solo", "соло"],
            "нашествие монстров": ["boss fight", "босс файт"],
            "город супергероев": ["super city", "супер сити"],
            "нита": ["nita"],
            "кольт": ["colt"],
            "динамайк": ["dynamike"],
            "пэм": ["pam"],
            "леон": ["leon"],
            "тара": ["tara"],
            "биби": ["bibi"],
            "поко": ["poco"],
            "брок": ["brock"],
            "булл": ["bull"],
            "спайк": ["spike"],
            "кроу": ["crow"]
        }
        return variants.get(correct_answer, [])

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState,
                                    after: disnake.VoiceState):
        """Начисление монет за нахождение в голосовом канале"""
        cursor = self.db.cursor()

        if after.channel and not before.channel:
            current_time = self.get_current_time().isoformat()
            cursor.execute('''
                INSERT INTO economy (user_id, guild_id, current_voice_session_start)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                current_voice_session_start = ?
            ''', (member.id, member.guild.id, current_time, current_time))
            self.db.commit()

        elif before.channel and not after.channel:
            cursor.execute('SELECT current_voice_session_start FROM economy WHERE user_id = ? AND guild_id = ?',
                           (member.id, member.guild.id))
            result = cursor.fetchone()

            if result and result[0]:
                start_time = datetime.datetime.fromisoformat(result[0])
                end_time = self.get_current_time()
                duration = int((end_time - start_time).total_seconds())

                if duration >= 60:
                    coins_gain = (duration // 60) * 2

                    if coins_gain > 0:
                        await self.add_coins_for_activity(member.id, member.guild.id, coins_gain, "голосовой канал")

                        cursor.execute('''
                            UPDATE economy 
                            SET voice_time = voice_time + ?, current_voice_session_start = NULL
                            WHERE user_id = ? AND guild_id = ?
                        ''', (duration, member.id, member.guild.id))
                        self.db.commit()

    # ==================== КОМАНДЫ ====================

    @commands.slash_command(name="balance", description="Показать ваш баланс")
    async def balance(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            user: Optional[disnake.Member] = commands.Param(default=None, description="Пользователь")
    ):
        """Показать баланс пользователя"""

        target_user = user or interaction.author

        cursor = self.db.cursor()
        cursor.execute('''
            SELECT balance, total_earned, total_spent, messages_count, voice_time 
            FROM economy 
            WHERE user_id = ? AND guild_id = ?
        ''', (target_user.id, interaction.guild.id))

        result = cursor.fetchone()

        if not result:
            balance = 0
            total_earned = 0
            total_spent = 0
            messages = 0
            voice_time = 0
        else:
            balance, total_earned, total_spent, messages, voice_time = result

        voice_hours = voice_time // 3600
        voice_minutes = (voice_time % 3600) // 60

        embed = disnake.Embed(
            title=f"💰 Баланс {target_user.display_name}",
            color=disnake.Color.gold(),
            timestamp=self.get_current_time()
        )

        embed.set_thumbnail(url=target_user.display_avatar.url)

        embed.add_field(
            name="🪙 Монеты",
            value=f"**{balance:,}** 🪙",
            inline=False
        )

        embed.add_field(
            name="📊 Статистика",
            value=f"**Всего заработано:** {total_earned:,} 🪙\n"
                  f"**Всего потрачено:** {total_spent:,} 🪙\n"
                  f"**💬 Сообщений:** {messages:,}\n"
                  f"**🎙️ В голосовых каналах:** {voice_hours}ч {voice_minutes}м",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @commands.slash_command(name="daily", description="Получить ежедневную награду")
    async def daily(self, interaction: disnake.ApplicationCommandInteraction):
        """Ежедневная награда (от 90 до 150 монет)"""

        cursor = self.db.cursor()
        cursor.execute('SELECT daily_last_claim FROM economy WHERE user_id = ? AND guild_id = ?',
                       (interaction.author.id, interaction.guild.id))
        result = cursor.fetchone()

        if result and result[0]:
            last_claim = datetime.datetime.fromisoformat(result[0])
            time_passed = (self.get_current_time() - last_claim).total_seconds()

            if time_passed < 86400:
                remaining = 86400 - time_passed
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)

                embed = disnake.Embed(
                    title="⏰ Уже получили!",
                    description=f"Вы уже получили ежедневную награду сегодня.\nСледующая награда через **{hours}ч {minutes}м**",
                    color=disnake.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        reward = random.randint(90, 150)

        await self.update_balance(interaction.author.id, interaction.guild.id, reward)

        cursor.execute('''
            INSERT INTO economy (user_id, guild_id, daily_last_claim)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET
            daily_last_claim = ?
        ''', (interaction.author.id, interaction.guild.id, self.get_current_time().isoformat(),
              self.get_current_time().isoformat()))
        self.db.commit()

        embed = disnake.Embed(
            title="🎁 Ежедневная награда!",
            description=f"Вы получили **{reward}** 🪙",
            color=disnake.Color.green(),
            timestamp=self.get_current_time()
        )
        embed.add_field(name="💰 Новый баланс",
                        value=f"{await self.get_balance(interaction.author.id, interaction.guild.id):,} 🪙",
                        inline=False)

        await interaction.response.send_message(embed=embed)

        log_embed = disnake.Embed(
            title="🎁 Ежедневная награда",
            color=disnake.Color.green(),
            timestamp=self.get_current_time()
        )
        log_embed.add_field(name="👤 Пользователь", value=interaction.author.mention, inline=True)
        log_embed.add_field(name="💰 Награда", value=f"{reward} 🪙", inline=True)
        await self.send_log(interaction.guild, log_embed)

    @commands.slash_command(name="work", description="Работа и получение монет")
    async def work(self, interaction: disnake.ApplicationCommandInteraction):
        """Работа (от 90 до 150 монет, раз в 24 часа)"""

        cursor = self.db.cursor()
        cursor.execute('SELECT work_last_claim FROM economy WHERE user_id = ? AND guild_id = ?',
                       (interaction.author.id, interaction.guild.id))
        result = cursor.fetchone()

        if result and result[0]:
            last_claim = datetime.datetime.fromisoformat(result[0])
            time_passed = (self.get_current_time() - last_claim).total_seconds()

            if time_passed < 86400:
                remaining = 86400 - time_passed
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)

                embed = disnake.Embed(
                    title="⏰ Уже работали!",
                    description=f"Вы уже работали сегодня.\nСледующая работа через **{hours}ч {minutes}м**",
                    color=disnake.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        # Работы в стиле Brawl Stars
        jobs = [
            "🏆 Участвовал в турнире по захвату кристаллов",
            "🎮 Стримил режим Нокаут на Twitch",
            "💪 Тренировался в Королевской битве",
            "🔧 Чинил кубки после режима Осада",
            "🎨 Рисовал карты для режима Горячая зона",
            "📹 Снимал гайды по режиму Футбол",
            "🏅 Проводил тренировку по режиму Звездная битва",
            "⚔️ Участвовал в клановой войне в режиме Нашествие",
            "🎯 Собирал кубки в режиме Выталкивание",
            "🤝 Помогал друзьям в режиме Контроль точек"
        ]

        reward = random.randint(90, 150)

        await self.update_balance(interaction.author.id, interaction.guild.id, reward)

        cursor.execute('''
            INSERT INTO economy (user_id, guild_id, work_last_claim)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET
            work_last_claim = ?
        ''', (interaction.author.id, interaction.guild.id, self.get_current_time().isoformat(),
              self.get_current_time().isoformat()))
        self.db.commit()

        job = random.choice(jobs)

        embed = disnake.Embed(
            title="💼 Работа",
            description=f"**{job}**\nВы заработали **{reward}** 🪙",
            color=disnake.Color.green(),
            timestamp=self.get_current_time()
        )
        embed.add_field(name="💰 Новый баланс",
                        value=f"{await self.get_balance(interaction.author.id, interaction.guild.id):,} 🪙",
                        inline=False)

        await interaction.response.send_message(embed=embed)

        log_embed = disnake.Embed(
            title="💼 Работа",
            color=disnake.Color.green(),
            timestamp=self.get_current_time()
        )
        log_embed.add_field(name="👤 Пользователь", value=interaction.author.mention, inline=True)
        log_embed.add_field(name="💰 Заработал", value=f"{reward} 🪙", inline=True)
        log_embed.add_field(name="📝 Работа", value=job, inline=False)
        await self.send_log(interaction.guild, log_embed)

    @commands.slash_command(name="shop", description="Магазин ролей")
    async def shop(self, interaction: disnake.ApplicationCommandInteraction):
        """Показать магазин ролей"""

        cursor = self.db.cursor()
        cursor.execute('SELECT role_name, role_price, role_description FROM shop_roles')
        roles = cursor.fetchall()

        if not roles:
            embed = disnake.Embed(
                title="🏪 Магазин",
                description="В магазине пока нет товаров",
                color=disnake.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
            return

        embed = disnake.Embed(
            title="🏪 Магазин ролей",
            description="Купите себе уникальные роли за монеты!",
            color=disnake.Color.gold(),
            timestamp=self.get_current_time()
        )

        for role_name, price, desc in roles:
            embed.add_field(
                name=f"{role_name} - {price} 🪙",
                value=desc,
                inline=False
            )

        embed.set_footer(text="Используйте /buy [роль] чтобы купить роль")

        await interaction.response.send_message(embed=embed)

    @commands.slash_command(name="buy", description="Купить роль в магазине")
    async def buy(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            role_name: str = commands.Param(description="Название роли (Top4ik, Kaif, Kentik)")
    ):
        """Купить роль"""

        cursor = self.db.cursor()
        cursor.execute('SELECT role_price, role_description, role_color FROM shop_roles WHERE role_name = ?',
                       (role_name,))
        result = cursor.fetchone()

        if not result:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description=f"Роль **{role_name}** не найдена в магазине!\nДоступные роли: Top4ik, Kaif, Kentik",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        price, description, color = result

        balance = await self.get_balance(interaction.author.id, interaction.guild.id)

        if balance < price:
            embed = disnake.Embed(
                title="❌ Недостаточно монет",
                description=f"Вам нужно еще **{price - balance}** 🪙 для покупки роли **{role_name}**",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Проверяем, не куплена ли уже роль
        cursor.execute('SELECT * FROM purchased_roles WHERE user_id = ? AND guild_id = ? AND role_name = ?',
                       (interaction.author.id, interaction.guild.id, role_name))
        if cursor.fetchone():
            embed = disnake.Embed(
                title="❌ Уже есть",
                description=f"У вас уже есть роль **{role_name}**",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Ищем существующую роль или создаем новую
        role = disnake.utils.get(interaction.guild.roles, name=role_name)

        if not role:
            try:
                color_value = int(color.replace("0x", ""), 16) if color.startswith("0x") else int(color, 16)
                
                role = await interaction.guild.create_role(
                    name=role_name,
                    color=disnake.Color(color_value),
                    reason=f"Создание роли для магазина",
                    mentionable=True
                )
            except Exception as e:
                print(f"Ошибка создания роли: {e}")
                embed = disnake.Embed(
                    title="❌ Ошибка",
                    description="Не удалось создать роль. Обратитесь к администратору.",
                    color=disnake.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        # Выдаем роль пользователю
        try:
            await interaction.author.add_roles(role, reason=f"Покупка роли за {price} монет")
        except Exception as e:
            print(f"Ошибка выдачи роли: {e}")
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Не удалось выдать роль. Возможно, у бота недостаточно прав.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Снимаем монеты
        await self.remove_balance(interaction.author.id, interaction.guild.id, price)

        # Сохраняем в базу
        cursor.execute('''
            INSERT INTO purchased_roles (user_id, guild_id, role_name, purchase_date)
            VALUES (?, ?, ?, ?)
        ''', (interaction.author.id, interaction.guild.id, role_name, self.get_current_time().isoformat()))
        self.db.commit()

        embed = disnake.Embed(
            title="✅ Покупка успешна!",
            description=f"Вы купили роль **{role_name}** за **{price}** 🪙",
            color=disnake.Color.green(),
            timestamp=self.get_current_time()
        )
        embed.add_field(name="💰 Новый баланс",
                        value=f"{await self.get_balance(interaction.author.id, interaction.guild.id):,} 🪙",
                        inline=False)
        embed.add_field(name="🏷️ Описание", value=description, inline=False)

        await interaction.response.send_message(embed=embed)

        log_embed = disnake.Embed(
            title="🛒 Покупка роли",
            color=disnake.Color.green(),
            timestamp=self.get_current_time()
        )
        log_embed.add_field(name="👤 Пользователь", value=interaction.author.mention, inline=True)
        log_embed.add_field(name="🎭 Роль", value=role_name, inline=True)
        log_embed.add_field(name="💰 Цена", value=f"{price} 🪙", inline=True)
        await self.send_log(interaction.guild, log_embed)

    @commands.slash_command(name="inventory", description="Показать ваши купленные роли")
    async def inventory(self, interaction: disnake.ApplicationCommandInteraction):
        """Показать купленные роли"""

        cursor = self.db.cursor()
        cursor.execute('SELECT role_name, purchase_date FROM purchased_roles WHERE user_id = ? AND guild_id = ?',
                       (interaction.author.id, interaction.guild.id))
        roles = cursor.fetchall()

        if not roles:
            embed = disnake.Embed(
                title="📦 Инвентарь",
                description="У вас пока нет купленных ролей",
                color=disnake.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
            return

        embed = disnake.Embed(
            title=f"📦 Инвентарь {interaction.author.display_name}",
            color=disnake.Color.gold(),
            timestamp=self.get_current_time()
        )

        embed.set_thumbnail(url=interaction.author.display_avatar.url)

        for role_name, purchase_date in roles:
            date = datetime.datetime.fromisoformat(purchase_date)
            embed.add_field(
                name=f"🎭 {role_name}",
                value=f"Куплена: <t:{int(date.timestamp())}:R>",
                inline=False
            )

        await interaction.response.send_message(embed=embed)


def setup(bot):
    bot.add_cog(EconomySystem(bot))
