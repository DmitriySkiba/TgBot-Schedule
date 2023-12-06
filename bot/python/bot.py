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
                    btn6 = types.InlineKeyboardButton('Расписание по дням недели', callback_data='start_weak')
                    markup_start.row(btn5, btn6)

                    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}, вот мои команды',
                                     reply_markup=markup_start)

                elif st['role'] == 'teacher':
                    markup_start = types.InlineKeyboardMarkup()
                    btn1 = types.InlineKeyboardButton('Где следующая пара?', callback_data='start_where_teacher')
                    btn2 = types.InlineKeyboardButton('Расписание на сегодня', callback_data='start_today_teacher')
                    markup_start.row(btn1, btn2)
                    btn3 = types.InlineKeyboardButton('Где группа/подгруппа?',
                                                      callback_data='start_where_group_teacher')
                    btn4 = types.InlineKeyboardButton('Расписание на завтра', callback_data='start_tomm_teacher')
                    markup_start.row(btn3, btn4)
                    btn5 = types.InlineKeyboardButton('Оставить комментарий', callback_data='start_comment_teacher')
                    btn6 = types.InlineKeyboardButton('Расписание по дням недели', callback_data='start_weak_teacher')
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

            @app.route("/register", methods=['POST'])
            def register():
                data = request.get_json()

                em_accept = u'\U00002705'
                bot.send_message(message.chat.id, em_accept + " Вы успешно авторизовались!")
                # Добавляем значения в состояние пользователя
                user_state[message.chat.id]['git_id'] = data["github_id"]
                user_state[message.chat.id]['role'] = data["role"]
                user_state[message.chat.id]['username'] = data["username"]
                user_state[message.chat.id]['group'] = data["group"]

                if user_state[message.chat.id]['role'] != 'student' or data["username"] != "":
                    bot.send_message(message.chat.id, 'Чтобы продолжить, нажмите /start')
                else:
                    bot.send_message(message.chat.id, 'Чтобы продолжить, введите ФИО.')

                resp = {'message': 'Success'}
                return resp, 200

            if __name__ == '__main__':
                app.run(port=8081)
        else:
            em_cancel = u'\U0000274C'
            bot.send_message(message.chat.id, em_cancel + 'Ошибка при авторизации')


# Пользователь вводит данные (ФИО и группу)
@bot.message_handler(func=lambda message: message.chat.id in user_state)
def handle_text_message(message):
    state = user_state[message.chat.id]

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

    elif callback.data == 'start_weak':
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
    text = '<b>Бот</b> создан для того, чтобы ученики могли удобно воспользоваться расписанием учебных занятий'
    bot.send_message(message.chat.id, text, parse_mode='html')


# Выход из системы
@bot.message_handler(commands=['logout'])
def handle_logout(message):
    del user_state[message.chat.id]
    bot.send_message(message.chat.id, 'Вы успешно вышли из системы')


monday = []
tuesday = []
wednesday = []
thursday = []
friday = []
lesson_now = [monday] + [tuesday] + [wednesday] + [thursday] + [friday]
day_weak = datetime.now().weekday()  # считает по N-1

if id:  # СТУДЕНТ
    count_today = 0
    sub_today = []

    count_tomm = 0
    sub_tomm = []

    count_mon = 0
    count_tues = 0
    count_wedn = 0
    count_thur = 0
    count_fri = 0


    # Следущая пара
    @bot.callback_query_handler(func=lambda callback: True)
    def callback_handler(callback):
        if callback.data == 'start_where':
            moscow_tz = pytz.timezone('Europe/Moscow')
            current_time = datetime.now(moscow_tz).time()
            if 0 <= day_weak <= 4:
                if time(8, 0) <= current_time < time(9, 30):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас идет ' + lesson_now[day_weak][0] + ', конец в 9:50\n Следующая пара: ' +
                                     lesson_now[day_weak][1] + '\nКабинет:')
                elif time(9, 30) <= current_time < time(9, 50):
                    bot.send_message(callback.message.chat.id,
                                     'Перемена, начало второй пары в 9:50\nСледующая пара: ' + lesson_now[day_weak][
                                         1] + '\nКабинет:')
                elif time(9, 50) <= current_time < time(11, 20):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас идет ' + lesson_now[day_weak][1] + ', конец в 11:20\n Следующая пара: ' +
                                     lesson_now[day_weak][2] + '\nКабинет:')
                elif time(11, 20) <= current_time < time(11, 30):
                    bot.send_message(callback.message.chat.id,
                                     'Перемена, начало третьей пары в 11:30\n Следующая пара: ' + lesson_now[day_weak][
                                         2] + '\nКабинет:')
                elif time(11, 30) <= current_time < time(13, 0):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас идет ' + lesson_now[day_weak][2] + ', конец в 13:00\n Следующая пара: ' +
                                     lesson_now[day_weak][3] + '\nКабинет:')
                elif time(13, 0) <= current_time < time(13, 20):
                    bot.send_message(callback.message.chat.id,
                                     'Перемена, начало четвертой пары в 13:20\n Следующая пара: ' +
                                     lesson_now[day_weak][3] + '\nКабинет:')
                elif time(13, 20) <= current_time < time(14, 50):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас идет ' + lesson_now[day_weak][3] + ', конец в 14:50\n Следующая пара: ' +
                                     lesson_now[day_weak][4] + '\nКабинет:')
                elif time(14, 50) <= current_time < time(15, 00):
                    bot.send_message(callback.message.chat.id,
                                     'Перемена, начало четвертого в 15:00\n Следующая пара: ' + lesson_now[day_weak][
                                         4] + '\nКабинет:')
                elif time(15, 0) <= current_time < time(16, 30):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас идет ' + lesson_now[day_weak][4] + ', конец в 16:30\n Эта пара последняя')
                else:
                    bot.send_message(callback.message.chat.id, 'Занятий нет')
            else:
                bot.send_message(callback.message.chat.id, 'Сегодня выходной день, занятий нет')

        # Расписание на сегодня
        elif callback.data == 'start_today':
            message = f'Сегодня {count_today} пар:'
            for i in range(count_today):
                message += f'\n{i + 1}. {sub_today[i]}'
            bot.send_message(callback.message.chat.id, message)

        # Расписание на завтра
        elif callback.data == 'start_tomm':
            message = f'Сегодня {count_tomm} пар:'
            for i in range(count_tomm):
                message += f'\n{i + 1}. {sub_tomm[i]}'
            bot.send_message(callback.message.chat.id, message)

        # Расписание на неделю
        elif callback.data == 'start_weak':
            markup_weak = types.InlineKeyboardMarkup()
            Monday = types.InlineKeyboardButton('Понедельник', callback_data='monday')
            Tuesday = types.InlineKeyboardButton('Вторник', callback_data='tuesday')
            markup_weak.row(Monday, Tuesday)
            Wednesday = types.InlineKeyboardButton('Среда', callback_data='wednesday')
            Thursday = types.InlineKeyboardButton('Четверг', callback_data='thursday')
            markup_weak.row(Wednesday, Thursday)
            Friday = types.InlineKeyboardButton('Пятница', callback_data='friday')
            markup_weak.row(Friday)

            bot.send_message(callback.message.chat.id, 'Выбери день недели', reply_markup=markup_weak)

        # Расписание дни недели
        elif callback.data == 'monday':
            message = f'В понедельник {count_mon} пар:'
            for i in range(count_mon):
                message += f'\n{i + 1}. {monday[i]}'
            bot.send_message(callback.message.chat.id, message)

        elif callback.data == 'tuesday':
            message = f'Во вторник {count_tues} пар:'
            for i in range(count_tues):
                message += f'\n{i + 1}. {tuesday[i]}'
            bot.send_message(callback.message.chat.id, message)

        elif callback.data == 'wednesday':
            message = f'В среду {count_wedn} пар:'
            for i in range(count_wedn):
                message += f'\n{i + 1}. {wednesday[i]}'
            bot.send_message(callback.message.chat.id, message)

        elif callback.data == 'thursday':
            message = f'В четверг {count_thur} пар:'
            for i in range(count_thur):
                message += f'\n{i + 1}. {thursday[i]}'
            bot.send_message(callback.message.chat.id, message)

        elif callback.data == 'friday':
            message = f'В пятницу {count_fri} пар:'
            for i in range(count_fri):
                message += f'\n{i + 1}. {friday[i]}'
            bot.send_message(callback.message.chat.id, message)

        # Где преподаватель
        elif callback.data == 'start_teach_where':
            markup_choose_sub = types.InlineKeyboardMarkup()
            ocg = types.InlineKeyboardButton('Основы цифровой граммотности', callback_data='ocg')
            pia = types.InlineKeyboardButton('Алгоритмитизация и программирование', callback_data='pia')
            markup_choose_sub.row(ocg, pia)
            vm = types.InlineKeyboardButton('Высшая математика', callback_data='vm')
            siaod = types.InlineKeyboardButton('Алгоритмы обработки данных', callback_data='siaod')
            markup_choose_sub.row(vm, siaod)
            rushis = types.InlineKeyboardButton('История России', callback_data='rushis')
            org = types.InlineKeyboardButton('ОРГ', callback_data='org')
            markup_choose_sub.row(rushis, org)
            eng = types.InlineKeyboardButton("Английский язык", callback_data='eng')
            dkirrk = types.InlineKeyboardButton("Деловая коммуникация", callback_data='dkirrk')
            markup_choose_sub.row(eng, dkirrk)
            bot.send_message(callback.message.chat.id, 'Выберите предмет', reply_markup=markup_choose_sub)

        elif callback.data == 'ocg':
            em_ocg = u'\U0001F3AE'
            bot.send_message(callback.chat.id, em_ocg + "<b>Корниенко Андрей Юрьевич</b>\nКабинет: 8А\nКафедра: 310-А",
                             parse_mode='html')

        elif callback.data == 'pia':
            em_laptop = u'\U0001F4BB'
            bot.send_message(callback.message.chat.id,
                             f"{em_laptop}<b>Чабанов Владимир Викторович</b>\n\nКафедра: 310-А\nE-mail: chabanov.vv@cfuv.ru\nVK: https://vk.com/id444710087\n\n\n"
                             f"{em_laptop}<b>Зойкин Евгений Сергеевич</b>\n\nКафедра: 310-А\nE-mail: kimstudreport@mail.ru\n\n\n"
                             f"{em_laptop}<b>Завьялов Илья Владиславович</b>\n\nКафедра: 310-А\nE-mail: ilya.zavyalov0@gmail.com\nVK: https://vk.com/mrshurukan",
                             parse_mode='html')

        elif callback.data == 'vm':
            em_matan = u'\U00002795'
            bot.send_message(callback.message.chat.id, em_matan +
                             "<b>Смирнова Светлана Ивановна</b>\n\nКафедра: 402-В\nE-mail: smirnovasi.vv@cfuv.ru",
                             parse_mode='html')

        elif callback.data == 'siaod':
            em_table = u'\U0001F4CA'
            bot.send_message(callback.message.chat.id, em_table + "<b>Горская Ирина Юрьевна</b>\n\nКафедра: 310-А",
                             parse_mode='html')

        elif callback.data == 'rushis':
            em_history = u'\U000023F3'
            bot.send_message(callback.message.chat.id,
                             em_history + "<b>Дорофеев Денис Владимирович</b>\n\nКабинет: 411-В\n\n\n",
                             em_history + "<b>Непомнящий Андрей Анатольевич</b>\n\nКабинет: 209-А",
                             parse_mode='html')

        elif callback.data == 'org':
            em_org = u'\U0001F1F7'
            bot.send_message(callback.message.chat.id,
                             em_org + "<b>Екатерина Николаевна Клименко</b>\n\nКабинет: 406-В",
                             parse_mode='html')

        elif callback.data == 'eng':
            em_angl = u'\U0001F1EC'
            bot.send_message(callback.message.chat.id,
                             em_angl + "<b>Елена Шестакова Сергеевна</b>\n\nКабинет: 500-Б\n\n\n",
                             em_angl + "<b>Ермоленко Оксана Владимировна</b>\n\nКабинет: 531-Б",
                             parse_mode='html')

        elif callback.data == 'dkirrk':
            em_rech = u'\U0001F4D6'
            bot.send_message(callback.message.chat.id, em_rech + "<b>Рудницкая Людмила Ивановна</b>\n\nКабинет: 309-А",
                             parse_mode='html')

        elif callback.data == 'start_exm':
            bot.send_message(callback.message.chat.id,
                             "<b>Экзамен</b>\n\nЭкзамен состоиться в январе после каникул по заданным предметам. Если вы не знаете по каким предметам будут экзамены у вас в группе, рекомендуем обратиться к куратору ",
                             parse_mode='html')


elif id and id.get("status") == "teacher":  # УЧИТЕЛЬ
    count_today_t = 0
    sub_today_t = []

    count_tomm_t = 0
    sub_tomm_t = []

    count_mon_t = 0
    monday_t = []
    count_tues_t = 0
    tuesday_t = []
    count_wedn_t = 0
    wednesday_t = []
    count_thur_t = 0
    thursaday_t = []
    count_fri_t = 0
    friday_t = []

    lesson_now_t = [monday_t] + [tuesday_t] + [wednesday_t] + [thursaday_t] + [friday_t]
    day_weak = datetime.now().weekday()  # считает по N-1

    lesson_now_teacher = 0
    lesson_teacher = []
    comment = ""


    @bot.message_handler(commands=['start'])
    def start(message):
        markup_start = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Где следующая пара', callback_data='start_where_teacher')
        btn2 = types.InlineKeyboardButton('Расписание на сегодня', callback_data='start_today_teacher')
        markup_start.row(btn1, btn2)
        btn3 = types.InlineKeyboardButton('Расписание на завтра', callback_data='start_tomm_teacher')
        btn4 = types.InlineKeyboardButton('Расписание по дням недели', callback_data='start_weak_teacher')
        markup_start.row(btn3, btn4)
        btn5 = types.InlineKeyboardButton('Оставить комментарий', callback_data='start_comment_teacher')
        btn6 = types.InlineKeyboardButton('Где группа/подгруппа', callback_data='start_where_group_teacher')
        markup_start.row(btn5, btn6)

        bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}', reply_markup=markup_start)


    @bot.callback_query_handler(func=lambda callback: True)
    def callback_handler(callback):
        if callback.data == 'start_where_teacher':
            moscow_tz = pytz.timezone('Europe/Moscow')
            current_time = datetime.now(moscow_tz).time()
            if 0 <= day_weak <= 4:
                if time(8, 0) <= current_time < time(9, 30):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас идет ' + lesson_now_t[day_weak][0] + ', конец в 9:50\n Следующая пара: ' +
                                     lesson_now_t[day_weak][1] + '\nКабинет:')

                elif time(9, 30) <= current_time < time(9, 50):
                    bot.send_message(callback.message.chat.id,
                                     'Перемена, начало второй пары в 9:50\nСледующая пара: ' + lesson_now_t[day_weak][
                                         1] + '\nКабинет:')

                elif time(9, 50) <= current_time < time(11, 20):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас идет ' + lesson_now_t[day_weak][1] + ', конец в 11:20\n Следующая пара: ' +
                                     lesson_now_t[day_weak][2] + '\nКабинет:')

                elif time(11, 20) <= current_time < time(11, 30):
                    bot.send_message(callback.message.chat.id,
                                     'Перемена, начало третьей пары в 11:30\n Следующая пара: ' +
                                     lesson_now_t[day_weak][2] + '\nКабинет:')

                elif time(11, 30) <= current_time < time(13, 0):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас идет ' + lesson_now_t[day_weak][2] + ', конец в 13:00\n Следующая пара: ' +
                                     lesson_now_t[day_weak][3] + '\nКабинет:')

                elif time(13, 0) <= current_time < time(13, 20):
                    bot.send_message(callback.message.chat.id,
                                     'Перемена, начало четвертой пары в 13:20\n Следующая пара: ' +
                                     lesson_now_t[day_weak][3] + '\nКабинет:')

                elif time(13, 20) <= current_time < time(14, 50):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас идет ' + lesson_now_t[day_weak][3] + ', конец в 14:50\n Следующая пара: ' +
                                     lesson_now_t[day_weak][4] + '\nКабинет:')

                elif time(14, 50) <= current_time < time(15, 00):
                    bot.send_message(callback.message.chat.id,
                                     'Перемена, начало четвертого в 15:00\n Следующая пара: ' + lesson_now_t[day_weak][
                                         4] + '\nКабинет:')

                elif time(15, 0) <= current_time < time(16, 30):
                    bot.send_message(callback.chat.id, 'Сейчас идет ' + lesson_now_t[day_weak][
                        4] + ', конец в 16:30\n Эта пара последняя')

                else:
                    bot.send_message(callback.message.chat.id, 'Занятий нет')
            else:
                bot.send_message(callback.message.chat.id, 'Сегодня выходной день, занятий нет')


        # Расписание на сегодня
        elif callback.data == 'start_today_teacher':
            message = f'Сегодня {count_today_t} пар:'
            for i in range(count_today_t):
                message += f'\n{i + 1}. {sub_today_t[i]}'
            bot.send_message(callback.message.chat.id, message)


        # Расписание на завтра
        elif callback.data == 'start_tomm_teacher':
            message = f'Сегодня {count_tomm_t} пар:'
            for i in range(count_tomm_t):
                message += f'\n{i + 1}. {sub_tomm_t[i]}'
            bot.send_message(callback.message.chat.id, message)


        # Расписание на дни недели
        elif callback.data == 'start_weak_teacher':
            markup_weak = types.InlineKeyboardMarkup()
            Monday = types.InlineKeyboardButton('Понедельник', callback_data='monday_teacher')
            Tuesday = types.InlineKeyboardButton('Вторник', callback_data='tuesday_teacher')
            markup_weak.row(Monday, Tuesday)
            Wednesday = types.InlineKeyboardButton('Среда', callback_data='wednesday_teacher')
            Thursday = types.InlineKeyboardButton('Четверг', callback_data='thursday_teacher')
            markup_weak.row(Wednesday, Thursday)
            Friday = types.InlineKeyboardButton('Пятница', callback_data='friday_teacher')
            markup_weak.row(Friday)

            bot.send_message(callback.message.chat.id, 'Выберите день недели', reply_markup=markup_weak)

        elif callback.data == 'monday_teacher':
            message = f'В понедельник {count_mon_t} пар:'
            for i in range(count_mon_t):
                message += f'\n{i + 1}. {monday_t[i]}'
            bot.send_message(callback.message.chat.id, message)

        elif callback.data == 'tuesday_teacher':
            message = f'Во вторник {count_tues_t} пар:'
            for i in range(count_tues_t):
                message += f'\n{i + 1}. {tuesday_t[i]}'
            bot.send_message(callback.message.chat.id, message)

        elif callback.data == 'wednesday_teacher':
            message = f'В среду {count_wedn_t} пар:'
            for i in range(count_wedn_t):
                message += f'\n{i + 1}. {wednesday_t[i]}'
            bot.send_message(callback.message.chat.id, message)

        elif callback.data == 'thursday_teacher':
            message = f'В четверг {count_thur_t} пар:'
            for i in range(count_thur_t):
                message += f'\n{i + 1}. {thursaday_t[i]}'
            bot.send_message(callback.message.chat.id, message)

        elif callback.data == 'friday_teacher':
            message = f'В пятницу {count_fri_t} пар:'
            for i in range(count_fri_t):
                message += f'\n{i + 1}. {friday_t[i]}'
            bot.send_message(callback.message.chat.id, message)

        elif callback.data == 'start_comment_teacher':
            bot.send_message(callback.message.chat.id, "Введите комментарий, который хотите оставить")
            bot.register_next_step_handler(callback.message, get_comment)

        elif callback.data == 'start_where_group_teacher':
            moscow_tz = pytz.timezone('Europe/Moscow')  # повтор
            current_time = datetime.now(moscow_tz).time()  # повтор
            if 0 <= day_weak <= 4:
                if time(8, 0) <= current_time < time(9, 30):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас у группы ' + lesson_now[day_weak][0] + ', конец в 9:50\nКабинет:')

                elif time(9, 30) <= current_time < time(9, 50):
                    bot.send_message(callback.message.chat.id,
                                     'Перемена, начало второй пары в 9:50\nСледующая пара: ' + lesson_now[day_weak][
                                         1] + '\nКабинет:')

                elif time(9, 50) <= current_time < time(11, 20):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас у группы ' + lesson_now[day_weak][1] + ', конец в 11:20\nКабинет:')

                elif time(11, 20) <= current_time < time(11, 30):
                    bot.send_message(callback.message.chat.id,
                                     'Перемена, начало третьей пары в 11:30\n Следующая пара: ' + lesson_now[day_weak][
                                         2] + '\nКабинет:')

                elif time(11, 30) <= current_time < time(13, 0):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас у группы ' + lesson_now[day_weak][2] + ', конец в 13:00\nКабинет:')

                elif time(13, 0) <= current_time < time(13, 20):
                    bot.send_message(callback.message.chat.id,
                                     'Перемена, начало четвертой пары в 13:20\n Следующая пара: ' +
                                     lesson_now[day_weak][3] + '\nКабинет:')

                elif time(13, 20) <= current_time < time(14, 50):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас у группы ' + lesson_now[day_weak][3] + ', конец в 14:50\nКабинет:')

                elif time(14, 50) <= current_time < time(15, 00):
                    bot.send_message(callback.message.chat.id,
                                     'Перемена, начало четвертого в 15:00\n Следующая пара: ' + lesson_now[day_weak][
                                         4] + '\nКабинет:')

                elif time(15, 0) <= current_time < time(16, 30):
                    bot.send_message(callback.message.chat.id,
                                     'Сейчас у группы ' + lesson_now[day_weak][4] + ', конец в 16:30\nКабинет:')

                else:
                    bot.send_message(callback.message.chat.id, 'Занятий нет')
            else:
                bot.send_message(callback.message.chat.id, 'Сегодня выходной день, занятий нет')


    def get_comment(message):
        global comment  # Объявляем переменную comment как глобальную
        comment = message.text

bot.polling(none_stop=True)
