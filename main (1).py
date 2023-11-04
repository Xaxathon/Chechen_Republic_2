import telebot
import psycopg2
import threading
import shutil
import psutil

TOKEN = '6941970070:AAG2PyMm0pzDdRrtdKSdNbo_2QblkoNkOdY'
bot = telebot.TeleBot(TOKEN)


conn = psycopg2.connect(
    dbname='test',
    user='postgres',
    password='wannarock',
    host='127.0.0.1',
    port='5432'
)

tracking_timers = {}

@bot.message_handler(commands=['start'])
def ask_for_dbname(message):
    chat_id = message.chat.id
    if(conn):
        bot.send_message(chat_id, 'Соединение с базой данных успешно установлено')
    else: 
        bot.send_message(chat_id, 'Не удалось установить соединение с базой данных')
    


def check_db(chat_id):
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM pg_stat_activity;")
        result = cursor.fetchall()
        active_sessions = len(result)
        bot.send_message(chat_id, f'Количество активных сессий: {active_sessions - 1}')
    
    # Запустить таймер снова, если он не был остановлен
    if chat_id in tracking_timers:
        tracking_timers[chat_id] = threading.Timer(15, check_db, args=(chat_id,))
        tracking_timers[chat_id].start()

@bot.message_handler(commands=['tracking_start'])
def tracking_start(message):
    chat_id = message.chat.id
    if chat_id not in tracking_timers:
        bot.send_message(chat_id, 'Трекинг активных сессий запущен.')
        tracking_timers[chat_id] = threading.Timer(15, check_db, args=(chat_id,))
        tracking_timers[chat_id].start()
    else:
        bot.send_message(chat_id, 'Трекинг уже запущен.')

@bot.message_handler(commands=['tracking_stop'])
def tracking_stop(message):
    chat_id = message.chat.id
    if chat_id in tracking_timers:
        tracking_timers[chat_id].cancel()  # Остановить текущий таймер
        del tracking_timers[chat_id]  # Удалить таймер из словаря
        bot.send_message(chat_id, 'Трекинг активных сессий остановлен.')
    else:
        bot.send_message(chat_id, 'Трекинг не был запущен.')

@bot.message_handler(commands=['check_lwlocks'])
def check_lwlocks(message):
    lwlock_sessions_count = get_lwlock_sessions_count()
    bot.send_message(message.chat.id, f'Количество сессий, ожидающих LWLock: {lwlock_sessions_count}')



def get_lwlock_sessions_count():
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pg_stat_activity 
            WHERE wait_event_type = 'Lock'
            AND wait_event LIKE '%LWLock%'
        """)
        result = cursor.fetchone()
        return result[0] if result else 0







@bot.message_handler(commands=['get_longest_transaction'])
def get_longest_transaction(message):
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT max(now() - xact_start) AS longest_transaction
            FROM pg_stat_activity
            WHERE xact_start IS NOT NULL;
        """)
        longest_transaction = cursor.fetchone()

        if longest_transaction[0]:
            bot.send_message(message.chat.id, f'Количество сессий, ожидающих LWLock: {longest_transaction[0]}')
        else:
            bot.send_message(message.chat.id, f'В данный момент активных транзакций нет.: {longest_transaction[0]}')






def get_free_disk_space():
    total, used, free = shutil.disk_usage("/")
    return free

@bot.message_handler(commands=['free_disk_space'])
def send_free_space(message):
    try:
        free_space_bytes = get_free_disk_space()
        free_space_gb = free_space_bytes / (1024**3)  # Преобразуем в гигабайты

        bot.reply_to(message, f"Свободно места на диске: {free_space_gb:.2f} ГБ")
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {e}")





def get_postgres_cpu_usage():
    for proc in psutil.process_iter(['pid', 'name']):
        if 'postgres' in proc.info['name']:
            return proc.cpu_percent(interval=1.0)
    return 0.0

@bot.message_handler(commands=['postgres_cpu_load'])
def send_postgres_cpu_load(message):
    cpu_usage = get_postgres_cpu_usage()
    bot.reply_to(message, f"Текущее использование CPU процессом PostgreSQL: {cpu_usage:.2f}%")


if __name__ == '__main__':
    bot.polling(none_stop=True)