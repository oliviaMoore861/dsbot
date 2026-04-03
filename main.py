import disnake
from disnake.ext import commands
import os



intents = disnake.Intents.all()

bot = commands.Bot(command_prefix=".", intents=intents, test_guilds=[1486013024048382153])


@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} готов!")
    print(f"📦 Загруженные коги: {list(bot.cogs.keys())}")


# Глобальный обработчик кнопок
@bot.event
async def on_button_click(inter: disnake.MessageInteraction):
    """Обработчик нажатий на кнопки"""
    if not inter.component.custom_id:
        return

    parts = inter.component.custom_id.split("_")
    if len(parts) != 2:
        return

    action = parts[0]
    try:
        owner_id = int(parts[1])
    except ValueError:
        return

    cog = bot.get_cog("Voice")
    if not cog:
        await inter.response.send_message("❌ Ошибка", ephemeral=True)
        return

    from cogs.voic import ControlPanelView
    view = ControlPanelView(owner_id, cog)
    await view.callback_handler(inter, action)


# Загружаем коги
for file in os.listdir("./cogs"):
    if file.endswith(".py") and file != "__init__.py":
        try:
            bot.load_extension(f"cogs.{file[:-3]}")
            print(f"✅ Загружен: {file}")
        except Exception as e:
            print(f"❌ Ошибка {file}: {e}")


from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Бот работает!"

def run():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run).start()


if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))
