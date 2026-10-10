"""Dash application factory for interactive analysis results."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dash_table, dcc, html

from teiko.config import Settings
from teiko.database import Database
from teiko.loader import POPULATIONS
from teiko.repository import FREQUENCY_COLUMNS, AnalysisRepository


class DashboardFactory:
    """Build a dashboard around an injected database configuration."""

    COLORS = {"yes": "#19a974", "no": "#e05260"}
    CARD = {
        "background": "white",
        "padding": "18px",
        "borderRadius": "12px",
        "boxShadow": "0 2px 10px rgba(28,40,55,.08)",
    }

    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def table(frame: pd.DataFrame, page_size: int = 10):
        return dash_table.DataTable(  # type: ignore[attr-defined]
            data=frame.to_dict("records"),
            columns=[{"name": column, "id": column} for column in frame.columns],
            page_size=page_size,
            sort_action="native",
            style_table={"overflowX": "auto"},
            style_cell={"padding": "8px", "textAlign": "left"},
            style_header={"backgroundColor": "#e9f1f4", "fontWeight": "bold"},
        )

    @staticmethod
    def frequency_table():
        return dash_table.DataTable(  # type: ignore[attr-defined]
            id="frequency-table",
            columns=[{"name": column, "id": column} for column in FREQUENCY_COLUMNS],
            page_current=0,
            page_size=15,
            page_action="custom",
            sort_action="custom",
            sort_mode="single",
            sort_by=[{"column_id": "sample", "direction": "asc"}],
            style_table={"overflowX": "auto"},
            style_cell={"padding": "8px", "textAlign": "left"},
            style_header={"backgroundColor": "#e9f1f4", "fontWeight": "bold"},
        )

    def create(self) -> Dash:
        if not self.settings.database_path.exists():
            raise RuntimeError("Database missing. Run `make pipeline` first.")

        repository = AnalysisRepository(Database(self.settings.database_path))
        overview = repository.overview()
        cohort = repository.response_cohort()
        primary_statistics = repository.statistics("all_timepoints")
        baseline_statistics = repository.statistics("baseline")
        baseline = repository.baseline()
        projects = baseline.groupby("project").size().rename("samples").reset_index()
        responses = (
            baseline[["subject_id", "response"]]
            .drop_duplicates()
            .groupby("response")
            .size()
            .rename("subjects")
            .reset_index()
        )
        sexes = baseline[["subject_id", "sex"]].drop_duplicates().groupby("sex").size().rename("subjects").reset_index()

        app = Dash(__name__, title="Immune Cell Response Explorer")
        app.server.add_url_rule("/healthz", "healthz", lambda: ({"status": "ok"}, 200))
        app.layout = html.Div(
            [
                html.H1("Immune Cell Response Explorer"),
                html.P("Melanoma trial analysis • Loblaw Bio"),
                html.Div(
                    [
                        html.Div(
                            [html.Small("Samples"), html.H2(f"{overview['samples']:,}")],
                            style=self.CARD,
                        ),
                        html.Div(
                            [html.Small("Subjects"), html.H2(f"{overview['subjects']:,}")],
                            style=self.CARD,
                        ),
                        html.Div(
                            [html.Small("Baseline miraclib PBMC"), html.H2(f"{len(baseline):,}")],
                            style=self.CARD,
                        ),
                        html.Div(
                            [
                                html.Small("Male responder mean B cells, day 0"),
                                html.H2(f"{repository.male_responder_b_cell_mean():,.2f}"),
                            ],
                            style=self.CARD,
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit,minmax(190px,1fr))",
                        "gap": "14px",
                    },
                ),
                html.H2("Responder vs non-responder frequencies"),
                html.P(
                    "Melanoma, miraclib, PBMC only. Boxplots show samples; "
                    "inference averages repeated observations within subject."
                ),
                dcc.Dropdown(list(POPULATIONS), list(POPULATIONS), multi=True, id="plot-populations"),
                dcc.Graph(id="response-boxplot"),
                html.H3("Primary analysis: all timepoints"),
                self.table(primary_statistics.round(5)),
                html.H3("Sensitivity analysis: baseline only"),
                html.P(
                    "Baseline-only inference avoids using post-treatment measurements "
                    "when evaluating candidate predictive biomarkers."
                ),
                self.table(baseline_statistics.round(5)),
                html.H2("Baseline subset"),
                html.Div(
                    [
                        dcc.Graph(figure=px.bar(projects, x="project", y="samples", title="Samples by project")),
                        dcc.Graph(
                            figure=px.bar(
                                responses,
                                x="response",
                                y="subjects",
                                title="Subjects by response",
                                color="response",
                                color_discrete_map=self.COLORS,
                            )
                        ),
                        dcc.Graph(figure=px.bar(sexes, x="sex", y="subjects", title="Subjects by sex")),
                    ],
                    style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit,minmax(280px,1fr))"},
                ),
                html.H2("Sample frequency table"),
                html.P("Rows are fetched from SQLite one page at a time."),
                html.Div(
                    [
                        dcc.Input(id="sample-search", placeholder="Filter sample ID", debounce=True),
                        dcc.Dropdown(
                            options=[{"label": "All populations", "value": ""}]  # type: ignore[arg-type]
                            + [{"label": item, "value": item} for item in POPULATIONS],
                            value="",
                            clearable=False,
                            id="table-population",
                            style={"minWidth": "220px"},
                        ),
                    ],
                    style={"display": "flex", "gap": "12px", "marginBottom": "12px"},
                ),
                self.frequency_table(),
            ],
            style={
                "fontFamily": "Arial,sans-serif",
                "maxWidth": "1280px",
                "margin": "auto",
                "padding": "24px",
                "background": "#f5f8f9",
            },
        )

        @app.callback(Output("response-boxplot", "figure"), Input("plot-populations", "value"))
        def update_boxplot(selected: list[str] | None):
            frame = cohort[cohort.population.isin(selected or POPULATIONS)]
            figure = px.box(
                frame,
                x="population",
                y="percentage",
                color="response",
                points="outliers",
                color_discrete_map=self.COLORS,
                labels={"percentage": "Relative frequency (%)"},
            )
            figure.update_layout(legend_title_text="Response", template="plotly_white")
            return figure

        @app.callback(
            Output("frequency-table", "data"),
            Output("frequency-table", "page_count"),
            Input("frequency-table", "page_current"),
            Input("frequency-table", "page_size"),
            Input("frequency-table", "sort_by"),
            Input("sample-search", "value"),
            Input("table-population", "value"),
        )
        def update_frequency_table(page, page_size, sort_by, sample_search, population):
            ordering = sort_by[0] if sort_by else {"column_id": "sample", "direction": "asc"}
            frame, page_count = repository.frequency_page(
                page or 0,
                page_size or 15,
                ordering["column_id"],
                ordering["direction"],
                sample_search,
                population,
            )
            frame["percentage"] = frame["percentage"].round(3)
            return frame.to_dict("records"), page_count

        return app
