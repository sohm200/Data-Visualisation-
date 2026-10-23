"""Decides WHICH charts to make (SRS 4.3). Returns plain chart specifications; draws nothing.

Rules R1-R6 (SRS 4.3.2) produce candidates in the order R1, R2, R5, R4, R3, R6. The first
MAX_CHARTS are kept, with at most MAX_CHARTS_PER_TYPE of any one type (SRS 4.3.3).
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field

import config
from profiler import CATEGORY, DATE, NUMERIC, ColumnProfile, DataWarning, DatasetProfile

log = logging.getLogger("dashboard")

CHART_NAMES = {
    "line": ("line chart", "line charts"),
    "bar": ("bar chart", "bar charts"),
    "pie": ("pie chart", "pie charts"),
    "histogram": ("histogram", "histograms"),
    "scatter": ("scatter plot", "scatter plots"),
    "heatmap": ("correlation heatmap", "correlation heatmaps"),
}
AGG_LABELS = {"sum": "Total", "mean": "Average", "count": "Number of rows"}


@dataclass
class ChartSelection:
    specs: list[dict] = field(default_factory=list)
    warnings: list[DataWarning] = field(default_factory=list)


def select_charts(profile: DatasetProfile) -> ChartSelection:
    selection = ChartSelection()
    candidates: list[dict] = []
    for rule in (line_charts, bar_charts, scatter_charts, histograms, pie_charts, heatmaps):
        try:
            candidates.extend(rule(profile, selection.warnings))
        except Exception:                       # FR-53: a broken rule must not stop the other charts
            log.exception("Chart rule %s failed for %s", rule.__name__, profile.file_name)
            selection.warnings.append(DataWarning("item_failed", f"Some charts ({rule.__name__.replace('_', ' ')}) "
                                                                 "could not be prepared."))

    selection.specs, dropped = apply_limits(candidates)
    if dropped:
        selection.warnings.append(DataWarning("chart_skipped", _dropped_message(dropped)))
    for number, spec in enumerate(selection.specs, start=1):
        spec["id"] = f"chart-{number}"

    if not any(c.type in (NUMERIC, DATE, CATEGORY) for c in profile.columns):
        selection.warnings.append(DataWarning("no_charts", config.MESSAGES["E-08"]))
    return selection


def apply_limits(candidates: list[dict]) -> tuple[list[dict], list[dict]]:
    """FR-44 and SRS 4.3.3: first MAX_CHARTS candidates, at most MAX_CHARTS_PER_TYPE per chart type."""
    chosen, dropped, per_type = [], [], Counter()
    for spec in candidates:
        if len(chosen) < config.MAX_CHARTS and per_type[spec["type"]] < config.MAX_CHARTS_PER_TYPE:
            chosen.append(spec)
            per_type[spec["type"]] += 1
        else:
            dropped.append(spec)
    return chosen, dropped


# --- R1 Line chart ---------------------------------------------------------------------------

def line_charts(profile: DatasetProfile, warnings: list[DataWarning]) -> list[dict]:
    dates, numbers = profile.columns_of(DATE), profile.columns_of(NUMERIC)
    if not dates:
        return []
    date = dates[0]
    if date.distinct_days < config.LINE_MIN_POINTS:
        warnings.append(DataWarning("chart_skipped", f"No line chart: '{date.name}' has only one date."))
        return []

    monthly = date.distinct_days > config.LINE_MONTHLY_AFTER_DATES
    period = "month" if monthly else "day"
    x_label = f"{date.name} (month)" if monthly else date.name
    if not numbers:                             # FR-55: count rows over time instead
        caption = f"Shows how many rows there are for each {period} of {date.name}."
        if monthly:
            caption += f" Grouped by month because there are {date.distinct_days:,} different dates."
        return [{
            "type": "line", "rule": "R1", "x": date.name, "y": None, "agg": "count", "group": period,
            "title": f"Number of rows {'by month' if monthly else 'over time'}",
            "x_label": x_label, "y_label": AGG_LABELS["count"], "caption": caption,
        }]

    specs = []
    for number in numbers:
        agg = _agg(number)
        caption = f"Shows how {AGG_LABELS[agg].lower()} {number.name} changes over {date.name}."
        if monthly:
            caption += f" Grouped by month because there are {date.distinct_days:,} different dates."
        specs.append({
            "type": "line", "rule": "R1", "x": date.name, "y": number.name, "agg": agg, "group": period,
            "title": f"{AGG_LABELS[agg]} {number.name} {'by month' if monthly else 'over time'}",
            "x_label": x_label,
            "y_label": f"{AGG_LABELS[agg]} {_label(number)}",
            "caption": caption,
        })
    return specs


# --- R2 Bar chart ----------------------------------------------------------------------------

def bar_charts(profile: DatasetProfile, warnings: list[DataWarning]) -> list[dict]:
    categories = profile.columns_of(CATEGORY)
    measures: list[ColumnProfile | None] = profile.columns_of(NUMERIC) or [None]
    specs = []
    for measure in measures:                    # every category with the main number column first
        for category in categories:
            agg = _agg(measure) if measure else "count"
            groups = category.unique_count
            if measure:
                title = f"{AGG_LABELS[agg]} {measure.name} by {category.name}"
                caption = f"Compares {AGG_LABELS[agg].lower()} {measure.name} across {groups} {category.name} values."
                y_label = f"{AGG_LABELS[agg]} {_label(measure)}"
            else:
                title = f"Number of rows by {category.name}"
                caption = f"Counts the rows for each of the {groups} {category.name} values."
                y_label = "Number of rows"
            spec = {
                "type": "bar", "rule": "R2", "x": category.name, "y": measure.name if measure else None,
                "agg": agg, "top_n": config.BAR_TOP_N, "title": title, "caption": caption,
                "x_label": category.name, "y_label": y_label,
            }
            if groups > config.BAR_TOP_N:       # FR-46
                left_out = groups - config.BAR_TOP_N
                spec["note"] = (f"Showing the top {config.BAR_TOP_N} of {groups} {category.name} values; "
                                f"{left_out} smaller {'one is' if left_out == 1 else 'ones are'} left out.")
            specs.append(spec)
    return specs


# --- R5 Scatter plot -------------------------------------------------------------------------

def scatter_charts(profile: DatasetProfile, warnings: list[DataWarning]) -> list[dict]:
    if profile.correlations is None:
        return []
    names = [c.name for c in profile.columns_of(NUMERIC)]
    pairs = []
    for i, x in enumerate(names):
        for y in names[i + 1:]:
            r = profile.correlations.loc[x, y]
            if r == r and abs(r) >= config.SCATTER_MIN_CORRELATION:     # r == r skips NaN
                pairs.append((abs(r), x, y, float(r)))
    pairs.sort(key=lambda p: -p[0])

    specs = []
    for _, x, y, r in pairs[:config.SCATTER_MAX_PAIRS]:
        direction = "rise together" if r > 0 else "move in opposite directions"
        spec = {
            "type": "scatter", "rule": "R5", "x": x, "y": y, "correlation": round(r, 2),
            "title": f"{y} vs {x}",
            "x_label": _label(profile.column(x)), "y_label": _label(profile.column(y)),
            "caption": f"{x} and {y} tend to {direction} (correlation {r:+.2f}).",
        }
        points = int(profile.values[[x, y]].notna().all(axis=1).sum())
        if points > config.SCATTER_MAX_POINTS:  # FR-45
            spec["sample"] = config.SCATTER_MAX_POINTS
            spec["note"] = (f"Shows a random sample of {config.SCATTER_MAX_POINTS:,} of {points:,} points. "
                            "The correlation uses all rows.")
            warnings.append(DataWarning("chart_sampled", f"The scatter plot '{spec['title']}' shows a random sample "
                                                         f"of {config.SCATTER_MAX_POINTS:,} of {points:,} points."))
        specs.append(spec)
    return specs


# --- R4 Histogram ----------------------------------------------------------------------------

def histograms(profile: DatasetProfile, warnings: list[DataWarning]) -> list[dict]:
    specs, too_few = [], []
    for number in profile.columns_of(NUMERIC):
        if number.unique_count < config.HISTOGRAM_MIN_UNIQUE:
            too_few.append(number.name)
            continue
        specs.append({
            "type": "histogram", "rule": "R4", "x": number.name,
            "title": f"Spread of {number.name}",
            "x_label": _label(number), "y_label": "Number of rows",
            "caption": f"Shows how {number.name} values are spread across {number.count:,} rows.",
        })
    if too_few:
        listed = ", ".join(f"'{name}'" for name in too_few)
        warnings.append(DataWarning("chart_skipped", f"No histogram for {listed}: fewer than "
                                                     f"{config.HISTOGRAM_MIN_UNIQUE} different values."))
    return specs


# --- R3 Pie chart ----------------------------------------------------------------------------

def pie_charts(profile: DatasetProfile, warnings: list[DataWarning]) -> list[dict]:
    numbers = profile.columns_of(NUMERIC)
    main = numbers[0] if numbers else None
    # A pie needs counts or meaningful totals with no negative numbers (R3).
    measure = main if main and main.total_meaningful and (main.minimum or 0) >= 0 else None

    specs = []
    for category in profile.columns_of(CATEGORY):
        slices = category.unique_count
        if not config.PIE_MIN_SLICES <= slices <= config.PIE_MAX_SLICES:   # FR-14, BR-03
            reason = "only one value" if slices < config.PIE_MIN_SLICES else f"{slices} values"
            warnings.append(DataWarning("chart_skipped", f"No pie chart for '{category.name}': it has {reason}, and pie "
                                                         f"charts are only used for {config.PIE_MIN_SLICES} to "
                                                         f"{config.PIE_MAX_SLICES}. A bar chart is used instead."))
            continue
        if measure:
            title = f"Share of total {measure.name} by {category.name}"
            caption = f"Shows each {category.name} value's share of total {measure.name}."
        else:
            title = f"Share of rows by {category.name}"
            caption = f"Shows how the rows are split across the {slices} {category.name} values."
        specs.append({
            "type": "pie", "rule": "R3", "x": category.name, "y": measure.name if measure else None,
            "agg": "sum" if measure else "count", "title": title, "caption": caption,
        })
    return specs


# --- R6 Correlation heatmap ------------------------------------------------------------------

def heatmaps(profile: DatasetProfile, warnings: list[DataWarning]) -> list[dict]:
    if profile.numeric_count < config.HEATMAP_MIN_NUMERIC or profile.correlations is None:
        return []
    return [{
        "type": "heatmap", "rule": "R6", "columns": [c.name for c in profile.columns_of(NUMERIC)],
        "title": "How the number columns relate",
        "caption": "Shows how strongly each pair of number columns move together, "
                   "from -1 (opposite directions) to +1 (together).",
    }]


# --- Helpers ---------------------------------------------------------------------------------

def _agg(column: ColumnProfile) -> str:
    """Total where a total is meaningful (SRS 4.2.4), otherwise average."""
    return "sum" if column.total_meaningful else "mean"


def _label(column: ColumnProfile) -> str:
    return f"{column.name} ({column.unit})" if column.unit else column.name


def _dropped_message(dropped: list[dict]) -> str:
    counts = Counter(spec["type"] for spec in dropped)
    parts = [f"{n} {CHART_NAMES[kind][0] if n == 1 else CHART_NAMES[kind][1]}" for kind, n in counts.items()]
    total = len(dropped)
    return (f"{total} more chart{'s were' if total != 1 else ' was'} possible but not shown "
            f"(at most {config.MAX_CHARTS} charts, and {config.MAX_CHARTS_PER_TYPE} of each type): "
            f"{', '.join(parts)}.")
