import disnake
from disnake.ext import commands
from typing import Optional


class StaffCommands(commands.Cog):
    """Ког для выдачи и снятия ролей персонала"""

    def __init__(self, bot):
        self.bot = bot
        # ID роли, которая имеет право использовать команды
        self.staff_manager_role_id = 1488807475200262224
        # ID ролей, которые выдает команда
        self.roles_to_give = [1486046038619066448, 1486022367518920704]

    @commands.slash_command(name="give_staff", description="Выдать роли персонала")
    async def give_staff(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: Optional[disnake.Member] = commands.Param(
                default=None,
                description="Пользователь, которому выдать роли (по умолчанию - вы)"
            )
    ):
        """Выдать роли персонала"""

        # Проверяем, есть ли у пользователя роль менеджера
        if not self.has_staff_manager_role(interaction.author):
            embed = disnake.Embed(
                title="❌ Ошибка доступа",
                description="У вас нет прав на использование этой команды!\n"
                            "Требуется специальная роль менеджера персонала.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Если пользователь не указан, выдаем роли себе
        target_member = member or interaction.author

        # Проверяем, не является ли целевой пользователь ботом
        if target_member.bot:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Нельзя выдавать роли ботам!",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Проверяем права бота
        if not interaction.guild.me.guild_permissions.manage_roles:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="У бота нет прав на управление ролями!\n"
                            "Пожалуйста, выдайте боту права **Manage Roles**.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Проверяем, есть ли у пользователя уже эти роли
        roles_to_add = []
        already_has_roles = []

        for role_id in self.roles_to_give:
            role = interaction.guild.get_role(role_id)
            if not role:
                embed = disnake.Embed(
                    title="❌ Ошибка",
                    description=f"Роль с ID {role_id} не найдена на сервере!",
                    color=disnake.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if role in target_member.roles:
                already_has_roles.append(role.mention)
            else:
                # Проверяем, может ли бот выдавать эту роль
                if role >= interaction.guild.me.top_role:
                    embed = disnake.Embed(
                        title="❌ Ошибка",
                        description=f"Роль {role.mention} находится выше или на уровне роли бота!\n"
                                    f"Переместите роль бота выше в списке ролей.",
                        color=disnake.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                roles_to_add.append(role)

        # Выдаем роли
        added_roles = []
        failed_roles = []

        for role in roles_to_add:
            try:
                await target_member.add_roles(role, reason=f"Выдано пользователем {interaction.author}")
                added_roles.append(role.mention)
            except Exception as e:
                failed_roles.append(f"{role.mention} (ошибка: {str(e)})")

        # Создаем embed с результатом
        embed = disnake.Embed(
            title="🎉 Выдача ролей персонала",
            color=disnake.Color.green() if added_roles else disnake.Color.orange(),
            timestamp=disnake.utils.utcnow()
        )

        embed.add_field(
            name="👤 Пользователь",
            value=f"{target_member.mention}\n{target_member.name}#{target_member.discriminator}",
            inline=False
        )

        embed.add_field(
            name="👑 Выдал",
            value=f"{interaction.author.mention}",
            inline=False
        )

        if added_roles:
            embed.add_field(
                name="✅ Выданные роли",
                value="\n".join(added_roles),
                inline=False
            )

        if already_has_roles:
            embed.add_field(
                name="ℹ️ Уже были выданы",
                value="\n".join(already_has_roles),
                inline=False
            )

        if failed_roles:
            embed.add_field(
                name="❌ Не удалось выдать",
                value="\n".join(failed_roles),
                inline=False
            )

        embed.set_footer(text=f"ID: {target_member.id}")

        await interaction.response.send_message(embed=embed)

    @commands.slash_command(name="dell_staff", description="Снять роли персонала")
    async def dell_staff(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: Optional[disnake.Member] = commands.Param(
                default=None,
                description="Пользователь, у которого снять роли (по умолчанию - вы)"
            )
    ):
        """Снять роли персонала"""

        # Проверяем, есть ли у пользователя роль менеджера
        if not self.has_staff_manager_role(interaction.author):
            embed = disnake.Embed(
                title="❌ Ошибка доступа",
                description="У вас нет прав на использование этой команды!\n"
                            "Требуется специальная роль менеджера персонала.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Если пользователь не указан, снимаем роли с себя
        target_member = member or interaction.author

        # Проверяем, не является ли целевой пользователь ботом
        if target_member.bot:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Нельзя снимать роли с ботов!",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Проверяем права бота
        if not interaction.guild.me.guild_permissions.manage_roles:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="У бота нет прав на управление ролями!\n"
                            "Пожалуйста, выдайте боту права **Manage Roles**.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Проверяем, есть ли у пользователя эти роли
        roles_to_remove = []
        not_have_roles = []

        for role_id in self.roles_to_give:
            role = interaction.guild.get_role(role_id)
            if not role:
                embed = disnake.Embed(
                    title="❌ Ошибка",
                    description=f"Роль с ID {role_id} не найдена на сервере!",
                    color=disnake.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if role in target_member.roles:
                # Проверяем, может ли бот снимать эту роль
                if role >= interaction.guild.me.top_role:
                    embed = disnake.Embed(
                        title="❌ Ошибка",
                        description=f"Роль {role.mention} находится выше или на уровне роли бота!\n"
                                    f"Переместите роль бота выше в списке ролей.",
                        color=disnake.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                roles_to_remove.append(role)
            else:
                not_have_roles.append(role.mention)

        # Снимаем роли
        removed_roles = []
        failed_roles = []

        for role in roles_to_remove:
            try:
                await target_member.remove_roles(role, reason=f"Снято пользователем {interaction.author}")
                removed_roles.append(role.mention)
            except Exception as e:
                failed_roles.append(f"{role.mention} (ошибка: {str(e)})")

        # Создаем embed с результатом
        embed = disnake.Embed(
            title="🔰 Снятие ролей персонала",
            color=disnake.Color.orange() if removed_roles else disnake.Color.red(),
            timestamp=disnake.utils.utcnow()
        )

        embed.add_field(
            name="👤 Пользователь",
            value=f"{target_member.mention}\n{target_member.name}#{target_member.discriminator}",
            inline=False
        )

        embed.add_field(
            name="👑 Снял",
            value=f"{interaction.author.mention}",
            inline=False
        )

        if removed_roles:
            embed.add_field(
                name="✅ Снятые роли",
                value="\n".join(removed_roles),
                inline=False
            )

        if not_have_roles:
            embed.add_field(
                name="ℹ️ Не были выданы",
                value="\n".join(not_have_roles),
                inline=False
            )

        if failed_roles:
            embed.add_field(
                name="❌ Не удалось снять",
                value="\n".join(failed_roles),
                inline=False
            )

        embed.set_footer(text=f"ID: {target_member.id}")

        await interaction.response.send_message(embed=embed)

    def has_staff_manager_role(self, member: disnake.Member) -> bool:
        """Проверка наличия роли менеджера персонала"""
        role = member.guild.get_role(self.staff_manager_role_id)
        if not role:
            return False
        return role in member.roles


ROLE_IVENT_ID = 1488807586512896141  # ID роли для ивентов
ROLE_NEWS_ID = 1489685859811983430   # ID роли для новостей
CHANNEL_ID = 1489684413477290045     # ID канала, где работают команды

@bot.slash_command(name="give_ivent", description="Получить роль для участия в ивентах")
async def give_ivent(interaction: disnake.ApplicationCommandInteraction):
    """Выдача роли для ивентов"""
    
    # Проверяем, что команда вызвана в правильном канале
    if interaction.channel_id != CHANNEL_ID:
        embed = disnake.Embed(
            title="❌ Неправильный канал",
            description=f"Используйте эту команду только в <#{CHANNEL_ID}>",
            color=disnake.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    role = interaction.guild.get_role(ROLE_IVENT_ID)
    
    if not role:
        embed = disnake.Embed(
            title="❌ Ошибка",
            description="Роль не найдена! Обратитесь к администратору.",
            color=disnake.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Проверяем, есть ли уже роль у пользователя
    if role in interaction.author.roles:
        embed = disnake.Embed(
            title="⚠️ Уже есть",
            description=f"У вас уже есть роль **{role.name}**",
            color=disnake.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Выдаем роль
    try:
        await interaction.author.add_roles(role, reason="Выдача роли ивентов по команде /give_ivent")
        
        embed = disnake.Embed(
            title="✅ Роль выдана!",
            description=f"Вам выдана роль **{role.name}**\nТеперь вы будете получать уведомления о ивентах!",
            color=disnake.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Не удалось выдать роль. Ошибка: {e}",
            color=disnake.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name="dell_ivent", description="Снять роль для участия в ивентах")
async def dell_ivent(interaction: disnake.ApplicationCommandInteraction):
    """Снятие роли для ивентов"""
    
    # Проверяем, что команда вызвана в правильном канале
    if interaction.channel_id != CHANNEL_ID:
        embed = disnake.Embed(
            title="❌ Неправильный канал",
            description=f"Используйте эту команду только в <#{CHANNEL_ID}>",
            color=disnake.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    role = interaction.guild.get_role(ROLE_IVENT_ID)
    
    if not role:
        embed = disnake.Embed(
            title="❌ Ошибка",
            description="Роль не найдена! Обратитесь к администратору.",
            color=disnake.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Проверяем, есть ли роль у пользователя
    if role not in interaction.author.roles:
        embed = disnake.Embed(
            title="⚠️ Нет роли",
            description=f"У вас нет роли **{role.name}**",
            color=disnake.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Забираем роль
    try:
        await interaction.author.remove_roles(role, reason="Снятие роли ивентов по команде /dell_ivent")
        
        embed = disnake.Embed(
            title="✅ Роль снята!",
            description=f"С вас снята роль **{role.name}**\nВы больше не будете получать уведомления о ивентах.",
            color=disnake.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Не удалось снять роль. Ошибка: {e}",
            color=disnake.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name="give_news", description="Получить роль для получения новостей")
async def give_news(interaction: disnake.ApplicationCommandInteraction):
    """Выдача роли для новостей"""
    
    # Проверяем, что команда вызвана в правильном канале
    if interaction.channel_id != CHANNEL_ID:
        embed = disnake.Embed(
            title="❌ Неправильный канал",
            description=f"Используйте эту команду только в <#{CHANNEL_ID}>",
            color=disnake.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    role = interaction.guild.get_role(ROLE_NEWS_ID)
    
    if not role:
        embed = disnake.Embed(
            title="❌ Ошибка",
            description="Роль не найдена! Обратитесь к администратору.",
            color=disnake.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Проверяем, есть ли уже роль у пользователя
    if role in interaction.author.roles:
        embed = disnake.Embed(
            title="⚠️ Уже есть",
            description=f"У вас уже есть роль **{role.name}**",
            color=disnake.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Выдаем роль
    try:
        await interaction.author.add_roles(role, reason="Выдача роли новостей по команде /give_news")
        
        embed = disnake.Embed(
            title="✅ Роль выдана!",
            description=f"Вам выдана роль **{role.name}**\nТеперь вы будете получать уведомления о новостях!",
            color=disnake.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Не удалось выдать роль. Ошибка: {e}",
            color=disnake.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name="dell_news", description="Снять роль для получения новостей")
async def dell_news(interaction: disnake.ApplicationCommandInteraction):
    """Снятие роли для новостей"""
    
    # Проверяем, что команда вызвана в правильном канале
    if interaction.channel_id != CHANNEL_ID:
        embed = disnake.Embed(
            title="❌ Неправильный канал",
            description=f"Используйте эту команду только в <#{CHANNEL_ID}>",
            color=disnake.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    role = interaction.guild.get_role(ROLE_NEWS_ID)
    
    if not role:
        embed = disnake.Embed(
            title="❌ Ошибка",
            description="Роль не найдена! Обратитесь к администратору.",
            color=disnake.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Проверяем, есть ли роль у пользователя
    if role not in interaction.author.roles:
        embed = disnake.Embed(
            title="⚠️ Нет роли",
            description=f"У вас нет роли **{role.name}**",
            color=disnake.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Забираем роль
    try:
        await interaction.author.remove_roles(role, reason="Снятие роли новостей по команде /dell_news")
        
        embed = disnake.Embed(
            title="✅ Роль снята!",
            description=f"С вас снята роль **{role.name}**\nВы больше не будете получать уведомления о новостях.",
            color=disnake.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Не удалось снять роль. Ошибка: {e}",
            color=disnake.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

def setup(bot):
    """Загрузка кога"""
    bot.add_cog(StaffCommands(bot))
