import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import random
import os

# Настройки бота (включаем все интенты)
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

# Настройки для YouTube
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
    }],
    'quiet': True,
    'no_warnings': True,
    'cookiefile': 'cookies.txt',  # ← ДОБАВИТЬ ЭТУ СТРОКУ
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
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
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
        
        source = await discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(source, volume=current_volume/100)
        
        voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), bot.loop))

# Событие готовности
@bot.event
async def on_ready():
    await bot.sync_commands()  # Синхронизация слэш-команд для py-cord
    print(f'✅ Бот {bot.user} запущен и готов к работе!')
    await bot.change_presence(activity=discord.Game(name="/command | Маджестик"))

# ==================== МУЗЫКАЛЬНЫЕ КОМАНДЫ ====================

@bot.slash_command(name="play", description="Включить трек из YouTube")
async def play(ctx: discord.ApplicationContext, search: str):
    """Включает музыку из YouTube"""
    await ctx.defer()
    
    if not ctx.author.voice:
        await ctx.respond("❌ Вы не в голосовом канале!")
        return
    
    voice_channel = ctx.author.voice.channel
    
    if not ctx.guild.voice_client:
        await voice_channel.connect()
    
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)
            url = info['entries'][0]['webpage_url']
            title = info['entries'][0]['title']
        except Exception as e:
            await ctx.respond(f"❌ Не удалось найти трек: {str(e)}")
            return
    
    queue.append({'url': url, 'title': title})
    await ctx.respond(f"✅ Добавлено в очередь: **{title}**")
    
    if not ctx.guild.voice_client.is_playing():
        player = MusicPlayer(ctx)
        await player.play_song(url)

@bot.slash_command(name="stop", description="Остановить текущий трек")
async def stop(ctx: discord.ApplicationContext):
    if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
        ctx.guild.voice_client.pause()
        await ctx.respond("⏸️ Трек остановлен. Используйте `/resume` чтобы продолжить.")
    else:
        await ctx.respond("❌ Ничего не играет!")

@bot.slash_command(name="resume", description="Возобновить остановленный трек")
async def resume(ctx: discord.ApplicationContext):
    if ctx.guild.voice_client and ctx.guild.voice_client.is_paused():
        ctx.guild.voice_client.resume()
        await ctx.respond("▶️ Трек возобновлён!")
    else:
        await ctx.respond("❌ Нет остановленного трека!")

@bot.slash_command(name="volume", description="Изменить громкость (0-300%)")
async def volume(ctx: discord.ApplicationContext, level: int):
    global current_volume
    if level < 0 or level > 300:
        await ctx.respond("❌ Громкость должна быть от 0 до 300!")
        return
    current_volume = level
    if ctx.guild.voice_client and ctx.guild.voice_client.source:
        ctx.guild.voice_client.source.volume = level / 100
    await ctx.respond(f"🔊 Громкость установлена на {level}%")

@bot.slash_command(name="clear", description="Очистить очередь треков")
async def clear(ctx: discord.ApplicationContext):
    global queue
    queue = []
    if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
        ctx.guild.voice_client.stop()
    await ctx.respond("🗑️ Очередь полностью очищена!")

@bot.slash_command(name="skip", description="Пропустить текущий трек")
async def skip(ctx: discord.ApplicationContext):
    if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
        ctx.guild.voice_client.stop()
        await ctx.respond("⏭️ Трек пропущен!")
    else:
        await ctx.respond("❌ Ничего не играет!")

@bot.slash_command(name="leave", description="Выйти из голосового канала")
async def leave(ctx: discord.ApplicationContext):
    global queue
    queue = []
    if ctx.guild.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.respond("👋 Бот вышел из канала, очередь очищена!")
    else:
        await ctx.respond("❌ Бот не в голосовом канале!")

# ==================== КОМАНДЫ ФАМЫ ====================

@bot.slash_command(name="nexus", description="История создания фамы Nexus")
async def nexus(ctx: discord.ApplicationContext):
    story = """
╔══════════════════════════════════════════════════════════╗
║                    📜 ИСТОРИЯ NEXUS 📜                    ║
╚══════════════════════════════════════════════════════════╝

**🌅 КАК ВСЁ НАЧИНАЛОСЬ...**

Всё началось на сервере **Miami 8**. Мы были частью фамы **Pacman (Mans)**, но со временем лидер той фамы показал своё истинное лицо.

Он позволял себе **грязные выходки**, неуважение к участникам, воровал общий заработок и вёл себя как **настоящий тиран**. Люди уходили один за другим, потому что терпеть такое было невозможно.

**⚔️ РОЖДЕНИЕ ЛЕГЕНДЫ**

Тогда **Sanek** — один из ключевых игроков, уставший от беспредела, собрал самых верных и адекватных бойцов и сказал:

> *«Хватит терпеть эту несправедливость. Мы создадим СВОЮ фаму. Фаму, где будет уважение, помощь и реальный заработок!»*

Так **16 апреля 2026 года** родилась **NEXUS** — фама, построенная на честности, силе и взаимопомощи.

**💰 НАШ ПУТЬ СЕГОДНЯ**

Мы активно развиваемся, перешли на **кражу**, стали королями тайников и ограблений.

**🚗 ЧТО МЫ ПРЕДЛАГАЕМ:**

• 🎯 Регулярные заезды на **трассу**
• 🦹‍♂️ Профессиональные **ограбления**
• 📦 Зачистка **тайников**
• 💰 Стабильный **заработок**
• 🤝 **Обучение новичков** с нуля

**🚀 НАШ АВТОПАРК:**

У нас одни из самых больших гаражей на сервере. Десятки машин, от бюджетных до элитных. И мы готовы помочь тебе собрать ТВОЮ коллекцию!

**🔥 ЧТО МЫ ИЩЕМ:**

Активных, адекватных и целеустремлённых игроков, которые хотят развиваться и зарабатывать вместе с нами.

**С нами ты НЕ останешься с нулём в кармане. Мы всему научим, поможем встать на ноги и станем твоей второй семьёй в Miami 8!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🌟 NEXUS — МЫ СИЛА! ПРИСОЕДИНЯЙСЯ! 🌟**

*Основатель: Sanek | Дата основания: 16.04.2026*
"""
    embed = discord.Embed(
        title="🏰 LEGACY OF NEXUS 🏰",
        description=story,
        color=discord.Color.dark_gold()
    )
    embed.set_footer(text="Nexus | Miami 8 | Вместе мы сила!")
    await ctx.respond(embed=embed)

@bot.slash_command(name="compliment", description="Получить комплимент для игрока Маджестик")
async def compliment(ctx: discord.ApplicationContext, member: discord.Member = None):
    target = member if member else ctx.author
    compliment_text = random.choice(compliments)
    
    embed = discord.Embed(
        title="💝 КОМПЛИМЕНТ ДНЯ! 💝",
        description=f"{target.mention}, {compliment_text}",
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"✨ Сказано с любовью от {ctx.author.display_name}")
    await ctx.respond(embed=embed)

@bot.slash_command(name="majestic", description="Предсказание судьбы в Маджестик")
async def majestic(ctx: discord.ApplicationContext):
    prediction = random.choice(predictions)
    
    embed = discord.Embed(
        title="🔮 ВЕЛИКИЙ ОРАКУЛ МАДЖЕСТИК 🔮",
        description=prediction,
        color=discord.Color.purple()
    )
    embed.add_field(name="🌟 Совет дня:", value="Доверяй своим инстинктам и не бойся рисковать!", inline=False)
    embed.set_footer(text=f"Для {ctx.author.display_name} | Сила Маджестик внутри тебя!")
    await ctx.respond(embed=embed)

@bot.slash_command(name="botinfo", description="Информация о создателе бота")
async def botinfo(ctx: discord.ApplicationContext):
    embed = discord.Embed(
        title="🤖 О БОТЕ NEXUS 🤖",
        description="Вся информация о нашем музыкальном помощнике",
        color=discord.Color.blue()
    )
    embed.add_field(name="👨‍💻 **Создатель бота:**", value="**Vladosis Nexus** — разработал этого бота с нуля для комфорта нашей фамы", inline=False)
    embed.add_field(name="🎯 **Для чего этот бот?**", value="Бот создан для комфортного времяпрепровождения участников фамы Nexus на сервере Miami 8. Здесь ты можешь слушать музыку, получать предсказания, узнавать историю нашей фамы и многое другое!", inline=False)
    embed.add_field(name="📅 **Дата создания бота:**", value="16 апреля 2026 года", inline=True)
    embed.add_field(name="⚙️ **Версия:**", value="1.0.0 (Stable)", inline=True)
    embed.add_field(name="🛠️ **Технологии:**", value="Python + discord.py + YouTube API", inline=False)
    embed.add_field(name="📢 **По вопросам информации и обновлений:**", value="**@mod1kus777**", inline=False)
    embed.set_footer(text="Nexus Music Bot | Сделано с душой для своей фамы")
    await ctx.respond(embed=embed)

@bot.slash_command(name="promo", description="Получить промокод для Majestic RolePlay")
async def promo(ctx: discord.ApplicationContext):
    embed = discord.Embed(
        title="🎁 ПРОМОКОД NEXUS 🎁",
        description="**Станьте кем угодно в GTA 5 Majestic RolePlay!**",
        color=discord.Color.green()
    )
    embed.add_field(name="🌟 **Что тебя ждёт:**", value="Присоединяйся к игре вместе со мной на Majestic. Создавай персонажа прямо сейчас и начинай развиваться, воплощая свои мечты!\n\nТебе откроется огромный мир, в котором играют тысячи реальных игроков. Используй голосовой чат и сотни других возможностей, которых нет в других играх.", inline=False)
    embed.add_field(name="🎮 **ПРОМОКОД:**", value="```NEXUS```", inline=False)
    embed.add_field(name="📝 **Как активировать:**", value="Укажи промокод при регистрации или прямо в игре командой `/promo NEXUS`", inline=False)
    embed.add_field(name="💎 **Majestic Premium (7 дней)**", value="• Ускоренное развитие персонажа\n• Повышенный доход\n• Десятки эксклюзивных бонусов\n• Подписка действует для всех персонажей", inline=False)
    embed.add_field(name="💰 **Дополнительно:**", value="**50 000 игровой валюты** в подарок!", inline=False)
    embed.set_footer(text="Промокод активен для всех новых игроков | Nexus Family")
    await ctx.respond(embed=embed)

@bot.slash_command(name="toptulers", description="Топ тулеров фамы Nexus")
async def toptulers(ctx: discord.ApplicationContext):
    embed = discord.Embed(
        title="🏆 ТОП ТУЛЕРОВ ФАМЫ NEXUS 🏆",
        description="Наши крутые бойцы, которые знают, как делать деньги!",
        color=discord.Color.gold()
    )
    
    for medal, data in top_tulers.items():
        embed.add_field(
            name=f"{medal} {data['name']} {medal}",
            value=f"{data['description']}\n━━━━━━━━━━━━━━━━━",
            inline=False
        )
    
    embed.set_footer(text="Хочешь попасть в топ? Тулись как герой и мы тебя научим! | Nexus")
    await ctx.respond(embed=embed)

@bot.slash_command(name="command", description="Показать все команды бота")
async def commands_list(ctx: discord.ApplicationContext):
    embed = discord.Embed(
        title="🎵 NEXUS MUSIC BOT 🎵",
        description="Полный список команд для управления ботом:",
        color=discord.Color.purple()
    )
    embed.add_field(name="🎶 МУЗЫКАЛЬНЫЕ КОМАНДЫ", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/play [название]", value="▶️ Включить трек из YouTube", inline=False)
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
    await ctx.respond(embed=embed)

# Запуск бота
bot.run(os.getenv('DISCORD_TOKEN'))