def recalculate_check_totals(check_data: dict) -> dict:
    """Пересчет всех полей чека"""

    # Пересчитываем subtotal (сумма всех items)
    subtotal = sum(
        item["price"]  # * item["quantity"]
        for item in check_data.get("items", [])
    )
    check_data["subtotal"] = subtotal

    # Пересчитываем VAT если есть ставка
    vat_rate = check_data.get("vat", {}).get("rate", 0)
    if vat_rate:
        vat_amount = (subtotal * vat_rate) / 100
        check_data["vat"] = {
            "rate": vat_rate,
            "amount": round(vat_amount, 2)
        }
    else:
        check_data["vat"] = {
            "rate": 0,
            "amount": 0
        }

    # Пересчитываем service charge если есть
    service_charge = check_data.get("service_charge", {})
    service_charge_name = service_charge.get("name", "")
    if service_charge_name:
        import re
        if match := re.search(r'\((\d+)%\)', service_charge_name):
            service_rate = float(match.group(1))
            service_amount = (subtotal * service_rate) / 100
            check_data["service_charge"] = {
                "name": service_charge_name,
                "amount": round(service_amount, 2)
            }
    else:
        check_data["service_charge"] = {
            "name": "",
            "amount": 0
        }

    # Пересчитываем total (subtotal + vat + service charge)
    total = (
            check_data["subtotal"] +
            check_data["vat"]["amount"] +
            check_data["service_charge"]["amount"]
    )
    check_data["total"] = round(total, 2)

    return check_data
