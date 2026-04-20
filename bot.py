import disnake
from disnake.ext import commands
import os
import asyncio
import json
from typing import Optional

# ==================== НАСТРОЙКИ ====================
intents = disnake.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

# ID администратора (твой Discord ID)
ADMIN_ID = 1277950298928840705  # ЗАМЕНИ НА СВОЙ ID ПОЛЬЗОВАТЕЛЯ DISCORD (mod1kus777)

# ==================== ХРАНИЛИЩЕ ДАННЫХ ====================
# Файлы для хранения данных
GUIDES_FILE = "guides.json"
APPLICATIONS_FILE = "applications.json"

# Загружаем гайды из файла или создаем дефолтные
def load_guides():
    try:
        with open(GUIDES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "aim": {"title": "🎯 Гайд по Аиму", "url": "https://youtu.be/..."},
            "slides": {"title": "🏂 Гайд по Слайдам", "url": "https://youtu.be/..."},
            "reduces": {"title": "🔄 Гайд по Редуксам", "url": "https://youtu.be/..."},
            "tips": {"title": "💡 Полезные фишки", "url": "https://youtu.be/..."}
        }

def save_guides(guides):
    with open(GUIDES_FILE, 'w', encoding='utf-8') as f:
        json.dump(guides, f, ensure_ascii=False, indent=4)

# Загружаем принятых пользователей
def load_applications():
    try:
        with open(APPLICATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"accepted_users": []}

def save_applications(data):
    with open(APPLICATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

guides_data = load_guides()
applications_data = load_applications()

# ==================== КЛАССЫ ДЛЯ ИНТЕРАКТИВНЫХ ЭЛЕМЕНТОВ ====================

# Кнопка "Удалить" для быстрого удаления сообщений бота
class DeleteButton(disnake.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=None)
        self.author_id = author_id

    @disnake.ui.button(label="Удалить сообщение", style=disnake.ButtonStyle.danger, emoji="🗑️")
    async def delete_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # Только автор команды может удалить сообщение
        if inter.author.id == self.author_id:
            await inter.message.delete()
        else:
            await inter.response.send_message("Только автор команды может удалить это сообщение.", ephemeral=True)

# Форма заявки (Модальное окно)
class ApplicationModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Ваш игровой ник",
                placeholder="Введите ваш ник на Majestic RP",
                custom_id="nickname",
                style=disnake.TextInputStyle.short,
                max_length=50,
            ),
            disnake.ui.TextInput(
                label="Чему хотите научиться?",
                placeholder="Аим, слайды, редуксы, фишки...",
                custom_id="goal",
                style=disnake.TextInputStyle.paragraph,
                max_length=500,
            ),
            disnake.ui.TextInput(
                label="Сколько времени играете на Majestic RP?",
                placeholder="Пример: 3 месяца, 1 год",
                custom_id="playtime",
                style=disnake.TextInputStyle.short,
                max_length=100,
            ),
            disnake.ui.TextInput(
                label="Сколько готовы уделять на тренировки?",
                placeholder="Пример: 1 час в день, 3 раза в неделю",
                custom_id="training_time",
                style=disnake.TextInputStyle.short,
                max_length=100,
            ),
            disnake.ui.TextInput(
                label="Оцените вашу стрельбу 1-10",
                placeholder="Введите число от 1 до 10",
                custom_id="skill",
                style=disnake.TextInputStyle.short,
                max_length=2,
            ),
        ]
        super().__init__(title="📋 Заявка на обучение стрельбе", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        # Создаем Embed для отправки админу
        embed = disnake.Embed(
            title="🆕 НОВАЯ ЗАЯВКА НА ОБУЧЕНИЕ",
            color=disnake.Color.blue()
        )
        embed.add_field(name="👤 Discord", value=f"{inter.author.mention} (ID: `{inter.author.id}`)", inline=False)
        embed.add_field(name="🎮 Ник", value=inter.text_values["nickname"], inline=True)
        embed.add_field(name="🎯 Цель обучения", value=inter.text_values["goal"], inline=True)
        embed.add_field(name="⏳ Опыт игры", value=inter.text_values["playtime"], inline=True)
        embed.add_field(name="🏋️ Готовность к тренировкам", value=inter.text_values["training_time"], inline=True)
        embed.add_field(name="🎯 Оценка навыка", value=f"{inter.text_values['skill']}/10", inline=True)
        
        embed.set_footer(text=f"Заявка от {inter.author.name}")

        # Отправляем заявку админу в ЛС с кнопками принятия/отклонения
        admin_user = await bot.fetch_user(ADMIN_ID)
        if admin_user:
            view = ApplicationDecisionView(inter.author.id, inter.author.name)
            await admin_user.send(embed=embed, view=view)
            await inter.response.send_message("✅ Ваша заявка отправлена! Ожидайте решения в личных сообщениях.", ephemeral=True)
        else:
            await inter.response.send_message("❌ Ошибка: администратор не найден.", ephemeral=True)

# Кнопки принятия/отклонения для админа
class ApplicationDecisionView(disnake.ui.View):
    def __init__(self, applicant_id, applicant_name):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.applicant_name = applicant_name

    @disnake.ui.button(label="Принять", style=disnake.ButtonStyle.success, emoji="✅")
    async def accept_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # Добавляем пользователя в список принятых
        if self.applicant_id not in applications_data["accepted_users"]:
            applications_data["accepted_users"].append(self.applicant_id)
            save_applications(applications_data)

        # Сообщаем пользователю о принятии
        user = await bot.fetch_user(self.applicant_id)
        if user:
            try:
                embed = disnake.Embed(
                    title="✅ ЗАЯВКА ПРИНЯТА!",
                    description=f"Поздравляю! Твоя заявка на обучение стрельбе одобрена.\n\n"
                                f"Свяжись с администратором в Discord: <@{ADMIN_ID}> (`mod1kus777`)\n\n"
                                f"Теперь тебе доступны обучающие материалы. Используй команды:\n"
                                f"`/aim` - Гайд по аиму\n"
                                f"`/slides` - Гайд по слайдам\n"
                                f"`/reduces` - Гайд по редуксам\n"
                                f"`/tips` - Полезные фишки",
                    color=disnake.Color.green()
                )
                await user.send(embed=embed)
            except disnake.Forbidden:
                await inter.response.send_message("⚠️ Не могу отправить ЛС пользователю (закрыты ЛС).", ephemeral=True)
                return

        # Обновляем сообщение у админа
        await inter.message.edit(content="✅ **Заявка принята!**", view=None)
        await inter.response.send_message("Заявка принята, пользователь уведомлен.", ephemeral=True)

    @disnake.ui.button(label="Отклонить", style=disnake.ButtonStyle.danger, emoji="❌")
    async def decline_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        user = await bot.fetch_user(self.applicant_id)
        if user:
            try:
                await user.send("❌ К сожалению, ваша заявка на обучение отклонена. Попробуйте подать заявку позже, улучшив свой опыт игры.")
            except disnake.Forbidden:
                pass
        
        await inter.message.edit(content="❌ **Заявка отклонена.**", view=None)
        await inter.response.send_message("Заявка отклонена.", ephemeral=True)

# ==================== АДМИН-ПАНЕЛЬ (ЛС) ====================
class AdminPanelView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Изменить гайды", style=disnake.ButtonStyle.primary, emoji="📝")
    async def edit_guides(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != ADMIN_ID:
            return await inter.response.send_message("Нет доступа.", ephemeral=True)
        
        # Создаем Select Menu для выбора гайда
        options = [
            disnake.SelectOption(label="Аим", value="aim", emoji="🎯"),
            disnake.SelectOption(label="Слайды", value="slides", emoji="🏂"),
            disnake.SelectOption(label="Редуксы", value="reduces", emoji="🔄"),
            disnake.SelectOption(label="Фишки", value="tips", emoji="💡"),
        ]
        select = disnake.ui.Select(placeholder="Выберите гайд для изменения...", options=options)
        
        async def select_callback(select_inter: disnake.MessageInteraction):
            await select_inter.response.send_modal(EditGuideModal(select.values[0]))
        
        select.callback = select_callback
        
        view = disnake.ui.View()
        view.add_item(select)
        await inter.response.send_message("Выберите гайд для редактирования:", view=view, ephemeral=True)

    @disnake.ui.button(label="Список принятых", style=disnake.ButtonStyle.secondary, emoji="👥")
    async def list_accepted(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != ADMIN_ID:
            return await inter.response.send_message("Нет доступа.", ephemeral=True)
        
        if not applications_data["accepted_users"]:
            await inter.response.send_message("Список принятых пользователей пуст.", ephemeral=True)
            return
        
        users_text = ""
        for user_id in applications_data["accepted_users"]:
            users_text += f"• <@{user_id}>\n"
        
        embed = disnake.Embed(title="✅ Принятые ученики", description=users_text, color=disnake.Color.green())
        await inter.response.send_message(embed=embed, ephemeral=True)

class EditGuideModal(disnake.ui.Modal):
    def __init__(self, guide_key):
        self.guide_key = guide_key
        current_title = guides_data[guide_key]["title"]
        current_url = guides_data[guide_key]["url"]
        
        components = [
            disnake.ui.TextInput(
                label="Название гайда",
                placeholder="Введите новое название",
                custom_id="title",
                style=disnake.TextInputStyle.short,
                value=current_title,
                max_length=100,
            ),
            disnake.ui.TextInput(
                label="Ссылка на видео",
                placeholder="Вставьте новую ссылку YouTube",
                custom_id="url",
                style=disnake.TextInputStyle.short,
                value=current_url,
                max_length=200,
            ),
        ]
        super().__init__(title=f"Редактирование: {current_title}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        new_title = inter.text_values["title"]
        new_url = inter.text_values["url"]
        
        guides_data[self.guide_key] = {"title": new_title, "url": new_url}
        save_guides(guides_data)
        
        await inter.response.send_message(f"✅ Гайд `{new_title}` успешно обновлен!", ephemeral=True)

# ==================== СОБЫТИЯ БОТА ====================
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен и готов к работе!')
    await bot.change_presence(activity=disnake.Game(name="/command | Обучение стрельбе"))

# ==================== КОМАНДЫ БОТА ====================

async def send_with_delete_button(inter, content=None, embed=None):
    """Отправляет сообщение с кнопкой удаления"""
    view = DeleteButton(inter.author.id)
    if embed:
        await inter.response.send_message(embed=embed, view=view)
    else:
        await inter.response.send_message(content, view=view)

@bot.slash_command(name="nexus", description="📜 История создания фамы Nexus")
async def nexus(inter: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="📜 **ИСТОРИЯ ФАМЫ NEXUS** 📜",
        description=(
            "**🌅 КАК ВСЁ НАЧИНАЛОСЬ...**\n\n"
            "Всё началось на сервере **Miami 8**. Мы были частью фамы **Pacman (Mans)**, "
            "но со временем лидер той фамы показал своё истинное лицо.\n\n"
            "Он позволял себе **грязные выходки**, неуважение к участникам, воровал общий заработок "
            "и вёл себя как **настоящий тиран**. Люди уходили один за другим.\n\n"
            "**⚔️ РОЖДЕНИЕ ЛЕГЕНДЫ**\n\n"
            "Тогда **Sanek** — один из ключевых игроков, уставший от беспредела, собрал "
            "самых верных бойцов и сказал:\n"
            "*«Хватит терпеть эту несправедливость. Мы создадим СВОЮ фаму. "
            "Фаму, где будет уважение, помощь и реальный заработок!»*\n\n"
            "Так **16 апреля 2026 года** родилась **NEXUS** — фама, построенная на честности, силе и взаимопомощи.\n\n"
            "**💰 НАШ ПУТЬ СЕГОДНЯ**\n\n"
            "Мы активно развиваемся, перешли на **кражу**, стали королями тайников и ограблений.\n\n"
            "**🚗 ЧТО МЫ ПРЕДЛАГАЕМ:**\n"
            "• 🎯 Регулярные заезды на **трассу**\n"
            "• 🦹‍♂️ Профессиональные **ограбления**\n"
            "• 📦 Зачистка **тайников**\n"
            "• 💰 Стабильный **заработок**\n"
            "• 🤝 **Обучение новичков** с нуля\n\n"
            "**🚀 НАШ АВТОПАРК:**\n"
            "У нас одни из самых больших гаражей на сервере. Десятки машин, от бюджетных до элитных.\n\n"
            "**🔥 ЧТО МЫ ИЩЕМ:**\n"
            "Активных, адекватных и целеустремлённых игроков.\n\n"
            "**С нами ты НЕ останешься с нулём в кармане!**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**🌟 NEXUS — МЫ СИЛА! ПРИСОЕДИНЯЙСЯ! 🌟**"
        ),
        color=disnake.Color.dark_gold()
    )
    embed.set_footer(text="Основатель: Sanek | Дата основания: 16.04.2026")
    await send_with_delete_button(inter, embed=embed)

@bot.slash_command(name="promo", description="🎁 Получить промокод для Majestic RolePlay")
async def promo(inter: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="🎁 ПРОМОКОД NEXUS 🎁",
        description="**Станьте кем угодно в GTA 5 Majestic RolePlay!**",
        color=disnake.Color.green()
    )
    embed.add_field(name="🌟 **Что тебя ждёт:**", value="Присоединяйся к игре вместе со мной на Majestic. Создавай персонажа прямо сейчас и начинай развиваться!", inline=False)
    embed.add_field(name="🎮 **ПРОМОКОД:**", value="```NEXUS```", inline=False)
    embed.add_field(name="📝 **Как активировать:**", value="Укажи промокод при регистрации или командой `/promo NEXUS` в игре", inline=False)
    embed.add_field(name="💎 **Majestic Premium (7 дней)**", value="• Ускоренное развитие персонажа\n• Повышенный доход\n• Десятки эксклюзивных бонусов", inline=False)
    embed.add_field(name="💰 **Дополнительно:**", value="**50 000 игровой валюты** в подарок!", inline=False)
    embed.set_footer(text="Промокод активен для всех новых игроков | Nexus Family")
    await send_with_delete_button(inter, embed=embed)

@bot.slash_command(name="botinfo", description="🤖 Информация о создателе бота")
async def botinfo(inter: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="🤖 О БОТЕ NEXUS 🤖",
        description="Вся информация о нашем помощнике по обучению",
        color=disnake.Color.blue()
    )
    embed.add_field(name="👨‍💻 **Создатель бота:**", value="**Vladosis Nexus** — разработал этого бота с нуля для комфорта нашей фамы", inline=False)
    embed.add_field(name="🎯 **Для чего этот бот?**", value="Бот создан для обучения стрельбе участников фамы Nexus на сервере Miami 8.", inline=False)
    embed.add_field(name="📅 **Дата создания бота:**", value="16 апреля 2026 года", inline=True)
    embed.add_field(name="⚙️ **Версия:**", value="4.0.0 (Training)", inline=True)
    embed.add_field(name="📢 **По вопросам информации и обновлений:**", value="**@mod1kus777**", inline=False)
    embed.set_footer(text="Nexus Training Bot | Сделано с душой для своей фамы")
    await send_with_delete_button(inter, embed=embed)

@bot.slash_command(name="apply", description="📝 Подать заявку на обучение стрельбе")
async def apply(inter: disnake.ApplicationCommandInteraction):
    await inter.response.send_modal(ApplicationModal())

# Проверка доступа к гайдам (декоратор)
def is_accepted():
    async def predicate(inter: disnake.ApplicationCommandInteraction):
        if inter.author.id == ADMIN_ID:
            return True
        if inter.author.id in applications_data["accepted_users"]:
            return True
        await inter.response.send_message("❌ У вас нет доступа к гайдам. Сначала подайте заявку `/apply`.", ephemeral=True)
        return False
    return commands.check(predicate)

@bot.slash_command(name="aim", description="🎯 Гайд по аиму")
@is_accepted()
async def aim_guide(inter: disnake.ApplicationCommandInteraction):
    guide = guides_data["aim"]
    embed = disnake.Embed(title=guide["title"], description=f"[Нажмите сюда, чтобы открыть видео]({guide['url']})", color=disnake.Color.red())
    await send_with_delete_button(inter, embed=embed)

@bot.slash_command(name="slides", description="🏂 Гайд по слайдам")
@is_accepted()
async def slides_guide(inter: disnake.ApplicationCommandInteraction):
    guide = guides_data["slides"]
    embed = disnake.Embed(title=guide["title"], description=f"[Нажмите сюда, чтобы открыть видео]({guide['url']})", color=disnake.Color.blue())
    await send_with_delete_button(inter, embed=embed)

@bot.slash_command(name="reduces", description="🔄 Гайд по редуксам")
@is_accepted()
async def reduces_guide(inter: disnake.ApplicationCommandInteraction):
    guide = guides_data["reduces"]
    embed = disnake.Embed(title=guide["title"], description=f"[Нажмите сюда, чтобы открыть видео]({guide['url']})", color=disnake.Color.green())
    await send_with_delete_button(inter, embed=embed)

@bot.slash_command(name="tips", description="💡 Полезные фишки")
@is_accepted()
async def tips_guide(inter: disnake.ApplicationCommandInteraction):
    guide = guides_data["tips"]
    embed = disnake.Embed(title=guide["title"], description=f"[Нажмите сюда, чтобы открыть видео]({guide['url']})", color=disnake.Color.purple())
    await send_with_delete_button(inter, embed=embed)

@bot.slash_command(name="command", description="📋 Показать все команды бота")
async def commands_list(inter: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="🎯 NEXUS TRAINING BOT v4.0 🎯",
        description="Полный список команд для управления ботом:",
        color=disnake.Color.purple()
    )
    
    embed.add_field(name="📝 ОСНОВНЫЕ КОМАНДЫ", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/apply", value="📋 Подать заявку на обучение стрельбе", inline=False)
    
    embed.add_field(name="\n🎓 ОБУЧАЮЩИЕ МАТЕРИАЛЫ", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/aim", value="🎯 Гайд по аиму", inline=True)
    embed.add_field(name="/slides", value="🏂 Гайд по слайдам", inline=True)
    embed.add_field(name="/reduces", value="🔄 Гайд по редуксам", inline=True)
    embed.add_field(name="/tips", value="💡 Полезные фишки", inline=True)
    
    embed.add_field(name="\n✨ ИНФОРМАЦИОННЫЕ КОМАНДЫ", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/nexus", value="📜 История фамы Nexus", inline=True)
    embed.add_field(name="/promo", value="🎁 Промокод Majestic RP", inline=True)
    embed.add_field(name="/botinfo", value="🤖 Информация о боте", inline=True)
    embed.add_field(name="/command", value="📋 Показать это меню", inline=True)
    
    embed.set_footer(text="Создано Vladosis Nexus | Маджестик | Miami 8")
    await send_with_delete_button(inter, embed=embed)

@bot.slash_command(name="admin", description="⚙️ Админ-панель (только для админа в ЛС)")
async def admin_panel(inter: disnake.ApplicationCommandInteraction):
    if inter.author.id != ADMIN_ID:
        await inter.response.send_message("❌ У вас нет доступа к этой команде.", ephemeral=True)
        return
    
    embed = disnake.Embed(
        title="⚙️ АДМИН-ПАНЕЛЬ NEXUS TRAINING",
        description="Здесь вы можете управлять контентом бота.",
        color=disnake.Color.dark_blue()
    )
    view = AdminPanelView()
    await inter.response.send_message(embed=embed, view=view, ephemeral=True)

# ==================== ЗАПУСК БОТА ====================
bot.run(os.getenv('DISCORD_TOKEN'))