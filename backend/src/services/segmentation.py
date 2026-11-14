import math
import statistics

MAX_SAMPLES = 5000
DEFAULT_MIN_SEGMENT_LENGTH = 5
DEFAULT_CHANGE_PENALTY = 0.001
# 浮点求和顺序不同会让同一代价在末位出现差异；仅在拼接前/后缀最优代价时容差，
# 判断"代价更低"与"代价相同"仍用严格比较。
_SUM_TOLERANCE = 1e-12


def _validate_parameters(min_length, penalty):
    if isinstance(min_length, bool) or not isinstance(min_length, int):
        raise ValueError('最短段长必须为整数')
    if min_length < 1:
        raise ValueError('最短段长至少为1次观测')
    if not math.isfinite(penalty) or penalty <= 0:
        raise ValueError('变点惩罚值必须为正有限数')


def _same_total(left, right):
    return math.isclose(left, right, rel_tol=_SUM_TOLERANCE, abs_tol=0.0)


def _prefix_sums(values):
    n = len(values)
    origin = math.fsum(values) / n
    first = [0.0] * (n + 1)
    second = [0.0] * (n + 1)
    total = squares = 0.0
    for index, value in enumerate(values, 1):
        deviation = value - origin
        total += deviation
        squares += deviation * deviation
        first[index] = total
        second[index] = squares
    return first, second


def _forward(first, second, n, min_length, penalty):
    """cost[end]：前缀[0,end)的最小代价，count[end]：该代价下最少变点数。"""
    inf = float('inf')
    cost = [inf] * (n + 1)
    count = [0] * (n + 1)
    cost[0] = 0.0
    for end in range(min_length, n + 1):
        s1e, s2e = first[end], second[end]
        best = inf
        best_count = 0
        for start in range(0, end - min_length + 1):
            base = cost[start]
            if base == inf:
                continue
            length = end - start
            delta = s1e - first[start]
            rss = s2e - second[start] - delta * delta / length
            if rss < 0.0:
                rss = 0.0
            candidate = base + rss + (penalty if start else 0.0)
            candidate_count = count[start] + (1 if start else 0)
            if candidate < best:
                best, best_count = candidate, candidate_count
            elif candidate == best and candidate_count < best_count:
                best_count = candidate_count
        cost[end] = best
        count[end] = best_count
    return cost, count


def _backward(first, second, n, min_length, penalty):
    """tail[start]：后缀[start,n)的最小代价（含内部变点惩罚），及对应最少变点数。"""
    inf = float('inf')
    tail = [inf] * (n + 1)
    count = [0] * (n + 1)
    tail[n] = 0.0
    for start in range(n - min_length, -1, -1):
        s1s, s2s = first[start], second[start]
        best = inf
        best_count = 0
        for end in range(start + min_length, n + 1):
            base = tail[end]
            if base == inf:
                continue
            length = end - start
            delta = first[end] - s1s
            rss = second[end] - s2s - delta * delta / length
            if rss < 0.0:
                rss = 0.0
            candidate = rss + (penalty if end < n else 0.0) + base
            candidate_count = (1 if end < n else 0) + count[end]
            if candidate < best:
                best, best_count = candidate, candidate_count
            elif candidate == best and candidate_count < best_count:
                best_count = candidate_count
        tail[start] = best
        count[start] = best_count
    return tail, count


def _reconstruct(first, second, n, min_length, penalty, cost, count, tail, tail_count):
    """从前往后逐边界取最早可行位置：同代价先最少变点，再让变点位置依次靠前。"""
    target_cost, target_count = cost[n], count[n]
    starts = [0]
    position = 0
    accumulated = 0.0
    accumulated_count = 0
    while position < n:
        chosen = -1
        for end in range(position + min_length, n + 1):
            if tail[end] == float('inf'):
                continue
            length = end - position
            delta = first[end] - first[position]
            rss = second[end] - second[position] - delta * delta / length
            if rss < 0.0:
                rss = 0.0
            edge = accumulated + rss + (penalty if end < n else 0.0)
            edge_count = accumulated_count + (1 if end < n else 0) + tail_count[end]
            if edge_count != target_count:
                continue
            if not _same_total(edge + tail[end], target_cost):
                continue
            chosen = end
            break
        if chosen < 0:
            raise ValueError('无法重建全局最优分段，请检查最短段长与惩罚值')
        length = chosen - position
        delta = first[chosen] - first[position]
        rss = second[chosen] - second[position] - delta * delta / length
        if rss < 0.0:
            rss = 0.0
        accumulated += rss + (penalty if chosen < n else 0.0)
        accumulated_count += 1 if chosen < n else 0
        starts.append(chosen)
        position = chosen
    return starts


def segment_series(rows, min_length=DEFAULT_MIN_SEGMENT_LENGTH, penalty=DEFAULT_CHANGE_PENALTY):
    """对监控实测值做变点分段：最小化各段残差平方和 + 惩罚值×变点数。

    只用原始实测值和原观测序号；同代价先取变点更少的分段，
    仍相同则依次比较变点位置，取更靠前的分段。
    """
    _validate_parameters(min_length, penalty)
    if not rows:
        raise ValueError('监控区间没有观测，无法分段')
    if len(rows) > MAX_SAMPLES:
        raise ValueError(f'分段最多支持{MAX_SAMPLES}次观测')
    values = [row['value'] for row in rows]
    if any(not math.isfinite(value) for value in values):
        raise ValueError('监控数据含非有限值，无法分段')
    n = len(values)
    if n < min_length:
        raise ValueError(f'监控区间只有{n}次观测，少于最短段长{min_length}，无法分段')
    first, second = _prefix_sums(values)
    cost, count = _forward(first, second, n, min_length, penalty)
    if cost[n] == float('inf'):
        raise ValueError('在最短段长约束下无法完成分段')
    tail, tail_count = _backward(first, second, n, min_length, penalty)
    starts = _reconstruct(first, second, n, min_length, penalty, cost, count, tail, tail_count)
    segments = []
    for index, (start, end) in enumerate(zip(starts, starts[1:]), 1):
        chunk = values[start:end]
        mean = statistics.mean(chunk)
        rss = math.fsum((value - mean) ** 2 for value in chunk)
        segments.append({
            'index': index,
            'sequence_start': rows[start]['sequence'],
            'sequence_end': rows[end - 1]['sequence'],
            'sample_count': end - start,
            'mean': mean,
            'rss': rss,
        })
    change_count = len(segments) - 1
    rss_total = math.fsum(segment['rss'] for segment in segments)
    penalty_total = penalty * change_count
    # 分段代价按定义重算，便于页面与报告核对
    total_cost = rss_total + penalty_total
    return {
        'min_segment_length': min_length,
        'change_penalty': penalty,
        'sample_count': n,
        'change_count': change_count,
        'change_points': [segment['sequence_start'] for segment in segments[1:]],
        'segments': segments,
        'rss_total': rss_total,
        'penalty_total': penalty_total,
        'total_cost': total_cost,
    }
