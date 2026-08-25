import discord
from discord.ext import commands, tasks
import asyncio
import os
from dotenv import load_dotenv

# ==========================================
# 0. 경로 및 .env 설정
# ==========================================
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, ".env")

if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    print(f"📄 .env 로드 완료: {env_path}")
else:
    load_dotenv()

def load_bot_token():
    for env_name in ["DISCORD_BOT_TOKEN", "BOT_TOKEN", "TOKEN", "DISCORD_TOKEN"]:
        env_token = os.getenv(env_name)
        if env_token:
            return env_token.strip().strip("'").strip('"')

    for filename in ["Bot_Token", "Bot_Token.txt", "token.txt"]:
        path = os.path.join(base_dir, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    token = f.read().strip().strip("'").strip('"')
                    if token:
                        return token
            except Exception:
                pass
    return ""

DISCORD_BOT_TOKEN = load_bot_token()

# ==========================================
# 1. 봇 초기화 및 mtime 기반 파일 변경 추적
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)
cog_mtimes = {}

async def reload_cog_module(extension_name):
    try:
        await bot.reload_extension(extension_name)
        print(f"🔄 [자동 핫 리로드 성공] {extension_name}")
        return True
    except Exception:
        try:
            await bot.load_extension(extension_name)
            print(f"🧩 [자동 모듈 로드 성공] {extension_name}")
            return True
        except Exception as e:
            print(f"❌ [자동 핫 리로드 실패] {extension_name}: {e}")
            return False

@tasks.loop(seconds=3)
async def auto_reload_task():
    """cogs 폴더 내 파일 수정 시간(mtime) 최적화 감지"""
    cogs_dir = os.path.join(base_dir, "cogs")
    if not os.path.exists(cogs_dir):
        return

    has_changed = False
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py"):
            file_path = os.path.join(cogs_dir, filename)
            try:
                current_mtime = os.path.getmtime(file_path)
            except OSError:
                continue

            cog_name = f"cogs.{filename[:-3]}"

            if cog_name not in cog_mtimes:
                cog_mtimes[cog_name] = current_mtime
            elif cog_mtimes[cog_name] != current_mtime:
                cog_mtimes[cog_name] = current_mtime
                print(f"🔍 파일 변경 감지: {filename}")
                if await reload_cog_module(cog_name):
                    has_changed = True

    if has_changed:
        try:
            await bot.tree.sync()
            print("⚡ 파일 변경 반영 후 명령어 트리 동기화 완료!")
        except Exception as e:
            print(f"❌ 동기화 실패: {e}")

async def load_extensions():
    cogs_dir = os.path.join(base_dir, "cogs")
    if os.path.exists(cogs_dir):
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py"):
                extension_name = f"cogs.{filename[:-3]}"
                file_path = os.path.join(cogs_dir, filename)
                try:
                    cog_mtimes[extension_name] = os.path.getmtime(file_path)
                    await bot.load_extension(extension_name)
                    print(f"🧩 모듈 로드 성공: {extension_name}")
                except Exception as e:
                    print(f"❌ 모듈 로드 실패 ({extension_name}): {e}")

@bot.event
async def on_ready():
    print(f'✅ {bot.user.name} 봇 가동 중')

    for guild in bot.guilds:
        try:
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
        except Exception:
            pass

    try:
        synced = await bot.tree.sync()
        print(f"⚡ 전역 명령어 {len(synced)}개 단일 동기화 완료!")
    except Exception as e:
        print(f"❌ 전역 동기화 실패: {e}")

    if not auto_reload_task.is_running():
        auto_reload_task.start()
        print("👁️ mtime 기반 무중단 자동 감지 서비스 시작됨")

async def main():
    async with bot:
        await load_extensions()
        if DISCORD_BOT_TOKEN:
            await bot.start(DISCORD_BOT_TOKEN)
        else:
            print("❌ 토큰을 찾을 수 없습니다!")

if __name__ == "__main__":
    asyncio.run(main())