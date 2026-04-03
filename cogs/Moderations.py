import disnake
from disnake.ext import commands


class Moderations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="clear", description="Очищает указанное количество сообщений в канале.")
    @commands.has_permissions(manage_messages=True, ban_members=True)
    async def clear(self, ctx: disnake.ApplicationCommandInteraction, amount: int = commands.Param(ge=1, le=1000,
                                                                                                   description="Количество сообщений для удаления (от 1 до 1000)")):
        """
        Команда для массового удаления сообщений.

        Parameters
        ----------
        amount: Количество сообщений, которые нужно удалить.
        """
        # Отвечаем сразу, чтобы пользователь видел, что команда работает
        await ctx.response.defer(ephemeral=True)

        # Проверяем, что канал текстовый (в голосовых каналах удалять сообщения нельзя)
        if not isinstance(ctx.channel, disnake.TextChannel):
            return await ctx.edit_original_response(
                content="❌ Эту команду можно использовать только в текстовых каналах.")

        try:
            # Получаем историю сообщений
            # +1, так как мы хотим удалить и само сообщение с командой,
            # но если вы не хотите удалять команду, уберите +1
            messages_to_delete = []
            async for message in ctx.channel.history(limit=amount + 1):
                messages_to_delete.append(message)

            # Разделяем сообщения на "старые" (старше 14 дней) и "новые"
            # Discord не позволяет удалять сообщения старше 14 дней через bulk delete
            new_messages = []
            old_messages = []

            for msg in messages_to_delete:
                # Проверяем возраст сообщения (14 дней = 1209600 секунд)
                if (disnake.utils.utcnow() - msg.created_at).total_seconds() > 1209600:
                    old_messages.append(msg)
                else:
                    new_messages.append(msg)

            # Удаляем старые сообщения по одному (это медленно, но другого выхода нет)
            for msg in old_messages:
                try:
                    await msg.delete()
                except:
                    pass

            # Удаляем пачкой новые сообщения (быстро)
            if new_messages:
                deleted = await ctx.channel.purge(limit=len(new_messages), check=lambda m: m in new_messages)
                deleted_count = len(deleted)
            else:
                deleted_count = 0

            # Итоговый ответ
            total_deleted = deleted_count + len(old_messages)
            response_text = f"✅ Удалено сообщений: **{total_deleted}**"

            if old_messages:
                response_text += f"\n⚠️ {len(old_messages)} сообщений старше 14 дней были удалены по одному (это заняло больше времени)."

            await ctx.edit_original_response(content=response_text)

        except Exception as e:
            await ctx.edit_original_response(content=f"❌ Произошла ошибка: {e}")


# Функция для регистрации кога (если вы используете стандартную загрузку)
def setup(bot):
    bot.add_cog(Moderations(bot))