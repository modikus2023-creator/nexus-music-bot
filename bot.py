import disnake
from disnake.ext import commands
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import random

# ==================== НАСТРОЙКИ ====================
intents = disnake.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

# ID администратора
ADMIN_ID = 1277950298928840705  # ЗАМЕНИ НА СВОЙ ID

# ==================== ФАЙЛЫ ДАННЫХ ====================
GUIDES_FILE = "guides.json"
APPLICATIONS_FILE = "applications.json"
RATINGS_FILE = "ratings.json"
TOURNAMENTS_FILE = "tournaments.json"

# ==================== ЗАГРУЗКА ДАННЫХ ====================
def load_guides():
    try:
        with open(GUIDES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"categories": {}}

def save_guides(guides):
    with open(GUIDES_FILE, 'w', encoding='utf-8') as f:
        json.dump(guides, f, ensure_ascii=False, indent=4)

def load_applications():
    try:
        with open(APPLICATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"accepted_users": [], "user_applications": {}}

def save_applications(data):
    with open(APPLICATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_ratings():
    try:
        with open(RATINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"ratings": {}}

def save_ratings(data):
    with open(RATINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_tournaments():
    try:
        with open(TOURNAMENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"active_tournament": None, "history": []}

def save_tournaments(data):
    with open(TOURNAMENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

guides_data = load_guides()
applications_data = load_applications()
ratings_data = load_ratings()
tournaments_data = load_tournaments()

# ==================== УТЕШИТЕЛЬНЫЕ СООБЩЕНИЯ ====================
consolation_messages = [
    "Не расстраивайся! В следующий раз обязательно победишь! 💪",
    "Ты отлично постарался! Продолжай тренироваться и всё получится! 🌟",
    "Поражение - это шаг к победе! Ты стал сильнее! 🎯",
    "Главное не победа, а участие! Твой скилл уже вырос! 📈",
    "Каждый проигрыш делает тебя опытнее! Не сдавайся! 🔥"
]

# ==================== КЛАССЫ ИНТЕРФЕЙСА ====================

class DeleteButton(disnake.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=None)
        self.author_id = author_id

    @disnake.ui.button(label="Удалить сообщение", style=disnake.ButtonStyle.danger, emoji="🗑️")
    async def delete_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id == self.author_id:
            await inter.message.delete()
        else:
            await inter.response.send_message("Только автор команды может удалить это сообщение.", ephemeral=True)

class ApplicationModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(label="Ваш игровой ник", placeholder="Введите ваш ник на Majestic RP", 
                               custom_id="nickname", style=disnake.TextInputStyle.short, max_length=50),
            disnake.ui.TextInput(label="Чему хотите научиться?", placeholder="Аим, слайды, редуксы, фишки...", 
                               custom_id="goal", style=disnake.TextInputStyle.paragraph, max_length=500),
            disnake.ui.TextInput(label="Сколько времени играете на Majestic RP?", placeholder="Пример: 3 месяца, 1 год", 
                               custom_id="playtime", style=disnake.TextInputStyle.short, max_length=100),
            disnake.ui.TextInput(label="Сколько готовы уделять на тренировки?", placeholder="Пример: 1 час в день", 
                               custom_id="training_time", style=disnake.TextInputStyle.short, max_length=100),
            disnake.ui.TextInput(label="Оцените вашу стрельбу 1-10", placeholder="Введите число от 1 до 10", 
                               custom_id="skill", style=disnake.TextInputStyle.short, max_length=2),
        ]
        super().__init__(title="📋 Заявка на обучение стрельбе", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        embed = disnake.Embed(title="🆕 НОВАЯ ЗАЯВКА НА ОБУЧЕНИЕ", color=disnake.Color.blue())
        embed.add_field(name="👤 Discord", value=f"{inter.author.mention} (ID: `{inter.author.id}`)", inline=False)
        embed.add_field(name="🎮 Ник", value=inter.text_values["nickname"], inline=True)
        embed.add_field(name="🎯 Цель обучения", value=inter.text_values["goal"], inline=True)
        embed.add_field(name="⏳ Опыт игры", value=inter.text_values["playtime"], inline=True)
        embed.add_field(name="🏋️ Готовность к тренировкам", value=inter.text_values["training_time"], inline=True)
        embed.add_field(name="🎯 Оценка навыка", value=f"{inter.text_values['skill']}/10", inline=True)
        embed.set_footer(text=f"Заявка от {inter.author.name}")
        
        # Сохраняем данные заявки
        applications_data["user_applications"][str(inter.author.id)] = {
            "nickname": inter.text_values["nickname"],
            "skill": int(inter.text_values["skill"]),
            "apply_date": datetime.now().isoformat()
        }
        save_applications(applications_data)

        admin_user = await bot.fetch_user(ADMIN_ID)
        if admin_user:
            view = ApplicationDecisionView(inter.author.id, inter.author.name)
            await admin_user.send(embed=embed, view=view)
            await inter.response.send_message("✅ Ваша заявка отправлена! Ожидайте решения в личных сообщениях.", ephemeral=True)

class ApplicationDecisionView(disnake.ui.View):
    def __init__(self, applicant_id, applicant_name):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.applicant_name = applicant_name

    @disnake.ui.button(label="Принять", style=disnake.ButtonStyle.success, emoji="✅")
    async def accept_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if str(self.applicant_id) not in applications_data["accepted_users"]:
            applications_data["accepted_users"].append(str(self.applicant_id))
            # Устанавливаем начальный рейтинг
            ratings_data["ratings"][str(self.applicant_id)] = 0
            save_ratings(ratings_data)
            save_applications(applications_data)

        user = await bot.fetch_user(self.applicant_id)
        if user:
            try:
                embed = disnake.Embed(
                    title="✅ ЗАЯВКА ПРИНЯТА!",
                    description=f"Поздравляю! Твоя заявка на обучение стрельбе одобрена.\n\n"
                              f"Свяжись с администратором в Discord: <@{ADMIN_ID}> (`mod1kus777`)\n\n"
                              f"Теперь тебе доступны обучающие материалы. Используй команду `/guides` для просмотра доступных гайдов.",
                    color=disnake.Color.green()
                )
                await user.send(embed=embed)
            except disnake.Forbidden:
                pass

        await inter.message.edit(content="✅ **Заявка принята!**", view=None)
        await inter.response.send_message("Заявка принята, пользователь уведомлен.", ephemeral=True)

    @disnake.ui.button(label="Отклонить", style=disnake.ButtonStyle.danger, emoji="❌")
    async def decline_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        user = await bot.fetch_user(self.applicant_id)
        if user:
            try:
                await user.send("❌ К сожалению, ваша заявка на обучение отклонена.")
            except disnake.Forbidden:
                pass
        await inter.message.edit(content="❌ **Заявка отклонена.**", view=None)
        await inter.response.send_message("Заявка отклонена.", ephemeral=True)

class TournamentRegistrationView(disnake.ui.View):
    def __init__(self, tournament_id):
        super().__init__(timeout=None)
        self.tournament_id = tournament_id

    @disnake.ui.button(label="Участвовать", style=disnake.ButtonStyle.success, emoji="🎯")
    async def participate_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if str(inter.author.id) not in applications_data["accepted_users"]:
            await inter.response.send_message("❌ Только принятые участники могут регистрироваться на турниры!", ephemeral=True)
            return
        
        tournament = tournaments_data.get("active_tournament")
        if not tournament or tournament["id"] != self.tournament_id:
            await inter.response.send_message("❌ Этот турнир уже неактивен!", ephemeral=True)
            return
        
        if str(inter.author.id) in tournament["pending_participants"]:
            await inter.response.send_message("❌ Вы уже подали заявку на участие!", ephemeral=True)
            return
        
        if str(inter.author.id) in tournament["participants"]:
            await inter.response.send_message("❌ Вы уже участник турнира!", ephemeral=True)
            return
        
        tournament["pending_participants"].append(str(inter.author.id))
        save_tournaments(tournaments_data)
        
        # Уведомляем админа
        admin_user = await bot.fetch_user(ADMIN_ID)
        if admin_user:
            embed = disnake.Embed(
                title="🆕 Новая заявка на турнир",
                description=f"Пользователь {inter.author.mention} хочет участвовать в турнире",
                color=disnake.Color.blue()
            )
            view = TournamentParticipantView(inter.author.id, self.tournament_id)
            await admin_user.send(embed=embed, view=view)
        
        await inter.response.send_message("✅ Ваша заявка на участие отправлена! Ожидайте подтверждения.", ephemeral=True)

class TournamentParticipantView(disnake.ui.View):
    def __init__(self, user_id, tournament_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.tournament_id = tournament_id

    @disnake.ui.button(label="Принять в турнир", style=disnake.ButtonStyle.success, emoji="✅")
    async def accept_participant(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        tournament = tournaments_data.get("active_tournament")
        if tournament and tournament["id"] == self.tournament_id:
            if str(self.user_id) in tournament["pending_participants"]:
                tournament["pending_participants"].remove(str(self.user_id))
                tournament["participants"].append(str(self.user_id))
                save_tournaments(tournaments_data)
                
                user = await bot.fetch_user(self.user_id)
                if user:
                    try:
                        await user.send("✅ Ваша заявка на участие в турнире ПРИНЯТА! Ждите информации о проведении!")
                    except:
                        pass
                
                await inter.message.edit(content="✅ Участник принят в турнир!", view=None)
                await inter.response.send_message("Участник принят!", ephemeral=True)

    @disnake.ui.button(label="Отклонить", style=disnake.ButtonStyle.danger, emoji="❌")
    async def decline_participant(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        tournament = tournaments_data.get("active_tournament")
        if tournament and tournament["id"] == self.tournament_id:
            if str(self.user_id) in tournament["pending_participants"]:
                tournament["pending_participants"].remove(str(self.user_id))
                save_tournaments(tournaments_data)
                
                user = await bot.fetch_user(self.user_id)
                if user:
                    try:
                        await user.send("❌ К сожалению, ваша заявка на участие в турнире отклонена.")
                    except:
                        pass
                
                await inter.message.edit(content="❌ Участник отклонен!", view=None)
                await inter.response.send_message("Участник отклонен!", ephemeral=True)

class GuidesCategoryView(disnake.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id
        
        # Создаем кнопки для каждой категории
        for category_id, category_data in guides_data["categories"].items():
            button = disnake.ui.Button(
                label=category_data["name"],
                style=disnake.ButtonStyle.primary,
                custom_id=f"guide_cat_{category_id}"
            )
            button.callback = self.create_category_callback(category_id)
            self.add_item(button)
    
    def create_category_callback(self, category_id):
        async def callback(inter: disnake.MessageInteraction):
            if inter.author.id != self.user_id:
                await inter.response.send_message("Это не ваше меню!", ephemeral=True)
                return
            
            category = guides_data["categories"][category_id]
            embed = disnake.Embed(
                title=f"📚 {category['name']}",
                description="Выберите гайд для просмотра:",
                color=disnake.Color.blue()
            )
            
            view = GuidesItemsView(self.user_id, category_id)
            await inter.response.edit_message(embed=embed, view=view)
        
        return callback

class GuidesItemsView(disnake.ui.View):
    def __init__(self, user_id, category_id):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.category_id = category_id
        
        category = guides_data["categories"][category_id]
        for guide in category["guides"]:
            button = disnake.ui.Button(
                label=guide["title"],
                style=disnake.ButtonStyle.secondary,
                custom_id=f"guide_{guide['id']}"
            )
            button.callback = self.create_guide_callback(guide)
            self.add_item(button)
        
        # Кнопка назад
        back_button = disnake.ui.Button(label="◀ Назад", style=disnake.ButtonStyle.danger)
        back_button.callback = self.back_callback
        self.add_item(back_button)
    
    def create_guide_callback(self, guide):
        async def callback(inter: disnake.MessageInteraction):
            if inter.author.id != self.user_id:
                await inter.response.send_message("Это не ваше меню!", ephemeral=True)
                return
            
            embed = disnake.Embed(
                title=guide["title"],
                description=guide["description"],
                url=guide["url"],
                color=disnake.Color.green()
            )
            if guide.get("thumbnail"):
                embed.set_thumbnail(url=guide["thumbnail"])
            
            view = DeleteButton(inter.author.id)
            await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        
        return callback
    
    async def back_callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.user_id:
            await inter.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        embed = disnake.Embed(
            title="📚 ДОСТУПНЫЕ КАТЕГОРИИ ГАЙДОВ",
            description="Выберите категорию для просмотра гайдов:",
            color=disnake.Color.blue()
        )
        view = GuidesCategoryView(self.user_id)
        await inter.response.edit_message(embed=embed, view=view)

# ==================== АДМИН-ПАНЕЛЬ ====================

class AdminPanelView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="📚 Управление гайдами", style=disnake.ButtonStyle.primary, row=1)
    async def manage_guides(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != ADMIN_ID:
            return await inter.response.send_message("Нет доступа.", ephemeral=True)
        
        embed = disnake.Embed(
            title="📚 УПРАВЛЕНИЕ ГАЙДАМИ",
            description="Выберите действие:",
            color=disnake.Color.blue()
        )
        view = GuidesManagementView()
        await inter.response.edit_message(embed=embed, view=view)

    @disnake.ui.button(label="📊 Рейтинг участников", style=disnake.ButtonStyle.secondary, row=1)
    async def manage_ratings(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != ADMIN_ID:
            return await inter.response.send_message("Нет доступа.", ephemeral=True)
        
        embed = disnake.Embed(
            title="📊 УПРАВЛЕНИЕ РЕЙТИНГОМ",
            description="Выберите действие:",
            color=disnake.Color.gold()
        )
        view = RatingsManagementView()
        await inter.response.edit_message(embed=embed, view=view)

    @disnake.ui.button(label="📢 Рассылка", style=disnake.ButtonStyle.success, row=2)
    async def broadcast(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != ADMIN_ID:
            return await inter.response.send_message("Нет доступа.", ephemeral=True)
        
        embed = disnake.Embed(
            title="📢 РАССЫЛКА СООБЩЕНИЙ",
            description="Выберите тип рассылки:",
            color=disnake.Color.green()
        )
        view = BroadcastView()
        await inter.response.edit_message(embed=embed, view=view)

    @disnake.ui.button(label="🏆 Управление турнирами", style=disnake.ButtonStyle.danger, row=2)
    async def manage_tournaments(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != ADMIN_ID:
            return await inter.response.send_message("Нет доступа.", ephemeral=True)
        
        embed = disnake.Embed(
            title="🏆 УПРАВЛЕНИЕ ТУРНИРАМИ",
            description="Выберите действие:",
            color=disnake.Color.purple()
        )
        view = TournamentManagementView()
        await inter.response.edit_message(embed=embed, view=view)

    @disnake.ui.button(label="👥 Список принятых", style=disnake.ButtonStyle.secondary, row=3)
    async def list_accepted(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != ADMIN_ID:
            return await inter.response.send_message("Нет доступа.", ephemeral=True)
        
        if not applications_data["accepted_users"]:
            await inter.response.send_message("Список принятых пользователей пуст.", ephemeral=True)
            return
        
        users_text = ""
        for user_id in applications_data["accepted_users"]:
            user = await bot.fetch_user(int(user_id))
            rating = ratings_data["ratings"].get(user_id, 0)
            users_text += f"• {user.mention} - Рейтинг: {rating}\n"
        
        embed = disnake.Embed(title="✅ Принятые ученики", description=users_text, color=disnake.Color.green())
        await inter.response.send_message(embed=embed, ephemeral=True)

class GuidesManagementView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @disnake.ui.button(label="➕ Добавить категорию", style=disnake.ButtonStyle.success)
    async def add_category(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(AddCategoryModal())
    
    @disnake.ui.button(label="➕ Добавить гайд", style=disnake.ButtonStyle.primary)
    async def add_guide(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not guides_data["categories"]:
            await inter.response.send_message("❌ Сначала создайте хотя бы одну категорию!", ephemeral=True)
            return
        
        options = [
            disnake.SelectOption(label=data["name"], value=cat_id)
            for cat_id, data in guides_data["categories"].items()
        ]
        select = disnake.ui.Select(placeholder="Выберите категорию...", options=options)
        
        async def select_callback(select_inter: disnake.MessageInteraction):
            modal = AddGuideModal(select.values[0])
            await select_inter.response.send_modal(modal)
        
        select.callback = select_callback
        view = disnake.ui.View()
        view.add_item(select)
        await inter.response.send_message("Выберите категорию для нового гайда:", view=view, ephemeral=True)
    
    @disnake.ui.button(label="✏ Редактировать гайд", style=disnake.ButtonStyle.secondary)
    async def edit_guide(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not guides_data["categories"]:
            await inter.response.send_message("❌ Нет доступных гайдов для редактирования!", ephemeral=True)
            return
        
        options = []
        for cat_id, cat_data in guides_data["categories"].items():
            for guide in cat_data["guides"]:
                options.append(
                    disnake.SelectOption(
                        label=f"{guide['title']} ({cat_data['name']})",
                        value=f"{cat_id}|{guide['id']}"
                    )
                )
        
        if not options:
            await inter.response.send_message("❌ Нет гайдов для редактирования!", ephemeral=True)
            return
        
        select = disnake.ui.Select(placeholder="Выберите гайд для редактирования...", options=options[:25])
        
        async def select_callback(select_inter: disnake.MessageInteraction):
            cat_id, guide_id = select.values[0].split("|")
            guide = next(g for g in guides_data["categories"][cat_id]["guides"] if g["id"] == guide_id)
            modal = EditGuideModal(cat_id, guide)
            await select_inter.response.send_modal(modal)
        
        select.callback = select_callback
        view = disnake.ui.View()
        view.add_item(select)
        await inter.response.send_message("Выберите гайд для редактирования:", view=view, ephemeral=True)

class AddCategoryModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(label="Название категории", placeholder="Например: Аим, Слайды...", 
                               custom_id="name", style=disnake.TextInputStyle.short, max_length=50),
            disnake.ui.TextInput(label="Описание категории", placeholder="Краткое описание...", 
                               custom_id="description", style=disnake.TextInputStyle.paragraph, max_length=200, required=False),
        ]
        super().__init__(title="➕ Добавление категории", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        category_id = str(len(guides_data["categories"]) + 1)
        guides_data["categories"][category_id] = {
            "id": category_id,
            "name": inter.text_values["name"],
            "description": inter.text_values.get("description", ""),
            "guides": []
        }
        save_guides(guides_data)
        await inter.response.send_message(f"✅ Категория '{inter.text_values['name']}' создана!", ephemeral=True)

class AddGuideModal(disnake.ui.Modal):
    def __init__(self, category_id):
        self.category_id = category_id
        components = [
            disnake.ui.TextInput(label="Название гайда", placeholder="Введите название", 
                               custom_id="title", style=disnake.TextInputStyle.short, max_length=100),
            disnake.ui.TextInput(label="Ссылка на видео", placeholder="YouTube ссылка", 
                               custom_id="url", style=disnake.TextInputStyle.short, max_length=200),
            disnake.ui.TextInput(label="Описание", placeholder="Краткое описание гайда", 
                               custom_id="description", style=disnake.TextInputStyle.paragraph, max_length=500),
            disnake.ui.TextInput(label="Ссылка на превью (опционально)", placeholder="URL картинки для превью", 
                               custom_id="thumbnail", style=disnake.TextInputStyle.short, max_length=200, required=False),
        ]
        super().__init__(title="➕ Добавление гайда", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        guide_id = str(len(guides_data["categories"][self.category_id]["guides"]) + 1)
        guide = {
            "id": guide_id,
            "title": inter.text_values["title"],
            "url": inter.text_values["url"],
            "description": inter.text_values["description"],
            "thumbnail": inter.text_values.get("thumbnail", "")
        }
        guides_data["categories"][self.category_id]["guides"].append(guide)
        save_guides(guides_data)
        await inter.response.send_message(f"✅ Гайд '{guide['title']}' добавлен!", ephemeral=True)

class EditGuideModal(disnake.ui.Modal):
    def __init__(self, category_id, guide):
        self.category_id = category_id
        self.guide_id = guide["id"]
        components = [
            disnake.ui.TextInput(label="Название гайда", value=guide["title"], 
                               custom_id="title", style=disnake.TextInputStyle.short, max_length=100),
            disnake.ui.TextInput(label="Ссылка на видео", value=guide["url"], 
                               custom_id="url", style=disnake.TextInputStyle.short, max_length=200),
            disnake.ui.TextInput(label="Описание", value=guide["description"], 
                               custom_id="description", style=disnake.TextInputStyle.paragraph, max_length=500),
            disnake.ui.TextInput(label="Ссылка на превью", value=guide.get("thumbnail", ""), 
                               custom_id="thumbnail", style=disnake.TextInputStyle.short, max_length=200, required=False),
        ]
        super().__init__(title=f"✏ Редактирование: {guide['title']}", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        for guide in guides_data["categories"][self.category_id]["guides"]:
            if guide["id"] == self.guide_id:
                guide["title"] = inter.text_values["title"]
                guide["url"] = inter.text_values["url"]
                guide["description"] = inter.text_values["description"]
                guide["thumbnail"] = inter.text_values.get("thumbnail", "")
                break
        save_guides(guides_data)
        await inter.response.send_message(f"✅ Гайд обновлен!", ephemeral=True)

class RatingsManagementView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @disnake.ui.button(label="⭐ Установить рейтинг", style=disnake.ButtonStyle.primary)
    async def set_rating(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not applications_data["accepted_users"]:
            await inter.response.send_message("❌ Нет принятых пользователей!", ephemeral=True)
            return
        
        options = []
        for user_id in applications_data["accepted_users"]:
            try:
                user = await bot.fetch_user(int(user_id))
                rating = ratings_data["ratings"].get(user_id, 0)
                options.append(
                    disnake.SelectOption(
                        label=f"{user.name} (Рейтинг: {rating})",
                        value=user_id
                    )
                )
            except:
                pass
        
        select = disnake.ui.Select(placeholder="Выберите пользователя...", options=options[:25])
        
        async def select_callback(select_inter: disnake.MessageInteraction):
            modal = SetRatingModal(select.values[0])
            await select_inter.response.send_modal(modal)
        
        select.callback = select_callback
        view = disnake.ui.View()
        view.add_item(select)
        await inter.response.send_message("Выберите пользователя для установки рейтинга:", view=view, ephemeral=True)

class SetRatingModal(disnake.ui.Modal):
    def __init__(self, user_id):
        self.user_id = user_id
        current_rating = ratings_data["ratings"].get(user_id, 0)
        components = [
            disnake.ui.TextInput(label="Новый рейтинг (0-100)", placeholder="Введите число от 0 до 100", 
                               custom_id="rating", style=disnake.TextInputStyle.short, max_length=3, 
                               value=str(current_rating)),
        ]
        super().__init__(title="⭐ Установка рейтинга", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        try:
            rating = int(inter.text_values["rating"])
            if 0 <= rating <= 100:
                ratings_data["ratings"][self.user_id] = rating
                save_ratings(ratings_data)
                await inter.response.send_message(f"✅ Рейтинг установлен на {rating}!", ephemeral=True)
            else:
                await inter.response.send_message("❌ Рейтинг должен быть от 0 до 100!", ephemeral=True)
        except ValueError:
            await inter.response.send_message("❌ Введите корректное число!", ephemeral=True)

class BroadcastView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @disnake.ui.button(label="📢 Всем участникам", style=disnake.ButtonStyle.primary)
    async def broadcast_all(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        modal = BroadcastModal("all")
        await inter.response.send_modal(modal)
    
    @disnake.ui.button(label="👤 Конкретному участнику", style=disnake.ButtonStyle.secondary)
    async def broadcast_single(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not applications_data["accepted_users"]:
            await inter.response.send_message("❌ Нет принятых пользователей!", ephemeral=True)
            return
        
        options = []
        for user_id in applications_data["accepted_users"]:
            try:
                user = await bot.fetch_user(int(user_id))
                options.append(
                    disnake.SelectOption(
                        label=user.name,
                        value=user_id
                    )
                )
            except:
                pass
        
        select = disnake.ui.Select(placeholder="Выберите получателя...", options=options[:25])
        
        async def select_callback(select_inter: disnake.MessageInteraction):
            modal = BroadcastModal("single", select.values[0])
            await select_inter.response.send_modal(modal)
        
        select.callback = select_callback
        view = disnake.ui.View()
        view.add_item(select)
        await inter.response.send_message("Выберите получателя сообщения:", view=view, ephemeral=True)

class BroadcastModal(disnake.ui.Modal):
    def __init__(self, broadcast_type, user_id=None):
        self.broadcast_type = broadcast_type
        self.user_id = user_id
        components = [
            disnake.ui.TextInput(label="Заголовок сообщения", placeholder="Введите заголовок", 
                               custom_id="title", style=disnake.TextInputStyle.short, max_length=100),
            disnake.ui.TextInput(label="Текст сообщения", placeholder="Введите текст сообщения", 
                               custom_id="content", style=disnake.TextInputStyle.paragraph, max_length=1000),
        ]
        title = "📢 Рассылка всем" if broadcast_type == "all" else "👤 Личное сообщение"
        super().__init__(title=title, components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        embed = disnake.Embed(
            title=inter.text_values["title"],
            description=inter.text_values["content"],
            color=disnake.Color.blue()
        )
        embed.set_footer(text=f"Отправлено администратором")
        
        if self.broadcast_type == "all":
            success_count = 0
            for user_id in applications_data["accepted_users"]:
                try:
                    user = await bot.fetch_user(int(user_id))
                    await user.send(embed=embed)
                    success_count += 1
                except:
                    pass
            await inter.response.send_message(f"✅ Сообщение отправлено {success_count} участникам!", ephemeral=True)
        else:
            try:
                user = await bot.fetch_user(int(self.user_id))
                await user.send(embed=embed)
                await inter.response.send_message(f"✅ Сообщение отправлено пользователю {user.name}!", ephemeral=True)
            except:
                await inter.response.send_message("❌ Не удалось отправить сообщение!", ephemeral=True)

class TournamentManagementView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @disnake.ui.button(label="🏆 Создать турнир", style=disnake.ButtonStyle.success)
    async def create_tournament(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if tournaments_data.get("active_tournament"):
            await inter.response.send_message("❌ Уже есть активный турнир! Завершите его сначала.", ephemeral=True)
            return
        modal = CreateTournamentModal()
        await inter.response.send_modal(modal)
    
    @disnake.ui.button(label="📢 Объявить турнир", style=disnake.ButtonStyle.primary)
    async def announce_tournament(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        tournament = tournaments_data.get("active_tournament")
        if not tournament:
            await inter.response.send_message("❌ Нет активного турнира!", ephemeral=True)
            return
        
        embed = disnake.Embed(
            title=f"🏆 {tournament['name']}",
            description=tournament["description"],
            color=disnake.Color.gold()
        )
        embed.add_field(name="🥇 1 место", value=f"{tournament['prizes']['first']:,} $".replace(',', ' '), inline=True)
        embed.add_field(name="🥈 2 место", value=f"{tournament['prizes']['second']:,} $".replace(',', ' '), inline=True)
        embed.add_field(name="🥉 3 место", value=f"{tournament['prizes']['third']:,} $".replace(',', ' '), inline=True)
        embed.add_field(name="📅 Дата проведения", value=tournament.get("date", "Скоро"), inline=False)
        embed.set_footer(text="Нажмите кнопку ниже, чтобы участвовать!")
        
        view = TournamentRegistrationView(tournament["id"])
        
        success_count = 0
        for user_id in applications_data["accepted_users"]:
            try:
                user = await bot.fetch_user(int(user_id))
                await user.send(embed=embed, view=view)
                success_count += 1
            except:
                pass
        
        await inter.response.send_message(f"✅ Турнир анонсирован! Объявление отправлено {success_count} участникам.", ephemeral=True)
    
    @disnake.ui.button(label="🏁 Завершить турнир", style=disnake.ButtonStyle.danger)
    async def finish_tournament(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        tournament = tournaments_data.get("active_tournament")
        if not tournament:
            await inter.response.send_message("❌ Нет активного турнира!", ephemeral=True)
            return
        
        modal = FinishTournamentModal()
        await inter.response.send_modal(modal)

class CreateTournamentModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(label="Название турнира", placeholder="Например: Турнир по аиму", 
                               custom_id="name", style=disnake.TextInputStyle.short, max_length=100),
            disnake.ui.TextInput(label="Описание", placeholder="Подробное описание турнира", 
                               custom_id="description", style=disnake.TextInputStyle.paragraph, max_length=500),
            disnake.ui.TextInput(label="Приз за 1 место ($)", placeholder="Сумма в долларах", 
                               custom_id="prize1", style=disnake.TextInputStyle.short, max_length=10),
            disnake.ui.TextInput(label="Приз за 2 место ($)", placeholder="Сумма в долларах", 
                               custom_id="prize2", style=disnake.TextInputStyle.short, max_length=10),
            disnake.ui.TextInput(label="Приз за 3 место ($)", placeholder="Сумма в долларах", 
                               custom_id="prize3", style=disnake.TextInputStyle.short, max_length=10),
        ]
        super().__init__(title="🏆 Создание турнира", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        tournament = {
            "id": str(int(datetime.now().timestamp())),
            "name": inter.text_values["name"],
            "description": inter.text_values["description"],
            "prizes": {
                "first": int(inter.text_values["prize1"]),
                "second": int(inter.text_values["prize2"]),
                "third": int(inter.text_values["prize3"])
            },
            "created_at": datetime.now().isoformat(),
            "participants": [],
            "pending_participants": [],
            "status": "active"
        }
        tournaments_data["active_tournament"] = tournament
        save_tournaments(tournaments_data)
        await inter.response.send_message(f"✅ Турнир '{tournament['name']}' создан! Используйте кнопку 'Объявить турнир' для рассылки.", ephemeral=True)

class FinishTournamentModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(label="🥇 1 место (Discord ID)", placeholder="Введите Discord ID победителя", 
                               custom_id="first", style=disnake.TextInputStyle.short, max_length=20),
            disnake.ui.TextInput(label="🥈 2 место (Discord ID)", placeholder="Введите Discord ID", 
                               custom_id="second", style=disnake.TextInputStyle.short, max_length=20),
            disnake.ui.TextInput(label="🥉 3 место (Discord ID)", placeholder="Введите Discord ID", 
                               custom_id="third", style=disnake.TextInputStyle.short, max_length=20),
        ]
        super().__init__(title="🏁 Завершение турнира", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        tournament = tournaments_data.get("active_tournament")
        if not tournament:
            await inter.response.send_message("❌ Нет активного турнира!", ephemeral=True)
            return
        
        winners = {
            "first": inter.text_values["first"],
            "second": inter.text_values["second"],
            "third": inter.text_values["third"]
        }
        
        # Отправляем уведомления победителям и проигравшим
        for place, user_id in winners.items():
            try:
                user = await bot.fetch_user(int(user_id))
                prize = tournament["prizes"][place]
                embed = disnake.Embed(
                    title=f"🎉 ПОЗДРАВЛЯЕМ! 🎉",
                    description=f"Вы заняли **{['🥇 1-е', '🥈 2-е', '🥉 3-е'][['first', 'second', 'third'].index(place)]} место** в турнире «{tournament['name']}»!\n\n"
                              f"Ваш выигрыш: **{prize:,} $**\n\n"
                              f"Свяжитесь с администратором для получения приза!",
                    color=disnake.Color.gold()
                )
                await user.send(embed=embed)
            except:
                pass
        
        # Отправляем утешительные сообщения остальным участникам
        consolation = random.choice(consolation_messages)
        for user_id in tournament["participants"]:
            if str(user_id) not in winners.values():
                try:
                    user = await bot.fetch_user(int(user_id))
                    embed = disnake.Embed(
                        title="💪 Спасибо за участие!",
                        description=f"{consolation}\n\n"
                                  f"Продолжай тренироваться и в следующий раз обязательно победишь!",
                        color=disnake.Color.blue()
                    )
                    await user.send(embed=embed)
                except:
                    pass
        
        # Сохраняем турнир в историю
        tournament["status"] = "finished"
        tournament["winners"] = winners
        tournament["finished_at"] = datetime.now().isoformat()
        tournaments_data["history"].append(tournament)
        tournaments_data["active_tournament"] = None
        save_tournaments(tournaments_data)
        
        await inter.response.send_message("✅ Турнир завершен! Результаты отправлены участникам.", ephemeral=True)

# ==================== КОМАНДЫ БОТА ====================

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен и готов к работе!')
    await bot.change_presence(activity=disnake.Game(name="/command | Обучение стрельбе"))

async def send_with_delete_button(inter, content=None, embed=None, ephemeral=False):
    """Отправляет сообщение с кнопкой удаления"""
    view = DeleteButton(inter.author.id)
    if embed:
        await inter.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
    else:
        await inter.response.send_message(content, view=view, ephemeral=ephemeral)

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
    embed.add_field(name="⚙️ **Версия:**", value="5.0.0 (Ultimate Training)", inline=True)
    embed.add_field(name="📢 **По вопросам информации и обновлений:**", value="**@mod1kus777**", inline=False)
    embed.set_footer(text="Nexus Training Bot | Сделано с душой для своей фамы")
    await send_with_delete_button(inter, embed=embed)

@bot.slash_command(name="apply", description="📝 Подать заявку на обучение стрельбе")
async def apply(inter: disnake.ApplicationCommandInteraction):
    await inter.response.send_modal(ApplicationModal())

def is_accepted():
    async def predicate(inter: disnake.ApplicationCommandInteraction):
        if inter.author.id == ADMIN_ID:
            return True
        if str(inter.author.id) in applications_data["accepted_users"]:
            return True
        await inter.response.send_message("❌ У вас нет доступа к гайдам. Сначала подайте заявку `/apply`.", ephemeral=True)
        return False
    return commands.check(predicate)

@bot.slash_command(name="guides", description="📚 Показать все доступные гайды")
@is_accepted()
async def guides(inter: disnake.ApplicationCommandInteraction):
    if not guides_data["categories"]:
        await inter.response.send_message("❌ Пока нет доступных гайдов.", ephemeral=True)
        return
    
    embed = disnake.Embed(
        title="📚 ДОСТУПНЫЕ КАТЕГОРИИ ГАЙДОВ",
        description="Выберите категорию для просмотра гайдов:",
        color=disnake.Color.blue()
    )
    
    # Добавляем информацию о категориях
    for cat_id, cat_data in guides_data["categories"].items():
        embed.add_field(
            name=cat_data["name"],
            value=f"{cat_data.get('description', 'Нет описания')}\nГайдов: {len(cat_data['guides'])}",
            inline=False
        )
    
    view = GuidesCategoryView(inter.author.id)
    await inter.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.slash_command(name="rating", description="📊 Посмотреть рейтинг участников")
async def rating(inter: disnake.ApplicationCommandInteraction):
    if not ratings_data["ratings"]:
        await inter.response.send_message("❌ Пока нет рейтингов участников.", ephemeral=True)
        return
    
    # Сортируем участников по рейтингу
    sorted_ratings = sorted(ratings_data["ratings"].items(), key=lambda x: x[1], reverse=True)
    
    embed = disnake.Embed(
        title="🏆 ТОП УЧАСТНИКОВ ПО СТРЕЛЬБЕ",
        description="Рейтинг основан на оценке навыков администратором",
        color=disnake.Color.gold()
    )
    
    medals = ["🥇", "🥈", "🥉"]
    rating_list = ""
    
    for i, (user_id, rating) in enumerate(sorted_ratings[:10], 1):
        try:
            user = await bot.fetch_user(int(user_id))
            user_data = applications_data["user_applications"].get(user_id, {})
            nickname = user_data.get("nickname", "Неизвестно")
            
            medal = medals[i-1] if i <= 3 else f"{i}."
            rating_list += f"{medal} **{user.name}** ({nickname}) - **{rating}/100**\n"
        except:
            rating_list += f"{i}. Пользователь ID:{user_id} - **{rating}/100**\n"
    
    embed.add_field(name="Топ-10 участников:", value=rating_list or "Нет данных", inline=False)
    
    # Добавляем информацию о себе, если пользователь есть в рейтинге
    user_rating = ratings_data["ratings"].get(str(inter.author.id))
    if user_rating is not None:
        user_position = [i+1 for i, (uid, _) in enumerate(sorted_ratings) if uid == str(inter.author.id)][0]
        embed.add_field(
            name="📊 Ваша позиция",
            value=f"Вы на **{user_position}** месте с рейтингом **{user_rating}/100**",
            inline=False
        )
    
    embed.set_footer(text="Работайте над собой, чтобы подняться в топе!")
    await send_with_delete_button(inter, embed=embed)

@bot.slash_command(name="tournament", description="🏆 Информация о текущем турнире")
async def tournament_info(inter: disnake.ApplicationCommandInteraction):
    tournament = tournaments_data.get("active_tournament")
    
    if not tournament:
        # Показываем последний завершенный турнир
        if tournaments_data["history"]:
            last = tournaments_data["history"][-1]
            embed = disnake.Embed(
                title=f"🏆 ПОСЛЕДНИЙ ТУРНИР: {last['name']}",
                description=last["description"],
                color=disnake.Color.purple()
            )
            embed.add_field(name="🥇 1 место", value=f"Приз: {last['prizes']['first']:,} $".replace(',', ' '), inline=True)
            embed.add_field(name="🥈 2 место", value=f"Приз: {last['prizes']['second']:,} $".replace(',', ' '), inline=True)
            embed.add_field(name="🥉 3 место", value=f"Приз: {last['prizes']['third']:,} $".replace(',', ' '), inline=True)
            embed.set_footer(text="Следите за анонсами новых турниров!")
        else:
            embed = disnake.Embed(
                title="🏆 ТУРНИРЫ",
                description="Сейчас нет активных турниров. Следите за анонсами!",
                color=disnake.Color.blue()
            )
            embed.add_field(
                name="💡 Информация",
                value="Турниры проводятся регулярно. Победители получают денежные призы!",
                inline=False
            )
        await send_with_delete_button(inter, embed=embed)
        return
    
    embed = disnake.Embed(
        title=f"🏆 АКТИВНЫЙ ТУРНИР: {tournament['name']}",
        description=tournament["description"],
        color=disnake.Color.gold()
    )
    embed.add_field(name="🥇 1 место", value=f"{tournament['prizes']['first']:,} $".replace(',', ' '), inline=True)
    embed.add_field(name="🥈 2 место", value=f"{tournament['prizes']['second']:,} $".replace(',', ' '), inline=True)
    embed.add_field(name="🥉 3 место", value=f"{tournament['prizes']['third']:,} $".replace(',', ' '), inline=True)
    embed.add_field(name="👥 Участников", value=f"{len(tournament['participants'])} подтвержденных", inline=True)
    embed.add_field(name="⏳ В ожидании", value=f"{len(tournament['pending_participants'])} заявок", inline=True)
    
    if str(inter.author.id) in applications_data["accepted_users"]:
        view = TournamentRegistrationView(tournament["id"])
        await inter.response.send_message(embed=embed, view=view)
    else:
        embed.set_footer(text="Только принятые участники могут регистрироваться на турнир")
        await send_with_delete_button(inter, embed=embed)

@bot.slash_command(name="command", description="📋 Показать все команды бота")
async def commands_list(inter: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="🎯 NEXUS TRAINING BOT v5.0 🎯",
        description="Полный список команд для управления ботом:",
        color=disnake.Color.purple()
    )
    
    embed.add_field(name="📝 ОСНОВНЫЕ КОМАНДЫ", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/apply", value="📋 Подать заявку на обучение", inline=False)
    embed.add_field(name="/guides", value="📚 Просмотр всех гайдов (для принятых)", inline=False)
    embed.add_field(name="/rating", value="📊 Рейтинг участников по стрельбе", inline=False)
    embed.add_field(name="/tournament", value="🏆 Информация о турнирах", inline=False)
    
    embed.add_field(name="\n✨ ИНФОРМАЦИОННЫЕ КОМАНДЫ", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/nexus", value="📜 История фамы Nexus", inline=True)
    embed.add_field(name="/promo", value="🎁 Промокод Majestic RP", inline=True)
    embed.add_field(name="/botinfo", value="🤖 Информация о боте", inline=True)
    embed.add_field(name="/command", value="📋 Показать это меню", inline=True)
    
    if inter.author.id == ADMIN_ID:
        embed.add_field(name="\n⚙️ АДМИН-КОМАНДЫ", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
        embed.add_field(name="/admin", value="🔧 Панель управления ботом", inline=False)
    
    embed.set_footer(text="Создано Vladosis Nexus | Маджестик | Miami 8")
    await send_with_delete_button(inter, embed=embed)

@bot.slash_command(name="admin", description="⚙️ Админ-панель (только для админа)")
async def admin_panel(inter: disnake.ApplicationCommandInteraction):
    if inter.author.id != ADMIN_ID:
        await inter.response.send_message("❌ У вас нет доступа к этой команде.", ephemeral=True)
        return
    
    embed = disnake.Embed(
        title="⚙️ АДМИН-ПАНЕЛЬ NEXUS TRAINING",
        description="Здесь вы можете полностью управлять ботом и его контентом.",
        color=disnake.Color.dark_blue()
    )
    embed.add_field(name="📚 Гайды", value="Добавление категорий и гайдов в неограниченном количестве", inline=False)
    embed.add_field(name="📊 Рейтинг", value="Установка рейтинга участникам (0-100)", inline=False)
    embed.add_field(name="📢 Рассылка", value="Отправка сообщений всем или конкретным участникам", inline=False)
    embed.add_field(name="🏆 Турниры", value="Создание и управление турнирами с призами", inline=False)
    
    view = AdminPanelView()
    await inter.response.send_message(embed=embed, view=view, ephemeral=True)

# ==================== ЗАПУСК БОТА ====================
bot.run(os.getenv('DISCORD_TOKEN'))