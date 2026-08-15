import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as ytdl
import asyncio
import os

# ==========================================
# 1. 봇 토큰 읽기 (Bot_Token 파일 우선 -> 환경변수)
# ==========================================
def load_bot_token():
    # 1. Bot_Token 텍스트 파일 확인
    token_filename = "Bot_Token"
    if os.path.exists(token_filename):
        try:
            with open(token_filename, "r", encoding="utf-8") as f:
                token = f.read().strip()
                if token:
                    print(f"🔑 '{token_filename}' 파일에서 토큰을 성공적으로 불러왔습니다.")
                    return token
        except Exception as e:
            print(f"[경고] 토큰 파일 읽기 실패: {e}")

    # 2. Koyeb 환경변수 확인 (DISCORD_BOT_TOKEN)
    env_token = os.getenv("DISCORD_BOT_TOKEN")
    if env_token:
        print("🔑 Koyeb 환경변수(DISCORD_BOT_TOKEN)에서 토큰을 불러왔습니다.")
        return env_token

    print("❌ 경고: 토큰을 찾을 수 없습니다! Bot_Token 파일 또는 환경변수를 확인해 주세요.")
    return ""

DISCORD_BOT_TOKEN = load_bot_token()

# ==========================================
# 2. 봇 버전 및 패치노트 설정
# ==========================================
BOT_VERSION = "v1.2.0"
UPDATE_NOTES = (
    "• 채널 ID 입력 없이 디스코드 UI에서 직접 채널을 선택할 수 있습니다.\n"
    "• 제목 및 내용 검색을 통해 역할 안내 메시지를 자동으로 탐색합니다.\n"
    "• 역할 ID 기반 매핑 적용으로 안정성이 강화되었습니다.\n"
    "• 업데이트 자동 감지 및 자동 공지 시스템이 적용되었습니다."
)

VERSION_FILE = "last_version.txt"

# ==========================================
# 3. 클라이언트 초기화 및 권한 설정
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ==========================================
# 4. 고음질 오디오 추출 및 FFmpeg 옵션 설정
# ==========================================
YTDL_OPTIONS = {
    'format': 'bestaudio[ext=opus]/bestaudio[ext=m4a]/bestaudio/best',
    'extractflat': False,
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'no_warnings': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -ar 48000 -ac 2'
}

ytdl_client = ytdl.YoutubeDL(YTDL_OPTIONS)

def find_notice_channel(guild):
    for channel in guild.text_channels:
        if '일반' in channel.name.lower() or 'general' in channel.name.lower():
            if channel.permissions_for(guild.me).send_messages:
                return channel
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            return channel
    return None

async def send_update_notice_to_all_guilds():
    sent_count = 0
    for guild in bot.guilds:
        target_channel = find_notice_channel(guild)
        if target_channel:
            try:
                embed = discord.Embed(
                    title=f"🚀 봇 업데이트 안내 ({BOT_VERSION})",
                    description=f"**[ 주요 변경 사항 ]**\n{UPDATE_NOTES}",
                    color=discord.Color.blue()
                )
                await target_channel.send(embed=embed)
                print(f"[업데이트 공지 전송 성공] 서버: {guild.name} ➔ 채널: #{target_channel.name}")
                sent_count += 1
            except Exception as e:
                print(f"[경고] {guild.name} 서버 업데이트 공지 전송 실패: {e}")
    return sent_count

# ==========================================
# 5. 로그인 & 업데이트 자동 감지
# ==========================================
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ 슬래시 명령어 동기화 완료: {len(synced)}개 명령어 등록됨")
    except Exception as e:
        print(f"❌ 슬래시 명령어 동기화 실패: {e}")
        
    print(f'✅ {bot.user.name} 봇이 로그인되었습니다.')

    last_version = ""
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                last_version = f.read().strip()
        except Exception as e:
            print(f"[경고] 버전 파일 읽기 실패: {e}")

    if last_version != BOT_VERSION:
        print(f"📢 버전 변경 감지 ({last_version} -> {BOT_VERSION}): 업데이트 공지를 발송합니다.")
        await send_update_notice_to_all_guilds()
        
        try:
            with open(VERSION_FILE, "w", encoding="utf-8") as f:
                f.write(BOT_VERSION)
        except Exception as e:
            print(f"[경고] 버전 파일 쓰기 실패: {e}")

# ==========================================
# 6. 음악 기능 명령어 (/입장, /퇴장, /재생)
# ==========================================
@bot.tree.command(name="입장", description="봇을 현재 접속 중인 음성 채널에 입장시킵니다.")
async def slash_join(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        if interaction.guild.voice_client is not None:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect()
        await interaction.response.send_message(f"🎵 **{channel.name}** 음성 채널에 입장했습니다.")
    else:
        await interaction.response.send_message("⚠️ 먼저 음성 채널에 접속해 주세요!", ephemeral=True)

@bot.tree.command(name="퇴장", description="봇을 음성 채널에서 퇴장시킵니다.")
async def slash_leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 음성 채널에서 퇴장했습니다.")
    else:
        await interaction.response.send_message("⚠️ 봇이 음성 채널에 들어가 있지 않습니다.", ephemeral=True)

@bot.tree.command(name="재생", description="유튜브에서 음악을 검색하거나 URL을 통해 고음질로 재생합니다.")
@app_commands.describe(search="재생할 노래 제목 또는 유튜브 링크")
async def slash_play(interaction: discord.Interaction, search: str):
    if not interaction.user.voice:
        await interaction.response.send_message("⚠️ 먼저 음성 채널에 접속해 주세요!", ephemeral=True)
        return

    await interaction.response.defer()

    voice_client = interaction.guild.voice_client
    if voice_client is None:
        voice_client = await interaction.user.voice.channel.connect()
    elif voice_client.channel != interaction.user.voice.channel:
        await voice_client.move_to(interaction.user.voice.channel)

    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl_client.extract_info(search, download=False))

        if 'entries' in data and len(data['entries']) > 0:
            data = data['entries'][0]

        song_url = data.get('url')
        song_title = data.get('title', '제목 없음')

        if not song_url:
            await interaction.followup.send("❌ 오디오 스트림 URL을 가져오지 못했습니다.")
            return

        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()

        audio_source = discord.FFmpegPCMAudio(song_url, **FFMPEG_OPTIONS)
        voice_client.play(audio_source)

        await interaction.followup.send(f"🎶 **현재 재생 중:** {song_title}")

    except Exception as e:
        print(f"[재생 오류]: {e}")
        await interaction.followup.send(f"❌ 음악 재생 중 오류 발생: {e}")

# ==========================================
# 7. /도움말 및 자동화된 /업데이트공지 명령어
# ==========================================
@bot.tree.command(name="도움말", description="봇의 모든 슬래시 명령어와 사용법을 확인합니다.")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 디스코드 봇 명령어 안내",
        description="`/`를 입력하여 실행할 수 있는 전체 명령어 목록입니다.",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🎵 음악 기능",
        value="• `/입장` : 접속해 있는 음성 채널로 봇을 불러옵니다.\n"
              "• `/퇴장` : 접속해 있는 음성 채널에서 봇을 퇴장시킵니다.\n"
              "• `/재생 [검색어/URL]` : 유튜브 음악을 검색하거나 링크로 고음질 재생합니다.",
        inline=False
    )
    embed.add_field(
        name="🎭 반응형 역할 관리",
        value="• `/안내메시지 [채널] [제목] [내용]` : 선택한 채널에 안내 메시지를 작성합니다.\n"
              "• `/역할추가 [채널] [검색어] [이모지] [역할]` : 키워드로 메시지를 찾아 이모지 및 역할을 연결합니다.",
        inline=False
    )
    embed.add_field(
        name="📢 시스템 관리 기능",
        value="• `/업데이트공지` : 코드 상단에 설정된 최신 패치노트를 각 서버에 자동 발송합니다.",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="업데이트공지", description="[관리자] 설정된 최신 패치노트를 서버에 즉시 전송합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def slash_update_notice(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    sent_count = await send_update_notice_to_all_guilds()
    await interaction.followup.send(f"✅ 설정된 최신 패치노트({BOT_VERSION})를 총 **{sent_count}개 서버**에 발송했습니다!")

# ==========================================
# 8. 역할 명령어 (Role ID 기반)
# ==========================================
@bot.tree.command(name="안내메시지", description="[관리자] 지정한 채널에 역할 안내용 메시지를 생성합니다.")
@app_commands.describe(
    channel="메시지를 보낼 채널 선택",
    title="메시지 제목",
    content="안내 내용 설명"
)
@app_commands.checks.has_permissions(administrator=True)
async def slash_create_info_message(
    interaction: discord.Interaction, 
    channel: discord.TextChannel, 
    title: str, 
    content: str
):
    embed = discord.Embed(
        title=title,
        description=content,
        color=discord.Color.green()
    )
    embed.set_footer(text="[설정된 이모지 없음]")

    sent_msg = await channel.send(embed=embed)
    await interaction.response.send_message(f"✅ **{channel.mention}** 채널에 안내 메시지를 성공적으로 생성했습니다!", ephemeral=True)

@bot.tree.command(name="역할추가", description="[관리자] 제목이나 내용 검색으로 안내 메시지를 찾아 이모지 및 역할을 연결합니다.")
@app_commands.describe(
    channel="안내 메시지가 있는 채널 선택",
    search_keyword="찾을 메시지의 제목 또는 내용에 포함된 단어",
    emoji="사용할 이모지 (예: 🎮)",
    role="연결할 서버 역할 선택"
)
@app_commands.checks.has_permissions(administrator=True)
async def slash_add_role_by_search(
    interaction: discord.Interaction, 
    channel: discord.TextChannel, 
    search_keyword: str, 
    emoji: str, 
    role: discord.Role
):
    await interaction.response.defer(ephemeral=True)

    target_message = None

    async for msg in channel.history(limit=100):
        if msg.author.id == bot.user.id and msg.embeds:
            embed = msg.embeds[0]
            embed_title = embed.title or ""
            embed_desc = embed.description or ""

            if search_keyword in embed_title or search_keyword in embed_desc:
                target_message = msg
                break

    if not target_message:
        await interaction.followup.send(f"⚠️ **{channel.mention}** 채널에서 `{search_keyword}` 키워드가 포함된 안내 메시지를 찾을 수 없습니다.")
        return

    embed = target_message.embeds[0]
    current_footer = embed.footer.text if embed.footer else ""

    mapping_str = f"[{emoji}:{role.id}]"
    
    if "[설정된 이모지 없음]" in current_footer or not current_footer:
        new_footer = mapping_str
    else:
        if mapping_str in current_footer:
            await interaction.followup.send(f"⚠️ 이미 해당 메시지에 `{emoji}` 이모지와 `{role.name}` 역할이 연결되어 있습니다.")
            return
        new_footer = f"{current_footer} {mapping_str}"

    embed.set_footer(text=new_footer)
    await target_message.edit(embed=embed)

    try:
        await target_message.add_reaction(emoji)
    except Exception as e:
        print(f"[경고] 이모지 추가 실패: {e}")

    found_title = embed.title or "제목 없음"
    await interaction.followup.send(f"✅ 검색 성공! **'{found_title}'** 메시지에 {emoji} 반응 ➔ `{role.name}` 역할 연결이 완료되었습니다.")

# ==========================================
# 9. 이모지 반응 감지 (Role ID 기반)
# ==========================================
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild or not (channel := guild.get_channel(payload.channel_id)):
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception:
        return

    if message.author.id == bot.user.id and message.embeds:
        embed = message.embeds[0]
        footer_text = embed.footer.text if embed.footer else ""
        current_emoji = str(payload.emoji)
        
        if footer_text and "[" in footer_text:
            for item in footer_text.split("]"):
                if "[" in item and ":" in (raw := item.split("[")[1]):
                    saved_emoji, saved_role_id_str = raw.split(":", 1)
                    if saved_emoji == current_emoji:
                        try:
                            role = guild.get_role(int(saved_role_id_str))
                        except ValueError:
                            role = discord.utils.get(guild.roles, name=saved_role_id_str)

                        if role and payload.member:
                            try:
                                await payload.member.add_roles(role)
                            except discord.Forbidden:
                                pass

@bot.event
async def on_raw_reaction_remove(payload):
    guild = bot.get_guild(payload.guild_id)
    if not guild or not (channel := guild.get_channel(payload.channel_id)):
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception:
        return

    if message.author.id == bot.user.id and message.embeds:
        embed = message.embeds[0]
        footer_text = embed.footer.text if embed.footer else ""
        current_emoji = str(payload.emoji)

        if footer_text and "[" in footer_text:
            for item in footer_text.split("]"):
                if "[" in item and ":" in (raw := item.split("[")[1]):
                    saved_emoji, saved_role_id_str = raw.split(":", 1)
                    if saved_emoji == current_emoji:
                        try:
                            role = guild.get_role(int(saved_role_id_str))
                        except ValueError:
                            role = discord.utils.get(guild.roles, name=saved_role_id_str)

                        if role and (member := guild.get_member(payload.user_id)):
                            try:
                                await member.remove_roles(role)
                            except discord.Forbidden:
                                pass

# 실행
if __name__ == "__main__":
    if DISCORD_BOT_TOKEN:
        bot.run(DISCORD_BOT_TOKEN)
    else:
        print("❌ 토큰이 입력되지 않아 봇을 실행할 수 없습니다.")