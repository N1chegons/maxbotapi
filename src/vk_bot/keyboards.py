from vkbottle import Keyboard, KeyboardButtonColor, Text, OpenLink


def get_main_menu():
    keyboard = Keyboard(one_time=False, inline=True)

    keyboard.add(Text("💡 Факт дня", payload={"action": "fact"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🧩 Загадка", payload={"action": "riddle"}), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text("📝 Тест", payload={"action": "test"}), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("📚 Термин дня", payload={"action": "term"}), color=KeyboardButtonColor.SECONDARY)

    return keyboard.get_json()


def get_video_and_back_keyboard(video_url: str):
    keyboard = Keyboard(inline=True)
    keyboard.add(OpenLink(video_url, "🎬 Смотреть видео"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("↩️ В меню", payload={"action": "back_to_menu"}), color=KeyboardButtonColor.SECONDARY)

    return keyboard.get_json()