"""시계열 요약·통계. 순수 파이썬이라 Firestore·OpenAI 없이 시험할 수 있다."""
from collections import defaultdict
from statistics import mean
from typing import Dict, List


def _sorted(rows: List[Dict]) -> List[Dict]:
    return sorted((r for r in rows if r.get("date") is not None), key=lambda r: str(r["date"]))


def _pct(a: float, b: float) -> float:
    return round((a - b) / b * 100, 1) if b else 0.0


def build_summary(rows: List[Dict]) -> Dict:
    """기간·개수·기본 통계·최근 추세. /api/data/summary 와 시스템 프롬프트가 쓴다."""
    rs = _sorted(rows)
    if not rs:
        return {"period": "데이터 없음", "count": 0, "metrics": {}, "trend": "판단 불가", "latest": None}
    vals = [float(r["value"]) for r in rs]
    mx = max(rs, key=lambda r: r["value"])
    mn = min(rs, key=lambda r: r["value"])
    last = rs[-1]
    if len(vals) >= 6:  # 최근 3개월 평균 vs 직전 3개월 평균
        recent, prev = mean(vals[-3:]), mean(vals[-6:-3])
        ch = _pct(recent, prev)
        word = "상승" if ch > 5 else "하락" if ch < -5 else "유지"
        trend = f"{word} (최근 3개월 평균 {ch:+.1f}%, 직전 3개월 대비)"
    else:
        trend = "데이터 부족"
    by_ym = {str(r["date"])[:7]: float(r["value"]) for r in rs}
    ly = f"{int(str(last['date'])[:4]) - 1}{str(last['date'])[4:7]}"
    yoy = _pct(float(last["value"]), by_ym[ly]) if ly in by_ym else None
    return {
        "period": f"{str(rs[0]['date'])[:7]} ~ {str(last['date'])[:7]}",
        "count": len(rs),
        "metrics": {
            "total": round(sum(vals)),
            "average": round(mean(vals)),
            "max": round(mx["value"]), "max_date": str(mx["date"])[:7],
            "min": round(mn["value"]), "min_date": str(mn["date"])[:7],
        },
        "trend": trend,
        "latest": {"date": str(last["date"])[:7], "value": round(float(last["value"])), "yoy_pct": yoy},
    }


def build_statistics(rows: List[Dict]) -> Dict:
    """추가 지표: 연도별 합계, 1–12월 평균(계절성), 가장 붐비는 달, 전년 동월 대비 시계열."""
    rs = _sorted(rows)
    by_year, by_month, by_ym = defaultdict(float), defaultdict(list), {}
    for r in rs:
        d = str(r["date"])
        by_year[d[:4]] += float(r["value"])
        by_month[int(d[5:7])].append(float(r["value"]))
        by_ym[d[:7]] = float(r["value"])
    month_avg = {m: round(mean(v)) for m, v in sorted(by_month.items())}
    yoy = []
    for ym, v in by_ym.items():
        prev = f"{int(ym[:4]) - 1}{ym[4:]}"
        if prev in by_ym:
            yoy.append({"date": ym, "yoy_pct": _pct(v, by_ym[prev])})
    return {
        "yearly_total": {y: round(v) for y, v in sorted(by_year.items())},
        "month_average": month_avg,
        "busiest_month": max(month_avg, key=month_avg.get) if month_avg else None,
        "quietest_month": min(month_avg, key=month_avg.get) if month_avg else None,
        "yoy_series": yoy[-24:],
    }


def recent_rows(rows: List[Dict], n: int = 12) -> List[Dict]:
    return [{"date": str(r["date"])[:7], "value": round(float(r["value"])), "memo": r.get("memo", "")}
            for r in _sorted(rows)[-n:]]
