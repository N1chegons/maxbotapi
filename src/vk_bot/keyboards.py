from vkbottle import Keyboard, KeyboardButtonColor, Text, OpenLink, Callback

def get_admin_menu():
    keyboard = Keyboard(one_time=False, inline=True)

    keyboard.add(Text("💡 Факты"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("🧩 Загадки"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text("💬 Сборы Мнений"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("📝 Ролевые игры"), color=KeyboardButtonColor.SECONDARY)

    return keyboard.get_json()

def get_admin_fact_menu():
    keyboard = Keyboard(one_time=False, inline=True)

    keyboard.add(Callback("Созадть Факт", payload={"action": "create_fact"}), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Callback("Редактировать Факт", payload={"action": "edit_fact"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("↩️ В меню", payload={"action": "back_to_admin_menu"}), color=KeyboardButtonColor.SECONDARY)

    return keyboard.get_json()

def get_admin_riddle_menu():
    keyboard = Keyboard(one_time=False, inline=True)

    keyboard.add(Callback("Создать Загадку", payload={"action": "create_riddle"}), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Callback("Редактировать Загадку", payload={"action": "edit_riddle"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("↩️ В меню", payload={"action": "back_to_admin_menu"}), color=KeyboardButtonColor.SECONDARY)

    return keyboard.get_json()

def get_admin_opinions_menu():
    keyboard = Keyboard(one_time=False, inline=True)

    keyboard.add(Callback("Создать Сбор Мнений", payload={"action": "create_opinion"}), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Callback("Редактировать Сбор Мнений", payload={"action": "edit_opinion"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("↩️ В меню", payload={"action": "back_to_admin_menu"}), color=KeyboardButtonColor.SECONDARY)

    return keyboard.get_json()

def get_admin_tests_menu():
    keyboard = Keyboard(one_time=False, inline=True)

    keyboard.add(Callback("Создать Игру", payload={"action": "create_test"}), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Callback("Редактировать Игру", payload={"action": "edit_test"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("↩️ В меню", payload={"action": "back_to_admin_menu"}), color=KeyboardButtonColor.SECONDARY)

    return keyboard.get_json()

def admin_back():
    keyboard = Keyboard(inline=True)
    keyboard.add(Text("↩️ В меню", payload={"action": "back_to_admin_menu"}), color=KeyboardButtonColor.SECONDARY)

    return keyboard.get_json()