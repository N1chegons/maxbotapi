from vkbottle import Keyboard, KeyboardButtonColor, Text, OpenLink, Callback


def get_main_menu():
    keyboard = Keyboard(one_time=False, inline=True)

    keyboard.add(Text("💡 Факт дня", payload={"action": "fact"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🧩 Загадка", payload={"action": "riddle"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("📝 Тест", payload={"action": "test"}), color=KeyboardButtonColor.PRIMARY)

    return keyboard.get_json()


def get_video_and_back_keyboard(video_url: str):
    keyboard = Keyboard(inline=True)
    keyboard.add(OpenLink(video_url, "🎬 Смотреть видео"), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    keyboard.add(Text("↩️ В меню", payload={"action": "back_to_menu"}), color=KeyboardButtonColor.SECONDARY)

    return keyboard.get_json()

def get_admin_menu():
    keyboard = Keyboard(one_time=False, inline=True)

    keyboard.add(Callback("Созадть факт", payload={"action": "create_fact"}), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Callback("Создать загадку", payload={"action": "create_riddle"}), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    keyboard.add(Callback("Создать Тест", payload={"action": "create_test"}), color=KeyboardButtonColor.POSITIVE)

    return keyboard.get_json()

def admin_back():
    keyboard = Keyboard(inline=True)
    keyboard.add(Text("↩️ В меню", payload={"action": "back_to_admin_menu"}), color=KeyboardButtonColor.SECONDARY)

    return keyboard.get_json()