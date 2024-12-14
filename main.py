
from g4f.client import Client
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton , WebAppInfo
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums.parse_mode import ParseMode
import json
import os

API_TOKEN = "Ваш токен"

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)


aproved_admins_session = [] # одобренные сессии администраторов

# Пути к JSON-файлам
QUIZ_FILE = "quiz_data.json"
USERS_FILE = "users_data.json"


# Функции для работы с JSON
def load_data_from_json(file_path):
    """Загружает данные из JSON-файла"""
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

def save_data_to_json(file_path, data):
    """Сохраняет данные в JSON-файл."""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def save_quiz():
    save_data_to_json(QUIZ_FILE, quiz_questions)

def save_users():
    save_data_to_json(USERS_FILE, users_data)

###--  Подгрузка данных --###
quiz_questions = load_data_from_json(QUIZ_FILE)
users_data = load_data_from_json(USERS_FILE)


# Состояния
class QuizState(StatesGroup):
    question = State()
    feedback = State()

class wait_mesage(StatesGroup):
    wait_password = State()
    wait_message_for_gpt = State()
    wait_feeback_dop_ms = State()

class QuizAdminState(StatesGroup):
    adding_question = State()
    deleting_question = State()


# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Вопрос"), KeyboardButton(text="Начать викторину")],
        [KeyboardButton(text="Оставить отзыв"), KeyboardButton(text="Интарактивная карта города" ,  web_app=WebAppInfo(url="https://flecksis.github.io/interect_kard.io/"))]
    ],
    resize_keyboard=True
)

''' 
    Конец инициализации.
 
    Определение функций.
    
'''

@router.message(Command("start"))
async def start_handler(message: types.Message):
    print(users_data)

    if str(message.from_user.id) not in users_data:
        print('now')
        users_data[str(message.from_user.id)] = {"quiz_done": False, "feedback_done": False, "feedback_data": None ,'feedback_message': None ,"wrong_answers": []}
        save_users()
    await message.answer_photo(photo='https://nikatv.ru/public/user_upload/files/2023/11/IMG04291152.jpg' ,caption="*Привет! Я буду помогать твоему экскурсоводу для улучшения вашего опыта.*\nВыберите действие:", reply_markup=main_menu ,parse_mode=ParseMode.MARKDOWN)
    await message.answer('Сообщение для жюри\n'
                         'У нас есть админ панель для управления мультимедией и анализа\n'
                         'Для входа в неё нужно написать сообщение - admin и ввести пароль admin')


@router.message(lambda msg: msg.text == "Вопрос")
async def question_handler(message: types.Message , state: FSMContext):
    await state.set_state(wait_mesage.wait_message_for_gpt)
    await message.answer("Напиши свой вопрос, и я постараюсь ответить!")


@dp.message(wait_mesage.wait_message_for_gpt)
async def quest_gpt(message: types.Message, state: FSMContext):
    text = message.text
    user_id = message.from_user.id
    temp_point = 0

    m = await message.answer('Это может занять некоторое время ⌛️')

    try:

        client = Client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Запомни ты историк и отвечаешь на вопросы по истории абсалютно вопрос - {text}"}],

        )
        while response.choices[0].message.content == 'Misuse detected. Please get in touch, we can come up with a solution for your use case.':
            if temp_point == 10:
                break
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user",
                           "content": f"Запомни ты историк и отвечаешь на вопросы по истории абсалютно вопрос - {text}"}],

            )
            temp_point += 1

        await m.edit_text(f'{response.choices[0].message.content}')

    except:
        pass
    await state.clear()


# Викторина
@router.message(lambda msg: msg.text == "Начать викторину")
async def start_quiz(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if users_data[str(user_id)]["quiz_done"]:
        await message.answer("Вы уже прошли викторину!")
        return
    users_data[str(user_id)]["quiz_done"] = True
    users_data[str(user_id)]["wrong_answers"] = []
    await state.set_state(QuizState.question)
    await send_question(message.chat.id, 0, state)
    save_users()

async def send_question(chat_id, question_index, state: FSMContext):
    if question_index >= len(quiz_questions):
        await bot.send_message(chat_id, "Викторина завершена!")
        wrong_answers = users_data[str(chat_id)]["wrong_answers"]
        if wrong_answers:
            result = "Вот ваши ошибки:\n"
            for qa in wrong_answers:
                result += f"Вопрос: {qa['question']}\nВаш ответ: {qa['your_answer']}\nПравильный ответ: {qa['correct']}\n\n"
            await bot.send_message(chat_id, result)
        else:
            await bot.send_message(chat_id, "Поздравляю, вы ответили на все вопросы правильно!")
        users_data[str(chat_id)]["quiz_done"] = True
        save_users()
        return

    question_data = quiz_questions[question_index]
    question_text = question_data["question"]
    options = question_data["options"]
    # 4  в ряду
    # keyboard = InlineKeyboardMarkup(
    #     inline_keyboard=[
    #         [InlineKeyboardButton(text=option, callback_data=f"quiz_{question_index}_{option}") for option in options]
    #     ]
    # )
    keyboard = InlineKeyboardBuilder()
    for option in options:
        b = InlineKeyboardButton(text=option, callback_data=f"quiz_{question_index}_{option}")
        keyboard.row(b)
    await bot.send_message(chat_id, question_text, reply_markup=keyboard.as_markup()    )

@router.callback_query(lambda call: call.data.startswith("quiz_"))
async def quiz_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    _, question_index, selected_option = callback.data.split("_")
    question_index = int(question_index)
    question_data = quiz_questions[question_index]

    if selected_option != question_data["correct"]:
        users_data[str(callback.from_user.id)]["wrong_answers"].append({
            "question": question_data["question"],
            "your_answer": selected_option,
            "correct": question_data["correct"]
        })
# Переходим к следующему вопросу
    await callback.message.delete()
    await send_question(callback.from_user.id, question_index + 1, state)
    await callback.answer()


# Оставить отзыв
@router.message(lambda msg: msg.text == "Оставить отзыв")
async def feedback_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if users_data[str(user_id)]["feedback_done"]:
        await message.answer("Вы уже оставили отзыв!")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Первый", callback_data="feedback_1"),
             InlineKeyboardButton(text="Второй", callback_data="feedback_2")],
            [InlineKeyboardButton(text="Третий", callback_data="feedback_3"),
             InlineKeyboardButton(text="Четвертый", callback_data="feedback_4")]
        ]
    )
    await state.set_state(QuizState.feedback)
    await message.answer("Какой вагон вам понравился больше всего?", reply_markup=keyboard)

@router.callback_query(lambda call: call.data.startswith("feedback_"))
async def feedback_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    _, wagon = callback.data.split("_")
    await callback.message.delete()
    await callback.message.answer(f"Спасибо вы выбрали вагон: {wagon},\nТеперь вы можете написать доп комментарий\nЕсли вам нечего сказать напишите -")
    users_data[str(callback.from_user.id)]["feedback_done"] = True
    users_data[str(callback.from_user.id)]["feedback_data"] = wagon
    save_users()
    await state.clear()
    await callback.answer()
    await state.set_state(wait_mesage.wait_feeback_dop_ms)

@dp.message(wait_mesage.wait_feeback_dop_ms)
async def feedback_dop_mse(message: types.Message, state: FSMContext):
    text = message.text
    user_id = message.from_user.id
    print(text)
    users_data[str(user_id)]["feedback_message"] = text
    save_users()
    await message.answer('Спасибо , мы ценим ваш мнение!')
    await state.clear()


#--- админ функционал ---#
@router.message(lambda msg: msg.text == "admin")
async def admin_panel(message: types.Message, state: FSMContext):
    await state.set_state(wait_mesage.wait_password)
    await message.answer("Пожалуйста, введите пароль:")


@dp.message(wait_mesage.wait_password)
async def admin_pamel_activ(message: types.Message, state: FSMContext):
    password = message.text
    user_id = message.from_user.id
    valid_admin_pass = 'admin'
    if password == valid_admin_pass:
        admin_menu = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Добавить вопрос"), KeyboardButton(text="Удалить вопрос") , KeyboardButton(text="Анализ посещаемости") , KeyboardButton(text="Просмотр отзывов")  ],
            ],
            resize_keyboard=True
        )

        await message.answer('Вы успешно вошли в админ панель Автопоезда "Россия - моя история".'
                             ' В данный момент вы можете добавить или удалить вопросы по викторине '
                             'Анализировать посещаемость и интересы и просматривать отзывы', reply_markup=admin_menu)
        await state.clear()
        aproved_admins_session.append(user_id)
    else:
        await message.answer('Извинити видимо вы не тот самый!')
        await state.clear()


# Добавление вопроса
@router.message(lambda msg: msg.text == "Добавить вопрос")
async def add_question_handler(message: types.Message, state: FSMContext):
    if message.from_user.id in aproved_admins_session:
        await message.answer(
            "Введите новый вопрос в формате:\n\nВопрос;Вариант1,Вариант2,Вариант3,Вариант4;Правильный вариант")
        await state.set_state(QuizAdminState.adding_question)
    else:
        await message.answer('У вас нет доступа пожалуйста войдите в админ панель')


@router.message(QuizAdminState.adding_question)
async def save_question_handler(message: types.Message, state: FSMContext):

    try:
        # Парсим данные
        parts = message.text.split(";")
        question_text = parts[0].strip()
        options = parts[1].strip().split(",")
        correct_answer = parts[2].strip()

        if len(options) != 4:
            await message.answer("Ошибка: Укажите ровно 4 варианта ответов через запятую!")
            return

        if correct_answer not in options:
            await message.answer("Ошибка: Правильный ответ должен быть одним из вариантов!")
            return

        # Добавляем новый вопрос в список
        quiz_questions.append({"question": question_text, "options": options, "correct": correct_answer})
        save_quiz()
        await message.answer("Вопрос успешно добавлен!")
    except (IndexError, ValueError):
        await message.answer("Ошибка: Неверный формат. Попробуйте снова.")
    finally:
        await state.clear()


# Удаление вопроса
@router.message(lambda msg: msg.text == "Удалить вопрос")
async def delete_question_handler(message: types.Message):
    if not quiz_questions:
        await message.answer("Нет вопросов для удаления.")
        return

    if message.from_user.id not in aproved_admins_session:
        await message.answer('У вас нет доступа пожалуйста войдите в админ панель')
        return
    buttons = InlineKeyboardBuilder()
    for i, question in enumerate(quiz_questions):
        butt = InlineKeyboardButton(text=question["question"], callback_data=f"delete_{i}")
        buttons.row(butt)

    await message.answer("Выберите вопрос для удаления:", reply_markup=buttons.as_markup())


@router.callback_query(lambda call: call.data.startswith("delete_"))
async def delete_question_callback(callback: types.CallbackQuery):
    question_index = int(callback.data.split("_")[1])

    # Удаляем вопрос
    deleted_question = quiz_questions.pop(question_index)
    save_quiz()
    await callback.message.delete()
    await callback.message.answer(f"Вопрос удален:\t{deleted_question['question']}")
    await callback.answer()


@router.message(lambda msg: msg.text == "Анализ посещаемости")
async def add_question_handler(message: types.Message, state: FSMContext):
    if message.from_user.id in aproved_admins_session:
        await message.answer(
            f"Наш Автопоезд успело посетить уже {len(list(users_data))} человек"
            f"\n из них {sum(1 for user in users_data.values() if user['feedback_done'])} "
            f"Оставило отзыв и {sum(1 for user in users_data.values() if user['quiz_done'])} Прошло квиз")

    else:
        await message.answer('У вас нет доступа пожалуйста войдите в админ панель')


@router.message(lambda msg: msg.text == "Просмотр отзывов")
async def add_question_handler(message: types.Message, state: FSMContext):
    if message.from_user.id in aproved_admins_session:
        for user_id, data in users_data.items():
            chat = await bot.get_chat(user_id)
            username = chat.username if chat.username else f"{chat.first_name} {chat.last_name}"
            feedback_data = data.get('feedback_data', 'N/A')
            feedback_message = data.get('feedback_message', 'N/A')
            await message.answer(f"User: {username}\n - Вагончик понравился: {feedback_data}\n - Коментарий: {feedback_message}")
    else:

        await message.answer('У вас нет доступа пожалуйста войдите в админ панель')
#-- Админ функционал end --#


# Event реакции на обычное сообщение
@router.message(lambda msg: msg.text != "admin")
async def repeat_all_messages(message):
    await bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAKaYWdclnlNQQ7sCsKMnpANtyeE1kLKAAIaAAO3ZSIaQKmaSci8iFo2BA")
    #await bot.send_sticker(message.chat.id ,"CAACAgIAAxkBAAEMJdhmShoZVhMZzqpahLq55enAnOMhBwACkBMAAhRaKUg1Auhtf0w3QDUE")
    await bot.send_message(message.chat.id, "Это конечно не моё дело , но могли бы использовать команды пожалуйста?")


# --- Запуск
if __name__ == "__main__":
    import asyncio
    from aiogram.fsm.storage.memory import MemoryStorage

    dp.fsm.storage = MemoryStorage()  # Хранилище FSM
    asyncio.run(dp.start_polling(bot))

# pip install -U g4f[all]
# pip install aiogram
