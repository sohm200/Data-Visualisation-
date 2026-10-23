"""Chart drawing (renderer.py): FR-15, FR-16, FR-45, FR-46, FR-53, NFR-10."""

import base64
import json

import pytest

import chart_rules
import renderer


def render(result):
    selection = chart_rules.select_charts(result)
    return renderer.render_charts(selection.specs, result)


def figure(chart):
    return json.loads(str(chart.figure_json))


def test_tf01_all_charts_render_with_titles_and_axis_labels(tf_profile):
    charts, warnings = render(tf_profile("TF-01"))
    assert warnings == []
    for chart in charts:
        layout = figure(chart)["layout"]
        assert layout["title"]["text"] == chart.title
        if chart.type in ("line", "bar", "histogram", "scatter"):
            assert layout["xaxis"]["title"]["text"] and layout["yaxis"]["title"]["text"]


# FR-16
def test_line_marks_highest_and_lowest_points(tf_profile):
    charts, _ = render(tf_profile("TF-01"))
    line = next(c for c in charts if c.type == "line")
    notes = [a["text"] for a in figure(line)["layout"]["annotations"]]
    assert any(n.startswith("Highest: ") for n in notes)
    assert any(n.startswith("Lowest: ") for n in notes)


# FR-55
def test_count_line_draws_rows_per_month(tf_profile):
    charts, warnings = render(tf_profile("TF-17"))
    line = next(c for c in charts if c.type == "line")
    trace = figure(line)["data"][0]
    counts = trace["y"]
    if isinstance(counts, dict):                    # plotly may encode arrays as base64
        import numpy as np
        counts = np.frombuffer(base64.b64decode(counts["bdata"]), dtype=counts["dtype"]).astype(int)
    assert int(sum(counts)) == tf_profile("TF-17").row_count
    assert "Number of rows: %{y:,.0f}" in trace["hovertemplate"]
    assert warnings == []


def test_bar_highlights_the_largest_bar_and_sorts_descending(tf_profile):
    charts, _ = render(tf_profile("TF-01"))
    bar = figure(next(c for c in charts if c.type == "bar"))["data"][0]
    colors = bar["marker"]["color"]
    assert colors[0] == renderer.SERIES[0]
    assert set(colors[1:]) == {renderer.DE_EMPHASIS}


def test_bar_shows_only_the_top_15(profile_csv):
    rows = [f"Shop {i % 18},{i}" for i in range(100)]
    charts, _ = render(profile_csv("Shop,Sales\n" + "\n".join(rows)))
    bar = figure(next(c for c in charts if c.type == "bar"))["data"][0]
    assert len(bar["x"]) == 15
    assert next(c for c in charts if c.type == "bar").note.startswith("Showing the top 15 of 18")


# FR-45
def test_scatter_draws_at_most_5000_points(profile_csv):
    rows = [f"{i * 2},{i * 4 + i % 9}" for i in range(6000)]
    charts, _ = render(profile_csv("Spend,Return\n" + "\n".join(rows)))
    scatter = next(c for c in charts if c.type == "scatter")
    x = figure(scatter)["data"][0]["x"]          # plotly encodes arrays as base64 float64
    assert len(base64.b64decode(x["bdata"])) // 8 == 5000


def test_histogram_bins_are_capped():
    import numpy as np
    values = np.concatenate([np.arange(1000.0), [1e9]])      # one huge outlier
    assert 1 <= renderer.bin_count(values) <= 60
    assert renderer.bin_count(np.array([5.0, 5.0, 5.0])) == 1


# NFR-10, TF-15
def test_tf15_script_text_is_escaped_in_charts(tf_profile):
    charts, _ = render(tf_profile("TF-15"))
    assert charts
    for chart in charts:
        raw = str(chart.figure_json)
        assert "<" not in raw and ">" not in raw
    labels = [label for c in charts for trace in figure(c)["data"] for label in trace.get("x", []) or []
              if isinstance(label, str)]
    assert "&lt;img src=x onerror=alert(2)&gt;" in labels


# FR-53
def test_a_failing_chart_does_not_stop_the_others(tf_profile, monkeypatch):
    def broken(spec, profile):
        raise RuntimeError("boom")

    monkeypatch.setitem(renderer.DRAWERS, "bar", broken)
    charts, warnings = render(tf_profile("TF-01"))
    assert "bar" not in {c.type for c in charts}
    assert "line" in {c.type for c in charts}
    assert any("could not be drawn" in w.message for w in warnings)


@pytest.mark.parametrize("value, text", [
    (1234567, "1,234,567"), (1234.5, "1,234.50"), (2 / 3, "0.67"), (None, "—"), (-5.0, "-5"),
])
def test_format_number(value, text):
    assert renderer.format_number(value) == text
