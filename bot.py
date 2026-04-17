import disnake
from disnake.ext import commands
import yt_dlp as youtube_dl
import asyncio
import random
import os

# Настройки бота
intents = disnake.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

# НАСТРОЙКИ YT-DLP ДЛЯ SOUNDCLOUD (РАБОТАЕТ БЕЗ КУК)
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'no_color': True,
    'geo_bypass': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# Глобальные переменные
queues = {}
current_volume = 50
voice_clients = {}

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

def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]

async def play_next(guild_id):
    queue = get_queue(guild_id)
    
    if queue:
        queue.pop(0)
        if queue:
            next_song = queue[0]
            await play_song(guild_id, next_song['url'], next_song['is_youtube'])
        else:
            if guild_id in voice_clients:
                await voice_clients[guild_id].disconnect()
                del voice_clients[guild_id]
                if guild_id in queues:
                    del queues[guild_id]

async def play_song(guild_id, url, is_youtube=False):
    if guild_id not in voice_clients:
        return
    
    voice_client = voice_clients[guild_id]
    
    try:
        voice_client.stop()
        
        loop = asyncio.get_event_loop()
        
        def get_audio_url():
            # Для YouTube пробуем использовать yt-dlp с разными настройками
            local_opts = ydl_opts.copy()
            
            if is_youtube:
                # Для YouTube добавляем дополнительные заголовки
                local_opts['http_headers'] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                }
                # Пробуем использовать мобильный user-agent
                local_opts['headers'] = local_opts['http_headers']
            
            try:
                with youtube_dl.YoutubeDL(local_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    if 'entries' in info:
                        # Это плейлист или поиск
                        for entry in info['entries']:
                            if entry:
                                # Ищем аудио формат
                                formats = entry.get('formats', [])
                                for fmt in formats:
                                    if fmt.get('acodec') != 'none':
                                        return fmt['url']
                                if formats:
                                    return formats[-1]['url']
                    else:
                        formats = info.get('formats', [])
                        for fmt in formats:
                            if fmt.get('acodec') != 'none':
                                return fmt['url']
                        if formats:
                            return formats[-1]['url']
            except Exception as e:
                print(f"Ошибка извлечения: {e}")
                return None
        
        audio_url = await loop.run_in_executor(None, get_audio_url)
        
        if not audio_url:
            print("Не удалось получить аудио URL, пропускаем трек")
            await play_next(guild_id)
            return
        
        source = await disnake.FFmpegOpusAudio.from_probe(audio_url, **FFMPEG_OPTIONS)
        source = disnake.PCMVolumeTransformer(source, volume=current_volume/100)
        
        def after_play(error):
            if error:
                print(f"Ошибка воспроизведения: {error}")
            asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop)
        
        voice_client.play(source, after=after_play)
        
    except Exception as e:
        print(f"Общая ошибка: {e}")
        await play_next(guild_id)

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен и готов к работе!')
    await bot.change_presence(activity=disnake.Game(name="/command | Маджестик"))

# ==================== МУЗЫКАЛЬНЫЕ КОМАНДЫ ====================

@bot.slash_command(name="play", description="Включить трек (SoundCloud или YouTube)")
async def play(inter: disnake.ApplicationCommandInteraction, search: str):
    """Включает музыку с SoundCloud или YouTube"""
    await inter.response.defer()
    
    if not inter.author.voice:
        await inter.edit_original_response(content="❌ Вы не в голосовом канале!")
        return
    
    voice_channel = inter.author.voice.channel
    guild_id = inter.guild.id
    
    # Подключаемся к каналу
    if guild_id not in voice_clients:
        voice_clients[guild_id] = await voice_channel.connect()
    elif not voice_clients[guild_id].is_connected():
        voice_clients[guild_id] = await voice_channel.connect()
    
    try:
        loop = asyncio.get_event_loop()
        
        def search_music():
            is_youtube = False
            
            # Определяем тип ссылки
            if 'youtube.com' in search or 'youtu.be' in search:
                is_youtube = True
                search_query = search
            elif 'soundcloud.com' in search:
                is_youtube = False
                search_query = search
            else:
                # По умолчанию ищем на SoundCloud (работает без кук)
                is_youtube = False
                search_query = f"scsearch:{search}"
            
            try:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(search_query, download=False)
                    
                    if 'entries' in info and info['entries']:
                        entry = info['entries'][0]
                        url = entry.get('webpage_url') or entry.get('url')
                        title = entry.get('title', 'Неизвестный трек')
                        return url, title, is_youtube
                    else:
                        url = info.get('webpage_url') or info.get('url')
                        title = info.get('title', 'Неизвестный трек')
                        return url, title, is_youtube
            except Exception as e:
                print(f"Ошибка поиска: {e}")
                return None, None, False
        
        url, title, is_youtube = await loop.run_in_executor(None, search_music)
        
        if not url:
            await inter.edit_original_response(content="❌ Не удалось найти трек. Попробуйте другой запрос.")
            return
        
        queue = get_queue(guild_id)
        queue.append({'url': url, 'title': title, 'is_youtube': is_youtube})
        
        voice_client = voice_clients.get(guild_id)
        
        source_emoji = "🎵" if not is_youtube else "▶️"
        
        if voice_client and voice_client.is_playing():
            await inter.edit_original_response(content=f"✅ Добавлено в очередь: **{title}**")
        else:
            await inter.edit_original_response(content=f"{source_emoji} Сейчас играет: **{title}**")
            await play_song(guild_id, url, is_youtube)
            
    except Exception as e:
        await inter.edit_original_response(content=f"❌ Произошла ошибка: {str(e)}")

@bot.slash_command(name="play_sc", description="Включить трек с SoundCloud (рекомендуется)")
async def play_sc(inter: disnake.ApplicationCommandInteraction, search: str):
    """Включает музыку с SoundCloud (работает 100%)"""
    await inter.response.defer()
    
    if not inter.author.voice:
        await inter.edit_original_response(content="❌ Вы не в голосовом канале!")
        return
    
    voice_channel = inter.author.voice.channel
    guild_id = inter.guild.id
    
    if guild_id not in voice_clients:
        voice_clients[guild_id] = await voice_channel.connect()
    elif not voice_clients[guild_id].is_connected():
        voice_clients[guild_id] = await voice_channel.connect()
    
    try:
        loop = asyncio.get_event_loop()
        
        def search_soundcloud():
            if 'soundcloud.com' in search:
                search_query = search
            else:
                search_query = f"scsearch:{search}"
            
            try:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(search_query, download=False)
                    
                    if 'entries' in info and info['entries']:
                        entry = info['entries'][0]
                        url = entry.get('webpage_url') or entry.get('url')
                        title = entry.get('title', 'Неизвестный трек')
                        return url, title
                    else:
                        url = info.get('webpage_url') or info.get('url')
                        title = info.get('title', 'Неизвестный трек')
                        return url, title
            except Exception as e:
                print(f"Ошибка поиска: {e}")
                return None, None
        
        url, title = await loop.run_in_executor(None, search_soundcloud)
        
        if not url:
            await inter.edit_original_response(content="❌ Не удалось найти трек на SoundCloud.")
            return
        
        queue = get_queue(guild_id)
        queue.append({'url': url, 'title': title, 'is_youtube': False})
        
        voice_client = voice_clients.get(guild_id)
        
        if voice_client and voice_client.is_playing():
            await inter.edit_original_response(content=f"✅ Добавлено в очередь: **{title}**")
        else:
            await inter.edit_original_response(content=f"🎵 Сейчас играет: **{title}**")
            await play_song(guild_id, url, False)
            
    except Exception as e:
        await inter.edit_original_response(content=f"❌ Произошла ошибка: {str(e)}")

@bot.slash_command(name="stop", description="Остановить текущий трек")
async def stop(inter: disnake.ApplicationCommandInteraction):
    guild_id = inter.guild.id
    
    if guild_id in voice_clients and voice_clients[guild_id].is_playing():
        voice_clients[guild_id].pause()
        await inter.response.send_message("⏸️ Трек остановлен. Используйте `/resume` чтобы продолжить.")
    else:
        await inter.response.send_message("❌ Ничего не играет!")

@bot.slash_command(name="resume", description="Возобновить остановленный трек")
async def resume(inter: disnake.ApplicationCommandInteraction):
    guild_id = inter.guild.id
    
    if guild_id in voice_clients and voice_clients[guild_id].is_paused():
        voice_clients[guild_id].resume()
        await inter.response.send_message("▶️ Трек возобновлён!")
    else:
        await inter.response.send_message("❌ Нет остановленного трека!")

@bot.slash_command(name="volume", description="Изменить громкость (0-300%)")
async def volume(inter: disnake.ApplicationCommandInteraction, level: int):
    global current_volume
    guild_id = inter.guild.id
    
    if level < 0 or level > 300:
        await inter.response.send_message("❌ Громкость должна быть от 0 до 300!")
        return
    
    current_volume = level
    
    if guild_id in voice_clients and voice_clients[guild_id].source:
        voice_clients[guild_id].source.volume = level / 100
    
    await inter.response.send_message(f"🔊 Громкость установлена на {level}%")

@bot.slash_command(name="clear", description="Очистить очередь треков")
async def clear(inter: disnake.ApplicationCommandInteraction):
    guild_id = inter.guild.id
    queue = get_queue(guild_id)
    queue.clear()
    
    if guild_id in voice_clients and voice_clients[guild_id].is_playing():
        voice_clients[guild_id].stop()
    
    await inter.response.send_message("🗑️ Очередь полностью очищена!")

@bot.slash_command(name="skip", description="Пропустить текущий трек")
async def skip(inter: disnake.ApplicationCommandInteraction):
    guild_id = inter.guild.id
    
    if guild_id in voice_clients and voice_clients[guild_id].is_playing():
        voice_clients[guild_id].stop()
        await inter.response.send_message("⏭️ Трек пропущен!")
    else:
        await inter.response.send_message("❌ Ничего не играет!")

@bot.slash_command(name="leave", description="Выйти из голосового канала")
async def leave(inter: disnake.ApplicationCommandInteraction):
    guild_id = inter.guild.id
    
    if guild_id in queues:
        queues[guild_id] = []
    
    if guild_id in voice_clients:
        await voice_clients[guild_id].disconnect()
        del voice_clients[guild_id]
        await inter.response.send_message("👋 Бот вышел из канала, очередь очищена!")
    else:
        await inter.response.send_message("❌ Бот не в голосовом канале!")

@bot.slash_command(name="queue", description="Показать текущую очередь треков")
async def show_queue(inter: disnake.ApplicationCommandInteraction):
    guild_id = inter.guild.id
    queue = get_queue(guild_id)
    
    if not queue:
        await inter.response.send_message("📋 Очередь пуста!")
        return
    
    queue_text = "**📋 ТЕКУЩАЯ ОЧЕРЕДЬ:**\n\n"
    for i, song in enumerate(queue[:10], 1):
        queue_text += f"{i}. **{song['title']}**\n"
    
    if len(queue) > 10:
        queue_text += f"\n... и ещё {len(queue) - 10} треков"
    
    await inter.response.send_message(queue_text)

# ==================== КОМАНДЫ ФАМЫ ====================

@bot.slash_command(name="nexus", description="История создания фамы Nexus")
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
    await inter.response.send_message(embed=embed)

@bot.slash_command(name="compliment", description="Получить комплимент для игрока Маджестик")
async def compliment(inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
    target = member if member else inter.author
    compliment_text = random.choice(compliments)
    
    embed = disnake.Embed(
        title="💝 КОМПЛИМЕНТ ДНЯ! 💝",
        description=f"{target.mention}, {compliment_text}",
        color=disnake.Color.gold()
    )
    embed.set_footer(text=f"✨ Сказано с любовью от {inter.author.display_name}")
    await inter.response.send_message(embed=embed)

@bot.slash_command(name="majestic", description="Предсказание судьбы в Маджестик")
async def majestic(inter: disnake.ApplicationCommandInteraction):
    prediction = random.choice(predictions)
    
    embed = disnake.Embed(
        title="🔮 ВЕЛИКИЙ ОРАКУЛ МАДЖЕСТИК 🔮",
        description=prediction,
        color=disnake.Color.purple()
    )
    embed.add_field(name="🌟 Совет дня:", value="Доверяй своим инстинктам и не бойся рисковать!", inline=False)
    embed.set_footer(text=f"Для {inter.author.display_name} | Сила Маджестик внутри тебя!")
    await inter.response.send_message(embed=embed)

@bot.slash_command(name="botinfo", description="Информация о создателе бота")
async def botinfo(inter: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="🤖 О БОТЕ NEXUS 🤖",
        description="Вся информация о нашем музыкальном помощнике",
        color=disnake.Color.blue()
    )
    embed.add_field(name="👨‍💻 **Создатель бота:**", value="**Vladosis Nexus** — разработал этого бота с нуля для комфорта нашей фамы", inline=False)
    embed.add_field(name="🎯 **Для чего этот бот?**", value="Бот создан для комфортного времяпрепровождения участников фамы Nexus на сервере Miami 8.", inline=False)
    embed.add_field(name="📅 **Дата создания бота:**", value="16 апреля 2026 года", inline=True)
    embed.add_field(name="⚙️ **Версия:**", value="1.0.0 (Stable)", inline=True)
    embed.add_field(name="🛠️ **Технологии:**", value="Python + Disnake + yt-dlp", inline=False)
    embed.add_field(name="🎵 **Источники музыки:**", value="SoundCloud (основной) + YouTube", inline=False)
    embed.add_field(name="📢 **По вопросам информации и обновлений:**", value="**@mod1kus777**", inline=False)
    embed.set_footer(text="Nexus Music Bot | Сделано с душой для своей фамы")
    await inter.response.send_message(embed=embed)

@bot.slash_command(name="promo", description="Получить промокод для Majestic RolePlay")
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
    await inter.response.send_message(embed=embed)

@bot.slash_command(name="toptulers", description="Топ тулеров фамы Nexus")
async def toptulers(inter: disnake.ApplicationCommandInteraction):
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
    await inter.response.send_message(embed=embed)

@bot.slash_command(name="command", description="Показать все команды бота")
async def commands_list(inter: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="🎵 NEXUS MUSIC BOT 🎵",
        description="Полный список команд для управления ботом:",
        color=disnake.Color.purple()
    )
    embed.add_field(name="🎶 МУЗЫКАЛЬНЫЕ КОМАНДЫ", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/play [название/ссылка]", value="▶️ Включить трек (SoundCloud/YouTube)", inline=False)
    embed.add_field(name="/play_sc [название]", value="🎵 Включить с SoundCloud (100% работает)", inline=False)
    embed.add_field(name="/queue", value="📋 Показать очередь треков", inline=False)
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
    await inter.response.send_message(embed=embed)

# Запуск бота
bot.run(os.getenv('DISCORD_TOKEN'))