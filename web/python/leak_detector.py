# leak_detector.py
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class LeakDetector:
    """Детектор утечек воды без изменений БД"""

    def __init__(self):
        self.config = {
            'max_continuous_minutes': 60,  # 1 час непрерывно - подозрительно
            'night_hours': (0, 6),  # Ночное время 00:00-06:00
            'min_interval_minutes': 5,  # Менее 5 минут между изменениями - активно
            'high_consumption_multiplier': 3,  # В 3 раза выше нормы - утечка
        }

    def _ensure_naive(self, dt):
        """Преобразует datetime в naive (без timezone) для сравнения"""
        if dt is None:
            return datetime.now()
        if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt

    def analyze_device(self, device_changes: List[Dict], step_increment: float, 
                      current_value: float, serial_number: str) -> List[Dict]:
        """Анализирует данные устройства на наличие утечек"""

        if not device_changes or len(device_changes) < 3:
            return []

        # Преобразуем все временные метки в naive для корректного сравнения
        processed_changes = []
        for change in device_changes:
            if 'moment' in change and change['moment']:
                # Создаем копию и преобразуем время
                change_copy = change.copy()
                change_copy['moment'] = self._ensure_naive(change['moment'])
                processed_changes.append(change_copy)

        alerts = []

        # 1. Проверка на слишком долгое непрерывное использование
        long_usage = self._detect_long_continuous_usage(processed_changes, step_increment)
        if long_usage:
            alerts.append(long_usage)

        # 2. Проверка на ночные утечки
        night_leak = self._detect_night_leaks(processed_changes, step_increment)
        if night_leak:
            alerts.append(night_leak)

        # 3. Проверка на аномально высокую скорость потребления
        if len(processed_changes) > 10:
            high_rate = self._detect_high_consumption_rate(processed_changes, step_increment)
            if high_rate:
                alerts.append(high_rate)

        # Добавляем информацию об устройстве к каждому алерту
        for alert in alerts:
            alert['device_serial'] = serial_number
            alert['current_value'] = current_value
            alert['detected_at'] = datetime.now().strftime('%d.%m.%Y %H:%M')

        return alerts

    def _detect_long_continuous_usage(self, changes: List[Dict], step_increment: float) -> Dict:
        """Обнаружение слишком долгого непрерывного использования"""
        if not changes:
            return None

        # Сортируем по времени
        sorted_changes = sorted(changes, key=lambda x: x['moment'])

        continuous_start = None
        current_segment = []
        suspicious_segments = []

        for i in range(1, len(sorted_changes)):
            # Вычисляем разницу во времени
            time_diff = (sorted_changes[i]['moment'] - sorted_changes[i-1]['moment']).total_seconds()

            if time_diff <= self.config['min_interval_minutes'] * 60:
                # Продолжается использование
                if continuous_start is None:
                    continuous_start = sorted_changes[i-1]['moment']
                    current_segment = [sorted_changes[i-1]]
                current_segment.append(sorted_changes[i])
            else:
                # Большой перерыв
                if continuous_start is not None:
                    duration = (sorted_changes[i-1]['moment'] - continuous_start).total_seconds() / 60
                    if duration > self.config['max_continuous_minutes']:
                        suspicious_segments.append({
                            'start': continuous_start.strftime('%d.%m.%Y %H:%M'),
                            'end': sorted_changes[i-1]['moment'].strftime('%d.%m.%Y %H:%M'),
                            'duration_minutes': round(duration, 1),
                            'volume': len(current_segment) * step_increment
                        })
                continuous_start = None
                current_segment = []

        # Проверяем последний сегмент
        if continuous_start is not None:
            duration = (sorted_changes[-1]['moment'] - continuous_start).total_seconds() / 60
            if duration > self.config['max_continuous_minutes']:
                suspicious_segments.append({
                    'start': continuous_start.strftime('%d.%m.%Y %H:%M'),
                    'end': sorted_changes[-1]['moment'].strftime('%d.%m.%Y %H:%M'),
                    'duration_minutes': round(duration, 1),
                    'volume': len(current_segment) * step_increment
                })

        if suspicious_segments:
            total_duration = sum(s['duration_minutes'] for s in suspicious_segments)
            total_volume = sum(s['volume'] for s in suspicious_segments)

            return {
                'type': 'long_continuous_usage',
                'severity': 'high' if total_duration > 120 else 'medium',
                'message': f'Непрерывное использование воды {len(suspicious_segments)} раз(а)',
                'details': {
                    'segments': suspicious_segments,
                    'total_duration_minutes': round(total_duration, 1),
                    'total_volume': round(total_volume, 3)
                },
                'recommendation': 'Проверьте краны и сантехнику на протечки'
            }

        return None

    def _detect_night_leaks(self, changes: List[Dict], step_increment: float) -> Dict:
        """Обнаружение утечек в ночное время"""
        night_changes = []
        for change in changes:
            # Используем naive datetime для сравнения часов
            if self.config['night_hours'][0] <= change['moment'].hour < self.config['night_hours'][1]:
                night_changes.append(change)

        if len(night_changes) >= 3:  # 3+ изменения за ночь
            night_volume = len(night_changes) * step_increment

            return {
                'type': 'night_usage',
                'severity': 'high' if night_volume > 0.5 else 'medium',
                'message': f'Подозрительная активность ночью: {len(night_changes)} изменений',
                'details': {
                    'night_changes_count': len(night_changes),
                    'night_volume': round(night_volume, 3),
                    'period': f'{self.config["night_hours"][0]}:00-{self.config["night_hours"][1]}:00'
                },
                'recommendation': 'Проверьте туалетный бачок и скрытые протечки'
            }

        return None

    def _detect_high_consumption_rate(self, changes: List[Dict], step_increment: float) -> Dict:
        """Обнаружение аномально высокой скорости потребления"""
        now = datetime.now()
        two_hours_ago = now - timedelta(hours=2)

        # Анализируем последние 2 часа
        recent_changes = [c for c in changes if c['moment'] >= two_hours_ago]

        if len(recent_changes) < 5:
            return None

        # Вычисляем текущую скорость (м³/час)
        recent_changes_sorted = sorted(recent_changes, key=lambda x: x['moment'])
        time_span = (recent_changes_sorted[-1]['moment'] - recent_changes_sorted[0]['moment']).total_seconds() / 3600
        if time_span < 0.1:  # Менее 6 минут
            time_span = 0.1

        current_rate = (len(recent_changes) * step_increment) / time_span

        # Сравниваем с исторической нормой (последние 7 дней)
        week_ago = now - timedelta(days=7)
        historical_changes = [c for c in changes if c['moment'] >= week_ago]

        if len(historical_changes) < 20:
            return None

        # Вычисляем среднюю часовую норму
        historical_changes_sorted = sorted(historical_changes, key=lambda x: x['moment'])
        historical_time_span = (historical_changes_sorted[-1]['moment'] - historical_changes_sorted[0]['moment']).total_seconds() / 3600
        if historical_time_span < 1:
            historical_time_span = 1

        historical_rate = (len(historical_changes) * step_increment) / historical_time_span

        # Если текущая скорость в N раз выше нормы
        if historical_rate > 0 and current_rate > historical_rate * self.config['high_consumption_multiplier']:
            ratio = current_rate / historical_rate

            return {
                'type': 'high_consumption_rate',
                'severity': 'critical' if ratio > 5 else 'high',
                'message': f'Скорость потребления {current_rate:.2f} м³/ч (в {ratio:.1f} раз выше нормы)',
                'details': {
                    'current_rate': round(current_rate, 2),
                    'historical_rate': round(historical_rate, 2),
                    'ratio': round(ratio, 1)
                },
                'recommendation': 'Возможна прорывная утечка, проверьте систему немедленно!'
            }

        return None