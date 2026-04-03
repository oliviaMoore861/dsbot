import disnake
from disnake.ext import commands
import datetime


class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_channel_id = 1487876788607782982  # ID канала для приветствий

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        """Отправка приветствия при заходе участника на сервер"""

        if member.bot:
            return

        # Получаем канал для приветствий
        welcome_channel = self.bot.get_channel(self.welcome_channel_id)
        if not welcome_channel:
            welcome_channel = await self.bot.fetch_channel(self.welcome_channel_id)

        # Создаем приветственный embed для канала
        channel_embed = disnake.Embed(
            title="🎉 Добро пожаловать на сервер! 🎉",
            description=f"{member.mention}, мы рады приветствовать тебя на **{member.guild.name}**!",
            color=disnake.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )

        # Добавляем информацию о пользователе
        channel_embed.add_field(
            name="👤 Пользователь",
            value=f"{member.name}#{member.discriminator}",
            inline=True
        )
        channel_embed.add_field(
            name="🆔 ID",
            value=member.id,
            inline=True
        )
        channel_embed.add_field(
            name="📅 Дата регистрации",
            value=f"<t:{int(member.created_at.timestamp())}:R>",
            inline=True
        )
        channel_embed.add_field(
            name="📊 Всего участников",
            value=f"{member.guild.member_count}",
            inline=True
        )

        # Добавляем статистику сервера
        member_count = len([m for m in member.guild.members if not m.bot])
        bot_count = len([m for m in member.guild.members if m.bot])

        channel_embed.add_field(
            name="📈 Статистика сервера",
            value=f"**👤 Участников:** {member_count}\n"
                  f"**🤖 Ботов:** {bot_count}\n"
                  f"**👥 Всего:** {member.guild.member_count}",
            inline=False
        )

        # Добавляем информацию о том, что нужно посетить
        channel_embed.add_field(
            name="📋 Что нужно сделать?",
            value="🔹 **Ознакомься с правилами** - <#1486016641933246524>\n"
                  "🔹 **Посмотри** - <#1486016661281706077>\n"
                  "🔹 **У нас есть турниры** - <#1486054512933208134>\n"
                  "🔹 **Начни общение** - <#1486253733926141992>\n\n"
                  "✨ **Приятного времяпрепровождения на сервере!** ✨",
            inline=False
        )

        channel_embed.set_thumbnail(url=member.display_avatar.url)
        channel_embed.set_footer(text=f"ID: {member.id}")

        # Отправляем приветствие в канал
        await welcome_channel.send(content=f"{member.mention}", embed=channel_embed)

        # Отправляем простое личное сообщение без инструкций
        try:
            dm_embed = disnake.Embed(
                title=f"🎉 Добро пожаловать на {member.guild.name}! 🎉",
                description=f"Привет, **{member.name}**! Мы рады видеть тебя на нашем сервере!",
                color=disnake.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )

            dm_embed.add_field(
                name="📊 Статистика сервера",
                value=f"**👥 Всего участников:** {member.guild.member_count}\n"
                      f"**👤 Из них людей:** {member_count}\n"
                      f"**🤖 Ботов:** {bot_count}",
                inline=False
            )

            dm_embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else member.display_avatar.url)
            dm_embed.set_footer(text=f"Приятного времяпрепровождения на {member.guild.name}!")

            # Отправляем личное сообщение
            await member.send(embed=dm_embed)

        except Exception as e:
            print(f"Не удалось отправить личное сообщение {member.name}: {e}")


def setup(bot):
    bot.add_cog(WelcomeSystem(bot))