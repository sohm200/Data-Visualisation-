"""Turns chart specifications into Plotly charts, and formats values for the dashboard (SRS 4.3, 4.4).

All spreadsheet text placed in a chart (titles, labels, category names) is HTML-escaped first
(NFR-10). Data is aggregated or binned here so the page only carries what each chart shows.
"""

from __future__ import annotations

import html
import logging
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from markupsafe import Markup

import config
from profiler import DataWarning, DatasetProfile

log = logging.getLogger("dashboard")

# Reference data-viz palette: slot-1 blue for single series, fixed categorical order for pies.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
DE_EMPHASIS = "#c9c8c1"
DIVERGING = [[0.0, "#e34948"], [0.5, "#f0efec"], [1.0, "#2a78d6"]]
FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'

CHART_HELP = {
    "line": "Line chart: how a number changes over time. The highest and lowest points are marked.",
    "bar": "Bar chart: compares a number across groups, largest first. The largest bar is highlighted.",
    "pie": "Pie chart: how a whole is split into a few parts. Used only for 2 to 6 parts.",
    "histogram": "Histogram: how values are spread out. Taller bars mean more rows fall in that range.",
    "scatter": "Scatter plot: each dot is one row. Dots forming a rising or falling band mean the two columns are related.",
    "heatmap": "Correlation heatmap: blue squares mean two columns rise together, red means one rises as the other falls, grey means no clear link.",
}


class NothingToDraw(Exception):
    """The chart's columns have no usable rows together, so the chart is skipped (FR-17)."""


@dataclass
class RenderedChart:
    id: str
    type: str
    title: str
    caption: str
    note: str | None
    figure_json: Markup         # safe to place inside <script type="application/json">
    download_name: str


def render_charts(specs: list[dict], profile: DatasetProfile) -> tuple[list[RenderedChart], list[DataWarning]]:
    charts, warnings = [], []
    for spec in specs:
        try:
            figure = DRAWERS[spec["type"]](spec, profile)
        except NothingToDraw as reason:
            warnings.append(DataWarning("chart_skipped", f"The chart '{spec['title']}' was skipped: {reason}"))
            continue
        except Exception:                       # FR-53
            log.exception("Chart %r (%s) failed for %s", spec.get("title"), spec.get("rule"), profile.file_name)
            warnings.append(DataWarning("item_failed", f"The chart '{spec['title']}' could not be drawn."))
            continue
        charts.append(RenderedChart(
            id=spec["id"], type=spec["type"], title=spec["title"], caption=spec["caption"],
            note=spec.get("note"), figure_json=_script_safe_json(figure.to_json()),
            download_name=_download_name(spec["title"]),
        ))
    return charts, warnings


# --- Chart types -----------------------------------------------------------------------------

def line_figure(spec: dict, profile: DatasetProfile) -> go.Figure:
    columns = [spec["x"], spec["y"]] if spec["y"] else [spec["x"]]
    frame = profile.values[columns].dropna()
    if spec["group"] == "month":
        key = frame[spec["x"]].dt.to_period("M").dt.to_timestamp()
    else:
        key = frame[spec["x"]].dt.normalize()
    if spec["y"]:
        points = frame.groupby(key)[spec["y"]].agg(spec["agg"]).sort_index()
    else:                                       # FR-55: number of rows per period
        points = frame.groupby(key).size().sort_index()
    if len(points) < config.LINE_MIN_POINTS:
        raise NothingToDraw("there are not enough dates with a value.")

    date_format = "%b %Y" if spec["group"] == "month" else "%d %b %Y"
    figure = go.Figure(go.Scatter(
        x=points.index, y=points.values, mode="lines+markers" if len(points) <= 60 else "lines",
        line=dict(color=SERIES[0], width=2), marker=dict(size=6, color=SERIES[0]),
        hovertemplate=(f"%{{x|{date_format}}}<br>{_hover(spec['y_label'])}: "
                       f"%{{y:{',.0f' if spec['agg'] == 'count' else ',.2f'}}}<extra></extra>"),
    ))

    # FR-16: mark the highest and lowest points.
    extremes = [("Highest", points.idxmax(), points.max(), 1)]
    if points.min() != points.max():
        extremes.append(("Lowest", points.idxmin(), points.min(), -1))
    figure.add_trace(go.Scatter(
        x=[e[1] for e in extremes], y=[e[2] for e in extremes], mode="markers", hoverinfo="skip",
        marker=dict(size=11, color=SERIES[0], line=dict(color=SURFACE, width=2)),
    ))
    for label, x, y, direction in extremes:
        figure.add_annotation(
            x=x, y=y, text=f"{label}: {format_number(y)}", showarrow=True, arrowhead=0, arrowcolor=MUTED,
            ax=0, ay=-28 * direction, font=dict(color=INK, size=12), bgcolor=SURFACE,
        )
    figure.update_layout(**_layout(spec["title"], spec["x_label"], spec["y_label"]))
    figure.update_xaxes(type="date")
    return figure


def bar_figure(spec: dict, profile: DatasetProfile) -> go.Figure:
    grouped = _group_values(spec, profile).sort_values(ascending=False).head(spec["top_n"])
    # FR-16: highlight the largest bar, grey the rest; label only that bar.
    colors = [SERIES[0]] + [DE_EMPHASIS] * (len(grouped) - 1)
    labels = [format_number(grouped.iloc[0])] + [""] * (len(grouped) - 1)
    figure = go.Figure(go.Bar(
        x=[_text(v) for v in grouped.index], y=grouped.values, marker=dict(color=colors),
        text=labels, textposition="outside", cliponaxis=False, textfont=dict(color=INK),
        hovertemplate=f"%{{x}}<br>{_hover(spec['y_label'])}: %{{y:,.2f}}<extra></extra>",
    ))
    figure.update_layout(**_layout(spec["title"], spec["x_label"], spec["y_label"]), bargap=0.3)
    figure.update_xaxes(type="category")
    return figure


def pie_figure(spec: dict, profile: DatasetProfile) -> go.Figure:
    grouped = _group_values(spec, profile).sort_values(ascending=False)
    figure = go.Figure(go.Pie(
        labels=[_text(v) for v in grouped.index], values=grouped.values, sort=False, direction="clockwise",
        marker=dict(colors=list(SERIES[:len(grouped)]), line=dict(color=SURFACE, width=2)),
        textinfo="label+percent", textposition="inside", insidetextorientation="horizontal",
        hovertemplate="%{label}<br>%{value:,.2f} (%{percent})<extra></extra>",
    ))
    figure.update_layout(**{**_layout(spec["title"]), "showlegend": True,
                            "legend": dict(orientation="h", y=-0.05, font=dict(color=INK_SECONDARY))})
    return figure


def histogram_figure(spec: dict, profile: DatasetProfile) -> go.Figure:
    values = profile.values[spec["x"]].dropna().to_numpy(dtype=float)
    if not len(values):
        raise NothingToDraw("the column has no numbers.")
    counts, edges = np.histogram(values, bins=bin_count(values))
    figure = go.Figure(go.Bar(
        x=(edges[:-1] + edges[1:]) / 2, y=counts, width=np.diff(edges),
        customdata=np.column_stack([edges[:-1], edges[1:]]),
        marker=dict(color=SERIES[0], line=dict(color=SURFACE, width=1)),
        hovertemplate="%{customdata[0]:,.2f} to %{customdata[1]:,.2f}<br>Rows: %{y:,}<extra></extra>",
    ))
    figure.update_layout(**_layout(spec["title"], spec["x_label"], spec["y_label"]), bargap=0)
    return figure


def scatter_figure(spec: dict, profile: DatasetProfile) -> go.Figure:
    frame = profile.values[[spec["x"], spec["y"]]].dropna()
    if spec.get("sample") and len(frame) > spec["sample"]:        # FR-45
        frame = frame.sample(n=spec["sample"], random_state=config.SCATTER_SAMPLE_SEED)
    figure = go.Figure(go.Scatter(
        x=frame[spec["x"]].to_numpy(), y=frame[spec["y"]].to_numpy(), mode="markers",
        marker=dict(size=7, color=SERIES[0], opacity=0.55, line=dict(color=SURFACE, width=0.5)),
        hovertemplate=(f"{_hover(spec['x_label'])}: %{{x:,.2f}}<br>"
                       f"{_hover(spec['y_label'])}: %{{y:,.2f}}<extra></extra>"),
    ))
    figure.update_layout(**_layout(spec["title"], spec["x_label"], spec["y_label"]))
    return figure


def heatmap_figure(spec: dict, profile: DatasetProfile) -> go.Figure:
    columns = spec["columns"]
    matrix = profile.correlations.loc[columns, columns].round(2)
    labels = [_text(c) for c in columns]
    figure = go.Figure(go.Heatmap(
        z=matrix.to_numpy(), x=labels, y=labels, zmin=-1, zmax=1, colorscale=DIVERGING,
        texttemplate="%{z:.2f}" if len(columns) <= 12 else None, textfont=dict(color=INK),
        xgap=2, ygap=2, colorbar=dict(title=dict(text="Correlation"), thickness=12),
        hovertemplate="%{y} and %{x}<br>Correlation: %{z:.2f}<extra></extra>",
    ))
    figure.update_layout(**_layout(spec["title"]))
    figure.update_xaxes(type="category", showgrid=False, tickangle=-30)
    figure.update_yaxes(type="category", showgrid=False, autorange="reversed")
    return figure


DRAWERS = {
    "line": line_figure, "bar": bar_figure, "pie": pie_figure,
    "histogram": histogram_figure, "scatter": scatter_figure, "heatmap": heatmap_figure,
}


def bin_count(values: np.ndarray) -> int:
    """R4 automatic bins: the larger of the Sturges and Freedman-Diaconis counts, capped for readability."""
    n = len(values)
    low, high = float(values.min()), float(values.max())
    if n < 2 or low == high:
        return 1
    sturges = math.ceil(math.log2(n)) + 1
    q25, q75 = np.percentile(values, [25, 75])
    if q75 > q25:
        width = 2 * (q75 - q25) * n ** (-1 / 3)
        bins = max(sturges, math.ceil((high - low) / width))
    else:
        bins = sturges
    return int(min(bins, config.HISTOGRAM_MAX_BINS))


# --- Value formatting (shared with the dashboard template) ------------------------------------

def format_number(value) -> str:
    """Thousand separators, rounded to 2 decimal places (NFR-14); whole numbers without decimals."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    value = float(value)
    if abs(value) >= 1e15:
        return f"{value:.3e}"
    if value.is_integer():
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def format_date(value) -> str:
    if value is None or value is pd.NaT:
        return "—"
    return pd.Timestamp(value).strftime("%d %b %Y")


# --- Helpers ---------------------------------------------------------------------------------

def _group_values(spec: dict, profile: DatasetProfile) -> pd.Series:
    """Total, average or row count of the spec's measure for each category (missing categories left out)."""
    if spec["y"]:
        frame = profile.values[[spec["x"], spec["y"]]].dropna()
        grouped = frame.groupby(spec["x"])[spec["y"]].agg(spec["agg"])
    else:
        grouped = profile.values[spec["x"]].dropna().value_counts()
    if grouped.empty:
        raise NothingToDraw("there are no rows with both values.")
    return grouped


def _layout(title: str, x_label: str | None = None, y_label: str | None = None) -> dict:
    axis = dict(gridcolor=GRID, linecolor=AXIS, zeroline=False, automargin=True,
                tickfont=dict(color=INK_SECONDARY), title=dict(font=dict(color=INK_SECONDARY)))
    return dict(
        title=dict(text=_text(title), x=0.01, xanchor="left", font=dict(size=16, color=INK)),
        font=dict(family=FONT, size=12, color=INK_SECONDARY),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        margin=dict(l=16, r=24, t=64, b=16), height=420, showlegend=False,
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=AXIS, font=dict(color=INK, family=FONT)),
        xaxis={**axis, "title": {**axis["title"], "text": _text(x_label or "")}},
        yaxis={**axis, "title": {**axis["title"], "text": _text(y_label or "")}},
    )


def _text(value) -> str:
    """Spreadsheet text for Plotly, HTML-escaped so tags show as plain text (NFR-10)."""
    return html.escape(str(value), quote=False)


def _hover(value) -> str:
    """Escaped text for hover templates; also stops "%{" in a heading being read as a template field."""
    return _text(value).replace("%{", "%​{")


def _script_safe_json(text: str) -> Markup:
    """Escape <, > and & so the JSON can never close its <script> element."""
    return Markup(text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e"))


def _download_name(title: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in title).strip("_")
    return (cleaned or "chart")[:80]
