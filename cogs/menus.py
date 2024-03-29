import discord


class ViewMenu(discord.ui.View):

    def __init__(self, interaction, embeds, *, timeout=180):
        super().__init__(timeout=timeout)
        self.page = 0
        self.embeds = embeds
        self.interaction = interaction 

    async def interaction_check(self, interaction):
        return self.interaction.user == interaction.user

    async def update_view(self, interaction):
        if len(self.embeds) == 0:
            await interaction.response.edit_message(
                view=None,
                embed=None,
                content=':no_entry: No past games found.'
            )
            self.stop()
            return 
        if self.page > len(self.embeds) - 1:
            self.page = len(self.embeds) - 1 

        embed = self.embeds[self.page]
        await interaction.response.edit_message(embed=embed)

    async def update_from_modal(self, interaction):
        embed = self.embeds[self.page]
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(style=discord.ButtonStyle.blurple, label='\u21e4')
    async def beginning(self, interaction, button):
        if len(self.embeds) == 0:
            return await interaction.response.defer()
        if self.page == 0:
            return await interaction.response.defer()
        self.page = 0
        await self.update_view(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, label='\u2190')
    async def previous(self, interaction, button):
        if len(self.embeds) == 0:
            return await interaction.response.defer()
        if self.page == 0:
            return await interaction.response.defer()
        self.page -= 1
        await self.update_view(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, label='\u2192')
    async def _next(self, interaction, button):
        if len(self.embeds) == 0:
            return await interaction.response.defer()
        if self.page == len(self.embeds) - 1:
            return await interaction.response.defer()
        self.page += 1
        await self.update_view(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, label='\u21e5')
    async def end(self, interaction, button):
        if len(self.embeds) == 0:
            return await interaction.response.defer()
        if self.page == len(self.embeds) - 1:
            return await interaction.response.defer()
        self.page = len(self.embeds) - 1
        await self.update_view(interaction)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red, row=1)
    async def cancel(self, interaction, button):
        self.clear_items()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label='Jump', style=discord.ButtonStyle.gray)
    async def jump(self, interaction, button):

        class Modal(discord.ui.Modal, title='Enter a page to jump to.'):
            page = discord.ui.TextInput(
                label=f'A number from 1-{len(self.embeds)}',
                style=discord.TextStyle.short
            )

        async def on_submit(modal_i):
            try:
                page = int(self.page)
            except ValueError:
                await modal_i.response.send_message(
                    ':no_entry: You did not enter a number for the page.',
                    ephemeral=True
                )
                return

            if page < 1:
                page = 1
            if page > len(self.embeds):
                page = len(self.embeds)

            self.page = page - 1
            await self.update_from_modal(modal_i)

        modal = Modal()
        modal.on_submit = on_submit

        await interaction.response.send_modal(modal)

class HistoryMenu(ViewMenu):
    def __init__(self, interaction, embeds, *, timeout=180):
        super().__init__(interaction, embeds, timeout=timeout)
        if interaction.user.guild_permissions.administrator:

            async def callback(binter):
                rowid = int(self.embeds[self.page].footer.text.split()[1])
                query = 'DELETE FROM plays WHERE id = $1'
                await interaction.client.db.execute(query, rowid)
                self.embeds.pop(self.page)
                await self.update_view(binter)

            button = discord.ui.Button(
                label='Delete Entry',
                style=discord.ButtonStyle.gray,
                emoji='\u274c'
            )
            button.callback = callback 
            self.add_item(button)



class TemplatesMenu(ViewMenu):

    def __init__(self, interaction, default, custom, default_options, custom_options):
        super().__init__(interaction, default, timeout=180)
        self.embeds = default
        self.default = default
        self.custom = custom
        self.default_options = default_options
        self.custom_options = custom_options
        self.add_item(self.get_select())
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.label == 'Cancel':
                    self.remove_item(item)
                    break
        self.name = None
        self.template = None

    def get_select(self):
        if self.embeds == self.default:
            options = self.default_options[self.page]
        else:
            try:
                options = self.custom_options[self.page]
            except KeyError:
                return

        if not options:
            return None 

        selectoptions = []
        for n, info in options.items():
            selectoptions.append(discord.SelectOption(label=n, description=info[0]))
        select = discord.ui.Select(placeholder='Choose a template', options=selectoptions)

        async def callback(interaction):
            n2 = interaction.data['values'][0]
            info2 = options[int(n2)]
            name = info2[0]
            template = info2[1]

            self.name = name
            self.template = template

            self.clear_items()
            await interaction.response.edit_message(
                content=f'Selected: **{name}**',
                view=self, 
                embed=None
            )
            self.stop()

        select.callback = callback
        return select

    async def update_view(self, interaction):
        if len(self.embeds) == 0:
            embed = discord.Embed(
                title='No Custom Templates',
                color=self.interaction.user.color
            )
        else:
            embed = self.embeds[self.page]
        for item in self.children:
            if isinstance(item, discord.ui.Select):
                self.remove_item(item)
                break
        select = self.get_select()
        if select is not None:
            self.add_item(select)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Default Templates', style=discord.ButtonStyle.blurple, row=2)
    async def default(self, interaction, button):
        if self.embeds == self.default:
            return await interaction.response.defer()
        self.embeds = self.default
        self.page = 0
        await self.update_view(interaction)

    @discord.ui.button(label='Custom Templates', style=discord.ButtonStyle.blurple, row=2)
    async def custom(self, interaction, button):
        if self.embeds == self.custom:
            return await interaction.response.defer()
        self.embeds = self.custom
        self.page = 0
        await self.update_view(interaction)


class ShareYesNo(discord.ui.View):

    def __init__(self, interaction, name, story, participants):
        self.interaction = interaction
        self.bot = interaction.client
        self.story = story
        self.name = name
        self.participants = participants
        self.message = None
        super().__init__(timeout=15)

    async def interaction_check(self, interaction):
        return interaction.user == self.interaction.user

    async def on_timeout(self):
        for button in self.children:
            button.disabled = True
        await self.message.delete()
        self.stop()

    @discord.ui.button(label='Share!', style=discord.ButtonStyle.green)
    async def yes(self, interaction, button):
        ch = self.bot.get_channel(765759340405063680)
        if len(self.story) > 2042:
            self.story = self.story[:2041]
        embed = discord.Embed(
            title=self.name,
            description=f'```{self.story}```',
            color=discord.Colour.orange()
        )
        # for each one check if they opted
        plist = []
        for u in self.participants:
            if u.id in self.bot.incognito:
                plist.append('Anonymous User')
            else:
                plist.append(u.global_name)
            
        embed.add_field(name='Participants', value=', '.join(plist))
        await ch.send(embed=embed)

        self.remove_item(self.no)
        button.disabled = True
        button.label = 'Shared!'
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.gray)
    async def no(self, interaction, button):
        button.label = 'Not shared'
        button.disabled = True
        self.remove_item(self.yes)

        await interaction.response.edit_message(view=self)
        self.stop()

class ClearHistoryYesNo(discord.ui.View):

    def __init__(self, interaction):
        self.interaction = interaction
        self.bot = interaction.client
        self.message = None
        super().__init__(timeout=30)

    async def interaction_check(self, interaction):
        return interaction.user == self.interaction.user

    async def on_timeout(self):
        await self.message.edit(view=None, content=":thumbsup: Cancelled clearing history.")
        self.stop()

    @discord.ui.button(label='Yes', style=discord.ButtonStyle.green)
    async def yes(self, interaction, button):
        query = 'DELETE FROM plays WHERE guild_id = $1'
        await self.bot.db.execute(query, interaction.guild.id)
        await interaction.response.edit_message(view=None, content=":thumbsup: All game history in this server has been cleared.")
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.gray)
    async def no(self, interaction, button):
        await interaction.response.edit_message(view=None, content=":thumbsup: Cancelled clearing history.")
        self.stop()
