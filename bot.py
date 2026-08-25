import discord
from discord.ext import commands, tasks
import asyncio
import os
from dotenv import load_dotenv

# ==========================================
# 0. 경로 및 .env 설정 (절대 경로 고정)
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
# 1. 봇 초기화 및 Cogs 무중단 감지
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def reload_cog_module(extension_name):
    try:
        await bot.reload_extension(extension_name)
        print(f"🔄 [모듈 리로드 성공] {extension_name}")
        return True
    except Exception:
        try:
            await bot.load_extension(extension_name)
            print(f"🧩 [모듈 로드 성공] {extension_name}")
            return True
        except Exception as e:
            print(f"❌ [모듈 로드 실패] {extension_name}: {e}")
            return False

@tasks.loop(seconds=3)
async def auto_reload_task():
    """cogs 폴더 내 파일 변경 감지 루프"""
    cogs_dir = os.path.join(base_dir, "cogs")
    if not os.path.exists(cogs_dir):
        return

    py_files = [os.path.join(cogs_dir, f) for f in os.listdir(cogs_dir) if f.endswith(".py")]
    if not py_files:
        return

    latest_mtime = max(os.path.getmtime(f) for f in py_files)

    if hasattr(auto_reload_task, "last_mtime"):
        if latest_mtime > auto_reload_task.last_mtime:
            auto_reload_task.last_mtime = latest_mtime
            print("🔍 [파일 변경 감지] Cogs 모듈을 재로드합니다.")
            
            for filename in os.listdir(cogs_dir):
                if filename.endswith(".py"):
                    await reload_cog_module(f"cogs.{filename[:-3]}")
            
            try:
                await bot.tree.sync()
                print("⚡ 슬래시 명령어 트리 동기화 완료!")
            except Exception as e:
                print(f"❌ 명령어 동기화 실패: {e}")
    else:
        auto_reload_task.last_mtime = latest_mtime

async def load_extensions():
    cogs_dir = os.path.join(base_dir, "cogs")
    if os.path.exists(cogs_dir):
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py"):
                extension_name = f"cogs.{filename[:-3]}"
                try:
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
        print("👁️ 파일 변경 감지 서비스가 구동되었습니다.")

async def main():
    async with bot:
        await load_extensions()
        if DISCORD_BOT_TOKEN:
            await bot.start(DISCORD_BOT_TOKEN)
        else:
            print("❌ 토큰을 찾을 수 없습니다!")

if __name__ == "__main__":
    asyncio.run(main())