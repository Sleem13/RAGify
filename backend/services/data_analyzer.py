import pandas as pd
import tempfile
import os
import logging
import json

logger = logging.getLogger(__name__)

CHART_COLORS = [
    "rgba(99,102,241,0.8)",   # indigo
    "rgba(168,85,247,0.8)",   # purple
    "rgba(236,72,153,0.8)",   # pink
    "rgba(59,130,246,0.8)",   # blue
    "rgba(16,185,129,0.8)",   # emerald
    "rgba(245,158,11,0.8)",   # amber
    "rgba(239,68,68,0.8)",    # red
    "rgba(20,184,166,0.8)",   # teal
]

class DataAnalyzer:
    """
    Analyzes Excel, CSV, and JSON files using Pandas and produces:
      • Summary statistics
      • Multiple auto-detected charts for a rich dashboard (Bar, Pie, Line)
      • Human-readable AI insight string
    """

    async def analyze_excel(self, file_bytes: bytes, filename: str) -> dict:
        ext = os.path.splitext(filename)[1].lower()
        temp_file_path = None

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_bytes)
            temp_file_path = tmp.name

        try:
            # ── Read file ─────────────────────────────────────────────────────
            if ext == ".csv":
                df = pd.read_csv(temp_file_path, encoding="utf-8", on_bad_lines="skip")
            elif ext == ".json":
                try:
                    df = pd.read_json(temp_file_path)
                except Exception:
                    # Fallback for lines=True
                    df = pd.read_json(temp_file_path, lines=True)
            elif ext == ".xls":
                df = pd.read_excel(temp_file_path, engine="xlrd")
            else:
                df = pd.read_excel(temp_file_path, engine="openpyxl")

            df = df.where(pd.notnull(df), None)

            # ── Summary ───────────────────────────────────────────────────────
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
            
            # Clean up object columns that might be dates
            for col in cat_cols:
                try:
                    df[col] = pd.to_datetime(df[col])
                    cat_cols.remove(col)
                    if 'date_columns' not in locals(): date_cols = []
                    date_cols.append(col)
                except Exception:
                    pass

            date_cols = df.select_dtypes(include=["datetime"]).columns.tolist()

            summary = {
                "columns": list(df.columns),
                "rows_count": len(df),
                "numeric_columns": numeric_cols,
                "categorical_columns": cat_cols,
                "date_columns": date_cols
            }

            # ── Auto Multi-Chart generation ───────────────────────────────────
            charts = []
            insights = []

            # 1. Bar Chart (Top Categories by sum of numeric)
            if numeric_cols and cat_cols:
                cat_col = cat_cols[0]
                num_col = numeric_cols[0]

                grouped = df.groupby(cat_col)[num_col].sum().reset_index().sort_values(by=num_col, ascending=False).head(10)
                labels = grouped[cat_col].astype(str).tolist()
                values = grouped[num_col].tolist()
                colors = (CHART_COLORS * 5)[:len(labels)]

                charts.append({
                    "id": "bar_1",
                    "title": f"Top 10 {cat_col} by {num_col} (Sum)",
                    "type": "bar",
                    "labels": labels,
                    "datasets": [{
                        "label": f"Sum of {num_col}",
                        "data": values,
                        "backgroundColor": colors,
                        "borderWidth": 1
                    }]
                })
                insights.append(f"Highest '{cat_col}' by '{num_col}' is '{labels[0]}' ({values[0]:,.1f}).")

                # 2. Pie Chart (Distribution of another category or same)
                if len(cat_cols) > 1 or len(numeric_cols) > 1:
                    pie_cat = cat_cols[1] if len(cat_cols) > 1 else cat_cols[0]
                    pie_num = numeric_cols[1] if len(numeric_cols) > 1 else numeric_cols[0]
                    
                    pie_grouped = df.groupby(pie_cat)[pie_num].count().reset_index().sort_values(by=pie_num, ascending=False).head(5)
                    pie_labels = pie_grouped[pie_cat].astype(str).tolist()
                    pie_values = pie_grouped[pie_num].tolist()
                    
                    charts.append({
                        "id": "pie_1",
                        "title": f"Distribution of {pie_cat} (Count)",
                        "type": "pie",
                        "labels": pie_labels,
                        "datasets": [{
                            "data": pie_values,
                            "backgroundColor": (CHART_COLORS[::-1] * 3)[:len(pie_labels)]
                        }]
                    })
                    insights.append(f"Most frequent '{pie_cat}' is '{pie_labels[0]}'.")

            # 3. Line Chart (Time Series)
            if date_cols and numeric_cols:
                date_col = date_cols[0]
                num_col = numeric_cols[0]
                
                time_df = df.dropna(subset=[date_col, num_col]).copy()
                time_df['year_month'] = time_df[date_col].dt.to_period('M').astype(str)
                time_grouped = time_df.groupby('year_month')[num_col].sum().reset_index().sort_values(by='year_month')
                
                if not time_grouped.empty:
                    charts.append({
                        "id": "line_1",
                        "title": f"{num_col} Over Time",
                        "type": "line",
                        "labels": time_grouped['year_month'].tolist(),
                        "datasets": [{
                            "label": f"Trend of {num_col}",
                            "data": time_grouped[num_col].tolist(),
                            "borderColor": CHART_COLORS[3],
                            "backgroundColor": "rgba(59,130,246,0.1)",
                            "fill": True,
                            "tension": 0.4
                        }]
                    })
                    insights.append(f"Analyzed {len(time_grouped)} months of data for '{num_col}'.")

            if not charts:
                insights.append("Could not generate complex charts from the provided data types.")

            # Fallback for old frontend that expects single chart_data
            legacy_chart = charts[0] if charts else None

            return {
                "summary": summary,
                "chart_data": legacy_chart,  # For backward compatibility
                "charts": charts,            # New multi-chart array
                "insights": " | ".join(insights) if insights else "No clear insights extracted.",
            }

        except Exception as exc:
            logger.error(f"DataAnalyzer error on '{filename}': {exc}")
            raise

        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

data_analyzer = DataAnalyzer()
