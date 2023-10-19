import requests
import sqlite3

import json
import time
import os
import datetime


"""
    Функция чтения json-файла

    :param     filename: Название файла
    :type      filename: str.
    
    :returns: dict или list
"""


def json_load(filename):
    with open(filename, "r", encoding="utf8") as read_file:
        result = json.load(read_file)
    return result


"""
    Функция записи в json-файл

    :param     filename: Название файла
    :type      filename: str.
    :param     data: Записываемые данные
    :type      data: list or dict.
  
"""


def json_dump(filename, data):
    with open(filename, "w", encoding="utf8") as write_file:
        json.dump(data, write_file, ensure_ascii=False)


"""Создание базы"""
# ------ db_name - имя базы данных (пример - avtotovary, т.е. без .db)------#
def create_db(db_name):
    connect = sqlite3.connect(r"db/" + db_name + ".db")
    cursor = connect.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS {}(
        classid INTEGER PRIMARY KEY,
        old_price INTEGER
        )""".format(
            db_name
        )
    )
    return connect


"""Подключение к базе"""


def connect_db(db_name):
    sqlite_connection = sqlite3.connect(r"../db/" + db_name + ".db")
    return sqlite_connection


"""Добавление артикулов и цены в базу"""


def db_insert(connect, db_name, classid, old_price):
    cursor = connect.cursor()
    cursor.execute("INSERT INTO {} VALUES(?,?);".format(db_name), [classid, old_price])


def update_db(connect, db_name, classid, old_price):
    cursor = connect.cursor()
    cursor.execute(
        "UPDATE {} SET old_price={} WHERE classid={};".format(
            db_name, old_price, classid
        )
    )


"""Коммит"""


def do_commit(connect):
    connect.commit()


"""Получение цены по артикулу"""


def get_artikul_price(connect, db_name, product_artikul):
    cursor = connect.cursor()
    cursor.execute(
        "select old_price from {} where classid={};".format(db_name, product_artikul)
    )
    old_price = cursor.fetchone()
    if old_price is not None:
        return old_price
    else:
        return 0


"""Получение списка цен из базы данных для всех артикулов"""


def get_all_products(connect, db_name):
    cursor = connect.cursor()
    cursor.execute("select * from {};".format(db_name))
    old_price = cursor.fetchall()
    return old_price


"""
    Функция отправки сообщения в телеграм 

    :param     text: Отправляемый текст сообщения
    :type      text: str.
    :param tg_token: Токен телеграм-бота из BotFather
    :type  tg_token: str.
    :param  user_id: ID пользователя бота
    :type   user_id: int.
    :param  new_price: Новая цена на товар
    :type   new_price: float.
    :param  old_price: Старая цена на товар
    :type   old_price: float.
    :param  link: Ссылка на товар
    :type   link: str.

"""


def send_info(text, tg_token, user_id, new_price, old_price, link):

    URL = "https://api.telegram.org/bot"
    URL += tg_token
    method = URL + "/sendMessage"
    price_info = "Новая цена *{}* руб. Старая цена *{}* руб. \n".format(
        new_price, old_price
    )
    product_info = "Ссылка - {} \n".format(link)

    text = price_info + product_info

    requests.post(
        method, data={"chat_id": user_id, "text": text, "parse_mode": "markdown"}
    )

"""
    Функция отправки сообщения об ошибке в телеграм 

    :param     text: Отправляемый текст сообщения
    :type      text: str.
    :param tg_token: Токен телеграм-бота из BotFather
    :type  tg_token: str.
    :param  user_id: ID пользователя бота
    :type   user_id: int.

"""
def send_error_msg(text, tg_token, user_id):
    url_req = (
        "https://api.telegram.org/bot"
        + tg_token
        + "/sendMessage"
        + "?chat_id="
        + str(user_id)
        + "&text="
        + text
    )
    requests.get(url_req)
    
"""
    Функция проверки попадания текущего времени в заданных в часах промежуток

    :param start_time: Начало временного периода 
    :type  start_time: int.
    :param   end_time: Начало временного периода
    :type    end_time: int.
    
    :returns: True или False
"""


def time_in_range(start_time, end_time):

    start = datetime.time(start_time, 0, 0)
    end = datetime.time(end_time, 0, 0)
    hours = (int(time.strftime("%H", time.gmtime(time.time()))) + 3) % 24
    minutes = int(time.strftime("%M", time.gmtime(time.time())))
    x = datetime.time(hours, minutes, 0)
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end

"""
    Функция получения данных о товарах на заданной страницы 
"""
def get_page_info(session, section, page):
    api_url = "https://api.tsum.ru/v3/catalog/search"
    man_payload = {"section": section, "page": page}
    page_data = s.post(api_url, json=man_payload).json()

    return page_data if len(page_data) > 0 else []


"""
    Функция парсинга в базу данных (раз в сутки в заданное время происходит обновление цен в базе данных)
"""
def parser_to_db(connect, db_name, session, sections_list):

    db_products = {}
    result = get_all_products(connect, db_name)
    for item in result:
        db_products[item[0]] = item[1]

    for section in sections_list:
        page = 1
        while True:

            page_data = get_page_info(session, section, page)

            if len(page_data) == 0:
                break

            for item in page_data:
                classid = item["id"]
                price = item["skuList"][0]["price_original"]

                if int(classid) not in db_products.keys():

                    db_insert(connect, db_name, classid, price)
                    db_products[int(classid)] = price
                else:
                    db_price = db_products[int(classid)]
                    if db_price < price:
                        update_db(connect, db_name, classid, price)

                print(
                    str(section)
                    + "/"
                    + str(item["id"])
                    + " / "
                    + str(item["skuList"][0]["price_original"])
                    + " / "
                    + str(item["skuList"][0]["price_discount"])
                )

            page += 1

        do_commit(connect)

"""
    Функция поиска ошибочных цен на сайте с оповещение в телеграм
"""
def checker(connect, db_name, session, sections_list, sale):
    result = get_all_products(connect, db_name)

    db_products = {}
    reboot_time = time.time()

    for item in result:
        db_products[item[0]] = item[1]

    already = []
    while True:
        if (time.time() - reboot_time) > 2400:
            os.system("reboot now")

        for section in sections_list:
            page = 1
            while True:

                page_data = get_page_info(session, section, page)

                if len(page_data) == 0:
                    break

                for item in page_data:
                    classid = item["id"]
                    price = item["skuList"][0]["price_original"]
                    discount = item["skuList"][0]["price_discount"]
                    url = "https://www.tsum.ru/product/" + item["slug"]
                    try:
                        old_price = db_products[int(classid)]
                    except:
                        old_price = price

                    try:
                        if price / old_price < sale and classid not in already:
                            send_info(price, old_price, url)
                            already.append(classid)
                            print(
                                str(section)
                                + "/"
                                + str(item["id"])
                                + " / "
                                + str(item["skuList"][0]["price_original"])
                                + " / "
                                + str(item["skuList"][0]["price_discount"])
                            )

                        if discount / old_price < sale and classid not in already:
                            send_info(discount, old_price, url)
                            already.append(classid)
                            print(
                                str(section)
                                + "/"
                                + str(item["id"])
                                + " / "
                                + str(item["skuList"][0]["price_original"])
                                + " / "
                                + str(item["skuList"][0]["price_discount"])
                            )

                    except:

                        continue
                print(str(page) + "/" + str(section))
                page += 1


if __name__ == "__main__":
    count_of_errors = 0
    
    config          = json_load(r"./json/config.json")
    db_name         = config["db_name"]
    sections_list   = config["list_of_sections"]
    sale            = config["min_sale"]
    
    token          = config['tg_token']
    user_id        = config['user_id']
    start_time     = config['balance_update_time_start']
    end_time       = config['balance_update_time_end']
    
    time_flag       = time_in_range(start_time, end_time)
    
    connect         = create_db(db_name)

    woman_url = "https://www.tsum.ru/catalog/zhenskoe-18368/"
    man_url = "https://www.tsum.ru/catalog/muzhskoe-2408/"
    kids_url = "https://www.tsum.ru/catalog/detskie_tovary-2518/"

    cookies = json_load(r"./json/cookies.json")
    s = requests.Session()
    s.headers.update(cookies)
    
    # проверка времени для обновления базы данных
    if time_flag:
        while True:
            if count_of_errors > 10:
                break
            try:

                parser_to_db(connect, db_name, s, sections_list)
                break
            except Exception as e:
                count_of_errors += 1
               
                send_error_msg(str(e), token, user_id)
                continue
        while True:
            if count_of_errors > 10:
                break
            try:
                checker(connect, db_name, s, sections_list, sale)

            except Exception as e:
                count_of_errors += 1
                send_error_msg(str(e), token, user_id)
                continue

    else:
        while True:
            if count_of_errors > 10:
                break
            try:
                checker(connect, db_name, s, sections_list, sale)

            except Exception as e:
                count_of_errors += 1
                send_error_msg(str(e), token, user_id)
                continue
