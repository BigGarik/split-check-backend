# src/utils/memory_monitor.py
import asyncio
import gc
import logging
import os
import sys
import tracemalloc
from collections import deque, defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import psutil

from src.config import config

logger = logging.getLogger(config.app.service_name)


class MemoryMonitor:
    """Улучшенный монитор памяти с историей и детальной статистикой"""

    def __init__(self, history_size: int = 60):
        self.process = psutil.Process(os.getpid())
        self.history_size = history_size
        self.memory_history = deque(maxlen=history_size)
        self.start_memory = None
        self.peak_memory = 0
        self.last_memory_mb = None
        self.tracemalloc_enabled = False

    def start_tracemalloc(self):
        """Включить tracemalloc для детального анализа"""
        if not self.tracemalloc_enabled:
            tracemalloc.start()
            self.tracemalloc_enabled = True
            logger.info("Tracemalloc включен для детального анализа памяти")

    def stop_tracemalloc(self):
        """Выключить tracemalloc"""
        if self.tracemalloc_enabled:
            tracemalloc.stop()
            self.tracemalloc_enabled = False

    def get_memory_info(self) -> Dict:
        """Получить текущую информацию о памяти"""
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)

        # CPU и другие метрики
        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            num_threads = self.process.num_threads()
            num_fds = len(self.process.open_files())
        except:
            cpu_percent = 0
            num_threads = 0
            num_fds = 0

        return {
            'timestamp': datetime.now(),
            'memory_mb': round(memory_mb, 2),
            'memory_vms_mb': round(memory_info.vms / (1024 * 1024), 2),
            'cpu_percent': cpu_percent,
            'num_threads': num_threads,
            'num_fds': num_fds
        }

    def get_app_components_stats(self) -> Dict:
        """Получить статистику компонентов приложения"""
        stats = {}

        # WebSocket соединения
        try:
            from src.websockets.manager import ws_manager
            stats['websocket_connections'] = len(ws_manager.active_connections)
        except:
            stats['websocket_connections'] = 0

        # Redis очередь
        try:
            from src.redis.queue_processor import get_queue_processor
            queue_processor = get_queue_processor()
            queue_stats = asyncio.run_coroutine_threadsafe(
                queue_processor.get_stats(),
                asyncio.get_event_loop()
            ).result(timeout=1)
            stats['active_tasks'] = queue_stats['active_tasks_count']
            stats['queue_workers'] = queue_stats['max_workers']
        except:
            stats['active_tasks'] = 0
            stats['queue_workers'] = 0

        # Классификатор
        try:
            from src.services.classifier.classifier_instance import classifier
            stats['classifier_loaded'] = classifier is not None
        except:
            stats['classifier_loaded'] = False

        return stats

    def get_top_memory_consumers(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Получить топ потребителей памяти по типам объектов"""
        if not self.tracemalloc_enabled:
            return []

        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')

        # Группируем по файлам
        file_stats = defaultdict(int)
        for stat in top_stats[:50]:  # Берем топ 50 для анализа
            filename = stat.traceback[0].filename
            # Упрощаем путь
            if '/site-packages/' in filename:
                filename = filename.split('/site-packages/')[-1]
            elif '/src/' in filename:
                filename = 'src/' + filename.split('/src/')[-1]

            file_stats[filename] += stat.size

        # Сортируем и возвращаем топ
        sorted_stats = sorted(file_stats.items(), key=lambda x: x[1], reverse=True)
        return [(f, s / (1024 * 1024)) for f, s in sorted_stats[:limit]]

    def analyze_memory(self) -> Dict:
        """Полный анализ памяти"""
        current_info = self.get_memory_info()

        # Сохраняем историю
        self.memory_history.append(current_info)

        # Обновляем пиковое значение
        if current_info['memory_mb'] > self.peak_memory:
            self.peak_memory = current_info['memory_mb']

        # Инициализируем начальное значение
        if self.start_memory is None:
            self.start_memory = current_info['memory_mb']

        # Сохраняем/рассчитываем изменение памяти с предыдущей проверки
        if self.last_memory_mb is None:
            memory_change = 0.0
        else:
            memory_change = current_info['memory_mb'] - self.last_memory_mb

        self.last_memory_mb = current_info['memory_mb']  # Обновляем на текущее

        # Средняя память за последние N измерений
        if len(self.memory_history) > 0:
            avg_memory = sum(h['memory_mb'] for h in self.memory_history) / len(self.memory_history)
        else:
            avg_memory = current_info['memory_mb']

        # Скорость роста памяти (MB/мин)
        growth_rate = 0
        if len(self.memory_history) >= 2:
            time_diff = (self.memory_history[-1]['timestamp'] - self.memory_history[0][
                'timestamp']).total_seconds() / 60
            if time_diff > 0:
                memory_diff = self.memory_history[-1]['memory_mb'] - self.memory_history[0]['memory_mb']
                growth_rate = memory_diff / time_diff

        analysis = {
            'current': current_info,
            'start_memory_mb': self.start_memory,
            'peak_memory_mb': self.peak_memory,
            'average_memory_mb': round(avg_memory, 2),
            'memory_change_mb': round(memory_change, 2),
            'growth_rate_mb_per_min': round(growth_rate, 3),
            'components': self.get_app_components_stats()
        }

        # Добавляем топ потребителей если включен tracemalloc
        if self.tracemalloc_enabled:
            analysis['top_consumers'] = self.get_top_memory_consumers()

        return analysis

    def format_report(self, analysis: Dict) -> str:
        """Форматировать отчет для логирования"""
        current = analysis['current']
        components = analysis['components']

        lines = [
            f"=== Мониторинг памяти ===",
            f"Память: {current['memory_mb']} MB (VMS: {current['memory_vms_mb']} MB)",
            f"Изменение: {analysis['memory_change_mb']:+.2f} MB с последней проверки",
            f"Пик: {analysis['peak_memory_mb']} MB | Среднее: {analysis['average_memory_mb']} MB",
            f"Рост: {analysis['growth_rate_mb_per_min']:+.3f} MB/мин",
            f"CPU: {current['cpu_percent']}% | Потоки: {current['num_threads']} | Файлы: {current['num_fds']}",
            f"--- Компоненты ---",
            f"WebSocket соединений: {components['websocket_connections']}",
            f"Активных задач: {components['active_tasks']} (воркеров: {components['queue_workers']})",
            f"Классификатор загружен: {'Да' if components['classifier_loaded'] else 'Нет'}"
        ]

        if 'top_consumers' in analysis and analysis['top_consumers']:
            lines.append("--- Топ потребителей памяти ---")
            for filename, size_mb in analysis['top_consumers'][:5]:
                lines.append(f"  {filename}: {size_mb:.2f} MB")

        return "\n".join(lines)


async def monitor_memory_improved(
        monitor: Optional[MemoryMonitor] = None,
        interval: int = 60,
        warning_threshold_mb: float = 500,
        critical_threshold_mb: float = 1000,
        enable_tracemalloc: bool = False
):
    """
    Улучшенная функция мониторинга памяти

    Args:
        monitor: Экземпляр MemoryMonitor (создается автоматически если None)
        interval: Интервал проверки в секундах
        warning_threshold_mb: Порог для предупреждения
        critical_threshold_mb: Критический порог
        enable_tracemalloc: Включить детальный анализ (может влиять на производительность)
    """
    if monitor is None:
        monitor = MemoryMonitor()

    # Включаем tracemalloc если нужно
    if enable_tracemalloc and not monitor.tracemalloc_enabled:
        monitor.start_tracemalloc()

    logger.info("Запущен улучшенный мониторинг памяти")

    try:
        while True:
            # Собираем мусор перед анализом
            gc.collect()

            # Анализируем память
            analysis = monitor.analyze_memory()
            current_memory = analysis['current']['memory_mb']

            # Определяем уровень логирования
            if current_memory > critical_threshold_mb:
                log_level = logging.ERROR

                # При критическом уровне включаем tracemalloc если не включен
                if not monitor.tracemalloc_enabled:
                    monitor.start_tracemalloc()
                    logger.warning("Включен tracemalloc из-за высокого потребления памяти")

            elif current_memory > warning_threshold_mb:
                log_level = logging.WARNING
            else:
                log_level = logging.INFO

            # Логируем отчет
            report = monitor.format_report(analysis)
            logger.log(log_level, f"\n{report}")

            # Проверяем скорость роста
            growth_rate = analysis['growth_rate_mb_per_min']
            if growth_rate > 1.0:  # Более 1 MB/мин
                logger.warning(f"⚠️ Обнаружен быстрый рост памяти: {growth_rate:.3f} MB/мин")

            # Ждем следующей итерации
            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        logger.info("Мониторинг памяти остановлен")
        if monitor.tracemalloc_enabled:
            monitor.stop_tracemalloc()
        raise
    except Exception as e:
        logger.exception(f"Ошибка в мониторе памяти: {e}")
        raise