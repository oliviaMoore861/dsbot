import disnake
from disnake.ext import commands
from typing import Optional


class StaffRolesManager(commands.Cog):
    """Ког для управления ролями персонала"""

    def __init__(self, bot):
        self.bot = bot
        # ID роли, которая имеет право использовать команды
        self.staff_manager_role_id = 1488807475200262224

        # ID ролей
        self.support_role_id = 1488887550352425192
        self.old_support_role_id = 1486046038619066448
        self.jun_moder_role_id = 1488807287186259978
        self.moder_role_id = 1486045899674353775
        self.staff_role_id = 1486022367518920704
        self.trial_role_id = 1488807206748033034
        self.helper_role_id = 1486045943051587636

        # Список всех ролей для dell_all_staff
        self.all_staff_roles = [
            self.staff_role_id,
            self.old_support_role_id,
            self.support_role_id,
            self.jun_moder_role_id,
            self.moder_role_id,
            self.trial_role_id,
            self.helper_role_id
        ]

    def has_staff_manager_role(self, member: disnake.Member) -> bool:
        """Проверка наличия роли менеджера персонала"""
        role = member.guild.get_role(self.staff_manager_role_id)
        if not role:
            return False
        return role in member.roles

    async def check_permissions(self, interaction: disnake.ApplicationCommandInteraction) -> bool:
        """Проверка прав на использование команд"""
        if not self.has_staff_manager_role(interaction.author):
            embed = disnake.Embed(
                title="❌ Ошибка доступа",
                description="У вас нет прав на использование этой команды!\n"
                            "Требуется специальная роль менеджера персонала.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def check_bot_permissions(self, interaction: disnake.ApplicationCommandInteraction) -> bool:
        """Проверка прав бота"""
        if not interaction.guild.me.guild_permissions.manage_roles:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="У бота нет прав на управление ролями!\n"
                            "Пожалуйста, выдайте боту права **Manage Roles**.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def get_role(self, guild: disnake.Guild, role_id: int) -> Optional[disnake.Role]:
        """Получить роль по ID"""
        role = guild.get_role(role_id)
        if not role:
            return None
        return role

    async def give_role(self, member: disnake.Member, role: disnake.Role, reason: str) -> bool:
        """Выдать роль"""
        try:
            if role not in member.roles:
                await member.add_roles(role, reason=reason)
                return True
            return False
        except Exception as e:
            print(f"Ошибка при выдаче роли {role.name}: {e}")
            return False

    async def remove_role(self, member: disnake.Member, role: disnake.Role, reason: str) -> bool:
        """Снять роль"""
        try:
            if role in member.roles:
                await member.remove_roles(role, reason=reason)
                return True
            return False
        except Exception as e:
            print(f"Ошибка при снятии роли {role.name}: {e}")
            return False

    async def handle_role_swap(self, interaction: disnake.ApplicationCommandInteraction,
                               member: disnake.Member,
                               role_to_give_id: int,
                               role_to_remove_id: int,
                               command_name: str):
        """Универсальная функция для замены ролей"""

        # Проверяем права
        if not await self.check_permissions(interaction):
            return
        if not await self.check_bot_permissions(interaction):
            return

        # Проверяем, что целевой пользователь не бот
        if member.bot:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Нельзя изменять роли ботов!",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Получаем роли
        role_to_give = await self.get_role(interaction.guild, role_to_give_id)
        role_to_remove = await self.get_role(interaction.guild, role_to_remove_id)

        if not role_to_give:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description=f"Роль с ID {role_to_give_id} не найдена на сервере!",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not role_to_remove:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description=f"Роль с ID {role_to_remove_id} не найдена на сервере!",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Проверяем, может ли бот выдавать/снимать эти роли
        if role_to_give >= interaction.guild.me.top_role:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description=f"Роль {role_to_give.mention} находится выше или на уровне роли бота!\n"
                            f"Переместите роль бота выше в списке ролей.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if role_to_remove >= interaction.guild.me.top_role:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description=f"Роль {role_to_remove.mention} находится выше или на уровне роли бота!\n"
                            f"Переместите роль бота выше в списке ролей.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Выдаем и снимаем роли
        reason = f"{command_name} от {interaction.author}"

        gave_role = await self.give_role(member, role_to_give, reason)
        removed_role = await self.remove_role(member, role_to_remove, reason)

        # Создаем embed с результатом
        embed = disnake.Embed(
            title="🎯 Изменение ролей",
            color=disnake.Color.green() if gave_role or removed_role else disnake.Color.orange(),
            timestamp=disnake.utils.utcnow()
        )

        embed.add_field(
            name="👤 Пользователь",
            value=f"{member.mention}\n{member.name}#{member.discriminator}",
            inline=False
        )

        embed.add_field(
            name="👑 Выполнил",
            value=f"{interaction.author.mention}",
            inline=False
        )

        if gave_role:
            embed.add_field(
                name="✅ Выдана роль",
                value=role_to_give.mention,
                inline=True
            )
        else:
            embed.add_field(
                name="ℹ️ Роль уже была",
                value=role_to_give.mention,
                inline=True
            )

        if removed_role:
            embed.add_field(
                name="❌ Снята роль",
                value=role_to_remove.mention,
                inline=True
            )
        else:
            embed.add_field(
                name="ℹ️ Роль не была выдана",
                value=role_to_remove.mention,
                inline=True
            )

        embed.set_footer(text=f"ID: {member.id}")

        await interaction.response.send_message(embed=embed)

    # --- Команды ---
    @commands.slash_command(name="give_support", description="Выдать роль Support и снять роль Junior Support")
    async def give_support(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: disnake.Member = commands.Param(description="Пользователь, которому выдать роль")
    ):
        """Выдать роль Support и снять роль Junior Support"""
        await self.handle_role_swap(
            interaction,
            member,
            self.support_role_id,
            self.old_support_role_id,
            "give_support"
        )

    @commands.slash_command(name="dell_support", description="Выдать роль Junior Support и снять роль Support")
    async def dell_support(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: disnake.Member = commands.Param(description="Пользователь, которому выдать роль")
    ):
        """Выдать роль Junior Support и снять роль Support"""
        await self.handle_role_swap(
            interaction,
            member,
            self.old_support_role_id,
            self.support_role_id,
            "dell_support"
        )

    @commands.slash_command(name="give_jun_moder", description="Выдать роль Junior Moderator и снять роль Support")
    async def give_jun_moder(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: disnake.Member = commands.Param(description="Пользователь, которому выдать роль")
    ):
        """Выдать роль Junior Moderator и снять роль Support"""
        await self.handle_role_swap(
            interaction,
            member,
            self.jun_moder_role_id,
            self.support_role_id,
            "give_jun_moder"
        )

    @commands.slash_command(name="dell_jun_moder", description="Выдать роль Support и снять роль Junior Moderator")
    async def dell_jun_moder(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: disnake.Member = commands.Param(description="Пользователь, которому выдать роль")
    ):
        """Выдать роль Support и снять роль Junior Moderator"""
        await self.handle_role_swap(
            interaction,
            member,
            self.support_role_id,
            self.jun_moder_role_id,
            "dell_jun_moder"
        )

    @commands.slash_command(name="give_moder", description="Выдать роль Moderator и снять роль Junior Moderator")
    async def give_moder(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: disnake.Member = commands.Param(description="Пользователь, которому выдать роль")
    ):
        """Выдать роль Moderator и снять роль Junior Moderator"""
        await self.handle_role_swap(
            interaction,
            member,
            self.moder_role_id,
            self.jun_moder_role_id,
            "give_moder"
        )

    @commands.slash_command(name="dell_moder", description="Выдать роль Junior Moderator и снять роль Moderator")
    async def dell_moder(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: disnake.Member = commands.Param(description="Пользователь, которому выдать роль")
    ):
        """Выдать роль Junior Moderator и снять роль Moderator"""
        await self.handle_role_swap(
            interaction,
            member,
            self.jun_moder_role_id,
            self.moder_role_id,
            "dell_moder"
        )

    @commands.slash_command(name="dell_all_staff", description="Снять все роли персонала с пользователя")
    async def dell_all_staff(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: disnake.Member = commands.Param(description="Пользователь, у которого снять все роли")
    ):
        """Снять все роли персонала с пользователя"""

        # Проверяем права
        if not await self.check_permissions(interaction):
            return
        if not await self.check_bot_permissions(interaction):
            return

        # Проверяем, что целевой пользователь не бот
        if member.bot:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Нельзя изменять роли ботов!",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Снимаем все роли
        removed_roles = []
        not_have_roles = []
        failed_roles = []

        for role_id in self.all_staff_roles:
            role = await self.get_role(interaction.guild, role_id)
            if not role:
                continue

            # Проверяем, может ли бот снимать эту роль
            if role >= interaction.guild.me.top_role:
                failed_roles.append(f"{role.mention} (роль выше роли бота)")
                continue

            if role in member.roles:
                try:
                    await member.remove_roles(role, reason=f"dell_all_staff от {interaction.author}")
                    removed_roles.append(role.mention)
                except Exception as e:
                    failed_roles.append(f"{role.mention} (ошибка: {str(e)})")
            else:
                not_have_roles.append(role.mention)

        # Создаем embed с результатом
        embed = disnake.Embed(
            title="🔰 Снятие всех ролей персонала",
            color=disnake.Color.green() if removed_roles else disnake.Color.red(),
            timestamp=disnake.utils.utcnow()
        )

        embed.add_field(
            name="👤 Пользователь",
            value=f"{member.mention}\n{member.name}#{member.discriminator}",
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

        embed.set_footer(text=f"ID: {member.id}")

        await interaction.response.send_message(embed=embed)


def setup(bot):
    """Загрузка кога"""
    bot.add_cog(StaffRolesManager(bot))