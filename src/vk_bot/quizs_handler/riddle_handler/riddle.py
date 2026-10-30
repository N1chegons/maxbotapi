from vkbottle.bot import Message, BotLabeler, MessageEvent


from src.logger_config import setup_logger


riddle_labeler = BotLabeler()

logger = setup_logger('riddle_handler_vk', 'vk', 'riddle_handler_vk.log')

# @riddle_labeler.message(payload={"action": "riddle"})
# async def send_fact(message: Message):
#     user_id = message.from_id
#
#     try:
#         exists_user = await VkUserRepository.get_user(user_id)
#         logger.info(f"Получение пользователя VK {user_id}")
#
#         if not exists_user:
#             logger.warning(f"Пользователь не {user_id} не создан. Создание")
#             user_info = await message.get_user()
#             first_name = user_info.first_name
#             await VkUserRepository.create_user(user_id, first_name)
#
#         now = datetime.datetime.now()
#         if exists_user.last_fact_date:
#             time_diff = now - exists_user.last_fact_date
#             if time_diff.total_seconds() < 86400:
#                 logger.info(f"Пользователь {user_id} уже просматривал ежедневный факт")
#                 return await message.answer(
#                     "Ты уже видел факт дня сегодня! Возвращайся завтра 😉",
#                     keyboard=get_main_menu()
#                 )
#
#         random_fact = await VkFactRepository.get_random_fact()
#         if not random_fact:
#             return await message.answer("Пока фактов нет. Загляни позже!")
#
#         await VkUserRepository.update_last_fact_date(user_id)
#         logger.info(f"Обновление статуса - последний прсомотр факта дня у пользоватея {user_id}")
#
#         await message.answer(
#             Formatter("{:bold}:\n\n{}").format("💡 Факт дня", random_fact.title),
#             keyboard=get_video_and_back_keyboard(random_fact.video_url)
#         )
#
#     except Exception as e:
#         logger.info(f"Пользователь {user_id} получил неизвестную ошибку: {e}")
#         await message.answer(f"Неизвестная ошибка")