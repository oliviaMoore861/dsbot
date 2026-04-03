import disnake
from disnake.ext import commands
from typing import Optional, Dict
import asyncio

# ========== НАСТРОЙКИ ==========
# ID категории, где будут создаваться каналы
CATEGORY_ID = 1489213690585813123

# ID триггерных каналов и их настройки
TRIGGER_CHANNELS = {
    1489212953168445481: {  # Канал для создания дуо каналов
        "limit": 2,
        "name_template": "🎤 Дуо-{number}",
        "prefix": "Duo"
    },
    1489212987951681606: {  # Канал для создания трио каналов
        "limit": 3,
        "name_template": "🎤 Трио-{number}",
        "prefix": "Trio"
    },
    1489213431910502470: {  # Канал для создания квартет каналов
        "limit": 4,
        "name_template": "🎤 Сквад-{number}",
        "prefix": "Quartet"
    }
}


# =================================


class AutoVoiceCog(commands.Cog):
    """Ког для автоматического создания голосовых каналов"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_channels: Dict[int, dict] = {}  # {channel_id: {"owner_id": int, "trigger_channel_id": int}}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member,
                                    before: disnake.VoiceState,
                                    after: disnake.VoiceState):
        """Обработка изменения голосового состояния"""

        # Если пользователь зашел в триггерный канал
        if after.channel and after.channel.id in TRIGGER_CHANNELS:
            await self.create_voice_channel(member, after.channel)

        # Если пользователь вышел из созданного канала
        if before.channel and before.channel.id in self.active_channels:
            # Проверяем, остались ли ещё люди в канале
            if len(before.channel.members) == 0:
                await self.delete_voice_channel(before.channel)

    async def create_voice_channel(self, member: disnake.Member, trigger_channel: disnake.VoiceChannel):
        """Создает новый голосовой канал с нужным лимитом"""

        # Получаем настройки для этого триггерного канала
        settings = TRIGGER_CHANNELS[trigger_channel.id]

        # Получаем категорию
        category = member.guild.get_channel(CATEGORY_ID)
        if not category:
            print(f"❌ Категория с ID {CATEGORY_ID} не найдена!")
            return

        # Находим следующий доступный номер для канала
        number = 1
        existing_channels = [ch for ch in category.voice_channels if ch.name.startswith(settings["prefix"])]

        # Ищем максимальный номер
        max_number = 0
        for channel in existing_channels:
            try:
                # Извлекаем номер из названия (например "Duo-1" -> 1)
                num = int(channel.name.split("-")[-1])
                if num > max_number:
                    max_number = num
            except:
                pass

        number = max_number + 1

        # Создаем новый голосовой канал
        channel_name = settings["name_template"].format(number=number)

        try:
            new_channel = await category.create_voice_channel(
                name=channel_name,
                user_limit=settings["limit"],
                reason=f"Создан пользователем {member.display_name}"
            )

            # Сохраняем информацию о созданном канале
            self.active_channels[new_channel.id] = {
                "owner_id": member.id,
                "trigger_channel_id": trigger_channel.id,
                "limit": settings["limit"],
                "prefix": settings["prefix"]
            }

            # Перемещаем пользователя в новый канал
            await member.move_to(new_channel, reason="Автоматическое перемещение в созданный канал")

            # Отправляем уведомление (опционально)
            # await member.send(f"✅ Для вас создан канал {new_channel.mention} с лимитом {settings['limit']} человек")

            print(f"✅ Создан канал {channel_name} (ID: {new_channel.id}) для {member.display_name}")

        except Exception as e:
            print(f"❌ Ошибка при создании канала: {e}")

    async def delete_voice_channel(self, channel: disnake.VoiceChannel):
        """Удаляет пустой голосовой канал"""

        if channel.id in self.active_channels:
            channel_info = self.active_channels[channel.id]

            try:
                # Удаляем канал
                await channel.delete(reason="Канал пуст, автоматическое удаление")
                del self.active_channels[channel.id]
                print(f"🗑️ Удален пустой канал {channel.name}")
            except Exception as e:
                print(f"❌ Ошибка при удалении канала: {e}")

    # Команда для ручного удаления всех созданных каналов (опционально)
    @commands.slash_command(name="clear_voice_channels", description="Очистить все созданные голосовые каналы")
    @commands.has_permissions(administrator=True)
    async def clear_voice_channels(self, inter: disnake.ApplicationCommandInteraction):
        """Удалить все созданные ботом голосовые каналы"""

        category = inter.guild.get_channel(CATEGORY_ID)
        if not category:
            await inter.response.send_message("❌ Категория не найдена!", ephemeral=True)
            return

        deleted_count = 0
        for channel in category.voice_channels:
            if channel.id in self.active_channels:
                try:
                    await channel.delete()
                    del self.active_channels[channel.id]
                    deleted_count += 1
                except:
                    pass

        await inter.response.send_message(f"✅ Удалено {deleted_count} каналов!", ephemeral=True)

    # Команда для просмотра активных каналов
    @commands.slash_command(name="list_voice_channels", description="Показать все созданные голосовые каналы")
    @commands.has_permissions(administrator=True)
    async def list_voice_channels(self, inter: disnake.ApplicationCommandInteraction):
        """Показать список всех созданных каналов"""

        if not self.active_channels:
            await inter.response.send_message("📭 Нет активных созданных каналов!", ephemeral=True)
            return

        embed = disnake.Embed(
            title="🎤 Активные голосовые каналы",
            color=disnake.Color.blue()
        )

        for channel_id, info in self.active_channels.items():
            channel = inter.guild.get_channel(channel_id)
            if channel:
                member_count = len(channel.members)
                embed.add_field(
                    name=channel.name,
                    value=f"Лимит: {info['limit']} | Участников: {member_count} | Владелец: <@{info['owner_id']}>",
                    inline=False
                )

        await inter.response.send_message(embed=embed, ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(AutoVoiceCog(bot))
