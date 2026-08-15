import discord
from discord import app_commands
from discord.ext import commands

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="도움말", description="봇의 전체 명령어와 사용법을 확인합니다.")
    async def slash_help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 디스코드 봇 명령어 안내",
            description="`/`를 입력하여 실행할 수 있는 전체 명령어 목록입니다.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📢 서버 관리 & 핫 리로드",
            value="• `/리로드` : [관리자] 무중단으로 최신 모듈 코드를 반영합니다.\n"
                  "• `/안내메시지` / `/역할추가` : 반응형 역할 메시지 세팅",
            inline=False
        )
        embed.add_field(
            name="🎵 음악 기능",
            value="• `/재생 [검색어/URL]` : 음성 채널 접속 후 노래 재생\n"
                  "• `/입장` / `/퇴장` : 음성 채널 수동 입장 및 퇴장",
            inline=False
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="안내메시지", description="[관리자] 지정한 채널에 역할 안내용 메시지를 생성합니다.")
    @app_commands.describe(channel="메시지를 보낼 채널 선택", title="메시지 제목", content="안내 내용 설명")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_create_info_message(self, interaction: discord.Interaction, channel: discord.TextChannel, title: str, content: str):
        embed = discord.Embed(title=title, description=content, color=discord.Color.green())
        embed.set_footer(text="[설정된 이모지 없음]")
        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ **{channel.mention}** 채널에 안내 메시지를 생성했습니다!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))