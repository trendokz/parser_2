import ast
import requests
import schedule
from bs4 import BeautifulSoup
from datetime import datetime

url = 'https://www.komfort.kz/dir/'
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 YaBrowser/22.11.3.818 Yowser/2.5 Safari/537.36"
}


def get_data():
    req = requests.get(url=url, headers=headers)
    req.encoding = 'UTF8'
    src = req.text
    soup = BeautifulSoup(src, 'lxml')

    # Сбор всех ссылок на каталоги
    catalogs_dict = []
    div_dir_item = soup.find('div', class_='all-products').find_all('div', class_='dir-item')
    for cat in div_dir_item:
        catalog = cat.find('h4', class_='level-1').find('a').get('href')
        catalogs_dict.append(catalog)

    del catalogs_dict[1]
    del catalogs_dict[-5]

    try:
        # Сбор всех карточек товарами из каждого каталога
        all_dict_cards = [["Название", "Код товара", "Цена"]]
        count_catalog = 0
        for url1 in catalogs_dict:
            count_catalog += 1
            page = 1
            next_page = True
            max_count_cards_in_page = 0
            while next_page:
                req1 = requests.get(url=f'{url1}?p={page}', headers=headers)
                req1.encoding = 'UTF8'
                src1 = req1.text
                soup1 = BeautifulSoup(src1, 'lxml')

                # print(len(soup1.find('div', class_='pages').find('ul', class_='items pages-items').find_all('a', class_='action next')))
                if len(soup1.find('div', class_='pages').find('ul', class_='items pages-items').find_all('a', class_='action next')) == 0:
                    next_page = False

                name_and_id_product = []
                cards = soup1.find_all('li', class_='item product product-item')
                # len_cards = len(cards)
                for card in cards:
                    name_product = card.find('a', class_='product-item-link').text
                    id_product = card.find('a', class_='product-item-link').get('data-id-product')

                    name_and_id_product.append(
                        [
                            name_product,
                            id_product
                        ]
                    )

                all_data_product_id = []

                a = soup1.find_all('li', class_='item product product-item')
                data_product_id = []
                for b in a:
                    c = b.find('div', class_='product-item-info')
                    data_product_id.append(c)

                first = 'https://www.komfort.kz/loyalty/products/prices/?ids%5B%5D='
                second = ''
                for product_id in data_product_id:
                    second += f'{product_id.get("data-product-id")}&ids%5B%5D='
                    all_data_product_id.append(product_id.get("data-product-id"))

                a = second.rsplit('ids%5B%5D', 1)
                second = '_'.join(a)

                url_price_page = f'{first}{second}'

                req2 = requests.get(url=url_price_page, headers=headers)
                req2.encoding = 'UTF8'
                src2 = req2.content
                dict_price = ast.literal_eval(src2.decode('utf-8'))
                data_json_prices = dict_price['prices']

                count_cards_in_page = 0
                num_card_page = 0
                for data_cards_page in all_data_product_id:
                    html_data_prices = data_json_prices[data_cards_page]
                    soup2 = BeautifulSoup(html_data_prices, 'lxml')

                    if len(soup2.find_all('span', class_='special-price')) == 1:
                        price_product = soup2.find('span', class_='special-price').find('span', class_='price').text.split('₸')[0]
                    else:
                        price_product = soup2.find('span', class_='price').text.split('₸')[0]

                    name_and_id_product[num_card_page].append(price_product.replace('\xa0', ''))

                    # print(name_and_id_product[num_card_page])
                    # print(len(name_and_id_product[num_card_page]))
                    if name_and_id_product[num_card_page] in all_dict_cards:
                        count_cards_in_page += 1
                        name_and_id_product.remove(name_and_id_product[num_card_page])
                        # next_page = False

                    else:
                        all_dict_cards.append(name_and_id_product[num_card_page])
                        num_card_page += 1
                        count_cards_in_page += 1

                # print(count_cards_in_page)
                if max_count_cards_in_page == count_cards_in_page:
                    print(f'Страница {page}')
                    page += 1
                    continue

                elif max_count_cards_in_page < count_cards_in_page:
                    max_count_cards_in_page = count_cards_in_page
                    print(f'Страница {page}')
                    page += 1

                else:
                    print(f'Страница {page}')
                    next_page = False

            print(f'{count_catalog} каталог готов!')

        # print(all_dict_cards)
        # print(len(all_dict_cards))
        google_table(dict_cards=all_dict_cards)

    except Exception as ex:
        print(ex)
        print(url1)
        google_table(dict_cards=all_dict_cards)


def google_table(dict_cards):
    import os.path
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.oauth2 import service_account

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials.json')

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    # mail bot 'parsers@parsers-372008.iam.gserviceaccount.com'
    SAMPLE_SPREADSHEET_ID = '107SdHe8_dV6npe_dKE-7xA2QJgxz6ZOywOy-GZyrZX0'
    SAMPLE_RANGE_NAME = 'komfort.kz'

    try:
        service = build('sheets', 'v4', credentials=credentials).spreadsheets().values()

        # Чистим(удаляет) весь лист
        array_clear = {}
        clear_table = service.clear(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME,
                                    body=array_clear).execute()

        # добавляет информации
        array = {'values': dict_cards}
        response = service.append(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                  range=SAMPLE_RANGE_NAME,
                                  valueInputOption='USER_ENTERED',
                                  insertDataOption='OVERWRITE',
                                  body=array).execute()

    except HttpError as err:
        print(err)


def main():
    start_time = datetime.now()

    schedule.every(35).minutes.do(get_data)

    while True:
        schedule.run_pending()

    finish_time = datetime.now()
    spent_time = finish_time - start_time
    print(spent_time)


if __name__ == '__main__':
    main()
