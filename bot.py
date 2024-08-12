import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup as bs
import re

TOKEN = ''
bot = telebot.TeleBot(TOKEN)

# Dictionary to store user input for each chat
user_inputs = {}


def get_html_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = requests.get(url, headers=headers)
    return response.text


def extract_atb_data(html_content):
    soup = bs(html_content, "html.parser")  # Створення об'єкта BeautifulSoup для парсингу HTML-змісту сторінки.
    prices = soup.find_all('div',
                           class_='catalog-item__bottom')  # Пошук усіх контейнерів з цінами та назвами продуктів на сторінці.
    product_names = soup.find_all('div', class_='catalog-item__info')

    products_atb = []

    for price_container, names_container in zip(prices,
                                                product_names):  # Цикл, який ітерується одночасно по контейнерах цін і назв продуктів.
        price_data_tag = price_container.find('data', class_='product-price__top')  # пошук ціни в контейнері
        product_name_tag = names_container.find('div', class_='catalog-item__title')  # пошук імені в контейнері

        if price_data_tag and product_name_tag:  # Перевірка, чи отримано дані про ціну та назву продукту.
            price_value = float(price_data_tag['value'])  # Отримання числового значення ціни.
            product_name_tag_a = product_name_tag.find('a')
            if product_name_tag_a:  # Пошук тегу <a>, який може містити посилання на продукт.
                product_name = product_name_tag_a.text.strip()  # Отримання тексту (назви продукту) та видалення зайвих пробілів.
                href_link = product_name_tag_a[
                    'href']  # Отримання значення атрибуту href тегу <a> (посилання на продукт).
                masked_product_name = f"[{product_name}](https://www.atbmarket.com{href_link})"
                products_atb.append({"name": f"{masked_product_name}", "price": price_value})

    return products_atb


def extract_tavria_data(html_content):
    soup = bs(html_content, "html.parser")
    products = soup.find_all('div', class_='products__item')

    products_tavria = []

    for product in products:
        price_data_tag = product.find('p', class_='product__price')  # пошук ціни в контейнері
        product_name_tag = product.find('p', class_='product__title')  # пошук імені в контейнері

        if price_data_tag and product_name_tag:
            price_value_match = re.search(r'(\d+\.\d+)', price_data_tag.text)
            price_value = float(price_value_match.group()) if price_value_match else float('inf')

            product_name_tag_a = product_name_tag.find('a')
            if product_name_tag_a:
                product_name = product_name_tag_a.text.strip()
                href_link = product_name_tag_a['href']
                masked_product_name = f"[{product_name}](https://www.tavriav.ua{href_link})"
                products_tavria.append({"name": f"{masked_product_name}", "price": price_value})

    return products_tavria



@bot.message_handler(func=lambda message: True)
def start(message):
    bot.reply_to(message, "Введіть, що ви шукаєте:")
    bot.register_next_step_handler(message, choose_store)


def choose_store(message):
    keyboard = types.ReplyKeyboardMarkup( resize_keyboard=True)
    button_atb = types.KeyboardButton('АТБ')
    button_tavria = types.KeyboardButton('Таврія')
    button_all = types.KeyboardButton('Всі магазини')
    button = types.KeyboardButton('🔍Пошук товара')
    keyboard.add(button_atb, button_tavria, button_all,button)

    msg = bot.reply_to(message, "Виберіть магазин:", reply_markup=keyboard)

    # Store user input for this chat
    user_inputs[message.chat.id] = {'query': message.text}

    bot.register_next_step_handler(msg, process_store_choice)


def process_store_choice(message):
    chat_id = message.chat.id

    if message.text.lower() == 'атб':
        search_in_atb(chat_id)
    elif message.text.lower() == 'таврія':
        search_in_tavria(chat_id)
    elif message.text.lower() == 'всі магазини':
        search_in_all_stores(chat_id)
    elif message.text.lower() == '🔍Пошук товара':
        start(message)
    else:
        bot.reply_to(message, "Невірний вибір. Спробуйте ще раз.")


def search_in_atb(chat_id):
    zapit = user_inputs[chat_id]['query']
    url_atb = f"https://www.atbmarket.com/sch?page=1&lang=uk&location=1154&query={zapit}"
    html_content_atb = get_html_content(url_atb)
    products_atb = extract_atb_data(html_content_atb)
    send_results(chat_id, "АТБ", products_atb)


def search_in_tavria(chat_id):
    zapit = user_inputs[chat_id]['query']
    url_tavria = f"https://www.tavriav.ua/catalog/search/?query={zapit}"
    html_content_tavria = get_html_content(url_tavria)
    products_tavria = extract_tavria_data(html_content_tavria)
    send_results(chat_id, "Таврія", products_tavria)


def search_in_all_stores(chat_id):
    zapit = user_inputs[chat_id]['query']
    url_atb = f"https://www.atbmarket.com/sch?page=1&lang=uk&location=1154&query={zapit}"
    html_content_atb = get_html_content(url_atb)
    products_atb = extract_atb_data(html_content_atb)
    send_results(chat_id, "АТБ", products_atb)

    zapit = user_inputs[chat_id]['query']
    url_tavria = f"https://www.tavriav.ua/catalog/search/?query={zapit}"
    html_content_tavria = get_html_content(url_tavria)
    products_tavria = extract_tavria_data(html_content_tavria)
    send_results(chat_id, "Таврія", products_tavria)


def send_results(chat_id, store_name, products):
    sorted_products = sorted(products, key=lambda x: x["price"])

    result_message = f"Результати пошуку у магазині {store_name}:\n"
    for product in sorted_products:
        masked_link = f"{store_name}", f"{product['name']}, Ціна: {product['price']}"
        result_message += f"{masked_link}\n"

    message_chunks = [result_message[i:i + 4096] for i in range(0, len(result_message), 4096)]

    for chunk in message_chunks:
        bot.send_message(chat_id, chunk, parse_mode='Markdown')


if __name__ == "__main__":
    bot.polling()
