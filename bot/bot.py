import logging
import re
from pathlib import Path
import psycopg2
from psycopg2 import Error

import paramiko
import os

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from dotenv import load_dotenv

logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

token = os.getenv('TOKEN')

host = os.getenv('RM_HOST')
port = os.getenv('RM_PORT')
username = os.getenv('RM_USER')
password = os.getenv('RM_PASSWORD')

db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_database = os.getenv('DB_DATABASE')


def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name}!')
    return ConversationHandler.END


def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')

    return 'find_phone_number'


def findEmailCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска Email адресов: ')

    return 'find_email'


def verifyPasswordCommand(update: Update, context):
    update.message.reply_text('Введите проверяемый пароль: ')

    return 'verify_password'


def findPhoneNumbers(update, context):
    user_input = update.message.text

    regex_1 = re.compile(r'(?:\+7|8)\s?\(\d{3}\)\s?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b')
    regex_2 = re.compile(r'(?:\+7|8)[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b')

    context.user_data['phone_numbers'] = []
    phoneNumberList = []

    phoneNumberList.extend(regex_1.findall(user_input))
    phoneNumberList.extend(regex_2.findall(user_input))

    if not phoneNumberList:
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END

    phoneNumbers = ''
    for i, number in enumerate(phoneNumberList, start=1):
        phoneNumbers += f'{i}. {number}\n'

    update.message.reply_text(phoneNumbers)

    update.message.reply_text('Хотите сохранить эти номера в базе данных? (да/нет)')

    context.user_data['phone_numbers'] = phoneNumberList

    return 'save_phone_numbers'


def formatPhoneNumber(phone_number):
    digits = re.sub(r'\D', '', phone_number)

    formatted_number = re.sub(r'(\d{1})(\d{3})(\d{3})(\d{2})(\d{2})', r'8 (\2) \3-\4-\5', digits)

    return formatted_number


def savePhoneNumbers(update, context):
    user_input = update.message.text.lower()
    if user_input == 'да':
        conn = context.bot_data['db_conn']
        cursor = conn.cursor()
        try:
            existing_numbers = set()
            cursor.execute("SELECT phone_number FROM phone_numbers")
            for row in cursor.fetchall():
                existing_numbers.add(row[0])
            for number in context.user_data['phone_numbers']:
                formatted_number = formatPhoneNumber(number)
                cursor.execute("SELECT phone_number FROM phone_numbers WHERE phone_number = %s",
                               (formatted_number,))
                existing_number = cursor.fetchone()
                if formatted_number not in existing_numbers and existing_number is None:
                    cursor.execute("INSERT INTO phone_numbers (phone_number) VALUES (%s)", (formatted_number,))
            conn.commit()
            update.message.reply_text('Номера успешно сохранены в базе данных')
        except psycopg2.Error as e:
            update.message.reply_text('Ошибка при сохранении номеров в базе данных')
            logger.error(f"Error saving phone numbers: {e}")
            conn.rollback()
            return ConversationHandler.END
        finally:
            cursor.close()
            return ConversationHandler.END
    else:
        update.message.reply_text('Номера не сохранены')
        return ConversationHandler.END


def findEmail(update, context):
    user_input = update.message.text

    emailRegex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

    emailList = emailRegex.findall(user_input)
    context.user_data['emails'] = []

    if not emailList:
        update.message.reply_text('Email адреса не найдены')
        return ConversationHandler.END

    context.user_data['emails'].extend(emailList)

    emails = ''
    for i, email in enumerate(emailList, start=1):
        emails += f'{i}. {email}\n'

    update.message.reply_text(emails)

    update.message.reply_text('Хотите сохранить эти email в базе данных? (да/нет)')

    return 'save_email'


def saveEmail(update, context):
    user_input = update.message.text.lower()
    if user_input == 'да':
        conn = context.bot_data['db_conn']
        cursor = conn.cursor()
        try:
            existing_emails = set()
            cursor.execute("SELECT email FROM emails")
            for row in cursor.fetchall():
                existing_emails.add(row[0])
            for email in context.user_data['emails']:
                cursor.execute("SELECT email FROM emails WHERE email = %s", (email,))
                existing_email = cursor.fetchone()
                if email not in existing_emails and existing_email is None:
                    cursor.execute("INSERT INTO emails (email) VALUES (%s)", (email,))
            conn.commit()
            update.message.reply_text('Email успешно сохранены в базе данных')
        except psycopg2.Error as e:
            update.message.reply_text('Ошибка при сохранении email в базе данных')
            logger.error(f"Error saving emails: {e}")
            conn.rollback()
            return ConversationHandler.END
        finally:
            cursor.close()
            return ConversationHandler.END
    else:
        update.message.reply_text('Email не сохранены')
        return ConversationHandler.END


def verifyPassword(update, context):
    user_input = update.message.text

    if ' ' in user_input:
        update.message.reply_text('Пароль не должен содержать пробелов.')
        return ConversationHandler.END

    passwordRegex = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()])[A-Za-z\d!@#$%^&*()]{8,}$')

    if passwordRegex.match(user_input):
        update.message.reply_text('Пароль сложный')
    else:
        update.message.reply_text('Пароль простой')

    return ConversationHandler.END


def splitAndSendTelegramMessage(update: Update, text):
    max_message_length = 4096

    parts = [text[i:i + max_message_length] for i in range(0, len(text), max_message_length)]

    for part in parts:
        update.message.reply_text(part)


def getRelease(update: Update, context):
    client = context.bot_data['ssh_client']
    stdin, stdout, stderr = client.exec_command('lsb_release -a')
    release_info = stdout.read().decode('utf-8')

    update.message.reply_text(release_info)
    return ConversationHandler.END


def getUname(update: Update, context):
    client = context.bot_data['ssh_client']
    stdin, stdout, stderr = client.exec_command('uname -a')
    uname_info = stdout.read().decode('utf-8')

    update.message.reply_text(uname_info)
    return ConversationHandler.END


def getUptime(update: Update, context):
    client = context.bot_data['ssh_client']
    stdin, stdout, stderr = client.exec_command('uptime')
    uptime_info = stdout.read().decode('utf-8')

    update.message.reply_text(uptime_info)
    return ConversationHandler.END


def getDf(update: Update, context):
    client = context.bot_data['ssh_client']
    stdin, stdout, stderr = client.exec_command('df -h')
    df_info = stdout.read().decode('utf-8')

    update.message.reply_text(df_info)
    return ConversationHandler.END


def getFree(update: Update, context):
    client = context.bot_data['ssh_client']
    stdin, stdout, stderr = client.exec_command('free -h')
    free_info = stdout.read().decode('utf-8')

    update.message.reply_text(free_info)
    return ConversationHandler.END


def getMpstat(update: Update, context):
    client = context.bot_data['ssh_client']
    stdin, stdout, stderr = client.exec_command('mpstat')
    mpstat_info = stdout.read().decode('utf-8')

    update.message.reply_text(mpstat_info)
    return ConversationHandler.END


def getW(update: Update, context):
    client = context.bot_data['ssh_client']
    stdin, stdout, stderr = client.exec_command('w')
    w_info = stdout.read().decode('utf-8')

    update.message.reply_text(w_info)
    return ConversationHandler.END


def getAuths(update: Update, context):
    client = context.bot_data['ssh_client']
    stdin, stdout, stderr = client.exec_command('last -10')
    auths_info = stdout.read().decode('utf-8')

    update.message.reply_text(auths_info)
    return ConversationHandler.END


def getCritical(update: Update, context):
    client = context.bot_data['ssh_client']
    stdin, stdout, stderr = client.exec_command('journalctl -p 3 -n 5')
    critical_info = stdout.read().decode('utf-8')

    update.message.reply_text(critical_info)
    return ConversationHandler.END


def getPs(update: Update, context):
    client = context.bot_data['ssh_client']
    stdin, stdout, stderr = client.exec_command('ps aux')
    ps_info = stdout.read().decode('utf-8')

    splitAndSendTelegramMessage(update, ps_info)

    return ConversationHandler.END


def getSs(update: Update, context):
    client = context.bot_data['ssh_client']
    stdin, stdout, stderr = client.exec_command('ss -tuln')
    ss_info = stdout.read().decode('utf-8')

    update.message.reply_text(ss_info)
    return ConversationHandler.END


def getAptList(update: Update, context):
    client = context.bot_data['ssh_client']
    user_input = context.args
    if user_input:
        package_name = user_input[0]
        stdin, stdout, stderr = client.exec_command(f'apt show {package_name}')
        package_info = stdout.read().decode('utf-8')
        splitAndSendTelegramMessage(update, package_info)
        return ConversationHandler.END
    else:
        stdin, stdout, stderr = client.exec_command('apt list --installed')
        apt_list_info = stdout.read().decode('utf-8')
        splitAndSendTelegramMessage(update, apt_list_info)
        return ConversationHandler.END


def getServices(update: Update, context):
    client = context.bot_data['ssh_client']
    stdin, stdout, stderr = client.exec_command("service --status-all | grep '\[ + \]'")
    services_info = stdout.read().decode('utf-8')

    splitAndSendTelegramMessage(update, services_info)

    return ConversationHandler.END


def getReplLogs(update: Update, context):
    client = context.bot_data['ssh_client']
    # for docker
    #stdin, stdout, stderr = client.exec_command("docker logs -n 40 db_image")
    #repl_logs = stderr.read().decode('utf-8')

    #for ansible
    stdin, stdout, stderr = client.exec_command("cat /var/log/postgresql/postgresql-14-main.log")
    repl_logs = stdout.read().decode('utf-8')
    
    splitAndSendTelegramMessage(update, repl_logs)

    return ConversationHandler.END


def getEmails(update: Update, context):
    conn = context.bot_data['db_conn']
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ID, email FROM emails")
        emails = cursor.fetchall()
        email_text = '\n'.join(f"{email[0]} {email[1]}" for email in emails)
        splitAndSendTelegramMessage(update, email_text)
    except psycopg2.Error as e:
        logger.error(f"Error fetching emails: {e}")
        return ConversationHandler.END
    finally:
        cursor.close()
        return ConversationHandler.END


def getPhoneNumbers(update: Update, context):
    conn = context.bot_data['db_conn']
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ID, phone_number FROM phone_numbers")
        phone_numbers = cursor.fetchall()
        phone_number_text = '\n'.join(f"{phone_number[0]} {phone_number[1]}" for phone_number in phone_numbers)
        splitAndSendTelegramMessage(update, phone_number_text)
    except psycopg2.Error as e:
        logger.error(f"Error fetching phone_numbers: {e}")
        return ConversationHandler.END
    finally:
        cursor.close()
        return ConversationHandler.END


def helpCommand(update: Update, context):
    if context.args and context.args[0] == "-b":
        text = "(Help) I need somebody\n(Help) Not just anybody\n(Help) You know I need someone\n(Help!)"
        update.message.reply_text(text)
        return ConversationHandler.END
    else:
        commands = [
            "/find_phone_number - Найти телефонные номера в тексте",
            "/find_email - Найти email адреса в тексте",
            "/verify_password - Проверить сложность пароля",
            "/get_release - Получить информацию о релизе системы",
            "/get_uname - Получить информацию о системе с помощью uname",
            "/get_uptime - Получить информацию о времени работы системы",
            "/get_df - Получить информацию о дисковом пространстве",
            "/get_free - Получить информацию о свободной памяти",
            "/get_mpstat - Получить информацию о процессоре с помощью mpstat",
            "/get_w - Получить информацию о пользователях системы",
            "/get_auths - Получить информацию о последних аутентификациях",
            "/get_critical - Получить критические сообщения журнала системы",
            "/get_ps - Получить список активных процессов",
            "/get_ss - Получить информацию о сетевых соединениях",
            "/get_apt_list - Получить список установленных пакетов с помощью apt",
            "/get_apt_list <name> - Получить информацию об установленном пакете",
            "/get_services - Получить список сервисов системы",
            "/get_repl_logs - Вывод логов о репликации",
            "/get_emails - Вывод email адресов из базы данных",
            "/get_phone_numbers - Вывод номеров телефонов из базы данных"
            "/help - Показать список команд",
        ]
        update.message.reply_text("\n".join(commands))
        return ConversationHandler.END


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=username, password=password, port=port)

    conn = psycopg2.connect(
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port,
        database=db_database
    )

    updater = Updater(token, use_context=True)

    dp = updater.dispatcher

    dp.bot_data['db_conn'] = conn
    dp.bot_data['ssh_client'] = client

    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', findPhoneNumbersCommand)],
        states={
            'find_phone_number': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            'save_phone_numbers': [MessageHandler(Filters.text & ~Filters.command, savePhoneNumbers)],
        },
        fallbacks=[]
    )

    convHandlerFindEmail = ConversationHandler(
        entry_points=[CommandHandler('find_email', findEmailCommand)],
        states={
            'find_email': [MessageHandler(Filters.text & ~Filters.command, findEmail)],
            'save_email': [MessageHandler(Filters.text & ~Filters.command, saveEmail)],
        },
        fallbacks=[]
    )

    convHandlerVerifyPassword = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verifyPasswordCommand)],
        states={
            'verify_password': [MessageHandler(Filters.text & ~Filters.command, verifyPassword)],
        },
        fallbacks=[]
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(convHandlerFindPhoneNumbers)
    dp.add_handler(convHandlerFindEmail)
    dp.add_handler(convHandlerVerifyPassword)

    dp.add_handler(CommandHandler("get_release", getRelease))
    dp.add_handler(CommandHandler("get_uname", getUname))
    dp.add_handler(CommandHandler("get_uptime", getUptime))
    dp.add_handler(CommandHandler("get_df", getDf))
    dp.add_handler(CommandHandler("get_free", getFree))
    dp.add_handler(CommandHandler("get_mpstat", getMpstat))
    dp.add_handler(CommandHandler("get_w", getW))
    dp.add_handler(CommandHandler("get_auths", getAuths))
    dp.add_handler(CommandHandler("get_critical", getCritical))
    dp.add_handler(CommandHandler("get_ps", getPs))
    dp.add_handler(CommandHandler("get_ss", getSs))
    dp.add_handler(CommandHandler("get_apt_list", getAptList))
    dp.add_handler(CommandHandler("get_services", getServices))

    dp.add_handler(CommandHandler("get_repl_logs", getReplLogs))
    dp.add_handler(CommandHandler("get_emails", getEmails))
    dp.add_handler(CommandHandler("get_phone_numbers", getPhoneNumbers))

    dp.add_handler(CommandHandler("help", helpCommand))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
