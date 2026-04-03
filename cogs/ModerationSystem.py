import disnake
from disnake.ext import commands
import datetime
import asyncio
import re
from typing import Optional


class ModerationSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = 1488227522536542300
        self.allowed_channel_id = 1488811577330368572

    def check_allowed_channel(self, interaction: disnake.ApplicationCommandInteraction) -> bool:
        return interaction.channel_id == self.allowed_channel_id

    async def send_log(self, guild: disnake.Guild, embed: disnake.Embed):
        try:
            channel = self.bot.get_channel(self.log_channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(self.log_channel_id)
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Ошибка при отправке лога: {e}")

    async def get_target_user(self, interaction: disnake.ApplicationCommandInteraction, user_input: str):
        target_user = None

        try:
            if user_input.isdigit():
                target_user = interaction.guild.get_member(int(user_input))
            else:
                match = re.search(r'<@!?(\d+)>', user_input)
                if match:
                    target_user = interaction.guild.get_member(int(match.group(1)))
        except:
            pass

        if not target_user:
            try:
                user_id = None
                if user_input.isdigit():
                    user_id = int(user_input)
                else:
                    match = re.search(r'<@!?(\d+)>', user_input)
                    if match:
                        user_id = int(match.group(1))

                if user_id:
                    target_user = await self.bot.fetch_user(user_id)
            except:
                pass

        return target_user

    @commands.slash_command(name="ban", description="Временно забанить участника")
    @commands.has_permissions(ban_members=True)
    async def ban(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            user: str = commands.Param(description="ID пользователя или упоминание"),
            duration: str = commands.Param(description="Длительность бана (1d, 2h, 30m, 1w)"),
            reason: str = commands.Param(default="Причина не указана", description="Причина бана")
    ):
        if not self.check_allowed_channel(interaction):
            await interaction.response.send_message(
                f"❌ Команда `/ban` доступна только в канале <#{self.allowed_channel_id}>",
                ephemeral=True
            )
            return

        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.response.send_message("❌ У меня нет прав на бан!", ephemeral=True)
            return

        target_user = await self.get_target_user(interaction, user)

        if not target_user:
            await interaction.response.send_message(
                "❌ Пользователь не найден! Укажите корректный ID или упоминание.",
                ephemeral=True
            )
            return

        if isinstance(target_user, disnake.Member) and target_user == interaction.author:
            await interaction.response.send_message("❌ Вы не можете забанить самого себя!", ephemeral=True)
            return

        if target_user.bot:
            await interaction.response.send_message("❌ Вы не можете забанить бота!", ephemeral=True)
            return

        if isinstance(target_user, disnake.Member):
            if target_user.top_role >= interaction.author.top_role and interaction.author != interaction.guild.owner:
                await interaction.response.send_message(
                    "❌ Вы не можете забанить пользователя с ролью выше или равной вашей!", ephemeral=True)
                return

            if target_user.top_role >= interaction.guild.me.top_role:
                await interaction.response.send_message("❌ Я не могу забанить этого пользователя из-за иерархии ролей!",
                                                        ephemeral=True)
                return

        duration_seconds = self.parse_duration(duration)
        if not duration_seconds:
            await interaction.response.send_message("❌ Неверный формат длительности! Используйте: 1d, 2h, 30m, 1w",
                                                    ephemeral=True)
            return

        embed = disnake.Embed(
            title="🔨 Временный бан",
            description=f"Вы уверены, что хотите забанить {target_user.mention} на **{duration}**?",
            color=disnake.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="👤 Пользователь", value=f"{target_user.name}#{target_user.discriminator}", inline=True)
        embed.add_field(name="🆔 ID", value=target_user.id, inline=True)
        embed.add_field(name="⏰ Длительность", value=duration, inline=True)
        embed.add_field(name="📝 Причина", value=reason[:1024], inline=False)
        embed.set_thumbnail(url=target_user.display_avatar.url)

        class BanView(disnake.ui.View):
            def __init__(self, cog, target_user, duration_seconds, duration_str, reason_str):
                super().__init__(timeout=60)
                self.cog = cog
                self.target_user = target_user
                self.duration_seconds = duration_seconds
                self.duration_str = duration_str
                self.reason_str = reason_str

            @disnake.ui.button(label="✅ Забанить", style=disnake.ButtonStyle.danger, emoji="🔨")
            async def confirm_ban(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                await inter.response.defer()

                try:
                    await inter.guild.ban(
                        self.target_user,
                        reason=f"Временный бан на {self.duration_str} | Модератор: {inter.user} | Причина: {self.reason_str}",
                        clean_history_duration=datetime.timedelta(days=0)
                    )

                    asyncio.create_task(
                        self.cog.schedule_unban(inter.guild.id, self.target_user.id, self.duration_seconds))

                    success_embed = disnake.Embed(
                        title="✅ Пользователь забанен",
                        description=f"{self.target_user.mention} успешно забанен на **{self.duration_str}**!",
                        color=disnake.Color.green(),
                        timestamp=datetime.datetime.utcnow()
                    )
                    success_embed.add_field(name="👤 Пользователь",
                                            value=f"{self.target_user.name}#{self.target_user.discriminator}",
                                            inline=True)
                    success_embed.add_field(name="🆔 ID", value=self.target_user.id, inline=True)
                    success_embed.add_field(name="⏰ Длительность", value=self.duration_str, inline=True)
                    success_embed.add_field(name="👮 Модератор", value=inter.user.mention, inline=True)
                    success_embed.add_field(name="📝 Причина", value=self.reason_str, inline=False)
                    success_embed.set_thumbnail(url=self.target_user.display_avatar.url)

                    await inter.edit_original_response(embed=success_embed, view=None)

                    log_embed = disnake.Embed(
                        title="🔨 ВРЕМЕННЫЙ БАН",
                        color=disnake.Color.red(),
                        timestamp=datetime.datetime.utcnow()
                    )
                    log_embed.add_field(name="👤 Пользователь",
                                        value=f"{self.target_user.name}#{self.target_user.discriminator}\n({self.target_user.mention})",
                                        inline=True)
                    log_embed.add_field(name="🆔 ID", value=self.target_user.id, inline=True)
                    log_embed.add_field(name="👮 Модератор",
                                        value=f"{inter.user.name}#{inter.user.discriminator}\n({inter.user.mention})",
                                        inline=True)
                    log_embed.add_field(name="⏰ Длительность", value=self.duration_str, inline=True)
                    log_embed.add_field(name="📝 Причина", value=self.reason_str, inline=False)
                    log_embed.set_thumbnail(url=self.target_user.display_avatar.url)

                    await self.cog.send_log(inter.guild, log_embed)

                    try:
                        dm_embed = disnake.Embed(
                            title=f"🔨 Вы были временно забанены на {inter.guild.name}",
                            description=f"**Длительность:** {self.duration_str}\n**Причина:** {self.reason_str}\n**Модератор:** {inter.user.mention}",
                            color=disnake.Color.red()
                        )
                        await self.target_user.send(embed=dm_embed)
                    except:
                        pass

                except Exception as e:
                    error_embed = disnake.Embed(
                        title="❌ Ошибка",
                        description=f"Не удалось забанить: {e}",
                        color=disnake.Color.red()
                    )
                    await inter.edit_original_response(embed=error_embed, view=None)

            @disnake.ui.button(label="❌ Отмена", style=disnake.ButtonStyle.secondary, emoji="❌")
            async def cancel_ban(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                cancel_embed = disnake.Embed(
                    title="❌ Отменено",
                    description="Бан отменен.",
                    color=disnake.Color.red()
                )
                await inter.response.edit_message(embed=cancel_embed, view=None)

        view = BanView(self, target_user, duration_seconds, duration, reason)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.slash_command(name="permban", description="Перманентно забанить участника")
    @commands.has_permissions(ban_members=True)
    async def permban(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            user: str = commands.Param(description="ID пользователя или упоминание"),
            reason: str = commands.Param(default="Причина не указана", description="Причина бана"),
            clean_days: int = commands.Param(default=0, ge=0, le=7,
                                             description="Удалить сообщения за последние X дней (0-7)")
    ):
        if not self.check_allowed_channel(interaction):
            await interaction.response.send_message(
                f"❌ Команда `/permban` доступна только в канале <#{self.allowed_channel_id}>",
                ephemeral=True
            )
            return

        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.response.send_message("❌ У меня нет прав на бан!", ephemeral=True)
            return

        target_user = await self.get_target_user(interaction, user)

        if not target_user:
            await interaction.response.send_message(
                "❌ Пользователь не найден! Укажите корректный ID или упоминание.",
                ephemeral=True
            )
            return

        if isinstance(target_user, disnake.Member) and target_user == interaction.author:
            await interaction.response.send_message("❌ Вы не можете забанить самого себя!", ephemeral=True)
            return

        if target_user.bot:
            await interaction.response.send_message("❌ Вы не можете забанить бота!", ephemeral=True)
            return

        if isinstance(target_user, disnake.Member):
            if target_user.top_role >= interaction.author.top_role and interaction.author != interaction.guild.owner:
                await interaction.response.send_message(
                    "❌ Вы не можете забанить пользователя с ролью выше или равной вашей!", ephemeral=True)
                return

            if target_user.top_role >= interaction.guild.me.top_role:
                await interaction.response.send_message("❌ Я не могу забанить этого пользователя из-за иерархии ролей!",
                                                        ephemeral=True)
                return

        embed = disnake.Embed(
            title="🔨 Перманентный бан",
            description=f"Вы уверены, что хотите **перманентно** забанить {target_user.mention}?",
            color=disnake.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="👤 Пользователь", value=f"{target_user.name}#{target_user.discriminator}", inline=True)
        embed.add_field(name="🆔 ID", value=target_user.id, inline=True)
        embed.add_field(name="📝 Причина", value=reason[:1024], inline=False)
        if clean_days > 0:
            embed.add_field(name="🗑️ Удалено сообщений", value=f"За последние {clean_days} дней", inline=True)
        embed.set_thumbnail(url=target_user.display_avatar.url)

        class PermBanView(disnake.ui.View):
            def __init__(self, cog, target_user, reason_str, clean_days):
                super().__init__(timeout=60)
                self.cog = cog
                self.target_user = target_user
                self.reason_str = reason_str
                self.clean_days = clean_days

            @disnake.ui.button(label="✅ Забанить навсегда", style=disnake.ButtonStyle.danger, emoji="🔨")
            async def confirm_ban(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                await inter.response.defer()

                try:
                    await inter.guild.ban(
                        self.target_user,
                        reason=f"Перманентный бан | Модератор: {inter.user} | Причина: {self.reason_str}",
                        clean_history_duration=datetime.timedelta(days=self.clean_days)
                    )

                    success_embed = disnake.Embed(
                        title="✅ Пользователь забанен навсегда",
                        description=f"{self.target_user.mention} успешно **перманентно** забанен!",
                        color=disnake.Color.green(),
                        timestamp=datetime.datetime.utcnow()
                    )
                    success_embed.add_field(name="👤 Пользователь",
                                            value=f"{self.target_user.name}#{self.target_user.discriminator}",
                                            inline=True)
                    success_embed.add_field(name="🆔 ID", value=self.target_user.id, inline=True)
                    success_embed.add_field(name="👮 Модератор", value=inter.user.mention, inline=True)
                    success_embed.add_field(name="📝 Причина", value=self.reason_str, inline=False)
                    if self.clean_days > 0:
                        success_embed.add_field(name="🗑️ Удалено сообщений",
                                                value=f"За последние {self.clean_days} дней", inline=True)
                    success_embed.set_thumbnail(url=self.target_user.display_avatar.url)

                    await inter.edit_original_response(embed=success_embed, view=None)

                    log_embed = disnake.Embed(
                        title="🔨 ПЕРМАНЕНТНЫЙ БАН",
                        color=disnake.Color.red(),
                        timestamp=datetime.datetime.utcnow()
                    )
                    log_embed.add_field(name="👤 Пользователь",
                                        value=f"{self.target_user.name}#{self.target_user.discriminator}\n({self.target_user.mention})",
                                        inline=True)
                    log_embed.add_field(name="🆔 ID", value=self.target_user.id, inline=True)
                    log_embed.add_field(name="👮 Модератор",
                                        value=f"{inter.user.name}#{inter.user.discriminator}\n({inter.user.mention})",
                                        inline=True)
                    log_embed.add_field(name="📝 Причина", value=self.reason_str, inline=False)
                    if self.clean_days > 0:
                        log_embed.add_field(name="🗑️ Удалено сообщений", value=f"За последние {self.clean_days} дней",
                                            inline=True)
                    log_embed.set_thumbnail(url=self.target_user.display_avatar.url)

                    await self.cog.send_log(inter.guild, log_embed)

                    try:
                        dm_embed = disnake.Embed(
                            title=f"🔨 Вы были ПЕРМАНЕНТНО забанены на {inter.guild.name}",
                            description=f"**Причина:** {self.reason_str}\n**Модератор:** {inter.user.mention}\n\nЭтот бан бессрочный.",
                            color=disnake.Color.red()
                        )
                        await self.target_user.send(embed=dm_embed)
                    except:
                        pass

                except Exception as e:
                    error_embed = disnake.Embed(
                        title="❌ Ошибка",
                        description=f"Не удалось забанить: {e}",
                        color=disnake.Color.red()
                    )
                    await inter.edit_original_response(embed=error_embed, view=None)

            @disnake.ui.button(label="❌ Отмена", style=disnake.ButtonStyle.secondary, emoji="❌")
            async def cancel_ban(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                cancel_embed = disnake.Embed(
                    title="❌ Отменено",
                    description="Бан отменен.",
                    color=disnake.Color.red()
                )
                await inter.response.edit_message(embed=cancel_embed, view=None)

        view = PermBanView(self, target_user, reason, clean_days)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.slash_command(name="unban", description="Разбанить участника")
    @commands.has_permissions(ban_members=True)
    async def unban(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            user_id: Optional[str] = commands.Param(
                default=None,
                description="ID пользователя или имя#тег (например: 123456789012345678 или User#1234)"
            ),
            user_mention: Optional[disnake.User] = commands.Param(
                default=None,
                description="Упомяните пользователя для разбана"
            )
    ):
        if not self.check_allowed_channel(interaction):
            await interaction.response.send_message(
                f"❌ Команда `/unban` доступна только в канале <#{self.allowed_channel_id}>",
                ephemeral=True
            )
            return

        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.response.send_message("❌ У меня нет прав на разбан!", ephemeral=True)
            return

        target_user = None
        search_method = None

        if user_mention:
            target_user = user_mention
            search_method = "упоминанию"
        elif user_id:
            if user_id.isdigit():
                try:
                    target_user = await self.bot.fetch_user(int(user_id))
                    search_method = "ID"
                except:
                    pass

            if not target_user and "#" in user_id:
                try:
                    name, discriminator = user_id.rsplit("#", 1)
                    async for ban_entry in interaction.guild.bans():
                        if ban_entry.user.name == name and ban_entry.user.discriminator == discriminator:
                            target_user = ban_entry.user
                            search_method = "имени#тег"
                            break
                except:
                    pass

        if not target_user:
            embed = disnake.Embed(
                title="❌ Пользователь не найден",
                description="Попробуйте:\n• Упомянуть пользователя\n• Ввести ID пользователя\n• Ввести имя#тег (например: User#1234)",
                color=disnake.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        is_banned = False
        ban_reason = None

        async for ban in interaction.guild.bans():
            if ban.user.id == target_user.id:
                is_banned = True
                ban_reason = ban.reason
                break

        if not is_banned:
            embed = disnake.Embed(
                title="ℹ️ Пользователь не забанен",
                description=f"{target_user.mention} не находится в списке забаненных.",
                color=disnake.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = disnake.Embed(
            title="🔓 Разбан участника",
            description=f"Вы уверены, что хотите разбанить {target_user.mention}?",
            color=disnake.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="👤 Пользователь", value=f"{target_user.name}#{target_user.discriminator}", inline=True)
        embed.add_field(name="🆔 ID", value=target_user.id, inline=True)
        if ban_reason:
            embed.add_field(name="📝 Причина бана", value=ban_reason[:1024], inline=False)
        embed.set_thumbnail(url=target_user.display_avatar.url)

        class UnbanView(disnake.ui.View):
            def __init__(self, cog, user, ban_reason, search_method):
                super().__init__(timeout=60)
                self.cog = cog
                self.user = user
                self.ban_reason = ban_reason
                self.search_method = search_method

            @disnake.ui.button(label="✅ Разбанить", style=disnake.ButtonStyle.green, emoji="🔓")
            async def confirm_unban(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                await inter.response.defer()

                try:
                    await inter.guild.unban(self.user,
                                            reason=f"Разбанен модератором {inter.user}")

                    success_embed = disnake.Embed(
                        title="✅ Пользователь разбанен",
                        description=f"{self.user.mention} успешно разбанен!",
                        color=disnake.Color.green(),
                        timestamp=datetime.datetime.utcnow()
                    )
                    success_embed.add_field(name="👤 Пользователь", value=f"{self.user.name}#{self.user.discriminator}",
                                            inline=True)
                    success_embed.add_field(name="🆔 ID", value=self.user.id, inline=True)
                    success_embed.add_field(name="👮 Модератор", value=inter.user.mention, inline=True)
                    success_embed.set_thumbnail(url=self.user.display_avatar.url)

                    await inter.edit_original_response(embed=success_embed, view=None)

                    log_embed = disnake.Embed(
                        title="🔓 РАЗБАН",
                        color=disnake.Color.green(),
                        timestamp=datetime.datetime.utcnow()
                    )
                    log_embed.add_field(name="👤 Пользователь",
                                        value=f"{self.user.name}#{self.user.discriminator}\n({self.user.mention})",
                                        inline=True)
                    log_embed.add_field(name="🆔 ID", value=self.user.id, inline=True)
                    log_embed.add_field(name="👮 Модератор",
                                        value=f"{inter.user.name}#{inter.user.discriminator}\n({inter.user.mention})",
                                        inline=True)
                    if self.ban_reason:
                        log_embed.add_field(name="📝 Причина бана", value=self.ban_reason, inline=False)
                    log_embed.add_field(name="🔍 Найден по", value=self.search_method, inline=True)
                    log_embed.set_thumbnail(url=self.user.display_avatar.url)
                    log_embed.set_footer(text=f"ID: {self.user.id}")

                    await self.cog.send_log(inter.guild, log_embed)

                    try:
                        dm_embed = disnake.Embed(
                            title=f"🔓 Вы были разбанены на {inter.guild.name}",
                            description=f"Модератор: {inter.user.mention}",
                            color=disnake.Color.green()
                        )
                        await self.user.send(embed=dm_embed)
                    except:
                        pass

                except Exception as e:
                    error_embed = disnake.Embed(
                        title="❌ Ошибка",
                        description=f"Не удалось разбанить: {e}",
                        color=disnake.Color.red()
                    )
                    await inter.edit_original_response(embed=error_embed, view=None)

            @disnake.ui.button(label="❌ Отмена", style=disnake.ButtonStyle.red, emoji="❌")
            async def cancel_unban(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                cancel_embed = disnake.Embed(
                    title="❌ Отменено",
                    description="Разбан отменен.",
                    color=disnake.Color.red()
                )
                await inter.response.edit_message(embed=cancel_embed, view=None)

        view = UnbanView(self, target_user, ban_reason, search_method)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.slash_command(name="banlist", description="Показать список забаненных")
    @commands.has_permissions(ban_members=True)
    async def banlist(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            page: int = commands.Param(default=1, ge=1, description="Номер страницы")
    ):
        if not self.check_allowed_channel(interaction):
            await interaction.response.send_message(
                f"❌ Команда `/banlist` доступна только в канале <#{self.allowed_channel_id}>",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        ban_list = []
        async for ban in interaction.guild.bans():
            ban_list.append(ban)

        if not ban_list:
            embed = disnake.Embed(
                title="📋 Список забаненных",
                description="Нет забаненных пользователей.",
                color=disnake.Color.green()
            )
            await interaction.followup.send(embed=embed)
            return

        items_per_page = 10
        total_pages = (len(ban_list) + items_per_page - 1) // items_per_page
        page = min(page, total_pages)

        start = (page - 1) * items_per_page
        end = start + items_per_page
        current_bans = ban_list[start:end]

        embed = disnake.Embed(
            title=f"📋 Список забаненных ({len(ban_list)} всего)",
            color=disnake.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )

        for ban in current_bans:
            user = ban.user
            reason = ban.reason or "Причина не указана"
            embed.add_field(
                name=f"👤 {user.name}#{user.discriminator}",
                value=f"**ID:** {user.id}\n**Причина:** {reason[:100]}",
                inline=False
            )

        embed.set_footer(text=f"Страница {page}/{total_pages}")

        class BanlistView(disnake.ui.View):
            def __init__(self, cog, ban_list, current_page, total_pages):
                super().__init__(timeout=60)
                self.cog = cog
                self.ban_list = ban_list
                self.current_page = current_page
                self.total_pages = total_pages

            @disnake.ui.button(label="◀️ Назад", style=disnake.ButtonStyle.primary)
            async def previous(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                if self.current_page > 1:
                    self.current_page -= 1
                    await self.update(inter)

            @disnake.ui.button(label="Вперед ▶️", style=disnake.ButtonStyle.primary)
            async def next(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
                if self.current_page < self.total_pages:
                    self.current_page += 1
                    await self.update(inter)

            async def update(self, inter: disnake.MessageInteraction):
                start = (self.current_page - 1) * 10
                end = start + 10
                current = self.ban_list[start:end]

                embed = disnake.Embed(
                    title=f"📋 Список забаненных ({len(self.ban_list)} всего)",
                    color=disnake.Color.orange(),
                    timestamp=datetime.datetime.utcnow()
                )

                for ban in current:
                    user = ban.user
                    reason = ban.reason or "Причина не указана"
                    embed.add_field(
                        name=f"👤 {user.name}#{user.discriminator}",
                        value=f"**ID:** {user.id}\n**Причина:** {reason[:100]}",
                        inline=False
                    )

                embed.set_footer(text=f"Страница {self.current_page}/{self.total_pages}")
                await inter.response.edit_message(embed=embed, view=self)

        if total_pages > 1:
            view = BanlistView(self, ban_list, page, total_pages)
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(embed=embed)

    @commands.slash_command(name="baninfo", description="Информация о бане пользователя")
    @commands.has_permissions(ban_members=True)
    async def baninfo(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            user: str = commands.Param(description="ID пользователя или упоминание")
    ):
        if not self.check_allowed_channel(interaction):
            await interaction.response.send_message(
                f"❌ Команда `/baninfo` доступна только в канале <#{self.allowed_channel_id}>",
                ephemeral=True
            )
            return

        target_user = await self.get_target_user(interaction, user)

        if not target_user:
            await interaction.response.send_message(
                "❌ Пользователь не найден! Укажите корректный ID или упоминание.",
                ephemeral=True
            )
            return

        ban_info = None
        async for ban in interaction.guild.bans():
            if ban.user.id == target_user.id:
                ban_info = ban
                break

        if not ban_info:
            embed = disnake.Embed(
                title="ℹ️ Информация о бане",
                description=f"{target_user.mention} не находится в списке забаненных.",
                color=disnake.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
            return

        embed = disnake.Embed(
            title=f"🔨 Информация о бане",
            color=disnake.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="👤 Пользователь", value=f"{target_user.name}#{target_user.discriminator}", inline=True)
        embed.add_field(name="🆔 ID", value=target_user.id, inline=True)

        if ban_info.reason:
            embed.add_field(name="📝 Причина бана", value=ban_info.reason[:1024], inline=False)
        else:
            embed.add_field(name="📝 Причина бана", value="Не указана", inline=False)

        embed.add_field(name="🔗 Аккаунт создан", value=f"<t:{int(target_user.created_at.timestamp())}:R>", inline=True)

        await interaction.response.send_message(embed=embed)

    def parse_duration(self, duration_str: str) -> Optional[int]:
        if not duration_str:
            return None

        duration_str = duration_str.lower().strip()

        units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800
        }

        number = ''
        unit = ''

        for char in duration_str:
            if char.isdigit():
                number += char
            else:
                unit += char

        if not number or not unit:
            return None

        try:
            number = int(number)
            if unit in units:
                return number * units[unit]
        except:
            return None

        return None

    async def schedule_unban(self, guild_id: int, user_id: int, delay_seconds: int):
        await asyncio.sleep(delay_seconds)

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        user = await self.bot.fetch_user(user_id)
        if not user:
            return

        try:
            is_banned = False
            async for ban in guild.bans():
                if ban.user.id == user_id:
                    is_banned = True
                    break

            if is_banned:
                await guild.unban(user, reason="Временный бан истек")

                log_embed = disnake.Embed(
                    title="⏰ АВТОМАТИЧЕСКИЙ РАЗБАН",
                    description=f"Временный бан пользователя {user.mention} истек.",
                    color=disnake.Color.green(),
                    timestamp=datetime.datetime.utcnow()
                )
                log_embed.add_field(name="👤 Пользователь", value=f"{user.name}#{user.discriminator}", inline=True)
                log_embed.add_field(name="🆔 ID", value=user.id, inline=True)

                await self.send_log(guild, log_embed)

                try:
                    dm_embed = disnake.Embed(
                        title=f"✅ Ваш бан на {guild.name} истек",
                        description="Вы можете зайти на сервер снова!",
                        color=disnake.Color.green()
                    )
                    await user.send(embed=dm_embed)
                except:
                    pass

        except Exception as e:
            print(f"Ошибка при автоматическом разбане: {e}")


def setup(bot):
    bot.add_cog(ModerationSystem(bot))