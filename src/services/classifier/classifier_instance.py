# src/services/classifier/classifier_instance.py
from src.services.classifier.classifier import AsyncImageClassifier

# Переменная для хранения экземпляра AsyncImageClassifier
classifier = None


def init_classifier():
    """Инициализация и возврат глобального экземпляра классификатора"""
    global classifier
    if classifier is None:
        # Изменяем параметры: уменьшаем batch_size и num_threads
        classifier = AsyncImageClassifier(batch_size=1, num_threads=2)
    return classifier


def get_classifier():
    """Возвращает экземпляр классификатора, если он был инициализирован"""
    if classifier is None:
        raise RuntimeError("Classifier is not initialized. Call `init_classifier` first.")
    return classifier
