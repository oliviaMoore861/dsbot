import disnake
from disnake.ext import commands

class RoleCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # ID ролей
        self.ROLE_IVENT_ID = 1488807586512896141        # Роль для ивентов (которую выдают/забирают)
        self.ROLE_NEWS_ID = 1489685859811983430         # Роль для новостей (которую выдают/забирают)
        self.STAFF_IVENT_ROLE_ID = 1488807529852047360  # Роль админа ивентов (кто может выдавать/забирать)
        self.STAFF_NEWS_ROLE_ID = 1488807435279007764   # Роль админа новостей (кто может выдавать/забирать)

    @commands.slash_command(name="give_ivent", description="Выдать роль ивента участнику")
    async def give_ivent(
        self, 
        interaction: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник, которому выдать роль")
    ):
        """Выдача роли для ивентов (только для персонала ивентов)"""
        
        # Проверяем, есть ли у пользователя роль для выдачи ивент-ролей
        staff_role = interaction.guild.get_role(self.STAFF_IVENT_ROLE_ID)
        
        if not staff_role:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Роль персонала ивентов не найдена! Обратитесь к администратору.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if staff_role not in interaction.author.roles:
            embed = disnake.Embed(
                title="❌ Нет прав",
                description=f"У вас нет роли **{staff_role.name}** для использования этой команды!",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Получаем роль, которую нужно выдать
        role = interaction.guild.get_role(self.ROLE_IVENT_ID)
        
        if not role:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Роль ивента не найдена! Обратитесь к администратору.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Проверяем, есть ли уже роль у участника
        if role in member.roles:
            embed = disnake.Embed(
                title="⚠️ Уже есть",
                description=f"У участника {member.mention} уже есть роль **{role.name}**",
                color=disnake.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Выдаем роль
        try:
            await member.add_roles(role, reason=f"Выдача роли ивентов от {interaction.author.name}")
            
            embed = disnake.Embed(
                title="✅ Роль выдана!",
                description=f"Участнику {member.mention} выдана роль **{role.name}**",
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

    @commands.slash_command(name="dell_ivent", description="Забрать роль ивента у участника")
    async def dell_ivent(
        self, 
        interaction: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник, у которого забрать роль")
    ):
        """Снятие роли для ивентов (только для персонала ивентов)"""
        
        # Проверяем, есть ли у пользователя роль для снятия ивент-ролей
        staff_role = interaction.guild.get_role(self.STAFF_IVENT_ROLE_ID)
        
        if not staff_role:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Роль персонала ивентов не найдена! Обратитесь к администратору.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if staff_role not in interaction.author.roles:
            embed = disnake.Embed(
                title="❌ Нет прав",
                description=f"У вас нет роли **{staff_role.name}** для использования этой команды!",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Получаем роль, которую нужно забрать
        role = interaction.guild.get_role(self.ROLE_IVENT_ID)
        
        if not role:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Роль ивента не найдена! Обратитесь к администратору.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Проверяем, есть ли роль у участника
        if role not in member.roles:
            embed = disnake.Embed(
                title="⚠️ Нет роли",
                description=f"У участника {member.mention} нет роли **{role.name}**",
                color=disnake.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Забираем роль
        try:
            await member.remove_roles(role, reason=f"Снятие роли ивентов от {interaction.author.name}")
            
            embed = disnake.Embed(
                title="✅ Роль снята!",
                description=f"У участника {member.mention} снята роль **{role.name}**",
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

    @commands.slash_command(name="give_news", description="Выдать роль новостей участнику")
    async def give_news(
        self, 
        interaction: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник, которому выдать роль")
    ):
        """Выдача роли для новостей (только для персонала новостей)"""
        
        # Проверяем, есть ли у пользователя роль для выдачи новостных ролей
        staff_role = interaction.guild.get_role(self.STAFF_NEWS_ROLE_ID)
        
        if not staff_role:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Роль персонала новостей не найдена! Обратитесь к администратору.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if staff_role not in interaction.author.roles:
            embed = disnake.Embed(
                title="❌ Нет прав",
                description=f"У вас нет роли **{staff_role.name}** для использования этой команды!",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Получаем роль, которую нужно выдать
        role = interaction.guild.get_role(self.ROLE_NEWS_ID)
        
        if not role:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Роль новостей не найдена! Обратитесь к администратору.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Проверяем, есть ли уже роль у участника
        if role in member.roles:
            embed = disnake.Embed(
                title="⚠️ Уже есть",
                description=f"У участника {member.mention} уже есть роль **{role.name}**",
                color=disnake.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Выдаем роль
        try:
            await member.add_roles(role, reason=f"Выдача роли новостей от {interaction.author.name}")
            
            embed = disnake.Embed(
                title="✅ Роль выдана!",
                description=f"Участнику {member.mention} выдана роль **{role.name}**",
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

    @commands.slash_command(name="dell_news", description="Забрать роль новостей у участника")
    async def dell_news(
        self, 
        interaction: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник, у которого забрать роль")
    ):
        """Снятие роли для новостей (только для персонала новостей)"""
        
        # Проверяем, есть ли у пользователя роль для снятия новостных ролей
        staff_role = interaction.guild.get_role(self.STAFF_NEWS_ROLE_ID)
        
        if not staff_role:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Роль персонала новостей не найдена! Обратитесь к администратору.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if staff_role not in interaction.author.roles:
            embed = disnake.Embed(
                title="❌ Нет прав",
                description=f"У вас нет роли **{staff_role.name}** для использования этой команды!",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Получаем роль, которую нужно забрать
        role = interaction.guild.get_role(self.ROLE_NEWS_ID)
        
        if not role:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Роль новостей не найдена! Обратитесь к администратору.",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Проверяем, есть ли роль у участника
        if role not in member.roles:
            embed = disnake.Embed(
                title="⚠️ Нет роли",
                description=f"У участника {member.mention} нет роли **{role.name}**",
                color=disnake.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Забираем роль
        try:
            await member.remove_roles(role, reason=f"Снятие роли новостей от {interaction.author.name}")
            
            embed = disnake.Embed(
                title="✅ Роль снята!",
                description=f"У участника {member.mention} снята роль **{role.name}**",
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
    """Регистрация кога"""
    bot.add_cog(RoleCommands(bot))
