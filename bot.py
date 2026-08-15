import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as ytdl
import asyncio
import os
import json

# ==========================================
# 1. 봇 토큰 읽기 (절대 경로 탐색 적용)
# ==========================================
def load_bot_token():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(base_dir, "Bot_Token")

    for path in [token_path, f"{token_path}.txt"]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    token = f.read().strip()
                    if token:
                        print(f"🔑 '{os.path.basename(path)}' 파일에서 토큰을 불러왔습니다.")
                        return token
            except Exception as e:
                print(f"[경고] 토큰 파일 읽기 실패: {e}")

    env_token = os.getenv("DISCORD_BOT_TOKEN")
    if env_token:
        print("🔑 환경변수(DISCORD_BOT_TOKEN)에서 토큰을 불러왔습니다.")
        return env_token

    print("❌ 경고: 토큰을 찾을 수 없습니다!")
    return ""

DISCORD_BOT_TOKEN = load_bot_token()

# ==========================================
# 2. 봇 버전 및 서버별 설정 파일 관리
# ==========================================
# 💡 코드를 수정하고 배포할 때 아래 BOT_VERSION을 올려주면 자동으로 업데이트 공지가 발송됩니다.
BOT_VERSION = "v1.5.0"
UPDATE_NOTES = (
    "• 봇 실행 시 버전 체크 및 업데이트 공지 발송이 완전 자동화되었습니다.\n"
    "• `last_version.txt` 파일이 시스템에 의해 자동으로 생성 및 관리됩니다.\n"
    "• `#음악-명령어` 자동 생성 및 스마트 음성 채널 자동 접속 기능이 유지됩니다."
)

VERSION_FILE = "last_version.txt"
SETTINGS_FILE = "server_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[경고] 설정 파일 읽기 실패: {e}")
    return {}

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[경고] 설정 파일 저장 실패: {e}")

# ==========================================
# 3. 클라이언트 초기화 및 권한 설정
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ==========================================
# 4. 음악 옵션 및 채널 관리 헬퍼 함수
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

async def ensure_music_channel(guild):
    """서버 내 음악 전용 채널 존재 여부를 확인하고 없으면 자동 생성합니다."""
    settings = load_settings()
    guild_id_str = str(guild.id)

    if guild_id_str in settings and "music_channel_id" in settings[guild_id_str]:
        m_channel = guild.get_channel(settings[guild_id_str]["music_channel_id"])
        if m_channel:
            return m_channel

    for channel in guild.text_channels:
        if channel.name == "음악-명령어":
            if guild_id_str not in settings:
                settings[guild_id_str] = {}
            settings[guild_id_str]["music_channel_id"] = channel.id
            save_settings(settings)
            return channel

    try:
        new_channel = await guild.create_text_channel("음악-명령어", topic="🎵 음악 관련 명령어만 사용할 수 있는 전용 채널입니다.")
        embed = discord.Embed(
            title="🎵 음악 전용 채널에 오신 것을 환영합니다!",
            description="이 채널에서 `/재생`, `/입장`, `/퇴장` 등의 음악 명령어를 입력해주세요.\n"
                        "음성이 있는 채널에 들어가신 후 `/재생 [노래 제목]`을 입력하면 봇이 자동으로 접속하여 노래를 틀어드립니다!",
            color=discord.Color.purple()
        )
        msg = await new_channel.send(embed=embed)
        try:
            await msg.pin()
        except Exception:
            pass

        if guild_id_str not in settings:
            settings[guild_id_str] = {}
        settings[guild_id_str]["music_channel_id"] = new_channel.id
        save_settings(settings)
        print(f"[채널 자동 생성] {guild.name} 서버에 #음악-명령어 채널 생성 완료")
        return new_channel
    except Exception as e:
        print(f"[경고] {guild.name} 서버 음악 채널 생성 실패: {e}")
        return None

def is_music_channel(interaction: discord.Interaction) -> bool:
    """현재 명령어가 실행된 채널이 설정된 음악 채널인지 확인합니다."""
    settings = load_settings()
    guild_id_str = str(interaction.guild_id)

    if guild_id_str in settings and "music_channel_id" in settings[guild_id_str]:
        target_id = settings[guild_id_str]["music_channel_id"]
        return interaction.channel_id == target_id

    if interaction.channel and interaction.channel.name == "음악-명령어":
        return True
        
    return False

def get_notice_channel(guild):
    """서버별 공지 채널 탐색 (지정된 채널 -> '일반/general' -> 첫 번째 텍스트 채널)"""
    settings = load_settings()
    guild_id_str = str(guild.id)
    
    if guild_id_str in settings and "notice_channel_id" in settings[guild_id_str]:
        channel_id = settings[guild_id_str]["notice_channel_id"]
        channel = guild.get_channel(channel_id)
        if channel and channel.permissions_for(guild.me).send_messages:
            return channel

    for channel in guild.text_channels:
        if '일반' in channel.name.lower() or 'general' in channel.name.lower():
            if channel.permissions_for(guild.me).send_messages:
                return channel
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            return channel
    return None

async def send_update_notice_to_all_guilds():
    """모든 연결된 서버에 버전 업데이트 공지를 자동 전송합니다."""
    sent_count = 0
    for guild in bot.guilds:
        target_channel = get_notice_channel(guild)
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
                print(f"[경고] {guild.name} 서버 공지 전송 실패: {e}")
    return sent_count

# ==========================================
# 5. 로그인 & 자동 버전 체크 및 last_version.txt 자동 갱신
# ==========================================
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ 슬래시 명령어 동기화 완료: {len(synced)}개 명령어 등록됨")
    except Exception as e:
        print(f"❌ 슬래시 명령어 동기화 실패: {e}")
        
    print(f'✅ {bot.user.name} 봇이 로그인되었습니다.')

    # 1. 모든 서버에 음악 전용 채널 체크 및 생성
    for guild in bot.guilds:
        await ensure_music_channel(guild)

    # 2. last_version.txt 읽기 및 버전 자동 변경 감지
    last_version = ""
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                last_version = f.read().strip()
        except Exception as e:
            print(f"[경고] 버전 파일 읽기 실패: {e}")

    # 버전에 차이가 있거나 파일이 없는 경우 자동으로 공지 발송 및 last_version.txt 자동 갱신
    if last_version != BOT_VERSION:
        print(f"📢 버전 변경 감지 (기존: '{last_version}' ➔ 신규: '{BOT_VERSION}'): 자동 업데이트 공지를 전송합니다.")
        await send_update_notice_to_all_guilds()
        
        try:
            with open(VERSION_FILE, "w", encoding="utf-8") as f:
                f.write(BOT_VERSION)
            print(f"📝 '{VERSION_FILE}' 파일이 '{BOT_VERSION}' 버전으로 자동 갱신되었습니다.")
        except Exception as e:
            print(f"[경고] 버전 파일 갱신 실패: {e}")

@bot.event
async def on_guild_join(guild):
    """새 서버에 초대되면 음악 채널을 자동 생성합니다."""
    print(f"🎉 새 서버 입장: {guild.name}")
    await ensure_music_channel(guild)

# ==========================================
# 6. 서버 설정 명령어 (/공지채널설정, /음악채널설정)
# ==========================================
@bot.tree.command(name="공지채널설정", description="[관리자] 이 서버의 봇 공지가 전송될 채널을 지정합니다.")
@app_commands.describe(channel="공지사항을 발송할 텍스트 채널 선택")
@app_commands.checks.has_permissions(administrator=True)
async def slash_set_notice_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    settings = load_settings()
    guild_id_str = str(interaction.guild_id)

    if guild_id_str not in settings:
        settings[guild_id_str] = {}

    settings[guild_id_str]["notice_channel_id"] = channel.id
    save_settings(settings)

    await interaction.response.send_message(
        f"✅ 이 서버의 공지 채널이 **{channel.mention}** (으)로 설정되었습니다!",
        ephemeral=True
    )

@bot.tree.command(name="음악채널설정", description="[관리자] 음악 명령어 전용 채널을 변경/지정합니다.")
@app_commands.describe(channel="음악 명령어 전용 텍스트 채널 선택")
@app_commands.checks.has_permissions(administrator=True)
async def slash_set_music_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    settings = load_settings()
    guild_id_str = str(interaction.guild_id)

    if guild_id_str not in settings:
        settings[guild_id_str] = {}

    settings[guild_id_str]["music_channel_id"] = channel.id
    save_settings(settings)

    await interaction.response.send_message(
        f"🎵 이 서버의 음악 전용 채널이 **{channel.mention}** (으)로 변경되었습니다!",
        ephemeral=True
    )

# ==========================================
# 7. 음악 기능 명령어
# ==========================================
@bot.tree.command(name="입장", description="봇을 현재 접속 중인 음성 채널에 입장시킵니다.")
async def slash_join(interaction: discord.Interaction):
    if not is_music_channel(interaction):
        m_chan = await ensure_music_channel(interaction.guild)
        chan_mention = m_chan.mention if m_chan else "`#음악-명령어`"
        await interaction.response.send_message(f"⚠️ 음악 관련 명령어는 {chan_mention} 채널에서만 사용할 수 있습니다!", ephemeral=True)
        return

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
    if not is_music_channel(interaction):
        m_chan = await ensure_music_channel(interaction.guild)
        chan_mention = m_chan.mention if m_chan else "`#음악-명령어`"
        await interaction.response.send_message(f"⚠️ 음악 관련 명령어는 {chan_mention} 채널에서만 사용할 수 있습니다!", ephemeral=True)
        return

    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 음성 채널에서 퇴장했습니다.")
    else:
        await interaction.response.send_message("⚠️ 봇이 음성 채널에 들어가 있지 않습니다.", ephemeral=True)

@bot.tree.command(name="재생", description="유튜브에서 음악을 검색하거나 URL을 통해 자동 접속하여 재생합니다.")
@app_commands.describe(search="재생할 노래 제목 또는 유튜브 링크")
async def slash_play(interaction: discord.Interaction, search: str):
    if not is_music_channel(interaction):
        m_chan = await ensure_music_channel(interaction.guild)
        chan_mention = m_chan.mention if m_chan else "`#음악-명령어`"
        await interaction.response.send_message(f"⚠️ 음악 명령어는 {chan_mention} 채널에서만 사용할 수 있습니다!", ephemeral=True)
        return

    if not interaction.user.voice:
        await interaction.response.send_message("⚠️ 노래를 재생하려면 먼저 음성 채널에 입장해 있어야 합니다!", ephemeral=True)
        return

    user_voice_channel = interaction.user.voice.channel
    await interaction.response.defer()

    voice_client = interaction.guild.voice_client
    if voice_client is None:
        voice_client = await user_voice_channel.connect()
    elif voice_client.channel != user_voice_channel:
        await voice_client.move_to(user_voice_channel)

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

        await interaction.followup.send(f"🎶 **[ {user_voice_channel.name} ]** 음성 채널에서 재생 중: **{song_title}**")

    except Exception as e:
        print(f"[재생 오류]: {e}")
        await interaction.followup.send(f"❌ 음악 재생 중 오류 발생: {e}")

# ==========================================
# 8. 도움말 및 일반/역할 명령어
# ==========================================
@bot.tree.command(name="도움말", description="봇의 전체 명령어와 사용법을 확인합니다.")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 디스코드 봇 명령어 안내",
        description="`/`를 입력하여 실행할 수 있는 전체 명령어 목록입니다.",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="📢 서버 설정 & 공지",
        value="• `/공지채널설정 [채널]` : [관리자] 업데이트 공지 채널을 변경합니다.\n"
              "• `/음악채널설정 [채널]` : [관리자] 음악 전용 채널을 직접 변경합니다.\n"
              "• `/업데이트공지` : [관리자] 패치노트를 수동으로 전송합니다.",
        inline=False
    )
    embed.add_field(
        name="🎵 음악 기능 (#음악-명령어 전용)",
        value="• `/재생 [검색어/URL]` : 음성 채널에 자동 접속 후 노래 재생\n"
              "• `/입장` / `/퇴장` : 음성 채널 수동 입장 및 퇴장",
        inline=False
    )
    embed.add_field(
        name="🎭 반응형 역할 관리",
        value="• `/안내메시지 [채널] [제목] [내용]`\n"
              "• `/역할추가 [채널] [검색어] [이모지] [역할]`",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="업데이트공지", description="[관리자] 설정된 최신 패치노트를 지정 채널에 전송합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def slash_update_notice(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    sent_count = await send_update_notice_to_all_guilds()
    await interaction.followup.send(f"✅ 최신 패치노트({BOT_VERSION})를 총 **{sent_count}개 서버**에 발송했습니다!")

@bot.tree.command(name="안내메시지", description="[관리자] 지정한 채널에 역할 안내용 메시지를 생성합니다.")
@app_commands.describe(channel="메시지를 보낼 채널 선택", title="메시지 제목", content="안내 내용 설명")
@app_commands.checks.has_permissions(administrator=True)
async def slash_create_info_message(interaction: discord.Interaction, channel: discord.TextChannel, title: str, content: str):
    embed = discord.Embed(title=title, description=content, color=discord.Color.green())
    embed.set_footer(text="[설정된 이모지 없음]")
    await channel.send(embed=embed)
    await interaction.response.send_message(f"✅ **{channel.mention}** 채널에 안내 메시지를 생성했습니다!", ephemeral=True)

@bot.tree.command(name="역할추가", description="[관리자] 안내 메시지에 이모지와 역할을 연결합니다.")
@app_commands.describe(channel="채널 선택", search_keyword="검색 단어", emoji="이모지", role="역할 선택")
@app_commands.checks.has_permissions(administrator=True)
async def slash_add_role_by_search(interaction: discord.Interaction, channel: discord.TextChannel, search_keyword: str, emoji: str, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    target_message = None

    async for msg in channel.history(limit=100):
        if msg.author.id == bot.user.id and msg.embeds:
            embed = msg.embeds[0]
            if search_keyword in (embed.title or "") or search_keyword in (embed.description or ""):
                target_message = msg
                break

    if not target_message:
        await interaction.followup.send(f"⚠️ `{search_keyword}` 키워드가 포함된 메시지를 찾을 수 없습니다.")
        return

    embed = target_message.embeds[0]
    current_footer = embed.footer.text if embed.footer else ""
    mapping_str = f"[{emoji}:{role.id}]"
    
    if "[설정된 이모지 없음]" in current_footer or not current_footer:
        new_footer = mapping_str
    else:
        if mapping_str in current_footer:
            await interaction.followup.send(f"⚠️ 이미 해당 역할이 연결되어 있습니다.")
            return
        new_footer = f"{current_footer} {mapping_str}"

    embed.set_footer(text=new_footer)
    await target_message.edit(embed=embed)

    try:
        await target_message.add_reaction(emoji)
    except Exception as e:
        print(f"[경고] 이모지 추가 실패: {e}")

    await interaction.followup.send(f"✅ **'{embed.title}'** 메시지에 {emoji} ➔ `{role.name}` 역할이 연결되었습니다.")

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
        footer_text = message.embeds[0].footer.text if message.embeds[0].footer else ""
        current_emoji = str(payload.emoji)
        if footer_text and "[" in footer_text:
            for item in footer_text.split("]"):
                if "[" in item and ":" in (raw := item.split("[")[1]):
                    saved_emoji, saved_role_id_str = raw.split(":", 1)
                    if saved_emoji == current_emoji:
                        role = guild.get_role(int(saved_role_id_str))
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
        footer_text = message.embeds[0].footer.text if message.embeds[0].footer else ""
        current_emoji = str(payload.emoji)
        if footer_text and "[" in footer_text:
            for item in footer_text.split("]"):
                if "[" in item and ":" in (raw := item.split("[")[1]):
                    saved_emoji, saved_role_id_str = raw.split(":", 1)
                    if saved_emoji == current_emoji:
                        role = guild.get_role(int(saved_role_id_str))
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