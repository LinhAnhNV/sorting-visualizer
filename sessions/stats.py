# Thống kê trên danh sách Session (lấy từ SessionManager.sessions)


def _avg(total, count):
    return round(total / count, 2) if count else 0


def summarize(sessions):
    """Thống kê tổng quan cho toàn bộ session."""
    total = len(sessions)
    total_swaps = sum(s.swaps for s in sessions)
    total_comparisons = sum(s.comparisons for s in sessions)
    total_elements = sum(len(s.values) for s in sessions)

    most_used = None
    if sessions:
        counts = {}
        for s in sessions:
            counts[s.algorithm] = counts.get(s.algorithm, 0) + 1
        most_used = max(counts, key=counts.get)

    return {
        "total_sessions": total,
        "total_swaps": total_swaps,
        "total_comparisons": total_comparisons,
        "avg_swaps": _avg(total_swaps, total),
        "avg_comparisons": _avg(total_comparisons, total),
        "avg_size": _avg(total_elements, total),
        "most_used_algorithm": most_used,
    }


def by_algorithm(sessions):
    """Thống kê riêng cho từng thuật toán: {tên: {count, avg_swaps, avg_comparisons, avg_size}}."""
    groups = {}
    for s in sessions:
        groups.setdefault(s.algorithm, []).append(s)

    result = {}
    for name, items in groups.items():
        count = len(items)
        result[name] = {
            "count": count,
            "avg_swaps": _avg(sum(i.swaps for i in items), count),
            "avg_comparisons": _avg(sum(i.comparisons for i in items), count),
            "avg_size": _avg(sum(len(i.values) for i in items), count),
        }
    return result


def format_report(sessions):
    """Trả về đoạn text thống kê để hiển thị lên giao diện."""
    info = summarize(sessions)
    if info["total_sessions"] == 0:
        return "Chưa có session nào."

    lines = [
        f"Tổng số session: {info['total_sessions']}",
        f"Thuật toán dùng nhiều nhất: {info['most_used_algorithm']}",
        f"Trung bình: {info['avg_swaps']} swaps, {info['avg_comparisons']} so sánh, "
        f"{info['avg_size']} phần tử",
        "",
        "Theo từng thuật toán:",
    ]
    for name, st in sorted(by_algorithm(sessions).items()):
        lines.append(
            f"  - {name}: {st['count']} lần | TB {st['avg_swaps']} swaps, "
            f"{st['avg_comparisons']} so sánh"
        )
    return "\n".join(lines)