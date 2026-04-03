import disnake
from disnake.ext import commands

class RoleCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # ID ролей и каналов
        self.ROLE_IVENT_ID = 1488807586512896141  # ID роли для ивентов
        self.ROLE_NEWS_ID = 1489685859811983430   # ID роли для новостей
        self.CHANNEL_ID = 1489684413477290045     # ID канала, где работают команды

    @commands.slash_command(name="give_ivent", description="Получить роль для участия в ивентах")
    async def give_ivent(self, interaction: disnake.ApplicationCommandInteraction):
        """Выдача роли для ивентов"""
        
        # Проверяем, что команда вызвана в правильном канале
        if interaction.channel_id != self.CHANNEL_ID:
            embed = disnake.Embed(
                title="❌ Неправильный канал",
                description=f"Используйте эту команду только в <#{self.CHANNEL_ID}>",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        role = interaction.guild.get_role(self.ROLE_IVENT_ID)
        
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

    @commands.slash_command(name="dell_ivent", description="Снять роль для участия в ивентах")
    async def dell_ivent(self, interaction: disnake.ApplicationCommandInteraction):
        """Снятие роли для ивентов"""
        
        # Проверяем, что команда вызвана в правильном канале
        if interaction.channel_id != self.CHANNEL_ID:
            embed = disnake.Embed(
                title="❌ Неправильный канал",
                description=f"Используйте эту команду только в <#{self.CHANNEL_ID}>",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        role = interaction.guild.get_role(self.ROLE_IVENT_ID)
        
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

    @commands.slash_command(name="give_news", description="Получить роль для получения новостей")
    async def give_news(self, interaction: disnake.ApplicationCommandInteraction):
        """Выдача роли для новостей"""
        
        # Проверяем, что команда вызвана в правильном канале
        if interaction.channel_id != self.CHANNEL_ID:
            embed = disnake.Embed(
                title="❌ Неправильный канал",
                description=f"Используйте эту команду только в <#{self.CHANNEL_ID}>",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        role = interaction.guild.get_role(self.ROLE_NEWS_ID)
        
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

    @commands.slash_command(name="dell_news", description="Снять роль для получения новостей")
    async def dell_news(self, interaction: disnake.ApplicationCommandInteraction):
        """Снятие роли для новостей"""
        
        # Проверяем, что команда вызвана в правильном канале
        if interaction.channel_id != self.CHANNEL_ID:
            embed = disnake.Embed(
                title="❌ Неправильный канал",
                description=f"Используйте эту команду только в <#{self.CHANNEL_ID}>",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        role = interaction.guild.get_role(self.ROLE_NEWS_ID)
        
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
    """Регистрация кога"""
    bot.add_cog(RoleCommands(bot))
