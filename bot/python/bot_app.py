from asyncio import set_event_loop, new_event_loop
from datetime import datetime, time
import pytz
from telegram.ext import Updater, CommandHandler, CallbackContext
import requests
import telebot
from telebot import types
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from flask import Flask, request

bot = telebot.TeleBot('6609893395:AAEVle1CG-rV879l36p-cC7JUCsyJ8JIvho')
user_state = {}
loggedUser = {}

app = Flask(__name__)


@bot.message_handler(commands=['start'])
def handle_start(message):
    # Получение информации о текущем пользователе
    chat_id = message.chat.id

    if chat_id not in user_state:
        user_state[chat_id] = {'git_id': None, 'role': None, 'username': "", 'group': ""}

    st = user_state[chat_id]
    user_exists = st['git_id'] is not None

    if user_exists:
        if st['username'] != "" or st['role'] != 'student':
            if st['group'] != "" or st['role'] != 'student':

                if st['role'] == 'student':
                    markup_start = types.InlineKeyboardMarkup()
                    btn1 = types.InlineKeyboardButton('Где следующая пара?', callback_data='where_next_class')
                    btn2 = types.InlineKeyboardButton('Расписание на сегодня', callback_data='today')
                    markup_start.row(btn1, btn2)
                    btn3 = types.InlineKeyboardButton('Где преподаватель?', callback_data='where_teacher')
                    btn4 = types.InlineKeyboardButton('Расписание на завтра', callback_data='tomorrow')
                    markup_start.row(btn3, btn4)
                    btn5 = types.InlineKeyboardButton('Когда экзамен?', callback_data='when_exam')
                    btn6 = types.InlineKeyboardButton('Расписание по дням недели', callback_data='start_week')
                    markup_start.row(btn5, btn6)

                    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}, вот мои команды',
                                     reply_markup=markup_start)

                elif st['role'] == 'teacher':
                    markup_start = types.InlineKeyboardMarkup()
                    btn1 = types.InlineKeyboardButton('Где следующая пара?', callback_data='where_next_class')
                    btn2 = types.InlineKeyboardButton('Расписание на сегодня', callback_data='today')
                    markup_start.row(btn1, btn2)
                    btn3 = types.InlineKeyboardButton('Где группа/подгруппа?',
                                                      callback_data='start_where_group_teacher')
                    btn4 = types.InlineKeyboardButton('Расписание на завтра', callback_data='tomorrow')
                    markup_start.row(btn3, btn4)
                    btn5 = types.InlineKeyboardButton('Оставить комментарий', callback_data='comment')
                    btn6 = types.InlineKeyboardButton('Расписание по дням недели', callback_data='start_week')
                    markup_start.row(btn5, btn6)

                    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}',
                                     reply_markup=markup_start)

                if st['role'] == 'admin':
                    markup_start = types.InlineKeyboardMarkup()
                    btn1 = types.InlineKeyboardButton('Начать сеанс администрирования', callback_data='start_admin')
                    markup_start.row(btn1)
                    bot.send_message(message.chat.id,
                                     "Нажмите, чтобы получить ссылку для перехода в панель администратора",
                                     reply_markup=markup_start)

            else:
                bot.send_message(message.chat.id, 'Введите вашу группу (прим. ПИ-б-о-232(2) ).')
        else:
            bot.send_message(message.chat.id, 'Чтобы продолжить, введите ФИО.')

    # Если пользователя не существует, делаем запрос на авторизацию
    else:

        bot.send_message(message.chat.id, 'Привет! Я готов помочь тебе, если ты заблудился в универе.')

        url = f"http://localhost:8080/auth?chat_id={chat_id}"
        response = requests.get(url)

        if response.status_code == 200:
            bot.send_message(message.chat.id, response.text)

        else:
            em_cancel = u'\U0000274C'
            bot.send_message(message.chat.id, em_cancel + 'Ошибка при авторизации')


def register_confirm(data):

    chat_id = int(data['chat_id'])

    em_accept = u'\U00002705'
    bot.send_message(chat_id, em_accept + " Вы успешно авторизовались!")
    # Добавляем значения в состояние пользователя
    user_state[chat_id]['git_id'] = data["github_id"]
    user_state[chat_id]['role'] = data["role"]
    user_state[chat_id]['username'] = data["username"]
    user_state[chat_id]['group'] = data["group"]

    if user_state[chat_id]['role'] != 'student' or data["username"] != "":
        bot.send_message(chat_id, 'Чтобы продолжить, нажмите /start')
    else:
        bot.send_message(chat_id, 'Чтобы продолжить, введите ФИО.')


# Пользователь вводит данные (ФИО и группу)
@bot.message_handler(func=lambda message: message.chat.id in user_state)
def handle_text_message(message):
    state = user_state[message.chat.id]

    if 'awaiting_input' in state and state['awaiting_input']:
        text = message.text

        url = f"http://localhost:8080/schedule"
        response = requests.post(url, data={'git_id': state['git_id'], 'action': 'comment'})

        if response.status_code == 200:
            url = f"http://localhost:8083/comment"
            res = requests.post(url, data={'token': response.text, 'line': text, 'action': 'comment'})
            bot.send_message(message.chat.id, 'Комментарий добавлен')
            del state['awaiting_input']
        else:
            bot.send_message(message.chat.id, response.text)



    if state['role'] == 'student':
        # Ввод ФИО
        if state['username'] is None and message.text != '/help' and message.text != '/logout':
            state['username'] = message.text
            bot.reply_to(message, 'Введите вашу группу (прим. ПИ-б-о-232(2) )')

        # Ввод группы
        elif state['group'] is None and message.text != '/help' and message.text != '/logout':
            state['group'] = message.text

            url = f"http://localhost:8080/userdata"
            data = {'username': state['username'], 'group': state['group'], 'git_id': state['git_id']}
            response = requests.post(url, data=data)

            if response.status_code == 200:
                bot.send_message(message.chat.id, "Регистрация завершена, для продолжения нажмите /start")

    # Выход
    if message.text == '/logout':
        del user_state[message.chat.id]
        bot.send_message(message.chat.id, 'Вы успешно вышли из системы')

    # Инструкция
    elif message.text == '/help':
        text = '<b>Бот</b> создан для того, чтобы ученики могли удобно воспользоваться расписанием учебных занятий'
        bot.send_message(message.chat.id, text, parse_mode='html')


# Запрос на получение расписания
@bot.callback_query_handler(func=lambda callback: True)
def callback_handler(callback):
    state = user_state[callback.message.chat.id]

    # Начало сеанса администрирования
    if callback.data == 'start_admin':
        url = f"http://localhost:8080/admin"
        response = requests.post(url, data={'git_id': state['git_id']})

        if response.status_code == 200:
            url = f"http://localhost:8082/start-admin"
            res = requests.post(url, data={'data': response.text})
            link = f'<a href="{res.text}">Ссылка на панель администратора</a>'
            bot.send_message(callback.message.chat.id, link, parse_mode='html', disable_web_page_preview=False)
        else:
            bot.send_message(callback.message.chat.id, response.text)

    # Оставление комментария к паре
    elif callback.data == 'comment':
        bot.send_message(callback.message.chat.id, 'Введите комментарий (прим. - Нечетная неделя,ПИ-б-о 232(2),ВТ,3,<текст комментария>')
        state['awaiting_input'] = True

    elif callback.data == 'start_week':
        markup_weak = types.InlineKeyboardMarkup()
        mon = types.InlineKeyboardButton('Понедельник', callback_data='monday')
        tue = types.InlineKeyboardButton('Вторник', callback_data='tuesday')
        markup_weak.row(mon, tue)
        wed = types.InlineKeyboardButton('Среда', callback_data='wednesday')
        thur = types.InlineKeyboardButton('Четверг', callback_data='thursday')
        markup_weak.row(wed, thur)
        fri = types.InlineKeyboardButton('Пятница', callback_data='friday')
        markup_weak.row(fri)

        bot.send_message(callback.message.chat.id, 'Выберите день недели', reply_markup=markup_weak)

    elif callback.data == 'where_teacher':
        markup_choose_sub = types.InlineKeyboardMarkup()
        ocg = types.InlineKeyboardButton('Основы цифровой граммотности', callback_data='ocg')
        markup_choose_sub.row(ocg)
        prog = types.InlineKeyboardButton('Алгоритмитизация и программирование', callback_data='pia')
        markup_choose_sub.row(prog)
        math = types.InlineKeyboardButton('Высшая математика', callback_data='vm')
        markup_choose_sub.row(math)
        siaod = types.InlineKeyboardButton('СиАОД', callback_data='siaod')
        markup_choose_sub.row(siaod)
        history = types.InlineKeyboardButton('История России', callback_data='rushis')
        markup_choose_sub.row(history)
        org = types.InlineKeyboardButton('ОРГ', callback_data='org')
        markup_choose_sub.row(org)
        english = types.InlineKeyboardButton("Английский язык", callback_data='eng')
        markup_choose_sub.row(english)
        communication = types.InlineKeyboardButton("Деловая коммуникация", callback_data='dkirrk')
        markup_choose_sub.row(communication)

        bot.send_message(callback.message.chat.id, 'Выберите предмет', reply_markup=markup_choose_sub)

    # Получение информации о расписании
    else:
        url = f"http://localhost:8080/schedule"
        response = requests.post(url, data={'git_id': state['git_id'], 'action': callback.data})

        if response.status_code == 200:
            url = f"http://localhost:8083/get-schedule"
            res = requests.post(url, data={'token': response.text, 'action': callback.data})
            bot.send_message(callback.message.chat.id, res.text)
        else:
            bot.send_message(callback.message.chat.id, response.text)


# Инструкция
@bot.message_handler(commands=['help'])
def start(message):
    text = '<b>Бот</b> создан для того, чтобы уче+ники могли удобно воспользоваться расписанием учебных занятий'
    bot.send_message(message.chat.id, text, parse_mode='html')


# Выход из системы
@bot.message_handler(commands=['logout'])
def handle_logout(message):
    del user_state[message.chat.id]
    bot.send_message(message.chat.id, 'Вы успешно вышли из системы')


# Запуск приложения
def run():
    try:
        bot.infinity_polling()
        set_event_loop(new_event_loop())
    except Exception as ex:
        print(ex)


