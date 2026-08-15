import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as ytdl
import asyncio
import os
import json

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

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="입장", description="봇을 현재 접속 중인 음성 채널에 입장시킵니다.")
    async def slash_join(self, interaction: discord.Interaction):
        if interaction.user.voice:
            channel = interaction.user.voice.channel
            if interaction.guild.voice_client is not None:
                await interaction.guild.voice_client.move_to(channel)
            else:
                await channel.connect()
            await interaction.response.send_message(f"🎵 **{channel.name}** 음성 채널에 입장했습니다.")
        else:
            await interaction.response.send_message("⚠️ 먼저 음성 채널에 접속해 주세요!", ephemeral=True)

    @app_commands.command(name="퇴장", description="봇을 음성 채널에서 퇴장시킵니다.")
    async def slash_leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("👋 음성 채널에서 퇴장했습니다.")
        else:
            await interaction.response.send_message("⚠️ 봇이 음성 채널에 들어가 있지 않습니다.", ephemeral=True)

    @app_commands.command(name="재생", description="유튜브에서 음악을 검색하거나 URL을 통해 자동 접속하여 재생합니다.")
    @app_commands.describe(search="재생할 노래 제목 또는 유튜브 링크")
    async def slash_play(self, interaction: discord.Interaction, search: str):
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
            await interaction.followup.send(f"❌ 음악 재생 중 오류 발생: {e}")

async def setup(bot):
    await bot.add_cog(MusicCog(bot))