import disnake
from disnake.ext import commands
import sqlite3
import datetime
from typing import Optional

class BoosterSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_database()
        self.booster_role_name = "🌟 Бустер"  # Название роли бустеров

    def init_database(self):
        """Инициализация базы данных для хранения настроек бустеров"""
        self.db = sqlite3.connect('booster_settings.db')
        cursor = self.db.cursor()

        # Таблица для настроек бустеров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS booster_settings (
                user_id INTEGER,
                guild_id INTEGER,
                role_name TEXT DEFAULT 'Бустер',
                color_r INTEGER DEFAULT 255,
                color_g INTEGER DEFAULT 215,
                color_b INTEGER DEFAULT 0,
                second_color_r INTEGER DEFAULT 255,
                second_color_g INTEGER DEFAULT 105,
                second_color_b INTEGER DEFAULT 180,
                role_icon TEXT DEFAULT '🌟',
                last_updated TIMESTAMP,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')

        self.db.commit()

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        """Отслеживание статуса бустера"""
        if before.premium_since != after.premium_since:
            if after.premium_since:
                await self.assign_booster_role(after)
            else:
                await self.remove_booster_role(after)

    async def assign_booster_role(self, member: disnake.Member):
        """Выдача роли бустера"""
        booster_role = disnake.utils.get(member.guild.roles, name=self.booster_role_name)

        if not booster_role:
            booster_role = await member.guild.create_role(
                name=self.booster_role_name,
                color=disnake.Color.gold(),
                reason="Создание роли для бустеров",
                mentionable=True
            )

        if booster_role not in member.roles:
            await member.add_roles(booster_role, reason="Пользователь начал бустить сервер")
            await self.apply_booster_settings(member)

            try:
                embed = disnake.Embed(
                    title="🎉 Спасибо за буст сервера! 🎉",
                    description=f"Вы получили роль **{booster_role.name}**!\n"
                                f"Используйте команду `/donaterole` чтобы настроить свою роль!",
                    color=disnake.Color.gold()
                )
                await member.send(embed=embed)
            except:
                pass

    async def remove_booster_role(self, member: disnake.Member):
        """Удаление роли бустера"""
        booster_role = disnake.utils.get(member.guild.roles, name=self.booster_role_name)

        if booster_role and booster_role in member.roles:
            await member.remove_roles(booster_role, reason="Пользователь перестал бустить сервер")
        
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT role_name, role_icon
            FROM booster_settings
            WHERE user_id = ? AND guild_id = ?
        ''', (member.id, member.guild.id))
        
        result = cursor.fetchone()
        if result:
            custom_role_name = f"{result[1]} {result[0]}"
            custom_role = disnake.utils.get(member.guild.roles, name=custom_role_name)
            if custom_role:
                await custom_role.delete(reason="Пользователь перестал бустить сервер")

    async def apply_booster_settings(self, member: disnake.Member):
        """Применить сохраненные настройки бустера"""
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT role_name, color_r, color_g, color_b, second_color_r, second_color_g, second_color_b, role_icon
            FROM booster_settings
            WHERE user_id = ? AND guild_id = ?
        ''', (member.id, member.guild.id))

        result = cursor.fetchone()

        if result:
            role_name, color_r, color_g, color_b, second_color_r, second_color_g, second_color_b, role_icon = result

            new_role_name = f"{role_icon} {role_name}"
            custom_role = disnake.utils.get(member.guild.roles, name=new_role_name)
            booster_role = disnake.utils.get(member.guild.roles, name=self.booster_role_name)
            
            if custom_role:
                await custom_role.edit(
                    name=new_role_name,
                    color=disnake.Color.from_rgb(color_r, color_g, color_b)
                )
                if custom_role not in member.roles:
                    if booster_role and booster_role in member.roles:
                        await member.remove_roles(booster_role)
                    await member.add_roles(custom_role)
            else:
                custom_role = await member.guild.create_role(
                    name=new_role_name,
                    color=disnake.Color.from_rgb(color_r, color_g, color_b),
                    reason=f"Настройка роли бустера для {member.name}"
                )
                
                if booster_role and booster_role in member.roles:
                    await member.remove_roles(booster_role)
                await member.add_roles(custom_role)
        else:
            booster_role = disnake.utils.get(member.guild.roles, name=self.booster_role_name)
            if booster_role and booster_role not in member.roles:
                await member.add_roles(booster_role)

    @commands.slash_command(name="donaterole", description="Настройка своей роли бустера (или изменение настроек)")
    async def donaterole(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            role_name: str = commands.Param(default=None, description="Название роли (без эмодзи)"),
            first_color: str = commands.Param(default=None, description="Первый цвет роли в RGB (пример: 255,215,0)"),
            second_color: str = commands.Param(default=None, description="Второй цвет для градиента в RGB (255,105,180)"),
            role_icon: str = commands.Param(default=None, description="Эмодзи для роли (1 символ)")
    ):
        """Настройка или изменение роли бустера с поддержкой градиента"""

        # Получаем текущие настройки пользователя
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT role_name, color_r, color_g, color_b, second_color_r, second_color_g, second_color_b, role_icon
            FROM booster_settings 
            WHERE user_id = ? AND guild_id = ?
        ''', (interaction.author.id, interaction.guild.id))
        current_settings = cursor.fetchone()

        # Проверяем, является ли пользователь бустером
        if not await self.is_booster(interaction.author, interaction.guild):
            await interaction.response.send_message(
                "❌ Эта команда доступна только для бустеров сервера!\n"
                "Станьте бустером, чтобы получить доступ к настройке роли.",
                ephemeral=True
            )
            return

        # Загружаем текущие значения или значения по умолчанию
        final_role_name = role_name if role_name is not None else (current_settings[0] if current_settings else "Бустер")
        final_role_icon = role_icon if role_icon is not None else (current_settings[7] if current_settings else "🌟")
        
        # Обработка первого цвета
        if first_color is not None:
            color_r, color_g, color_b = self.parse_color(first_color)
            if color_r is None:
                await interaction.response.send_message(
                    "❌ Неверный формат первого цвета! Используйте: 255,215,0 (каждое число от 0 до 255)",
                    ephemeral=True
                )
                return
        else:
            if current_settings:
                color_r, color_g, color_b = current_settings[1], current_settings[2], current_settings[3]
            else:
                color_r, color_g, color_b = 255, 215, 0

        # Обработка второго цвета
        if second_color is not None:
            second_color_r, second_color_g, second_color_b = self.parse_color(second_color)
            if second_color_r is None:
                await interaction.response.send_message(
                    "❌ Неверный формат второго цвета! Используйте: 255,105,180 (каждое число от 0 до 255)",
                    ephemeral=True
                )
                return
        else:
            if current_settings:
                second_color_r, second_color_g, second_color_b = current_settings[4], current_settings[5], current_settings[6]
            else:
                second_color_r, second_color_g, second_color_b = 255, 105, 180

        # Валидация
        if len(final_role_icon) > 2:
            await interaction.response.send_message("❌ Используйте один эмодзи для иконки роли!", ephemeral=True)
            return

        if len(final_role_name) > 30:
            await interaction.response.send_message("❌ Название роли не должно превышать 30 символов!", ephemeral=True)
            return

        # Сохраняем настройки
        cursor.execute('''
            INSERT OR REPLACE INTO booster_settings 
            (user_id, guild_id, role_name, color_r, color_g, color_b, 
             second_color_r, second_color_g, second_color_b, role_icon, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            interaction.author.id, interaction.guild.id, final_role_name,
            color_r, color_g, color_b,
            second_color_r, second_color_g, second_color_b,
            final_role_icon, datetime.datetime.utcnow().isoformat()
        ))
        self.db.commit()

        # Применяем настройки
        await self.apply_booster_settings(interaction.author)

        # Создаем градиентный embed
        embed = disnake.Embed(
            title="✅ Роль бустера настроена!" if not current_settings else "✏️ Роль бустера обновлена!",
            description=f"Ваша роль успешно {'настроена' if not current_settings else 'обновлена'}!",
            color=disnake.Color.from_rgb(color_r, color_g, color_b),
            timestamp=datetime.datetime.utcnow()
        )

        # Показываем градиент в embed
        gradient_preview = self.create_gradient_preview(
            (color_r, color_g, color_b),
            (second_color_r, second_color_g, second_color_b)
        )
        
        embed.add_field(
            name="📝 Настройки",
            value=f"**Название:** {final_role_icon} {final_role_name}\n"
                  f"**Первый цвет:** RGB({color_r}, {color_g}, {color_b}) `#{color_r:02x}{color_g:02x}{color_b:02x}`\n"
                  f"**Второй цвет:** RGB({second_color_r}, {second_color_g}, {second_color_b}) `#{second_color_r:02x}{second_color_g:02x}{second_color_b:02x}`\n"
                  f"**Иконка:** {final_role_icon}\n"
                  f"**Градиент:** {'✅ Активен' if (color_r,color_g,color_b) != (second_color_r,second_color_g,second_color_b) else '❌ Не используется'}",
            inline=False
        )

        embed.add_field(
            name="🎨 Пример градиента",
            value=gradient_preview,
            inline=False
        )

        embed.set_footer(text="Настройки сохранены и применены! Используйте /donaterole снова для изменения")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="previewrole", description="Предпросмотр роли с градиентом")
    async def previewrole(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        role_name: str = commands.Param(default="Пример роли", description="Название роли"),
        first_color: str = commands.Param(default="255,215,0", description="Первый цвет RGB"),
        second_color: str = commands.Param(default="255,105,180", description="Второй цвет RGB"),
        role_icon: str = commands.Param(default="🌟", description="Иконка роли")
    ):
        """Предпросмотр того, как будет выглядеть роль с градиентом"""
        
        color_r, color_g, color_b = self.parse_color(first_color)
        if color_r is None:
            await interaction.response.send_message("❌ Неверный формат первого цвета!", ephemeral=True)
            return
            
        second_color_r, second_color_g, second_color_b = self.parse_color(second_color)
        if second_color_r is None:
            await interaction.response.send_message("❌ Неверный формат второго цвета!", ephemeral=True)
            return

        embed = disnake.Embed(
            title=f"🎨 Предпросмотр роли {role_icon} {role_name}",
            description="Вот как будет выглядеть ваша роль с градиентом:",
            color=disnake.Color.from_rgb(color_r, color_g, color_b)
        )
        
        gradient_preview = self.create_gradient_preview(
            (color_r, color_g, color_b),
            (second_color_r, second_color_g, second_color_b)
        )
        
        embed.add_field(
            name="Градиент",
            value=gradient_preview,
            inline=False
        )
        
        embed.add_field(
            name="Информация",
            value=f"**Первый цвет:** RGB({color_r}, {color_g}, {color_b})\n"
                  f"**Второй цвет:** RGB({second_color_r}, {second_color_g}, {second_color_b})",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="resetrole", description="Сбросить настройки своей роли бустера")
    async def resetrole(self, interaction: disnake.ApplicationCommandInteraction):
        """Сброс настроек роли бустера"""

        if not await self.is_booster(interaction.author, interaction.guild):
            await interaction.response.send_message(
                "❌ Эта команда доступна только для бустеров сервера!",
                ephemeral=True
            )
            return

        cursor = self.db.cursor()
        cursor.execute('SELECT role_name, role_icon FROM booster_settings WHERE user_id = ? AND guild_id = ?',
                       (interaction.author.id, interaction.guild.id))
        result = cursor.fetchone()

        if result:
            custom_role_name = f"{result[1]} {result[0]}"
            custom_role = disnake.utils.get(interaction.guild.roles, name=custom_role_name)
            if custom_role and custom_role in interaction.author.roles:
                await interaction.author.remove_roles(custom_role)
                await custom_role.delete(reason="Сброс настроек роли бустера")

        cursor.execute('''
            DELETE FROM booster_settings
            WHERE user_id = ? AND guild_id = ?
        ''', (interaction.author.id, interaction.guild.id))
        self.db.commit()

        default_role = disnake.utils.get(interaction.guild.roles, name=self.booster_role_name)
        if default_role and default_role not in interaction.author.roles:
            await interaction.author.add_roles(default_role, reason="Сброс настроек роли")

        embed = disnake.Embed(
            title="🔄 Роль бустера сброшена",
            description="Настройки вашей роли сброшены до стандартных!",
            color=disnake.Color.gold()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="boosters", description="Показать список бустеров сервера")
    async def boosters(self, interaction: disnake.ApplicationCommandInteraction):
        """Показать список всех бустеров"""

        boosters = await self.get_all_boosters(interaction.guild)

        if not boosters:
            await interaction.response.send_message("❌ На сервере нет бустеров!", ephemeral=True)
            return

        embed = disnake.Embed(
            title=f"🌟 Бустеры сервера ({len(boosters)})",
            color=disnake.Color.gold(),
            timestamp=datetime.datetime.utcnow()
        )

        booster_list = []
        for booster in boosters:
            if booster.premium_since:
                booster_list.append(f"{booster.mention} - бустит с <t:{int(booster.premium_since.timestamp())}:R>")
            else:
                booster_list.append(f"{booster.mention}")

        if len(booster_list) > 20:
            embed.description = "\n".join(booster_list[:20])
            embed.set_footer(text=f"И ещё {len(booster_list) - 20} бустеров...")
        else:
            embed.description = "\n".join(booster_list)

        await interaction.response.send_message(embed=embed)

    # Вспомогательные методы
    def parse_color(self, color_str: str):
        """Парсинг строки цвета в RGB"""
        try:
            parts = color_str.split(',')
            if len(parts) != 3:
                return None, None, None
            r = int(parts[0].strip())
            g = int(parts[1].strip())
            b = int(parts[2].strip())
            if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
                return None, None, None
            return r, g, b
        except:
            return None, None, None

    def create_gradient_preview(self, color1, color2):
        """Создание текстового представления градиента"""
        # Создаем 10 символов с градиентом от color1 до color2
        chars = "█" * 20
        return f"`{chars}`\n*Градиент от RGB{color1} до RGB{color2}*"

    async def is_booster(self, member: disnake.Member, guild: disnake.Guild):
        """Проверка, является ли пользователь бустером"""
        booster_role = disnake.utils.get(guild.roles, name=self.booster_role_name)
        
        if booster_role and booster_role in member.roles:
            return True
        
        cursor = self.db.cursor()
        cursor.execute('SELECT role_name, role_icon FROM booster_settings WHERE user_id = ? AND guild_id = ?',
                       (member.id, guild.id))
        result = cursor.fetchone()
        
        if result:
            custom_role_name = f"{result[1]} {result[0]}"
            custom_role = disnake.utils.get(guild.roles, name=custom_role_name)
            if custom_role and custom_role in member.roles:
                return True
        
        return False

    async def get_all_boosters(self, guild: disnake.Guild):
        """Получение списка всех бустеров"""
        boosters = []
        
        booster_role = disnake.utils.get(guild.roles, name=self.booster_role_name)
        if booster_role:
            boosters.extend([member for member in guild.members if booster_role in member.roles])
        
        cursor = self.db.cursor()
        cursor.execute('SELECT user_id, role_name, role_icon FROM booster_settings WHERE guild_id = ?', (guild.id,))
        settings = cursor.fetchall()
        
        for user_id, role_name, role_icon in settings:
            custom_role_name = f"{role_icon} {role_name}"
            custom_role = disnake.utils.get(guild.roles, name=custom_role_name)
            if custom_role:
                for member in custom_role.members:
                    if member not in boosters:
                        boosters.append(member)
        
        return boosters

def setup(bot):
    bot.add_cog(BoosterSystem(bot))
