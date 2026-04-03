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
                user_id INTEGER PRIMARY KEY,
                guild_id INTEGER,
                role_name TEXT DEFAULT '🌟 Бустер',
                color_r INTEGER DEFAULT 255,
                color_g INTEGER DEFAULT 215,
                color_b INTEGER DEFAULT 0,
                second_color_r INTEGER DEFAULT 255,
                second_color_g INTEGER DEFAULT 105,
                second_color_b INTEGER DEFAULT 180,
                role_icon TEXT DEFAULT '🌟',
                last_updated TIMESTAMP
            )
        ''')

        self.db.commit()

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        """Отслеживание статуса бустера"""
        # Проверяем, изменился ли статус бустера
        if before.premium_since != after.premium_since:
            if after.premium_since:
                # Пользователь начал бустить сервер
                await self.assign_booster_role(after)
            else:
                # Пользователь перестал бустить сервер
                await self.remove_booster_role(after)

    async def assign_booster_role(self, member: disnake.Member):
        """Выдача роли бустера"""
        # Проверяем, существует ли роль бустера
        booster_role = disnake.utils.get(member.guild.roles, name=self.booster_role_name)

        if not booster_role:
            # Создаем роль бустера если её нет
            booster_role = await member.guild.create_role(
                name=self.booster_role_name,
                color=disnake.Color.gold(),
                reason="Создание роли для бустеров",
                mentionable=True
            )

        # Выдаем роль
        if booster_role not in member.roles:
            await member.add_roles(booster_role, reason="Пользователь начал бустить сервер")

            # Применяем сохраненные настройки
            await self.apply_booster_settings(member)

            # Уведомление
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

            # Получаем роль бустера
            booster_role = disnake.utils.get(member.guild.roles, name=self.booster_role_name)

            if booster_role:
                # Создаем новую роль с настройками
                new_role_name = f"{role_icon} {role_name}"

                # Проверяем, существует ли уже кастомная роль
                custom_role = disnake.utils.get(member.guild.roles, name=new_role_name)

                if not custom_role:
                    # Создаем новую роль
                    custom_role = await member.guild.create_role(
                        name=new_role_name,
                        color=disnake.Color.from_rgb(color_r, color_g, color_b),
                        reason=f"Настройка роли бустера для {member.name}"
                    )

                    # Удаляем старую роль бустера
                    if booster_role in member.roles:
                        await member.remove_roles(booster_role)

                    # Добавляем новую роль
                    await member.add_roles(custom_role)
                else:
                    # Обновляем существующую роль
                    await custom_role.edit(
                        name=new_role_name,
                        color=disnake.Color.from_rgb(color_r, color_g, color_b)
                    )

    @commands.slash_command(name="donaterole", description="Настройка своей роли бустера")
    async def donaterole(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            role_name: str = commands.Param(default="Бустер", description="Название роли (без эмодзи)"),
            color: str = commands.Param(default="255,215,0", description="Цвет роли в RGB (пример: 255,215,0)"),
            second_color: str = commands.Param(default="255,105,180",
                                               description="Второй цвет роли в RGB (пока не используется)"),
            role_icon: str = commands.Param(default="🌟", description="Эмодзи для роли (1 символ)")
    ):
        """Настройка роли бустера"""

        # Проверяем, является ли пользователь бустером
        booster_role = disnake.utils.get(interaction.guild.roles, name=self.booster_role_name)

        if not booster_role or booster_role not in interaction.author.roles:
            await interaction.response.send_message(
                "❌ Эта команда доступна только для бустеров сервера!\n"
                "Станьте бустером, чтобы получить доступ к настройке роли.",
                ephemeral=True
            )
            return

        # Парсим цвета
        try:
            color_parts = color.split(',')
            if len(color_parts) != 3:
                raise ValueError
            color_r = int(color_parts[0].strip())
            color_g = int(color_parts[1].strip())
            color_b = int(color_parts[2].strip())

            # Проверяем диапазон RGB
            if not (0 <= color_r <= 255 and 0 <= color_g <= 255 and 0 <= color_b <= 255):
                raise ValueError

        except:
            await interaction.response.send_message(
                "❌ Неверный формат цвета! Используйте: 255,215,0 (каждое число от 0 до 255)",
                ephemeral=True
            )
            return

        # Парсим второй цвет
        try:
            second_color_parts = second_color.split(',')
            if len(second_color_parts) != 3:
                raise ValueError
            second_color_r = int(second_color_parts[0].strip())
            second_color_g = int(second_color_parts[1].strip())
            second_color_b = int(second_color_parts[2].strip())

            if not (0 <= second_color_r <= 255 and 0 <= second_color_g <= 255 and 0 <= second_color_b <= 255):
                raise ValueError

        except:
            await interaction.response.send_message(
                "❌ Неверный формат второго цвета! Используйте: 255,105,180 (каждое число от 0 до 255)",
                ephemeral=True
            )
            return

        # Проверяем эмодзи
        if len(role_icon) > 2:
            await interaction.response.send_message(
                "❌ Используйте один эмодзи для иконки роли!",
                ephemeral=True
            )
            return

        # Проверяем название роли
        if len(role_name) > 30:
            await interaction.response.send_message(
                "❌ Название роли не должно превышать 30 символов!",
                ephemeral=True
            )
            return

        # Сохраняем настройки в базу данных
        cursor = self.db.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO booster_settings 
            (user_id, guild_id, role_name, color_r, color_g, color_b, second_color_r, second_color_g, second_color_b, role_icon, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            interaction.author.id, interaction.guild.id, role_name,
            color_r, color_g, color_b,
            second_color_r, second_color_g, second_color_b,
            role_icon, datetime.datetime.utcnow().isoformat()
        ))
        self.db.commit()

        # Применяем настройки
        await self.apply_booster_settings(interaction.author)

        # Создаем embed с подтверждением
        embed = disnake.Embed(
            title="✅ Роль бустера настроена!",
            description=f"Ваша роль успешно настроена!",
            color=disnake.Color.from_rgb(color_r, color_g, color_b),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(
            name="📝 Настройки",
            value=f"**Название:** {role_icon} {role_name}\n"
                  f"**Цвет:** RGB({color_r}, {color_g}, {color_b})\n"
                  f"**Второй цвет:** RGB({second_color_r}, {second_color_g}, {second_color_b})\n"
                  f"**Иконка:** {role_icon}",
            inline=False
        )

        # Показываем пример роли
        embed.add_field(
            name="🎨 Пример",
            value=f"{role_icon} **{role_name}** - это ваша новая роль!",
            inline=False
        )

        embed.set_footer(text="Настройки сохранены и применены!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="resetrole", description="Сбросить настройки своей роли бустера")
    async def resetrole(self, interaction: disnake.ApplicationCommandInteraction):
        """Сброс настроек роли бустера"""

        # Проверяем, является ли пользователь бустером
        booster_role = disnake.utils.get(interaction.guild.roles, name=self.booster_role_name)

        if not booster_role or booster_role not in interaction.author.roles:
            await interaction.response.send_message(
                "❌ Эта команда доступна только для бустеров сервера!",
                ephemeral=True
            )
            return

        # Удаляем настройки из базы
        cursor = self.db.cursor()
        cursor.execute('''
            DELETE FROM booster_settings
            WHERE user_id = ? AND guild_id = ?
        ''', (interaction.author.id, interaction.guild.id))
        self.db.commit()

        # Сбрасываем роль
        # Находим кастомную роль
        cursor.execute('SELECT role_name, role_icon FROM booster_settings WHERE user_id = ? AND guild_id = ?',
                       (interaction.author.id, interaction.guild.id))
        result = cursor.fetchone()

        if result:
            old_role_name = f"{result[1]} {result[0]}"
            custom_role = disnake.utils.get(interaction.guild.roles, name=old_role_name)

            if custom_role:
                await custom_role.delete(reason="Сброс настроек роли бустера")

        # Выдаем стандартную роль
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

        booster_role = disnake.utils.get(interaction.guild.roles, name=self.booster_role_name)

        if not booster_role:
            await interaction.response.send_message("❌ На сервере нет бустеров!", ephemeral=True)
            return

        boosters = [member for member in interaction.guild.members if booster_role in member.roles]

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
            # Получаем кастомную роль бустера
            custom_role = None
            for role in booster.roles:
                if role.name != self.booster_role_name and booster_role in booster.roles:
                    custom_role = role
                    break

            if custom_role:
                booster_list.append(f"{custom_role.mention} - бустит с <t:{int(booster.premium_since.timestamp())}:R>")
            else:
                booster_list.append(f"{booster.mention} - бустит с <t:{int(booster.premium_since.timestamp())}:R>")

        embed.description = "\n".join(booster_list)

        await interaction.response.send_message(embed=embed)


def setup(bot):
    bot.add_cog(BoosterSystem(bot))