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
        
        # Запускаем автоматическую публикацию загадок
        self.post_riddle.start()

    def init_database(self):
        """Инициализация базы данных"""
        self.db = sqlite3.connect('economy.db')
        cursor = self.db.cursor()

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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchased_roles (
                user_id INTEGER,
                guild_id INTEGER,
                role_name TEXT,
                purchase_date TIMESTAMP,
                PRIMARY KEY (user_id, guild_id, role_name)
            )
        ''')

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
        return datetime.datetime.now(datetime.timezone.utc)

    async def send_log(self, guild: disnake.Guild, embed: disnake.Embed):
        try:
            channel = self.bot.get_channel(self.log_channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(self.log_channel_id)
            await channel.send(embed=embed)
        except:
            pass

    async def get_balance(self, user_id: int, guild_id: int) -> int:
        cursor = self.db.cursor()
        cursor.execute('SELECT balance FROM economy WHERE user_id = ? AND guild_id = ?', (user_id, guild_id))
        result = cursor.fetchone()
        return result[0] if result else 0

    async def update_balance(self, user_id: int, guild_id: int, amount: int):
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

    # ==================== АВТОМАТИЧЕСКАЯ ПУБЛИКАЦИЯ ЗАГАДОК КАЖДЫЕ 30 МИНУТ ====================
    
    @tasks.loop(minutes=30)
    async def post_riddle(self):
        """Публикует новую загадку каждые 30 минут"""
        await asyncio.sleep(10)  # Ждем запуска бота
        while True:
            try:
                channel = self.bot.get_channel(self.riddle_channel_id)
                if channel:
                    # Выбираем случайную загадку
                    self.active_riddle = random.choice(self.riddles)
                    self.riddle_solved = False
                    
                    embed = disnake.Embed(
                        title="🎯 НОВАЯ ЗАГАДКА BRAWL STARS! 🎯",
                        description=f"**{self.active_riddle['question']}**\n\n💡 **Подсказка:** ||{self.active_riddle['hint']}||",
                        color=disnake.Color.purple()
                    )
                    embed.set_footer(text="Ответь правильно и получи 150 монет! | Следующая загадка через 30 минут")
                    await channel.send(embed=embed)
                    
                    # Логируем
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

    # ==================== ЗАГАДКИ ПРО BRAWL STARS ====================
    
    @property
    def riddles(self):
        return [
            # Режимы
            {"question": "В каком режиме нужно собрать 10 кристаллов, появляющихся в центре карты?", "answer": "Захват кристаллов", "hint": "Gem Grab"},
            {"question": "Как называется режим, где нужно выбить всех врагов из зоны, которая постепенно сужается?", "answer": "Королевская битва", "hint": "Showdown"},
            {"question": "В каком режиме команда получает звезды за убийства?", "answer": "Охота на звезды", "hint": "Bounty"},
            {"question": "Как называется режим, где нужно защищать свою базу от робота?", "answer": "Осада", "hint": "Siege"},
            {"question": "В каком режиме нужно контролировать зону, которая приносит очки?", "answer": "Горячая зона", "hint": "Hot Zone"},
            {"question": "Как называется режим, где команда должна выиграть 2 раунда из 3?", "answer": "Нокаут", "hint": "Knockout"},
            {"question": "В каком режиме нужно забить мяч в ворота соперника 2 раза?", "answer": "Футбол", "hint": "Brawl Ball"},
            {"question": "Как называется одиночный режим, где 10 игроков сражаются друг с другом?", "answer": "Одиночный бой", "hint": "Solo Showdown"},
            {"question": "В каком режиме команда из 3 человек сражается с огромным роботом?", "answer": "Нашествие монстров", "hint": "Boss Fight"},
            # Бойцы
            {"question": "Как зовут бойца, который мечет бумеранг и имеет пса по имени Брюс?", "answer": "Нита", "hint": "Nita"},
            {"question": "Какой боец стреляет двумя пистолетами?", "answer": "Кольт", "hint": "Colt"},
            {"question": "Как зовут бойца, который кидает динамитные шашки?", "answer": "Динамайк", "hint": "Dynamike"},
            {"question": "Какой боец может лечить союзников и имеет птицу по имени Чико?", "answer": "Пэм", "hint": "Pam"},
            {"question": "Как зовут бойца с дробовиком, который может становиться невидимым?", "answer": "Леон", "hint": "Leon"},
            {"question": "Какой боец мечет карты и создает клонов?", "answer": "Тара", "hint": "Tara"},
            {"question": "Как зовут бойца с битой, который отбивает снаряды?", "answer": "Биби", "hint": "Bibi"},
            {"question": "Какой боец играет на флейте и лечит союзников?", "answer": "Поко", "hint": "Poco"},
            {"question": "Как зовут бойца с реактивным ранцем?", "answer": "Брок", "hint": "Brock"},
            {"question": "Какой боец бросает бочки и заряжается сквозь стены?", "answer": "Булл", "hint": "Bull"},
            # История
            {"question": "В каком году вышла игра Brawl Stars в глобальном релизе?", "answer": "2018", "hint": "Год выхода 20XX"},
            {"question": "Какой легендарный боец был добавлен в игру первым?", "answer": "Спайк", "hint": "Кактус"},
            {"question": "В каком обновлении добавили режим 'Королевская битва'?", "answer": "Июль 2018", "hint": "Лето 2018"},
            {"question": "Какой боец был наградой за бета-тест Brawl Stars?", "answer": "Стар Шелли", "hint": "Star Shelly"},
            {"question": "Какой первый легендарный боец был добавлен после Спайка?", "answer": "Кроу", "hint": "Ворона"}
        ]

    def get_answer_variants(self, correct_answer: str):
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

    # ==================== ОБРАБОТКА СООБЩЕНИЙ (ТОЛЬКО ДЛЯ ОТВЕТОВ) ====================

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        """Обработка ответов на загадки и начисление монет за сообщения"""
        if message.author.bot:
            return

        # === ОБРАБОТКА ЗАГАДОК (ТОЛЬКО В КАНАЛЕ ЗАГАДОК) ===
        if message.channel.id == self.riddle_channel_id:
            # Если нет активной загадки - ничего не делаем (ждем следующую по таймеру)
            if not self.active_riddle or self.riddle_solved:
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
                    
                    # active_riddle остается, но помечен как solved
                    # Следующая загадка появится через 30 минут по таймеру
                return

        # === НАЧИСЛЕНИЕ МОНЕТ ЗА СООБЩЕНИЯ (В ДРУГИХ КАНАЛАХ) ===
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
        embed.add_field(name="🪙 Монеты", value=f"**{balance:,}** 🪙", inline=False)
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
                    description=f"Следующая награда через **{hours}ч {minutes}м**",
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
                    description=f"Следующая работа через **{hours}ч {minutes}м**",
                    color=disnake.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        jobs = [
            "🏆 Участвовал в турнире по захвату кристаллов",
            "🎮 Стримил режим Нокаут на Twitch",
            "💪 Тренировался в Королевской битве",
            "🔧 Чинил кубки после режима Осада",
            "🎨 Рисовал карты для режима Горячая зона"
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

    @commands.slash_command(name="shop", description="Магазин ролей")
    async def shop(self, interaction: disnake.ApplicationCommandInteraction):
        cursor = self.db.cursor()
        cursor.execute('SELECT role_name, role_price, role_description FROM shop_roles')
        roles = cursor.fetchall()

        if not roles:
            embed = disnake.Embed(title="🏪 Магазин", description="В магазине пока нет товаров", color=disnake.Color.orange())
            await interaction.response.send_message(embed=embed)
            return

        embed = disnake.Embed(title="🏪 Магазин ролей", description="Купите себе уникальные роли!", color=disnake.Color.gold())
        for role_name, price, desc in roles:
            embed.add_field(name=f"{role_name} - {price} 🪙", value=desc, inline=False)
        embed.set_footer(text="Используйте /buy [роль] чтобы купить роль")
        await interaction.response.send_message(embed=embed)

    @commands.slash_command(name="buy", description="Купить роль в магазине")
    async def buy(self, interaction: disnake.ApplicationCommandInteraction, role_name: str = commands.Param(description="Top4ik, Kaif или Kentik")):
        cursor = self.db.cursor()
        cursor.execute('SELECT role_price, role_description, role_color FROM shop_roles WHERE role_name = ?', (role_name,))
        result = cursor.fetchone()

        if not result:
            embed = disnake.Embed(title="❌ Ошибка", description=f"Роль **{role_name}** не найдена!", color=disnake.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        price, description, color = result
        balance = await self.get_balance(interaction.author.id, interaction.guild.id)

        if balance < price:
            embed = disnake.Embed(title="❌ Недостаточно монет", description=f"Нужно еще **{price - balance}** 🪙", color=disnake.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        cursor.execute('SELECT * FROM purchased_roles WHERE user_id = ? AND role_name = ?', (interaction.author.id, role_name))
        if cursor.fetchone():
            embed = disnake.Embed(title="❌ Уже есть", description=f"У вас уже есть роль **{role_name}**", color=disnake.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        role = disnake.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            color_value = int(color.replace("0x", ""), 16)
            role = await interaction.guild.create_role(name=role_name, color=disnake.Color(color_value), mentionable=True)

        await interaction.author.add_roles(role)
        await self.remove_balance(interaction.author.id, interaction.guild.id, price)

        cursor.execute('INSERT INTO purchased_roles (user_id, guild_id, role_name, purchase_date) VALUES (?, ?, ?, ?)',
                       (interaction.author.id, interaction.guild.id, role_name, self.get_current_time().isoformat()))
        self.db.commit()

        embed = disnake.Embed(title="✅ Покупка успешна!", description=f"Вы купили роль **{role_name}** за **{price}** 🪙", color=disnake.Color.green())
        await interaction.response.send_message(embed=embed)

    @commands.slash_command(name="inventory", description="Показать ваши купленные роли")
    async def inventory(self, interaction: disnake.ApplicationCommandInteraction):
        cursor = self.db.cursor()
        cursor.execute('SELECT role_name, purchase_date FROM purchased_roles WHERE user_id = ?', (interaction.author.id,))
        roles = cursor.fetchall()

        if not roles:
            embed = disnake.Embed(title="📦 Инвентарь", description="У вас пока нет купленных ролей", color=disnake.Color.orange())
            await interaction.response.send_message(embed=embed)
            return

        embed = disnake.Embed(title=f"📦 Инвентарь {interaction.author.display_name}", color=disnake.Color.gold())
        embed.set_thumbnail(url=interaction.author.display_avatar.url)
        for role_name, purchase_date in roles:
            date = datetime.datetime.fromisoformat(purchase_date)
            embed.add_field(name=f"🎭 {role_name}", value=f"Куплена: <t:{int(date.timestamp())}:R>", inline=False)
        await interaction.response.send_message(embed=embed)


def setup(bot):
    bot.add_cog(EconomySystem(bot))
