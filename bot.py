import discord
from discord.ext import commands, tasks
import asyncio
import os
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

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
# 1. 봇 초기화 및 자동 감지 설정
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)
reload_queue = set()

class CogChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".py"):
            filename = os.path.basename(event.src_path)
            cog_name = f"cogs.{filename[:-3]}"
            reload_queue.add(cog_name)

async def reload_cog_module(extension_name):
    try:
        await bot.reload_extension(extension_name)
        print(f"🔄 [자동 핫 리로드 성공] {extension_name}")
    except Exception:
        try:
            await bot.load_extension(extension_name)
            print(f"🧩 [자동 모듈 로드 성공] {extension_name}")
        except Exception as e:
            print(f"❌ [자동 핫 리로드 실패] {extension_name}: {e}")

@tasks.loop(seconds=2)
async def auto_reload_task():
    if reload_queue:
        targets = list(reload_queue)
        reload_queue.clear()
        for ext in targets:
            await reload_cog_module(ext)
        try:
            await bot.tree.sync()
            print("⚡ 자동 핫 리로드 후 명령어 슬래시 트리 동기화 완료!")
        except Exception as e:
            print(f"❌ 동기화 실패: {e}")

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
    print(f'✅ {bot.user.name} 봇이 성공적으로 가동되었습니다.')

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

    cogs_dir = os.path.join(base_dir, "cogs")
    if os.path.exists(cogs_dir):
        event_handler = CogChangeHandler()
        observer = Observer()
        observer.schedule(event_handler, path=cogs_dir, recursive=False)
        observer.start()
        print("👁️ cogs 폴더 자동 감지(Watchdog) 서비스가 가동되었습니다.")

async def main():
    async with bot:
        await load_extensions()
        if DISCORD_BOT_TOKEN:
            await bot.start(DISCORD_BOT_TOKEN)
        else:
            print("❌ 토큰을 찾을 수 없습니다!")

if __name__ == "__main__":
    asyncio.run(main())