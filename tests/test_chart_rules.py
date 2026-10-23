"""Chart selection (SRS 4.3): rules R1-R6, priority and limits, FR-12 to FR-17, FR-44 to FR-48."""

from collections import Counter

import pytest

import chart_rules
import config


def charts_for(result):
    return chart_rules.select_charts(result)


def kinds(selection):
    return [spec["type"] for spec in selection.specs]


def warning_text(selection):
    return " | ".join(w.message for w in selection.warnings)


# TF-01, FR-12, FR-13, US-04
def test_tf01_gets_line_bar_histogram_and_pie(tf_profile):
    selection = charts_for(tf_profile("TF-01"))
    assert set(kinds(selection)) >= {"line", "bar", "histogram", "pie"}
    assert len(selection.specs) > 1
    line = selection.specs[0]
    assert (line["type"], line["x"], line["y"], line["agg"], line["group"]) == ("line", "Order Date", "Sales", "sum", "day")


def test_candidates_follow_the_priority_order(tf_profile):
    order = ["R1", "R2", "R5", "R4", "R3", "R6"]
    rules = [spec["rule"] for spec in charts_for(tf_profile("TF-10")).specs]
    assert rules == sorted(rules, key=order.index)


# FR-15, FR-48
def test_every_chart_has_a_title_and_caption(tf_profile):
    for spec in charts_for(tf_profile("TF-10")).specs:
        assert spec["title"] and spec["caption"]
        if spec["type"] not in ("pie", "heatmap"):
            assert spec["x_label"] and spec["y_label"]


def test_bar_caption_explains_the_choice(tf_profile):
    bar = next(s for s in charts_for(tf_profile("TF-01")).specs if s["type"] == "bar")
    assert bar["caption"] == "Compares total Sales across 4 Region values."


# FR-44, 4.3.3
def test_tf10_at_most_10_charts_and_3_per_type(tf_profile):
    selection = charts_for(tf_profile("TF-10"))
    assert len(selection.specs) == config.MAX_CHARTS
    assert max(Counter(kinds(selection)).values()) <= config.MAX_CHARTS_PER_TYPE
    assert "possible but not shown" in warning_text(selection)


def test_fewest_missing_columns_are_used_first(profile_csv):
    rows = [f"{['a', 'b'][i % 2]},{i * 3 if i % 4 else ''},{i * 5}" for i in range(20)]
    selection = charts_for(profile_csv("G,Gappy,Full\n" + "\n".join(rows)))
    first_bar = next(s for s in selection.specs if s["type"] == "bar")
    assert first_bar["y"] == "Full"


# R1
def test_line_groups_by_month_above_100_dates(tf_profile):
    line = charts_for(tf_profile("TF-10")).specs[0]
    assert (line["type"], line["group"]) == ("line", "month")


def test_line_uses_average_when_a_total_is_not_meaningful(profile_csv):
    rows = [f"{d:02d}-01-2026,{20 + d}" for d in range(1, 15)]
    line = charts_for(profile_csv("Day,Average Temp\n" + "\n".join(rows))).specs[0]
    assert (line["type"], line["agg"]) == ("line", "mean")
    assert line["title"] == "Average Average Temp over time"


# FR-55
def test_line_counts_rows_without_a_number_column(profile_csv):
    rows = [f"{d:02d}-01-2026,{['x', 'y'][d % 2]}" for d in range(1, 15)]
    line = charts_for(profile_csv("Day,Kind\n" + "\n".join(rows))).specs[0]
    assert (line["type"], line["y"], line["agg"], line["group"]) == ("line", None, "count", "day")
    assert line["title"] == "Number of rows over time"
    assert line["y_label"] == "Number of rows"


def test_tf17_change_history_charts(tf_profile):
    selection = charts_for(tf_profile("TF-17"))
    line = selection.specs[0]
    assert (line["type"], line["x"], line["agg"], line["group"]) == ("line", "CHANGED_DATE", "count", "month")
    assert line["title"] == "Number of rows by month"
    ids = {"WORK_ITEM_ID", "STATE_SEQ", "REVISION_NO"}
    for spec in selection.specs:
        assert not ids & {spec.get("x"), spec.get("y")}


# R2, FR-46
def test_bar_counts_rows_when_there_is_no_number_column(profile_csv):
    rows = [["Pune", "Goa", "Delhi"][i % 3] for i in range(30)]
    bar = charts_for(profile_csv("City\n" + "\n".join(rows))).specs[0]
    assert (bar["type"], bar["y"], bar["agg"]) == ("bar", None, "count")


def test_bar_with_more_than_15_categories_notes_the_rest(profile_csv):
    rows = [f"Shop {i % 18},{i}" for i in range(100)]
    bar = next(s for s in charts_for(profile_csv("Shop,Sales\n" + "\n".join(rows))).specs if s["type"] == "bar")
    assert bar["top_n"] == 15
    assert bar["note"] == "Showing the top 15 of 18 Shop values; 3 smaller ones are left out."


# R3, FR-14, BR-03, US-04
def test_pie_for_4_categories_but_not_for_12(profile_csv):
    rows = [f"{['N', 'S', 'E', 'W'][i % 4]},City {i % 12},{i * 3}" for i in range(60)]
    selection = charts_for(profile_csv("Region,City,Sales\n" + "\n".join(rows)))
    pies = [s["x"] for s in selection.specs if s["type"] == "pie"]
    bars = [s["x"] for s in selection.specs if s["type"] == "bar"]
    assert pies == ["Region"]
    assert "City" in bars
    assert "No pie chart for 'City': it has 12 values" in warning_text(selection)


def test_tf08_fifty_values_get_a_top_15_bar_and_no_pie(tf_profile):
    selection = charts_for(tf_profile("TF-08"))
    assert "pie" not in kinds(selection)
    bar = next(s for s in selection.specs if s["type"] == "bar")
    assert bar["x"] == "Store"
    assert bar["note"] == "Showing the top 15 of 50 Store values; 35 smaller ones are left out."


def test_pie_uses_counts_when_values_can_be_negative(profile_csv):
    rows = [f"{['Up', 'Down'][i % 2]},{i - 10}" for i in range(30)]
    pie = next(s for s in charts_for(profile_csv("Trend,Profit\n" + "\n".join(rows))).specs if s["type"] == "pie")
    assert (pie["y"], pie["agg"]) == (None, "count")


# R4
def test_histogram_needs_10_different_values(profile_csv):
    rows = [f"{i % 5},{i * 1.5}" for i in range(40)]
    selection = charts_for(profile_csv("Rating,Amount\n" + "\n".join(rows)))
    assert [s["x"] for s in selection.specs if s["type"] == "histogram"] == ["Amount"]
    assert "No histogram for 'Rating'" in warning_text(selection)


# R5
def test_scatter_for_the_two_strongest_pairs_only(profile_csv):
    rows = [f"{i * 3},{i * 6 + (i % 3)},{i * 9 + (i % 7) * 4},{(i * 37) % 11}" for i in range(40)]
    selection = charts_for(profile_csv("A,B,C,Noise\n" + "\n".join(rows)))
    scatters = [s for s in selection.specs if s["type"] == "scatter"]
    assert len(scatters) == config.SCATTER_MAX_PAIRS
    assert all("Noise" not in (s["x"], s["y"]) for s in scatters)


def test_no_scatter_below_0_5_correlation(profile_csv):
    rows = [f"{i * 3},{(i * 37) % 11}" for i in range(40)]
    assert "scatter" not in kinds(charts_for(profile_csv("A,Noise\n" + "\n".join(rows))))


# FR-45
def test_scatter_with_more_than_5000_points_is_sampled(profile_csv):
    rows = [f"{i * 2},{i * 4 + i % 9}" for i in range(6000)]
    selection = charts_for(profile_csv("Spend,Return\n" + "\n".join(rows)))
    scatter = next(s for s in selection.specs if s["type"] == "scatter")
    assert scatter["sample"] == 5000
    assert "random sample of 5,000 of 6,000 points" in warning_text(selection)


# R6, FR-47
def test_heatmap_needs_3_numeric_columns(profile_csv):
    rows3 = [f"{i * 3},{i * i},{(i * 7) % 13}" for i in range(20)]
    rows2 = [f"{i * 3},{i * i}" for i in range(20)]
    assert "heatmap" in kinds(charts_for(profile_csv("A,B,C\n" + "\n".join(rows3))))
    assert "heatmap" not in kinds(charts_for(profile_csv("A,B\n" + "\n".join(rows2))))


# FR-42, BR-06
def test_tf09_id_column_is_never_charted(tf_profile):
    for spec in charts_for(tf_profile("TF-09")).specs:
        assert "Roll No" not in (spec.get("x"), spec.get("y"))
        assert "Roll No" not in spec.get("columns", [])


# E-08, TF-16
def test_tf16_text_only_has_no_charts_and_warns(tf_profile):
    selection = charts_for(tf_profile("TF-16"))
    assert selection.specs == []
    assert config.MESSAGES["E-08"] in warning_text(selection)


# FR-53
def test_a_failing_rule_does_not_stop_the_others(tf_profile, monkeypatch):
    def broken(profile, warnings):
        raise RuntimeError("boom")

    broken.__name__ = "bar_charts"
    monkeypatch.setattr(chart_rules, "bar_charts", broken)
    selection = charts_for(tf_profile("TF-01"))
    assert "bar" not in kinds(selection)
    assert "line" in kinds(selection)
    assert "could not be prepared" in warning_text(selection)


@pytest.mark.parametrize("test_file", ["TF-01", "TF-05", "TF-06", "TF-07", "TF-09", "TF-12", "TF-14", "TF-15",
                                       "TF-17", "TF-18"])
def test_chart_ids_are_unique(tf_profile, test_file):
    ids = [s["id"] for s in charts_for(tf_profile(test_file)).specs]
    assert len(ids) == len(set(ids))
