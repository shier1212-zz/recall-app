"""SM-2 遗忘曲线复习排程算法。"""
from datetime import datetime, timedelta


def sm2(repetitions: int, ease: float, interval_days: int, quality: int):
    """SM-2 单次复习更新。

    :param repetitions: 连续正确次数
    :param ease: 易度因子（初始 2.5）
    :param interval_days: 当前间隔天数
    :param quality: 自评质量 0-5（5=完全掌握，3=犹豫，<3=遗忘）
    :return: (repetitions, ease, interval_days)
    """
    if quality >= 3:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval_days * ease)
        repetitions += 1
        ease = max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    else:
        repetitions = 0
        interval = 1
        ease = max(1.3, ease - 0.2)
    return repetitions, ease, interval


def next_review_date(last_review: datetime, interval_days: int) -> datetime:
    """根据间隔天数计算下次复习日期。"""
    return last_review + timedelta(days=interval_days)
