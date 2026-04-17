import disnake
from disnake.ext import commands
import yt_dlp as youtube_dl
import asyncio
import random
import os
import aiohttp
import json
import re

# Настройки бота
intents = disnake.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

# ==================== НАСТРОЙКИ ДЛЯ SOUNDCLOUD ====================
SOUNDCLOUD_CLIENT_ID = "a3eRgIiQkK4RkYg7HGYK0zE2h0wbqKqA"

SC_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'no_color': True,
    'geo_bypass': True,
    'socket_timeout': 30,
    'retries': 3,
    'fragment_retries': 3,
    'extractor_args': {
        'soundcloud': {
            'client_id': SOUNDCLOUD_CLIENT_ID
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://soundcloud.com',
        'Referer': 'https://soundcloud.com/',
    }
}

# ==================== НАСТРОЙКИ ДЛЯ VK ====================
VK_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'no_color': True,
    'socket_timeout': 30,
    'retries': 3,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
queues = {}
current_volume = 50
voice_clients = {}
current_track = {}

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

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]

async def search_vk_track(query):
    """Поиск трека в VK через yt-dlp"""
    try:
        loop = asyncio.get_event_loop()
        
        def _search():
            with youtube_dl.YoutubeDL(VK_OPTS) as ydl:
                if 'vk.com' in query:
                    info = ydl.extract_info(query, download=False)
                else:
                    info = ydl.extract_info(f"vksearch:{query}", download=False)
                
                if info and 'entries' in info and info['entries']:
                    entry = info['entries'][0]
                    return {
                        'url': entry.get('webpage_url') or entry.get('url'),
                        'title': entry.get('title', 'Неизвестный трек'),
                        'duration': entry.get('duration', 0),
                        'uploader': entry.get('uploader', 'VK')
                    }
                elif info:
                    return {
                        'url': info.get('webpage_url') or info.get('url'),
                        'title': info.get('title', 'Неизвестный трек'),
                        'duration': info.get('duration', 0),
                        'uploader': info.get('uploader', 'VK')
                    }
                return None
                
        return await loop.run_in_executor(None, _search)
    except Exception as e:
        print(f"VK search error: {e}")
        return None

async def search_sc_track(query):
    """Поиск трека в SoundCloud через yt-dlp"""
    try:
        loop = asyncio.get_event_loop()
        
        def _search():
            with youtube_dl.YoutubeDL(SC_OPTS) as ydl:
                if 'soundcloud.com' in query:
                    info = ydl.extract_info(query, download=False)
                else:
                    info = ydl.extract_info(f"scsearch5:{query}", download=False)
                
                if info and 'entries' in info and info['entries']:
                    # Ищем первый рабочий трек
                    for entry in info['entries']:
                        if entry:
                            return {
                                'url': entry.get('webpage_url') or entry.get('url'),
                                'title': entry.get('title', 'Неизвестный трек'),
                                'duration': entry.get('duration', 0),
                                'uploader': entry.get('uploader', 'SoundCloud')
                            }
                elif info:
                    return {
                        'url': info.get('webpage_url') or info.get('url'),
                        'title': info.get('title', 'Неизвестный трек'),
                        'duration': info.get('duration', 0),
                        'uploader': info.get('uploader', 'SoundCloud')
                    }
                return None
                
        return await loop.run_in_executor(None, _search)
    except Exception as e:
        print(f"SoundCloud search error: {e}")
        return None

async def extract_audio_url(track_url, source='sc'):
    """Извлекает прямой URL аудио из трека"""
    try:
        loop = asyncio.get_event_loop()
        opts = SC_OPTS if source == 'sc' else VK_OPTS
        
        def _extract():
            with youtube_dl.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(track_url, download=False)
                if info:
                    # Проверяем formats
                    if 'formats' in info:
                        for fmt in info['formats']:
                            if fmt.get('acodec') != 'none' and 'url' in fmt:
                                return fmt['url']
                    
                    # Проверяем прямой url
                    if 'url' in info:
                        return info['url']
                    
                    # Проверяем entries
                    if 'entries' in info and info['entries']:
                        entry = info['entries'][0]
                        if 'formats' in entry:
                            for fmt in entry['formats']:
                                if fmt.get('acodec') != 'none' and 'url' in fmt:
                                    return fmt['url']
                        if 'url' in entry:
                            return entry['url']
                return None
                
        return await loop.run_in_executor(None, _extract)
    except Exception as e:
        print(f"Audio extraction error: {e}")
        return None

async def play_next(guild_id):
    """Проигрывает следующий трек в очереди"""
    queue = get_queue(guild_id)
    
    if queue:
        queue.pop(0)
        if queue:
            next_song = queue[0]
            current_track[guild_id] = next_song
            await play_song(guild_id, next_song['url'], next_song['source'])
        else:
            if guild_id in voice_clients:
                await voice_clients[guild_id].disconnect()
                del voice_clients[guild_id]
                if guild_id in queues:
                    del queues[guild_id]
                if guild_id in current_track:
                    del current_track[guild_id]

async def play_song(guild_id, track_url, source):
    """Проигрывает трек"""
    if guild_id not in voice_clients:
        return
    
    voice_client = voice_clients[guild_id]
    
    try:
        voice_client.stop()
        
        # Извлекаем аудио URL
        audio_url = await extract_audio_url(track_url, source)
        
        if not audio_url:
            print(f"Failed to extract audio URL for {track_url}")
            await play_next(guild_id)
            return
        
        print(f"Playing audio from: {audio_url[:100]}...")
        
        # Создаем источник
        try:
            source_audio = await disnake.FFmpegOpusAudio.from_probe(audio_url, **FFMPEG_OPTIONS)
        except:
            source_audio = disnake.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        
        source_audio = disnake.PCMVolumeTransformer(source_audio, volume=current_volume/100)
        
        def after_play(error):
            if error:
                print(f"Playback error: {error}")
            asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop)
        
        voice_client.play(source_audio, after=after_play)
        
    except Exception as e:
        print(f"Play song error: {e}")
        await play_next(guild_id)

# ==================== СОБЫТИЯ БОТА ====================
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен и готов к работе!')
    await bot.change_presence(activity=disnake.Game(name="/command | Маджестик"))

# ==================== МУЗЫКАЛЬНЫЕ КОМАНДЫ ====================

@bot.slash_command(name="play", description="🎵 Включить трек с SoundCloud (поиск или ссылка)")
async def play(inter: disnake.ApplicationCommandInteraction, запрос: str):
    """Включает музыку с SoundCloud"""
    await inter.response.defer()
    
    if not inter.author.voice:
        await inter.edit_original_response(content="❌ Вы не в голосовом канале!")
        return
    
    voice_channel = inter.author.voice.channel
    guild_id = inter.guild.id
    
    # Подключаемся к каналу
    try:
        if guild_id not in voice_clients:
            voice_clients[guild_id] = await voice_channel.connect()
        elif not voice_clients[guild_id].is_connected():
            voice_clients[guild_id] = await voice_channel.connect()
    except Exception as e:
        await inter.edit_original_response(content=f"❌ Не удалось подключиться: {str(e)}")
        return
    
    # Ищем трек
    track_info = await search_sc_track(запрос)
    
    if not track_info:
        await inter.edit_original_response(content="❌ Трек не найден на SoundCloud")
        return
    
    # Добавляем в очередь
    queue = get_queue(guild_id)
    track_info['source'] = 'sc'
    queue.append(track_info)
    
    voice_client = voice_clients.get(guild_id)
    
    if voice_client and voice_client.is_playing():
        await inter.edit_original_response(content=f"✅ Добавлено в очередь: **{track_info['title']}**")
    else:
        current_track[guild_id] = track_info
        await inter.edit_original_response(content=f"🎵 Сейчас играет: **{track_info['title']}**")
        await play_song(guild_id, track_info['url'], 'sc')


@bot.slash_command(name="vk", description="🎵 Включить трек из VK Музыки (поиск или ссылка)")
async def vk(inter: disnake.ApplicationCommandInteraction, запрос: str):
    """Включает музыку из VK"""
    await inter.response.defer()
    
    if not inter.author.voice:
        await inter.edit_original_response(content="❌ Вы не в голосовом канале!")
        return
    
    voice_channel = inter.author.voice.channel
    guild_id = inter.guild.id
    
    # Подключаемся к каналу
    try:
        if guild_id not in voice_clients:
            voice_clients[guild_id] = await voice_channel.connect()
        elif not voice_clients[guild_id].is_connected():
            voice_clients[guild_id] = await voice_channel.connect()
    except Exception as e:
        await inter.edit_original_response(content=f"❌ Не удалось подключиться: {str(e)}")
        return
    
    # Ищем трек
    track_info = await search_vk_track(запрос)
    
    if not track_info:
        await inter.edit_original_response(content="❌ Трек не найден в VK")
        return
    
    # Добавляем в очередь
    queue = get_queue(guild_id)
    track_info['source'] = 'vk'
    queue.append(track_info)
    
    voice_client = voice_clients.get(guild_id)
    
    if voice_client and voice_client.is_playing():
        await inter.edit_original_response(content=f"✅ Добавлено в очередь: **{track_info['title']}**")
    else:
        current_track[guild_id] = track_info
        await inter.edit_original_response(content=f"🎵 Сейчас играет: **{track_info['title']}**")
        await play_song(guild_id, track_info['url'], 'vk')


@bot.slash_command(name="stop", description="⏸️ Остановить текущий трек")
async def stop(inter: disnake.ApplicationCommandInteraction):
    guild_id = inter.guild.id
    
    if guild_id in voice_clients and voice_clients[guild_id].is_playing():
        voice_clients[guild_id].pause()
        await inter.response.send_message("⏸️ Трек остановлен. Используйте `/resume` чтобы продолжить.")
    else:
        await inter.response.send_message("❌ Ничего не играет!")


@bot.slash_command(name="resume", description="▶️ Возобновить остановленный трек")
async def resume(inter: disnake.ApplicationCommandInteraction):
    guild_id = inter.guild.id
    
    if guild_id in voice_clients and voice_clients[guild_id].is_paused():
        voice_clients[guild_id].resume()
        await inter.response.send_message("▶️ Трек возобновлён!")
    else:
        await inter.response.send_message("❌ Нет остановленного трека!")


@bot.slash_command(name="volume", description="🔊 Изменить громкость (0-300%)")
async def volume(inter: disnake.ApplicationCommandInteraction, уровень: int):
    global current_volume
    guild_id = inter.guild.id
    
    if уровень < 0 or уровень > 300:
        await inter.response.send_message("❌ Громкость должна быть от 0 до 300!")
        return
    
    current_volume = уровень
    
    if guild_id in voice_clients and voice_clients[guild_id].source:
        voice_clients[guild_id].source.volume = уровень / 100
    
    await inter.response.send_message(f"🔊 Громкость установлена на {уровень}%")


@bot.slash_command(name="skip", description="⏭️ Пропустить текущий трек")
async def skip(inter: disnake.ApplicationCommandInteraction):
    guild_id = inter.guild.id
    
    if guild_id in voice_clients and voice_clients[guild_id].is_playing():
        voice_clients[guild_id].stop()
        await inter.response.send_message("⏭️ Трек пропущен!")
    else:
        await inter.response.send_message("❌ Ничего не играет!")


@bot.slash_command(name="clear", description="🗑️ Очистить очередь треков")
async def clear(inter: disnake.ApplicationCommandInteraction):
    guild_id = inter.guild.id
    queue = get_queue(guild_id)
    queue.clear()
    
    if guild_id in voice_clients and voice_clients[guild_id].is_playing():
        voice_clients[guild_id].stop()
    
    await inter.response.send_message("🗑️ Очередь полностью очищена!")


@bot.slash_command(name="leave", description="👋 Выйти из голосового канала")
async def leave(inter: disnake.ApplicationCommandInteraction):
    guild_id = inter.guild.id
    
    if guild_id in queues:
        queues[guild_id] = []
    
    if guild_id in voice_clients:
        await voice_clients[guild_id].disconnect()
        del voice_clients[guild_id]
        if guild_id in current_track:
            del current_track[guild_id]
        await inter.response.send_message("👋 Бот вышел из канала, очередь очищена!")
    else:
        await inter.response.send_message("❌ Бот не в голосовом канале!")


@bot.slash_command(name="queue", description="📋 Показать текущую очередь треков")
async def show_queue(inter: disnake.ApplicationCommandInteraction):
    guild_id = inter.guild.id
    queue = get_queue(guild_id)
    
    if not queue:
        await inter.response.send_message("📋 Очередь пуста!")
        return
    
    queue_text = "**📋 ТЕКУЩАЯ ОЧЕРЕДЬ:**\n\n"
    
    # Показываем текущий трек
    if guild_id in current_track:
        track = current_track[guild_id]
        source_icon = "🎵" if track['source'] == 'sc' else "🎶"
        queue_text += f"**Сейчас играет:** {source_icon} {track['title']}\n\n"
    
    # Показываем очередь
    if len(queue) > 0:
        queue_text += "**В очереди:**\n"
        for i, song in enumerate(queue[:10], 1):
            source_icon = "🎵" if song['source'] == 'sc' else "🎶"
            queue_text += f"{i}. {source_icon} **{song['title']}**\n"
        
        if len(queue) > 10:
            queue_text += f"\n... и ещё {len(queue) - 10} треков"
    
    await inter.response.send_message(queue_text)


@bot.slash_command(name="now", description="🎵 Показать что сейчас играет")
async def now_playing(inter: disnake.ApplicationCommandInteraction):
    guild_id = inter.guild.id
    
    if guild_id in current_track and guild_id in voice_clients and voice_clients[guild_id].is_playing():
        track = current_track[guild_id]
        source_name = "SoundCloud" if track['source'] == 'sc' else "VK Музыка"
        source_icon = "🎵" if track['source'] == 'sc' else "🎶"
        
        embed = disnake.Embed(
            title=f"{source_icon} СЕЙЧАС ИГРАЕТ",
            description=f"**{track['title']}**",
            color=disnake.Color.green()
        )
        embed.add_field(name="Источник", value=source_name, inline=True)
        if track.get('uploader'):
            embed.add_field(name="Исполнитель", value=track['uploader'], inline=True)
        embed.set_footer(text=f"Громкость: {current_volume}%")
        
        await inter.response.send_message(embed=embed)
    else:
        await inter.response.send_message("❌ Сейчас ничего не играет!")

# ==================== КОМАНДЫ ФАМЫ (БЕЗ ИЗМЕНЕНИЙ) ====================

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
    embed.add_field(name="⚙️ **Версия:**", value="2.0.0 (Multi-Source)", inline=True)
    embed.add_field(name="🛠️ **Технологии:**", value="Python + Disnake + yt-dlp", inline=False)
    embed.add_field(name="🎵 **Источники музыки:**", value="SoundCloud + VK Музыка", inline=False)
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
        title="🎵 NEXUS MUSIC BOT v2.0 🎵",
        description="Полный список команд для управления ботом:",
        color=disnake.Color.purple()
    )
    
    embed.add_field(name="🎶 МУЗЫКА SOUNDCLOUD", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/play [название/ссылка]", value="🎵 Включить трек с SoundCloud", inline=False)
    
    embed.add_field(name="\n🎶 МУЗЫКА VK", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/vk [название/ссылка]", value="🎶 Включить трек из VK Музыки", inline=False)
    
    embed.add_field(name="\n📋 УПРАВЛЕНИЕ", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/queue", value="📋 Показать очередь треков", inline=True)
    embed.add_field(name="/now", value="🎵 Что сейчас играет", inline=True)
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


# ==================== ЗАПУСК БОТА ====================
bot.run(os.getenv('DISCORD_TOKEN'))