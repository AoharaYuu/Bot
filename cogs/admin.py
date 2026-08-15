import discord
from discord import app_commands
from discord.ext import commands
import os
import json

BOT_VERSION = "v3.5.0"
UPDATE_NOTES = (
    "• 전체 기존 기능(음악 채널 자동 생성, 역할 관리, 설정 유지)이 완전 복원되었습니다.\n"
    "• 업데이트 로그 및 관리자 기능이 `cogs/admin.py` 모듈로 통합되었습니다.\n"
    "• 파일 수정 시 봇 무중단 자동 핫 리로드(Watchdog)가 정상 가동됩니다."
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

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_notice_channel(self, guild):
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

    async def send_update_notice_to_all_guilds(self):
        sent_count = 0
        for guild in self.bot.guilds:
            target_channel = self.get_notice_channel(guild)
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

    @commands.Cog.listener()
    async def on_ready(self):
        # 버전 비교 및 자동 공지
        last_version = ""
        if os.path.exists(VERSION_FILE):
            try:
                with open(VERSION_FILE, "r", encoding="utf-8") as f:
                    last_version = f.read().strip()
            except Exception:
                pass

        if last_version != BOT_VERSION:
            print(f"📢 버전 변경 감지 (기존: '{last_version}' ➔ 신규: '{BOT_VERSION}')")
            await self.send_update_notice_to_all_guilds()
            try:
                with open(VERSION_FILE, "w", encoding="utf-8") as f:
                    f.write(BOT_VERSION)
                print(f"📝 '{VERSION_FILE}' 파일이 '{BOT_VERSION}' 버전으로 자동 갱신되었습니다.")
            except Exception as e:
                print(f"[경고] 버전 파일 갱신 실패: {e}")

    @app_commands.command(name="도움말", description="봇의 전체 명령어와 사용법을 확인합니다.")
    async def slash_help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 디스코드 봇 명령어 안내",
            description="`/`를 입력하여 실행할 수 있는 전체 명령어 목록입니다.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📢 서버 설정 & 공지",
            value="• `/공지채널설정 [채널]` : [관리자] 업데이트 공지 채널을 변경합니다.\n"
                  "• `/음악채널설정 [채널]` : [관리자] 음악 전용 채널을 직접 변경합니다.",
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

    @app_commands.command(name="공지채널설정", description="[관리자] 이 서버의 봇 공지가 전송될 채널을 지정합니다.")
    @app_commands.describe(channel="공지사항을 발송할 텍스트 채널 선택")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_set_notice_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
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

    @app_commands.command(name="음악채널설정", description="[관리자] 음악 명령어 전용 채널을 변경/지정합니다.")
    @app_commands.describe(channel="음악 명령어 전용 텍스트 채널 선택")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_set_music_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
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

    @app_commands.command(name="업데이트공지", description="[관리자] 설정된 최신 패치노트를 지정 채널에 전송합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_update_notice(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        sent_count = await self.send_update_notice_to_all_guilds()
        await interaction.followup.send(f"✅ 최신 패치노트({BOT_VERSION})를 총 **{sent_count}개 서버**에 발송했습니다!")

    @app_commands.command(name="안내메시지", description="[관리자] 지정한 채널에 역할 안내용 메시지를 생성합니다.")
    @app_commands.describe(channel="메시지를 보낼 채널 선택", title="메시지 제목", content="안내 내용 설명")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_create_info_message(self, interaction: discord.Interaction, channel: discord.TextChannel, title: str, content: str):
        embed = discord.Embed(title=title, description=content, color=discord.Color.green())
        embed.set_footer(text="[설정된 이모지 없음]")
        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ **{channel.mention}** 채널에 안내 메시지를 생성했습니다!", ephemeral=True)

    @app_commands.command(name="역할추가", description="[관리자] 안내 메시지에 이모지와 역할을 연결합니다.")
    @app_commands.describe(channel="채널 선택", search_keyword="검색 단어", emoji="이모지", role="역할 선택")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_add_role_by_search(self, interaction: discord.Interaction, channel: discord.TextChannel, search_keyword: str, emoji: str, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        target_message = None

        async for msg in channel.history(limit=100):
            if msg.author.id == self.bot.user.id and msg.embeds:
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

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild or not (channel := guild.get_channel(payload.channel_id)):
            return
        try:
            message = await channel.fetch_message(payload.message_id)
        except Exception:
            return

        if message.author.id == self.bot.user.id and message.embeds:
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

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild or not (channel := guild.get_channel(payload.channel_id)):
            return
        try:
            message = await channel.fetch_message(payload.message_id)
        except Exception:
            return

        if message.author.id == self.bot.user.id and message.embeds:
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

async def setup(bot):
    await bot.add_cog(AdminCog(bot))