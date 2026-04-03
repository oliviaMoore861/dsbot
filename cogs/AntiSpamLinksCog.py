import disnake
from disnake.ext import commands
import re
from datetime import timedelta


class AntiSpamLinksCog(commands.Cog):
    """Ког для автоматического мута за спам ссылками на Discord и Telegram"""

    def __init__(self, bot):
        self.bot = bot

        # Паттерны для поиска ссылок
        self.discord_pattern = re.compile(
            r'(?:https?://)?(?:www\.)?(?:discord(?:app)?\.(?:com|gg)/invite/|discord\.gg/)([a-zA-Z0-9\-_]+)',
            re.IGNORECASE
        )

        self.telegram_pattern = re.compile(
            r'(?:https?://)?(?:www\.)?t\.me/(?:joinchat/|\+)?([a-zA-Z0-9\-_]+)|telegram\.me/([a-zA-Z0-9\-_]+)',
            re.IGNORECASE
        )

        # Общий паттерн для быстрой проверки
        self.spam_pattern = re.compile(
            r'(?:https?://)?(?:www\.)?(?:discord(?:app)?\.(?:com|gg)/invite/|discord\.gg/|t\.me/|telegram\.me/)',
            re.IGNORECASE
        )

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        """Обработчик новых сообщений"""

        # Игнорируем сообщения от ботов и из личных сообщений
        if message.author.bot or not message.guild:
            return

        # Проверяем, есть ли запрещённые ссылки
        if not self.spam_pattern.search(message.content):
            return

        # Проверяем права пользователя (админы и модераторы игнорируются)
        if message.author.guild_permissions.manage_messages:
            return

        try:
            # Удаляем спам-сообщение
            await message.delete()

            # Выдаём таймаут на 1 час
            await message.author.timeout(
                timedelta(hours=1),
                reason="Спам ссылками на Discord или Telegram"
            )

            # Отправляем предупреждение (автоудаление через 5 секунд)
            warning = await message.channel.send(
                f"{message.author.mention}, вы получили таймаут на 1 час за отправку ссылок на Discord или Telegram."
            )
            await warning.delete(delay=5)

            # Логируем действие (опционально)
            print(
                f"[AntiSpam] {message.author} получил таймаут в {message.guild.name} за ссылку: {message.content[:50]}")

        except disnake.Forbidden:
            print(f"[AntiSpam] Нет прав для действия над {message.author} в {message.guild.name}")
        except Exception as e:
            print(f"[AntiSpam] Ошибка: {e}")

    @commands.Cog.listener()
    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        """Обработчик отредактированных сообщений"""

        # Игнорируем ботов и личные сообщения
        if after.author.bot or not after.guild:
            return

        # Проверяем только если контент изменился
        if before.content == after.content:
            return

        # Проверяем наличие ссылок в отредактированном сообщении
        if not self.spam_pattern.search(after.content):
            return

        # Проверяем права пользователя
        if after.author.guild_permissions.manage_messages:
            return

        try:
            # Удаляем отредактированное сообщение
            await after.delete()

            # Выдаём таймаут (если ещё не в таймауте)
            if not after.author.current_timeout:
                await after.author.timeout(
                    timedelta(hours=1),
                    reason="Спам ссылками на Discord или Telegram (отредактированное сообщение)"
                )

                warning = await after.channel.send(
                    f"{after.author.mention}, вы получили таймаут на 1 час за отправку ссылок в отредактированном сообщении."
                )
                await warning.delete(delay=5)

        except Exception as e:
            print(f"[AntiSpam] Ошибка при обработке отредактированного сообщения: {e}")

    @commands.command(name="spam_settings")
    @commands.has_permissions(administrator=True)
    async def spam_settings(self, ctx: commands.Context):
        """Показать настройки антиспама (только для админов)"""

        embed = disnake.Embed(
            title="🛡️ Настройки антиспама",
            description="Текущие правила автоматического мута за спам ссылками",
            color=disnake.Color.blue()
        )

        embed.add_field(
            name="❌ Запрещённые ссылки",
            value="• Discord приглашения (discord.gg, discord.com/invite)\n• Telegram ссылки (t.me, telegram.me)",
            inline=False
        )

        embed.add_field(
            name="⏰ Длительность мута",
            value="1 час (3600 секунд)",
            inline=True
        )

        embed.add_field(
            name="👮 Исключения",
            value="Пользователи с правом `manage_messages` (администраторы/модераторы)",
            inline=True
        )

        embed.add_field(
            name="📝 Действия при спаме",
            value="1. Сообщение удаляется\n2. Выдаётся таймаут на 1 час\n3. Отправляется предупреждение",
            inline=False
        )

        await ctx.send(embed=embed, delete_after=10)


def setup(bot):
    """Функция для загрузки кога"""
    bot.add_cog(AntiSpamLinksCog(bot))