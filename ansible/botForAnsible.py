#!/usr/bin/python3
import logging
import re
import os
import urllib3
import urllib
from telegram.ext import CallbackContext
from dotenv import load_dotenv
import paramiko
import socket
import psycopg2

import matplotlib



from telegram import Update, ForceReply, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler



load_dotenv()
TOKEN = os.getenv('TOKEN')
RM_HOST = os.getenv('RM_HOST')
RM_PORT = int(os.getenv('RM_PORT'))
RM_USER = os.getenv('RM_USER')
RM_PASSWORD = os.getenv('RM_PASSWORD')

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_DATABASE = os.getenv('DB_DATABASE')
DB_REPL_USER = os.getenv('DB_REPL_USER')
DB_REPL_PASSWORD = os.getenv('DB_REPL_PASSWORD')
DB_REPL_HOST = os.getenv('DB_REPL_HOST')
DB_REPL_PORT = os.getenv('DB_REPL_PORT')
DB_REPL_SSH_USER = os.getenv('DB_REPL_SSH_USER')

LOG_FILE_PATH = '/var/log/postgresql/postgresql-15-main.log'

print(DB_PASSWORD)

VERIFY_PASSWORD = 1
FIND_EMAIL = 1
GET_RELEASE = 1
LIST_PACKAGES, SEARCH_PACKAGE = range(2)
LIST_SERVICES, SELECT_SERVICE = range(2)
REQUEST_TEXT, CONFIRM_PHONE, CONFIRM_EMAIL = range(3)


# Подключаем логирование
logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name}!')


def helpCommand(update: Update, context):
    update.message.reply_text('Help!')

def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')

    return 'findPhoneNumbers'

def findPhoneNumbers(update: Update, context: CallbackContext):
    user_input = update.message.text  # Получаем текст, содержащий(или нет) номера телефонов

    phoneNumRegex = re.compile(r'''
        (?:\+7|8)           # Первая часть: +7 или 8
        \s?                 # Необязательный пробел
        \(?\d{3}\)?         # Код оператора (XXX), может быть в скобках
        [\s\-]?             # Разделитель: пробел или дефис
        \d{3}               # Следующие три цифры
        [\s\-]?             # Разделитель: пробел или дефис
        \d{2}               # Следующие две цифры
        [\s\-]?             # Разделитель: пробел или дефис
        \d{2}               # Последние две цифры
    ''', re.VERBOSE)

    phoneNumberList = phoneNumRegex.findall(user_input)  # Ищем номера телефонов

    if not phoneNumberList:  # Обрабатываем случай, когда номеров телефонов нет
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END  # Завершаем работу обработчика диалога

    phoneNumbers = ''  # Создаем строку, в которую будем записывать номера телефонов
    for i in range(len(phoneNumberList)):
        phoneNumbers += f'{i+1}. {phoneNumberList[i]}\n'  # Записываем очередной номер

    update.message.reply_text(phoneNumbers)  # Отправляем сообщение пользователю
    context.user_data['phone_numbers'] = phoneNumberList

    reply_keyboard = [['Записать', 'Отменить']]
    update.message.reply_text(
        'Хотите записать найденные номера телефонов в базу данных?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return CONFIRM_PHONE

def confirm_phone(update: Update, context: CallbackContext):
    if update.message.text == 'Записать':
        phone_numbers = context.user_data.get('phone_numbers')
        try:
            # Подключаемся к базе данных
            conn = psycopg2.connect(
                dbname=DB_DATABASE,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
            cursor = conn.cursor()

            # Вставляем номера телефонов в таблицу phone
            for phone in phone_numbers:
                cursor.execute("INSERT INTO phone (phonenum) VALUES (%s)", (phone,))

            conn.commit()
            cursor.close()
            conn.close()
            update.message.reply_text('Номера телефонов успешно записаны в базу данных.')
        except Exception as e:
            update.message.reply_text(f'Ошибка при записи номеров телефонов: {e}')
    else:
        update.message.reply_text('Запись номеров телефонов отменена.')

    return ConversationHandler.END



def find_email_command(update: Update, context: CallbackContext):
    update.message.reply_text('Введите текст для поиска email-адресов:') 
    return 'find_email'

def find_email(update: Update, context: CallbackContext):
    user_input = update.message.text  # Получаем текст от пользователя

    # Регулярное выражение для поиска email-адресов
    email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

    # Ищем email-адреса в тексте
    email_list = email_regex.findall(user_input)

    if not email_list:  # Обрабатываем случай, когда email-адресов нет
        update.message.reply_text('Email-адреса не найдены.')
        return ConversationHandler.END  # Завершаем работу обработчика диалога

    email_str = '\n'.join(email_list)  # Создаем строку с найденными email-адресами
    update.message.reply_text(f'Найденные email-адреса:\n{email_str}')
    context.user_data['emails'] = email_list

    reply_keyboard = [['Записать', 'Отменить']]
    update.message.reply_text(
        'Хотите записать найденные email-адреса в базу данных?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return CONFIRM_EMAIL

def confirm_email(update: Update, context: CallbackContext):
    if update.message.text == 'Записать':
        emails = context.user_data.get('emails')
        try:
            # Подключаемся к базе данных
            conn = psycopg2.connect(
                dbname=DB_DATABASE,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
            cursor = conn.cursor()

            # Вставляем email-адреса в таблицу mails
            for email in emails:
                cursor.execute("INSERT INTO mails (mail) VALUES (%s)", (email,))

            conn.commit()
            cursor.close()
            conn.close()
            update.message.reply_text('Email-адреса успешно записаны в базу данных.')
        except Exception as e:
            update.message.reply_text(f'Ошибка при записи email-адресов: {e}')
    else:
        update.message.reply_text('Запись email-адресов отменена.')

    return ConversationHandler.END


def verify_password_command(update: Update, context: CallbackContext):
    # Отправляем сообщение пользователю с просьбой ввести пароль
    update.message.reply_text('Введите пароль для проверки:')
    # Переходим в состояние ожидания пароля
    return VERIFY_PASSWORD

def verify_password(update: Update, context: CallbackContext):
    user_input = update.message.text  # Получаем пароль от пользователя

    # Регулярное выражение для проверки сложности пароля
    password_regex = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')

    # Проверяем, соответствует ли пароль требованиям
    if password_regex.match(user_input):
        update.message.reply_text('Пароль сложный')
    else:
        update.message.reply_text('Пароль простой')

    # Завершаем разговор
    return ConversationHandler.END

def get_release(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения информации о релизе системы...')
        # Выполняем команду для получения информации о релизе системы
        _, stdout, stderr = ssh.exec_command('lsb_release -a')
        release_info = stdout.read().decode()

        # Отправляем информацию о релизе пользователю
        update.message.reply_text(f'Информация о релизе системы:\n{release_info}')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации о релизе системы: {e}')

def get_uname(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения информации о системе...')
        # Выполняем команду для получения информации о системе
        _, stdout, stderr = ssh.exec_command('uname -a')
        uname_info = stdout.read().decode()

        # Отправляем информацию о системе пользователю
        update.message.reply_text(f'Информация о системе:\n{uname_info}')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации о системе: {e}')

def get_uptime(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения информации о времени работы системы...')
        # Выполняем команду для получения информации о времени работы системы
        _, stdout, stderr = ssh.exec_command('uptime')
        uptime_info = stdout.read().decode()

        # Отправляем информацию о времени работы системы пользователю
        update.message.reply_text(f'Информация о времени работы системы:\n{uptime_info}')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации о времени работы системы: {e}')

def get_df(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения информации о состоянии файловой системы...')
        # Выполняем команду для получения информации о состоянии файловой системы
        _, stdout, stderr = ssh.exec_command('df -h')
        df_info = stdout.read().decode()

        # Отправляем информацию о состоянии файловой системы пользователю
        update.message.reply_text(f'Информация о состоянии файловой системы:\n{df_info}')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации о состоянии файловой системы: {e}')


def get_free(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения информации о состоянии оперативной памяти...')
        # Выполняем команду для получения информации о состоянии оперативной памяти
        _, stdout, stderr = ssh.exec_command('free -h')
        free_info = stdout.read().decode()

        # Отправляем информацию о состоянии оперативной памяти пользователю
        update.message.reply_text(f'Информация о состоянии оперативной памяти:\n{free_info}')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации о состоянии оперативной памяти: {e}')

def get_mpstat(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения информации о производительности системы...')
        # Выполняем команду для получения информации о производительности системы
        _, stdout, stderr = ssh.exec_command('mpstat')
        mpstat_info = stdout.read().decode()

        # Отправляем информацию о производительности системы пользователю
        update.message.reply_text(f'Информация о производительности системы:\n{mpstat_info}')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации о производительности системы: {e}')


def get_w(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения информации о работающих пользователях...')
        # Выполняем команду для получения информации о работающих пользователях
        _, stdout, stderr = ssh.exec_command('w')
        w_info = stdout.read().decode()

        # Отправляем информацию о работающих пользователях пользователю
        update.message.reply_text(f'Информация о работающих пользователях:\n{w_info}')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации о работающих пользователях: {e}')

def get_auths(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения информации о последних 10 входах в систему...')
        # Выполняем команду для получения информации о последних 10 входах в систему
        _, stdout, stderr = ssh.exec_command('last -n 10')
        auths_info = stdout.read().decode()

        # Отправляем информацию о последних 10 входах в систему пользователю
        update.message.reply_text(f'Информация о последних 10 входах в систему:\n{auths_info}')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации о последних 10 входах в систему: {e}')

def get_critical(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения информации о последних 5 критических событиях...')
        # Выполняем команду для получения информации о последних 5 критических событиях
        _, stdout, stderr = ssh.exec_command('journalctl -p crit -n 5')
        critical_info = stdout.read().decode()

        # Отправляем информацию о последних 5 критических событиях пользователю
        update.message.reply_text(f'Информация о последних 5 критических событиях:\n{critical_info}')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации о последних 5 критических событиях: {e}')

def send_chunked_message(update: Update, message: str, chunk_size: int = 4096):
    """Отправляет длинное сообщение частями"""
    for i in range(0, len(message), chunk_size):
        update.message.reply_text(message[i:i+chunk_size])

def get_ps(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения информации о запущенных процессах...')
        # Выполняем команду для получения информации о запущенных процессах
        _, stdout, stderr = ssh.exec_command('ps aux')
        ps_info = stdout.read().decode()

        # Отправляем информацию о запущенных процессах пользователю частями
        send_chunked_message(update, f'Информация о запущенных процессах:\n{ps_info}')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации о запущенных процессах: {e}')

def get_ss(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения информации об используемых портах...')
        # Выполняем команду для получения информации об используемых портах
        _, stdout, stderr = ssh.exec_command('ss -tuln')
        ss_info = stdout.read().decode()

        # Отправляем информацию об используемых портах пользователю частями
        send_chunked_message(update, f'Информация об используемых портах:\n{ss_info}')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации об используемых портах: {e}')

def start(update: Update, context: CallbackContext):
    reply_keyboard = [['Вывести все пакеты', 'Найти пакет']]
    update.message.reply_text(
        'Выберите действие:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return LIST_PACKAGES

def start(update: Update, context: CallbackContext):
    reply_keyboard = [['Вывести все сервисы', 'Выбрать сервис']]
    update.message.reply_text(
        'Выберите действие:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return LIST_SERVICES

def list_packages(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения информации об установленных пакетах...')
        # Выполняем команду для получения информации об установленных пакетах
        _, stdout, stderr = ssh.exec_command('dpkg -l')
        apt_list_info = stdout.read().decode()

        # Отправляем информацию об установленных пакетах пользователю частями
        send_chunked_message(update, f'Информация об установленных пакетах:\n{apt_list_info}')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации об установленных пакетах: {e}')

    return ConversationHandler.END

def search_package(update: Update, context: CallbackContext):
    update.message.reply_text('Введите название пакета для поиска:')
    return SEARCH_PACKAGE

def get_package_info(update: Update, context: CallbackContext):
    package_name = update.message.text
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text(f'Выполняю команду для получения информации о пакете {package_name}...')
        # Выполняем команду для получения информации о пакете
        _, stdout, stderr = ssh.exec_command(f'dpkg -s {package_name}')
        package_info = stdout.read().decode()

        if package_info:
            # Отправляем информацию о пакете пользователю
            send_chunked_message(update, f'Информация о пакете {package_name}:\n{package_info}')
        else:
            update.message.reply_text(f'Пакет {package_name} не найден.')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации о пакете {package_name}: {e}')

    return ConversationHandler.END

def list_services(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения информации о запущенных сервисах...')
        # Выполняем команду для получения информации о запущенных сервисах
        _, stdout, stderr = ssh.exec_command('systemctl list-units --type=service --state=running')
        services_info = stdout.read().decode()

        # Отправляем информацию о запущенных сервисах пользователю частями
        send_chunked_message(update, f'Информация о запущенных сервисах:\n{services_info}')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации о запущенных сервисах: {e}')

    return ConversationHandler.END

def select_service(update: Update, context: CallbackContext):
    update.message.reply_text('Введите название сервиса для получения информации:')
    return SELECT_SERVICE

def get_service_info(update: Update, context: CallbackContext):
    service_name = update.message.text
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(RM_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text(f'Выполняю команду для получения информации о сервисе {service_name}...')
        # Выполняем команду для получения информации о сервисе
        _, stdout, stderr = ssh.exec_command(f'systemctl status {service_name}')
        service_info = stdout.read().decode()

        if service_info:
            # Отправляем информацию о сервисе пользователю
            send_chunked_message(update, f'Информация о сервисе {service_name}:\n{service_info}')
        else:
            update.message.reply_text(f'Сервис {service_name} не найден.')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении информации о сервисе {service_name}: {e}')

    return ConversationHandler.END

def get_repl_logs(update: Update, context: CallbackContext):
    try:
        update.message.reply_text('Проверяю доступность хоста...')
        # Проверяем доступность хоста
        socket.gethostbyname(DB_REPL_HOST)
        update.message.reply_text('Хост доступен.')

        update.message.reply_text('Устанавливаю SSH-соединение...')
        # Создаем SSH-клиент
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(DB_REPL_HOST, port=DB_REPL_PORT, username=DB_REPL_SSH_USER, password=RM_PASSWORD)
        update.message.reply_text('SSH-соединение установлено.')

        update.message.reply_text('Выполняю команду для получения логов о репликации...')
        # Выполняем команду для получения последних строк из лог-файла и фильтруем их
        command = f"grep -E 'replication|startup|shutdown|connection' {LOG_FILE_PATH}"
        _, stdout, stderr = ssh.exec_command(command)
        log_info = stdout.read().decode()

        if log_info:
            # Отправляем информацию о логах пользователю частями
            send_chunked_message(update, f'Логи о репликации:\n{log_info}')
        else:
            update.message.reply_text('Логи о репликации не найдены.')

        # Закрываем SSH-соединение
        ssh.close()
        update.message.reply_text('SSH-соединение закрыто.')
    except socket.gaierror:
        update.message.reply_text('Ошибка: Не удается разрешить имя хоста. Проверьте правильность имени хоста или IP-адреса.')
    except paramiko.SSHException as sshException:
        update.message.reply_text(f'Ошибка SSH: {sshException}')
    except Exception as e:
        update.message.reply_text(f'Ошибка при получении логов о репликации: {e}')

def get_emails(update: Update, context: CallbackContext):
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(
            dbname=DB_DATABASE,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        # Выполняем запрос для получения email-адресов
        cursor.execute("SELECT mail FROM mails")
        emails = cursor.fetchall()

        # Формируем сообщение с email-адресами
        email_list = "\n".join([email[0] for email in emails])
        message = f"Email-адреса:\n{email_list}"

        # Отправляем сообщение пользователю частями
        send_chunked_message(update, message)

        # Закрываем соединение с базой данных
        cursor.close()
        conn.close()
    except Exception as e:
        update.message.reply_text(f"Ошибка при получении email-адресов: {e}")

def get_phone_numbers(update: Update, context: CallbackContext):
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(
            dbname=DB_DATABASE,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        # Выполняем запрос для получения номеров телефонов
        cursor.execute("SELECT phonenum FROM phone")
        phone_numbers = cursor.fetchall()

        # Формируем сообщение с номерами телефонов
        phone_list = "\n".join([phone[0] for phone in phone_numbers])
        message = f"Номера телефонов:\n{phone_list}"

        # Отправляем сообщение пользователю частями
        send_chunked_message(update, message)

        # Закрываем соединение с базой данных
        cursor.close()
        conn.close()
    except Exception as e:
        update.message.reply_text(f"Ошибка при получении номеров телефонов: {e}")




def echo(update: Update, context):
    update.message.reply_text(update.message.text)

def main():
    updater = Updater(TOKEN, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher

    # Обработчик диалога
    

    phone_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', findPhoneNumbersCommand)],
        states={
            'findPhoneNumbers': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            CONFIRM_PHONE: [MessageHandler(Filters.regex('^(Записать|Отменить)$'), confirm_phone)]
        },
        fallbacks=[]
    )


    email_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('find_email', find_email_command)],
        states={
            'find_email': [MessageHandler(Filters.text & ~Filters.command, find_email)],
            CONFIRM_EMAIL: [MessageHandler(Filters.regex('^(Записать|Отменить)$'), confirm_email)]
        },
        fallbacks=[]
    )

     # Создаем ConversationHandler для проверки пароля
    conv_handler_verify_password = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verify_password_command)],
        states={
            VERIFY_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, verify_password)],
        },
        fallbacks=[]
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', start)],
        states={
            LIST_PACKAGES: [
                MessageHandler(Filters.regex('^Вывести все пакеты$'), list_packages),
                MessageHandler(Filters.regex('^Найти пакет$'), search_package)
            ],
            SEARCH_PACKAGE: [MessageHandler(Filters.text & ~Filters.command, get_package_info)]
        },
        fallbacks=[]
    )

    conv_handler_service = ConversationHandler(
        entry_points=[CommandHandler('get_services', start)],
        states={
            LIST_SERVICES: [
                MessageHandler(Filters.regex('^Вывести все сервисы$'), list_services),
                MessageHandler(Filters.regex('^Выбрать сервис$'), select_service)
            ],
            SELECT_SERVICE: [MessageHandler(Filters.text & ~Filters.command, get_service_info)]
        },
        fallbacks=[]
    )


    # Регистрируем ConversationHandler в диспетчере
    dp.add_handler(conv_handler_verify_password)
		
	# Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))
    
		
	# Регистрируем обработчик текстовых сообщений
    #dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    # For Linux SSH
    dp.add_handler(CommandHandler('get_release', get_release))
    dp.add_handler(CommandHandler('get_uname', get_uname))
    dp.add_handler(CommandHandler('get_uptime', get_uptime))
    dp.add_handler(CommandHandler('get_df', get_df))
    dp.add_handler(CommandHandler('get_free', get_free))
    dp.add_handler(CommandHandler('get_mpstat', get_mpstat))
    dp.add_handler(CommandHandler('get_w', get_w))
    dp.add_handler(CommandHandler('get_auths', get_auths))
    dp.add_handler(CommandHandler('get_critical', get_critical))
    dp.add_handler(CommandHandler('get_ps', get_ps))
    dp.add_handler(CommandHandler('get_ss', get_ss))
    dp.add_handler(conv_handler)
    dp.add_handler(conv_handler_service)
    dp.add_handler(CommandHandler('get_repl_logs', get_repl_logs))
    # не ссш
    dp.add_handler(CommandHandler('get_emails', get_emails))
    dp.add_handler(email_conv_handler)

    dp.add_handler(CommandHandler('get_phone_numbers', get_phone_numbers))
    dp.add_handler(phone_conv_handler)


    


    











		
	# Запускаем бота
    updater.start_polling()

	# Останавливаем бота при нажатии Ctrl+C
    updater.idle()

if __name__ == '__main__':
    main()
