import json
from anthropic import Anthropic
from loguru import logger

from src.config.settings import settings
from .message import form_message


api_key = settings.api_key
claude_model_name = settings.claude_model_name

client = Anthropic(api_key=api_key)


async def recognize_check_by_anthropic(file_location_directory: str):
    prompt = ("""
        <prompt>
        Ты специалист по распознаванию чеков из ресторанов и кафе. Внимательно изучи изображение и извлеки всю важную информацию в структурированном виде.
        
        <instructions>
        1. Для каждой позиции в чеке определи: 
           - порядковый номер 
           - точное наименование товара
           - количество
           - общую сумму
        2. Найди промежуточный итог (subtotal)
        3. Определи наличие сервисного сбора, его процент и сумму
        4. Определи наличие НДС, его ставку и сумму
        5. Определи наличие скидки, её ставку и сумму
        6. Найди итоговую сумму чека
        </instructions>
        
        <output_format>
        Выдай результат только в виде JSON без комментариев, пояснений и дополнительного форматирования.
        Структура должна строго соответствовать следующему формату:
        
        {
          "restaurant": "Название заведения (если есть)",
          "address": "Адрес заведения (если есть)",
          "phone": "Телефон заведения (если есть)",
          "table_number": "Номер стола (если есть)",
          "order_number": "Номер заказа (если есть)",
          "date": "Дата (ДД.ММ.ГГГГ) (если есть)",
          "time": "Время (ЧЧ:ММ) (если есть)",
          "waiter": "Имя официанта (если есть)",
          "items": [
            {
              "id": порядковый_номер,
              "name": "Точное наименование",
              "quantity": количество,
              "sum": общая_сумма
            },
            // другие позиции
          ],
          "subtotal": промежуточный_итог,
          "service_charge": {
            "name": "Название сбора",
            "percentage": процент_сбора,
            "amount": сумма_сбора
          },
          "vat": {
            "rate": ставка_ндс,
            "amount": сумма_ндс
          },
          "discount": {
            "name": процент_скидки,
            "amount": сумма_скидки
          },
          "total": итоговая_сумма
        }
        </output_format>
        
        <validation_rules>
        1. Все денежные суммы должны быть числами без разделителей тысяч и символов валюты
        2. Для отсутствующих значений используй null, а не пустые строки
        3. Если какой-то раздел полностью отсутствует (например, нет сервисного сбора), оставь соответствующее поле как null
        4. Проверь, что количество и цены являются числами, а не строками
        5. Убедись, что итоговая сумма соответствует сумме всех позиций с учетом сборов и налогов
        </validation_rules>
        </prompt>
    """)
    message = await form_message(file_location_directory, prompt=prompt)

    try:
        response = client.messages.create(
            model=claude_model_name,
            max_tokens=2048,
            messages=message
        )
        logger.info(f"Response: {response.content[0].text}")
        response_json = json.loads(response.content[0].text)
        return response_json
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error: {e}")
    except Exception as e:
        logger.error(f"Error with recognition request: {e}")
    return None


def test_claude():

    message = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "prompt"
                },
            ]
        }
    ]

    response = client.messages.create(
        model=claude_model_name,
        max_tokens=2048,
        messages=message
    )
    # response_data = json.loads(response.content[0].text)
    return json.loads(response.content[0].text)


if __name__ == '__main__':

    print(recognize_check_by_anthropic("../images/8e3e9dbe-b63f-4956-b73a-ce8ef067e5cc"))
