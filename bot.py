import disnake
from disnake.ext import commands
import yt_dlp as youtube_dl
import asyncio
import random
import os

# Настройки бота (включаем все интенты)
intents = disnake.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

# Настройки для YouTube
ydl_opts = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'm4a',
    }],
    'quiet': True,
    'no_warnings': True,
    'cookiefile': 'cookies.txt',
    'extract_flat': False,
    'force_generic_extractor': False,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"',
    'options': '-vn'
}

# Глобальные переменные
queue = []
current_volume = 50

# Комплименты
compliments = [
    "Ты 🔥 **имба** 🔥 в этом мире Маджестик!",
    "С тобой даже **топ-1 гильдия** бы проиграла от зависти! 💪",
    "Твой скилл на Маджестике — **легенда**, которую рассказывают новичкам! 🌟",
    "Ты не игрок, ты — **Машина для побед**! 🏆",
    "С тобой в пати — **100% победа**, даже если ты просто стоишь и улыбаешься! 😎"
]

# Предсказания
predictions = [
    "🎲 Сегодня ты **найдёшь легендарный меч** в подземелье! 🗡️",
    "🎲 **Твой крит урона** будет 9999+ в следующей битве! 💥",
    "🎲 **Осторожно**: сегодня у тебя будет **настоящий вызов** от секретного босса! 👑",
    "🎲 Фортуна улыбается тебе — **редкий артефакт** уже близко! ✨",
    "🎲 **Великий Оракул** говорит: завтра ты получишь **эпическую награду**! 🎁"
]

# Топ тулеров
top_tulers = {
    "🥇": {"name": "Vladosis Nexus", "description": "Король тайников и ограблений. Машина для заработка! Готов научить каждого, кто хочет тулиться как профи."},
    "🥈": {"name": "Vladislav Nexus", "description": "Стратег и мастер трассы. Знает всё о маршрутах и схемах. Научит зарабатывать миллионы!"},
    "🥉": {"name": "???", "description": "Твоё место здесь! Тулись как герой, показывай результат, и ты попадёшь в топ тулеров Nexus. Мы научим тебя всему!"}
}

# Музыкальные функции
class MusicPlayer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.voice_client = None

    async def play_next(self):
        global queue
        if queue:
            queue.pop(0)
            if queue:
                next_song = queue[0]
                await self.play_song(next_song['url'])
        else:
            if self.ctx.voice_client:
                await self.ctx.voice_client.disconnect()

    async def play_song(self, url):
        voice_client = self.ctx.voice_client
        if not voice_client:
            return
            
        voice_client.stop()
        
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Правильное извлечение URL потока
                if 'entries' in info:
                    # Это плейлист или результат поиска
                    url2 = info['entries'][0]['url']
                else:
                    # Это прямой URL видео
                    url2 = info['url']
                
                source = await disnake.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
                source = disnake.PCMVolumeTransformer(source, volume=current_volume/100)
                
                voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), bot.loop))
        except Exception as e:
            print(f"Ошибка воспроизведения: {e}")
            await self.play_next()

# Событие готовности
@bot.event
async def on_ready():
    # ИСПРАВЛЕНО: Вместо sync_global_commands() используем sync_application_commands()
    try:
        await bot.sync_application_commands()
        print(f'✅ Команды синхронизированы!')
    except Exception as e:
        print(f'⚠️ Ошибка синхронизации команд: {e}')
    
    print(f'✅ Бот {bot.user} запущен и готов к работе!')
    await bot.change_presence(activity=disnake.Game(name="/command | Маджестик"))

# ==================== МУЗЫКАЛЬНЫЕ КОМАНДЫ ====================

@bot.slash_command(name="play", description="Включить трек из YouTube")
async def play(ctx: disnake.ApplicationCommandInteraction, search: str):
    """Включает музыку из YouTube"""
    await ctx.response.defer()
    
    if not ctx.author.voice:
        await ctx.edit_original_response(content="❌ Вы не в голосовом канале!")
        return
    
    voice_channel = ctx.author.voice.channel
    
    # Подключаемся к каналу если ещё не подключены
    if not ctx.voice_client:
        await voice_channel.connect()
    
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            # Проверяем, является ли search ссылкой
            if search.startswith(('http://', 'https://')):
                info = ydl.extract_info(search, download=False)
                url = search
                title = info.get('title', 'Неизвестный трек')
            else:
                info = ydl.extract_info(f"ytsearch:{search}", download=False)
                url = info['entries'][0]['webpage_url']
                title = info['entries'][0]['title']
    except Exception as e:
        await ctx.edit_original_response(content=f"❌ Не удалось найти трек: {str(e)}")
        return
    
    queue.append({'url': url, 'title': title})
    
    # Проверяем, играет ли уже что-то
    if ctx.voice_client and ctx.voice_client.is_playing():
        await ctx.edit_original_response(content=f"✅ Добавлено в очередь: **{title}**")
    else:
        await ctx.edit_original_response(content=f"🎵 Сейчас играет: **{title}**")
        player = MusicPlayer(ctx)
        await player.play_song(url)

@bot.slash_command(name="stop", description="Остановить текущий трек")
async def stop(ctx: disnake.ApplicationCommandInteraction):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.response.send_message("⏸️ Трек остановлен. Используйте `/resume` чтобы продолжить.")
    else:
        await ctx.response.send_message("❌ Ничего не играет!")

@bot.slash_command(name="resume", description="Возобновить остановленный трек")
async def resume(ctx: disnake.ApplicationCommandInteraction):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.response.send_message("▶️ Трек возобновлён!")
    else:
        await ctx.response.send_message("❌ Нет остановленного трека!")

@bot.slash_command(name="volume", description="Изменить громкость (0-300%)")
async def volume(ctx: disnake.ApplicationCommandInteraction, level: int):
    global current_volume
    if level < 0 or level > 300:
        await ctx.response.send_message("❌ Громкость должна быть от 0 до 300!")
        return
    current_volume = level
    if ctx.voice_client and ctx.voice_client.source:
        ctx.voice_client.source.volume = level / 100
    await ctx.response.send_message(f"🔊 Громкость установлена на {level}%")

@bot.slash_command(name="clear", description="Очистить очередь треков")
async def clear(ctx: disnake.ApplicationCommandInteraction):
    global queue
    queue = []
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
    await ctx.response.send_message("🗑️ Очередь полностью очищена!")

@bot.slash_command(name="skip", description="Пропустить текущий трек")
async def skip(ctx: disnake.ApplicationCommandInteraction):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.response.send_message("⏭️ Трек пропущен!")
    else:
        await ctx.response.send_message("❌ Ничего не играет!")

@bot.slash_command(name="leave", description="Выйти из голосового канала")
async def leave(ctx: disnake.ApplicationCommandInteraction):
    global queue
    queue = []
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.response.send_message("👋 Бот вышел из канала, очередь очищена!")
    else:
        await ctx.response.send_message("❌ Бот не в голосовом канале!")

# ==================== КОМАНДЫ ФАМЫ ====================

@bot.slash_command(name="nexus", description="История создания фамы Nexus")
async def nexus(ctx: disnake.ApplicationCommandInteraction):
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
    await ctx.response.send_message(embed=embed)

@bot.slash_command(name="compliment", description="Получить комплимент для игрока Маджестик")
async def compliment(ctx: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
    target = member if member else ctx.author
    compliment_text = random.choice(compliments)
    
    embed = disnake.Embed(
        title="💝 КОМПЛИМЕНТ ДНЯ! 💝",
        description=f"{target.mention}, {compliment_text}",
        color=disnake.Color.gold()
    )
    embed.set_footer(text=f"✨ Сказано с любовью от {ctx.author.display_name}")
    await ctx.response.send_message(embed=embed)

@bot.slash_command(name="majestic", description="Предсказание судьбы в Маджестик")
async def majestic(ctx: disnake.ApplicationCommandInteraction):
    prediction = random.choice(predictions)
    
    embed = disnake.Embed(
        title="🔮 ВЕЛИКИЙ ОРАКУЛ МАДЖЕСТИК 🔮",
        description=prediction,
        color=disnake.Color.purple()
    )
    embed.add_field(name="🌟 Совет дня:", value="Доверяй своим инстинктам и не бойся рисковать!", inline=False)
    embed.set_footer(text=f"Для {ctx.author.display_name} | Сила Маджестик внутри тебя!")
    await ctx.response.send_message(embed=embed)

@bot.slash_command(name="botinfo", description="Информация о создателе бота")
async def botinfo(ctx: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="🤖 О БОТЕ NEXUS 🤖",
        description="Вся информация о нашем музыкальном помощнике",
        color=disnake.Color.blue()
    )
    embed.add_field(name="👨‍💻 **Создатель бота:**", value="**Vladosis Nexus** — разработал этого бота с нуля для комфорта нашей фамы", inline=False)
    embed.add_field(name="🎯 **Для чего этот бот?**", value="Бот создан для комфортного времяпрепровождения участников фамы Nexus на сервере Miami 8.", inline=False)
    embed.add_field(name="📅 **Дата создания бота:**", value="16 апреля 2026 года", inline=True)
    embed.add_field(name="⚙️ **Версия:**", value="1.0.0 (Stable)", inline=True)
    embed.add_field(name="🛠️ **Технологии:**", value="Python + Disnake + YouTube API", inline=False)
    embed.add_field(name="📢 **По вопросам информации и обновлений:**", value="**@mod1kus777**", inline=False)
    embed.set_footer(text="Nexus Music Bot | Сделано с душой для своей фамы")
    await ctx.response.send_message(embed=embed)

@bot.slash_command(name="promo", description="Получить промокод для Majestic RolePlay")
async def promo(ctx: disnake.ApplicationCommandInteraction):
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
    await ctx.response.send_message(embed=embed)

@bot.slash_command(name="toptulers", description="Топ тулеров фамы Nexus")
async def toptulers(ctx: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="🏆 ТОП ТУЛЕРОВ ФАМЫ NEXUS 🏆",
        description="Наши крутые бойцы, которые знают, как делать деньги!",
        color=disnake.Color.gold()
    )
    
    for medal, data in top_tulers.items():
        embed.add_field(
            name=f"{medal} {data['name']} {medal}",
            value=f"{data['description']}\n━━━━━━━━━━━━━━━━━",
            inline=False
        )
    
    embed.set_footer(text="Хочешь попасть в топ? Тулись как герой и мы тебя научим! | Nexus")
    await ctx.response.send_message(embed=embed)

@bot.slash_command(name="command", description="Показать все команды бота")
async def commands_list(ctx: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="🎵 NEXUS MUSIC BOT 🎵",
        description="Полный список команд для управления ботом:",
        color=disnake.Color.purple()
    )
    embed.add_field(name="🎶 МУЗЫКАЛЬНЫЕ КОМАНДЫ", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/play [название или ссылка]", value="▶️ Включить трек из YouTube", inline=False)
    embed.add_field(name="/stop", value="⏸️ Остановить трек", inline=True)
    embed.add_field(name="/resume", value="▶️ Возобновить трек", inline=True)
    embed.add_field(name="/skip", value="⏭️ Пропустить трек", inline=True)
    embed.add_field(name="/volume [0-300]", value="🔊 Громкость", inline=True)
    embed.add_field(name="/clear", value="🗑️ Очистить очередь", inline=True)
    embed.add_field(name="/leave", value="👋 Выйти из канала", inline=True)
    
    embed.add_field(name="\n✨ ИНТЕРАКТИВНЫЕ КОМАНДЫ", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/nexus", value="📜 История фамы Nexus", inline=True)
    embed.add_field(name="/compliment [@участник]", value="💝 Отправить комплимент", inline=True)
    embed.add_field(name="/majestic", value="🔮 Предсказание для Маджестик", inline=True)
    embed.add_field(name="/botinfo", value="🤖 Информация о боте", inline=True)
    embed.add_field(name="/promo", value="🎁 Промокод Majestic RP", inline=True)
    embed.add_field(name="/toptulers", value="🏆 Топ тулеров Nexus", inline=True)
    embed.add_field(name="/command", value="📋 Показать это меню", inline=True)
    
    embed.set_footer(text="Создано Vladosis Nexus | Маджестик | Miami 8")
    await ctx.response.send_message(embed=embed)

# Запуск бота
bot.run(os.getenv('DISCORD_TOKEN'))