import json
import logging
import os
from dotenv import load_dotenv

from src.config import config
from src.utils.check import to_float, to_int

# Загружаем .env до всех импортов, зависящих от settings
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from sqlalchemy import select
from sqlalchemy.orm import Session


from src.db.session import sync_engine
from src.models import Check, CheckItem, UserSelection, SelectedItem

engine = sync_engine


# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(config.app.service_name)


def migrate_check(check_uuid):
    with Session(engine) as db:
        check = db.execute(select(Check).filter_by(uuid=check_uuid)).scalar_one_or_none()
        if not check:
            logger.warning(f"Check with uuid {check_uuid} not found")
            return
        if not check.check_data:
            logger.warning(f"Check {check.uuid} has no check_data, skipping")
            return

        try:
            json_data = check.check_data
            logger.info(f"Processing check {check.uuid} with data: {json_data}")

            # Обновляем поля чека
            check.restaurant = json_data.get("restaurant")
            check.address = json_data.get("address")
            check.phone = json_data.get("phone")
            check.table_number = json_data.get("table_number")
            check.order_number = json_data.get("order_number")
            check.date = json_data.get("date")
            check.time = json_data.get("time")
            check.waiter = json_data.get("waiter")
            check.subtotal = to_float(json_data.get("subtotal"), 0)
            check.total = to_float(json_data.get("total"), 0)
            check.currency = json_data.get("currency")

            # Сервисный сбор
            service_charge = json_data.get("service_charge")
            if service_charge is not None:
                check.service_charge_name = service_charge.get("name")
                check.service_charge_percentage = to_float(service_charge.get("percentage"))
                check.service_charge_amount = to_float(service_charge.get("amount"))
            else:
                check.service_charge_name = None
                check.service_charge_percentage = None
                check.service_charge_amount = None

            # НДС
            vat = json_data.get("vat", {})
            if vat is not None:
                check.vat_rate = to_float(vat.get("rate"))
                check.vat_amount = to_float(vat.get("amount"))
            else:
                check.vat_rate = None
                check.vat_amount = None

            # Скидка
            discount = json_data.get("discount", {})
            if discount is not None:
                check.discount_percentage = discount.get("discount_percentage")
                check.discount_amount = to_float(discount.get("amount"))
            else:
                check.discount_percentage = None
                check.discount_amount = None

            # Удаляем старые элементы чека
            db.query(CheckItem).filter(CheckItem.check_uuid == check.uuid).delete()

            # Добавляем товары
            for item in json_data.get("items", []):
                item_id = to_int(item.get("id"))
                quantity = to_int(item.get("quantity"))
                sum_value = to_float(item.get("sum"))
                name = item.get("name")

                if item_id is None or quantity is None or sum_value is None or not name:
                    logger.warning(f"Skipping invalid item in check {check.uuid}: {item}")
                    continue

                check_item = CheckItem(
                    check_uuid=check.uuid,
                    item_id=item_id,
                    name=name,
                    quantity=quantity,
                    sum=sum_value
                )
                logger.info(f"Adding item to check {check.uuid}: {item}")
                db.add(check_item)

            # Фиксируем изменения
            logger.info(f"Committing changes for check {check.uuid}")
            db.commit()
            logger.info(f"Successfully migrated check {check.uuid}")

        except Exception as e:
            logger.error(f"Error migrating check {check.uuid}: {str(e)}", exc_info=True)
            db.rollback()
            logger.info(f"Rolled back changes for check {check.uuid}")
            return


# Функция миграции с проверками
def migrate_checks():
    with Session(engine) as db:
        checks = db.execute(select(Check)).scalars().all()
        total_checks = len(checks)
        migrated_count = 0

        logger.info(f"Starting migration for {total_checks} checks")

        for check in checks:
            migrate_check(check.uuid)
            if check.check_data:  # Увеличиваем счетчик только для чеков с данными
                migrated_count += 1

        logger.info(f"Migration completed: {migrated_count}/{total_checks} checks migrated successfully")


# Функция восстановления check_data
def restore_check_data():
    with Session(engine) as db:
        checks = db.execute(select(Check)).scalars().all()
        total_checks = len(checks)
        restored_count = 0

        logger.info(f"Starting restoration of check_data for {total_checks} checks")

        for check in checks:
            try:
                # Формируем JSON-структуру на основе текущих данных
                restored_json = {
                    "restaurant": check.restaurant,
                    "address": check.address,
                    "phone": check.phone,
                    "table_number": check.table_number,
                    "order_number": check.order_number,
                    "date": check.date,
                    "time": check.time,
                    "waiter": check.waiter,
                    "subtotal": check.subtotal,
                    "total": check.total,
                    "currency": check.currency,
                    "service_charge": {
                        "name": check.service_charge_name,
                        "percentage": check.service_charge_percentage,
                        "amount": check.service_charge_amount
                    },
                    "vat": {
                        "rate": check.vat_rate,
                        "amount": check.vat_amount
                    },
                    "discount": {
                        "name": check.discount_percentage,
                        "amount": check.discount_amount
                    },
                    "items": [
                        {
                            "id": item.item_id,
                            "name": item.name,
                            "quantity": item.quantity,
                            "sum": item.sum
                        } for item in db.query(CheckItem).filter(CheckItem.check_uuid == check.uuid).all()
                    ]
                }

                # Записываем восстановленный JSON в check_data
                check.check_data = restored_json

                restored_count += 1
                if restored_count % 100 == 0:
                    logger.info(f"Restored {restored_count}/{total_checks} checks")

            except Exception as e:
                logger.error(f"Error restoring check_data for check {check.uuid}: {str(e)}")
                db.rollback()
                continue

        db.commit()
        logger.info(f"Restoration completed: {restored_count}/{total_checks} checks restored successfully")


def migrate_user_selection_data():
    """
    Функция для миграции данных из JSON-поля selection модели UserSelection
    в новую таблицу SelectedItem. Пропускает записи с пустым списком selected_items.
    """
    with Session(engine) as db:
        # Получаем все записи UserSelection с непустым полем selection
        user_selections = db.query(UserSelection).filter(UserSelection.selection != None).all()

        for user_selection in user_selections:
            try:
                # Извлекаем данные из поля selection
                selection_data = user_selection.selection
                if isinstance(selection_data, str):
                    selection_data = json.loads(selection_data)

                # Проверяем наличие ключа 'selected_items' в данных
                if 'selected_items' in selection_data:
                    selected_items = selection_data['selected_items']

                    # Пропускаем запись, если selected_items — пустой список
                    if not selected_items:  # Проверка на пустой список
                        print(
                            f"Пропущена запись с пустым selected_items для UserSelection(user_id={user_selection.user_id}, check_uuid={user_selection.check_uuid})")
                        continue

                    # Обрабатываем непустой список selected_items
                    for item in selected_items:
                        item_id = item.get('item_id')
                        quantity = item.get('quantity')

                        # Проверяем, что item_id и quantity присутствуют
                        if item_id is not None and quantity is not None:
                            # Создаем новую запись в таблице SelectedItem
                            selected_item = SelectedItem(
                                user_selection_user_id=user_selection.user_id,
                                user_selection_check_uuid=user_selection.check_uuid,
                                item_id=item_id,
                                quantity=quantity
                            )
                            db.add(selected_item)
                        else:
                            print(
                                f"Некорректные данные в selection для UserSelection(user_id={user_selection.user_id}, check_uuid={user_selection.check_uuid}): {item}")
                else:
                    print(
                        f"Отсутствует ключ 'selected_items' в selection для UserSelection(user_id={user_selection.user_id}, check_uuid={user_selection.check_uuid})")

            except Exception as e:
                print(
                    f"Ошибка при обработке UserSelection(user_id={user_selection.user_id}, check_uuid={user_selection.check_uuid}): {e}")
                continue

        # Фиксируем изменения в базе данных
        db.commit()
        print("Миграция данных завершена.")

if __name__ == "__main__":
    # restore_check_data()
    migrate_checks()
    # migrate_check('45b934b7-96ca-44d3-8176-02a17ff4df02')
    migrate_user_selection_data()