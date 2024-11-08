

def create_event_message(message_type: str, payload: dict) -> dict:
    """Создает сообщение для всех участников."""
    return {
        "type": message_type,
        "payload": payload
    }


def create_event_status_message(message_type: str, status: str, message: str = "") -> dict:
    """Создает сообщение для всех участников."""
    return {
        "type": message_type,
        "status": status,
        "message": message
    }
