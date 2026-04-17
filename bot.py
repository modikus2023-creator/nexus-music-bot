import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp as youtube_dl
import asyncio
import random
import os

# Настройки бота
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Настройки для YouTube
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
    }],
    'quiet': True,
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# Глобальные переменные
queue = []
current_volume = 50

# Список комплиментов для /compliment
compliments = [
    "Ты 🔥 **имба** 🔥 в этом мире Маджестик!",
    "С тобой даже **топ-1 гильдия** бы проиграла от зависти! 💪",
    "Твой скилл на Маджестике — **легенда**, которую рассказывают новичкам! 🌟",
    "Ты не игрок, ты — **Машина для побед**! 🏆",
    "С тобой в пати — **100% победа**, даже если ты просто стоишь и улыбаешься! 😎"
]

# Предсказания для /majestic
predictions = [
    "🎲 Сегодня ты **найдёшь легендарный меч** в подземелье! 🗡️",
    "🎲 **Твой крит урона** будет 9999+ в следующей битве! 💥",
    "🎲 **Осторожно**: сегодня у тебя будет **настоящий вызов** от секретного босса! 👑",
    "🎲 Фортуна улыбается тебе — **редкий артефакт** уже близко! ✨",
    "🎲 **Великий Оракул** говорит: завтра ты получишь **эпическую награду**! 🎁"
]

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
            if self.voice_client:
                await self.voice_client.disconnect()

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

# Событие готовности бота
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'✅ Бот {bot.user} запущен и готов к работе!')
    await bot.change_presence(activity=discord.Game(name="/command | Маджестик"))

# ==================== МУЗЫКАЛЬНЫЕ КОМАНДЫ ====================

@bot.tree.command(name="play", description="Включить трек или плейлист из YouTube")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.defer()
    
    voice_channel = interaction.user.voice.channel if interaction.user.voice else None
    if not voice_channel:
        await interaction.followup.send("❌ Вы не в голосовом канале!")
        return
    
    if not interaction.guild.voice_client:
        await voice_channel.connect()
    
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)
            url = info['entries'][0]['webpage_url']
            title = info['entries'][0]['title']
        except Exception as e:
            await interaction.followup.send("❌ Не удалось найти трек!")
            return
    
    queue.append({'url': url, 'title': title})
    await interaction.followup.send(f"✅ Добавлено в очередь: **{title}**")
    
    if not interaction.guild.voice_client.is_playing():
        player = MusicPlayer(interaction)
        await player.play_song(url)

@bot.tree.command(name="stop", description="Остановить текущий трек")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.pause()
        await interaction.response.send_message("⏸️ Трек остановлен. Используйте `/resume` чтобы продолжить.")
    else:
        await interaction.response.send_message("❌ Ничего не играет!")

@bot.tree.command(name="resume", description="Возобновить остановленный трек")
async def resume(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.resume()
        await interaction.response.send_message("▶️ Трек возобновлён!")
    else:
        await interaction.response.send_message("❌ Нет остановленного трека!")

@bot.tree.command(name="volume", description="Изменить громкость (0-300%)")
async def volume(interaction: discord.Interaction, level: int):
    global current_volume
    if level < 0 or level > 300:
        await interaction.response.send_message("❌ Громкость должна быть от 0 до 300!")
        return
    current_volume = level
    if interaction.guild.voice_client and interaction.guild.voice_client.source:
        interaction.guild.voice_client.source.volume = level / 100
    await interaction.response.send_message(f"🔊 Громкость установлена на {level}%")

@bot.tree.command(name="clear", description="Очистить очередь треков")
async def clear(interaction: discord.Interaction):
    global queue
    queue = []
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
    await interaction.response.send_message("🗑️ Очередь полностью очищена!")

@bot.tree.command(name="skip", description="Пропустить текущий трек")
async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("⏭️ Трек пропущен!")
    else:
        await interaction.response.send_message("❌ Ничего не играет!")

@bot.tree.command(name="leave", description="Выйти из голосового канала")
async def leave(interaction: discord.Interaction):
    global queue
    queue = []
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Бот вышел из канала, очередь очищена!")
    else:
        await interaction.response.send_message("❌ Бот не в голосовом канале!")

# ==================== ИНТЕРАКТИВНЫЕ КОМАНДЫ ====================

@bot.tree.command(name="nexus", description="История легендарной фамы Nexus")
async def nexus(interaction: discord.Interaction):
    story = """
🏰 **★ 𝐓𝐇𝐄 𝐋𝐄𝐆𝐄𝐍𝐃 𝐎𝐅 𝐍𝐄𝐗𝐔𝐒 ★** 🏰

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   𝐁𝐨𝐫𝐧 𝐟𝐫𝐨𝐦 𝐭𝐡𝐞 𝐚𝐬𝐡𝐞𝐬 𝐨𝐟 𝐌𝐢𝐚𝐦𝐢 𝟖   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📜 **𝐂𝐡𝐚𝐩𝐭𝐞𝐫 𝐈: 𝐓𝐡𝐞 𝐃𝐚𝐰𝐧 𝐨𝐟 𝐍𝐞𝐱𝐮𝐬** 📜

В далёкий день **16 апреля 2026 года**, когда сервер **Miami 8** только начинал свою эпоху, в мире виртуальной реальности появился легендарный игрок с ником **Sanek**...

✨ **«Почему бы не создать нечто великое?»** — подумал он. ✨

И тогда, словно из ниоткуда, родилась **ФАМА NEXUS** — имя, которое заставит дрожать врагов и восхищаться союзников!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏠 **𝐂𝐡𝐚𝐩𝐭𝐞𝐫 𝐈𝐈: 𝐓𝐡𝐞 𝐆𝐫𝐚𝐧𝐝 𝐌𝐚𝐧𝐬𝐢𝐨𝐧** 🏠

Nexus не просто фама — это **ИМПЕРИЯ**! 
• Самый **РОСКОШНЫЙ ДОМ** на всём Miami 8 ✨
• **ЗОЛОТЫЕ СТЕНЫ** и **АЛМАЗНЫЕ ПОЛЫ** 💎
• Сад с **ЭКЗОТИЧЕСКИМИ РАСТЕНИЯМИ** 🌴
• Личный **ВЕРТОЛЁТНАЯ ПЛОЩАДКА** 🚁

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👑 **𝐂𝐡𝐚𝐩𝐭𝐞𝐫 𝐈𝐈𝐈: 𝐓𝐡𝐞 𝐄𝐥𝐢𝐭𝐞 𝐒𝐪𝐮𝐚𝐝** 👑

Состав Nexus — это **ЭЛИТА** Miami 8:
⚔️ **ТОП-1 PvP игроки** — непобедимы в битвах
🧠 **Гениальные стратеги** — просчитывают ходы на 10 шагов вперёд
😂 **Короли юмора** — позитив заряжает на 100500%
🤝 **Верные друзья** — в беде не бросят, в бою прикроют

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **𝐂𝐡𝐚𝐩𝐭𝐞𝐫 𝐈𝐕: 𝐓𝐡𝐞 𝐋𝐞𝐠𝐚𝐜𝐲** 🎯

Сегодня Nexus — это **НЕ ПРОСТО ФАМА**, это:
💪 **СИЛА** — которую невозможно сломить
🔥 **СТРАСТЬ** — к победам и достижениям
🏆 **УСПЕХ** — каждый день новые вершины
❤️ **СЕРДЦЕ** — которое бьётся в ритме Miami 8

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌟 **𝐉𝐨𝐢𝐧 𝐍𝐞𝐱𝐮𝐬 𝐭𝐨𝐝𝐚𝐲!** 🌟

*«Мы не ищем лёгких путей — мы создаём их!»* — **Sanek**, основатель Nexus

🎉🎊🎉 **NEXUS FOREVER!** 🎉🎊🎉
"""
    embed = discord.Embed(
        title="📜 История фамы Nexus 📜",
        description=story,
        color=discord.Color.purple()
    )
    embed.set_footer(text="Nexus | Miami 8 | Основана 16.04.2026")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="compliment", description="Получить комплимент для игрока Маджестик")
async def compliment(interaction: discord.Interaction, member: discord.Member = None):
    target = member if member else interaction.user
    compliment_text = random.choice(compliments)
    
    embed = discord.Embed(
        title="💝 **КОМПЛИМЕНТ ДНЯ!** 💝",
        description=f"{target.mention}, {compliment_text}",
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"✨ Сказано с любовью от {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="majestic", description="Предсказание судьбы в Маджестик")
async def majestic(interaction: discord.Interaction):
    prediction = random.choice(predictions)
    
    embed = discord.Embed(
        title="🔮 **ВЕЛИКИЙ ОРАКУЛ МАДЖЕСТИК** 🔮",
        description=prediction,
        color=discord.Color.purple()
    )
    embed.add_field(name="🌟 Совет дня:", value="Доверяй своим инстинктам и не бойся рисковать!", inline=False)
    embed.set_footer(text=f"Для {interaction.user.display_name} | Сила Маджестик внутри тебя!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="faction", description="Показать статистику фамы Nexus")
async def faction(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚔️ **СТАТИСТИКА ФАМЫ NEXUS** ⚔️",
        description="Наша сила растёт с каждым днём!",
        color=discord.Color.dark_gold()
    )
    embed.add_field(name="👥 Участников:", value="**12** активных бойцов", inline=True)
    embed.add_field(name="🏆 Побед в войнах:", value="**7**", inline=True)
    embed.add_field(name="💎 Уровень фамы:", value="**MASTER III**", inline=True)
    embed.add_field(name="🏠 Размер дома:", value="**S+ Ранг** (самый большой!)", inline=False)
    embed.add_field(name="📅 Дата основания:", value="**16 апреля 2026 года**", inline=True)
    embed.add_field(name="👑 Основатель:", value="**Sanek**", inline=True)
    embed.add_field(name="🎯 Статус:", value="🟢 **Активно набираем новичков!**", inline=False)
    embed.set_footer(text="Присоединяйся к Nexus и стань легендой!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="command", description="Показать все команды бота")
async def commands_list(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎵 **NEXUS MUSIC BOT** 🎵",
        description="Полный список команд для управления ботом:",
        color=discord.Color.purple()
    )
    embed.add_field(name="🎶 **МУЗЫКАЛЬНЫЕ КОМАНДЫ**", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/play [название]", value="▶️ Включить трек из YouTube", inline=False)
    embed.add_field(name="/stop", value="⏸️ Остановить трек", inline=True)
    embed.add_field(name="/resume", value="▶️ Возобновить трек", inline=True)
    embed.add_field(name="/skip", value="⏭️ Пропустить трек", inline=True)
    embed.add_field(name="/volume [0-300]", value="🔊 Громкость", inline=True)
    embed.add_field(name="/clear", value="🗑️ Очистить очередь", inline=True)
    embed.add_field(name="/leave", value="👋 Выйти из канала", inline=True)
    
    embed.add_field(name="\n✨ **ИНТЕРАКТИВНЫЕ КОМАНДЫ**", value="━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.add_field(name="/nexus", value="📜 История фамы Nexus", inline=True)
    embed.add_field(name="/compliment [@участник]", value="💝 Отправить комплимент", inline=True)
    embed.add_field(name="/majestic", value="🔮 Предсказание для Маджестик", inline=True)
    embed.add_field(name="/faction", value="⚔️ Статистика фамы", inline=True)
    embed.add_field(name="/command", value="📋 Показать это меню", inline=True)
    
    embed.set_footer(text="Создано Nexus | Маджестик | Miami 8")
    await interaction.response.send_message(embed=embed)

# ЗАПУСК БОТА — токен берётся из переменных окружения Railway
bot.run(os.getenv('DISCORD_TOKEN'))