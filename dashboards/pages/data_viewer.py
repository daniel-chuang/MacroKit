import streamlit as st
import pandas as pd
import numpy as np
import duckdb
from macrokit_datalake import config_utils
import collections as c
from typing import List, Optional
import pprint
import plotly.express as px
from streamlit_plotly_events import plotly_events

# Connect to DuckDB
config = config_utils.load_config()
db_path = config["database"]["path"]
conn = duckdb.connect(db_path)

# Load and process DuckDB tables

fetched_tables = conn.execute("SHOW ALL TABLES").fetchall()
pprint.pprint(fetched_tables)

# Process the tables fetched
# Dictionary to hold schema to table mapping
table_data = c.defaultdict(list)
for table in fetched_tables:
    schema, table_name = table[1], table[2]
    table_data[schema].append(table_name)
for key in table_data:
    table_data[key].sort()
pprint.pprint(table_data)


# Dictionary to hold columns
table_columns = {}
for schema in table_data:
    for table_name in table_data[schema]:
        full_table_name = f"{schema}.{table_name}"
        columns_info = conn.execute(
            f"PRAGMA table_info('{full_table_name}')"
        ).fetchall()
        columns = [col[1] for col in columns_info]
        table_columns[full_table_name] = columns
pprint.pprint(table_columns)


# Cached data loading function for a specific table
@st.cache_data
def load_data(table_name: str, columns: Optional[List[str]] = None) -> pd.DataFrame:
    if not columns:
        query = f"SELECT * FROM {table_name}"
    else:
        cols = ", ".join(columns)
        query = f"SELECT {cols} FROM {table_name}"
    return conn.execute(query).fetchdf()


# Streamlit UI Header
st.set_page_config(
    page_title="Data Viewer",
    layout="wide",
    page_icon="📊",
)
st.title("Data Viewer")

# Streamlit UI Body
selected_schema = st.selectbox("Select Schema", table_data.keys())
selected_tablename = st.selectbox("Select Table", table_data[selected_schema])
selected_table = f"{selected_schema}.{selected_tablename}"

tab1, tab2 = st.tabs(["Raw Data", "Time Series Plot"])
with tab1:
    data = load_data(selected_table)
    st.write("### Raw Data")

    # Add filtering section
    with st.expander("🔍 Filter Data", expanded=False):
        filter_cols = st.columns(3)
        filters = {}

        for idx, col in enumerate(data.columns):
            with filter_cols[idx % 3]:
                if pd.api.types.is_numeric_dtype(data[col]):
                    # Numeric filter - handle NaN
                    non_null_data = data[col].dropna()
                    if len(non_null_data) > 0:
                        min_val = float(non_null_data.min())
                        max_val = float(non_null_data.max())

                        selected_range = st.slider(
                            f"{col}",
                            min_val,
                            max_val,
                            (min_val, max_val),
                            key=f"filter_{col}",
                        )
                        filters[col] = ("numeric", selected_range)

                elif pd.api.types.is_datetime64_any_dtype(data[col]):
                    # Date filter - handle NaT
                    non_null_data = data[col].dropna()
                    if len(non_null_data) > 0:
                        min_date = non_null_data.min()
                        max_date = non_null_data.max()

                        # Convert to python date objects, handling timezone-aware datetimes
                        if hasattr(min_date, "date"):
                            min_date = min_date.date()
                            max_date = max_date.date()

                        selected_dates = st.date_input(
                            f"{col}", value=(min_date, max_date), key=f"filter_{col}"
                        )
                        if len(selected_dates) == 2:
                            filters[col] = ("datetime", selected_dates)

                else:
                    # Categorical filter - handle None/NaN
                    unique_vals = data[col].dropna().unique().tolist()
                    if len(unique_vals) <= 20 and len(unique_vals) > 0:
                        selected_vals = st.multiselect(
                            f"{col}",
                            unique_vals,
                            default=unique_vals,
                            key=f"filter_{col}",
                        )
                        filters[col] = ("categorical", selected_vals)

    # Apply filters
    filtered_data = data.copy()
    for col, (filter_type, filter_val) in filters.items():
        if filter_type == "numeric":
            filtered_data = filtered_data[
                (filtered_data[col].notna())
                & (filtered_data[col] >= filter_val[0])
                & (filtered_data[col] <= filter_val[1])
            ]
        elif filter_type == "datetime":
            # Convert column to datetime if not already
            if not pd.api.types.is_datetime64_any_dtype(filtered_data[col]):
                filtered_data[col] = pd.to_datetime(filtered_data[col], errors="coerce")

            # Filter out NaT and apply date range
            filtered_data = filtered_data[
                (filtered_data[col].notna())
                & (filtered_data[col] >= pd.Timestamp(filter_val[0]))
                & (filtered_data[col] <= pd.Timestamp(filter_val[1]))
            ]
        elif filter_type == "categorical":
            filtered_data = filtered_data[
                (filtered_data[col].notna()) & (filtered_data[col].isin(filter_val))
            ]

    st.write(f"Showing {len(filtered_data):,} of {len(data):,} rows")

    # Add option to include/exclude null values
    col_null1, col_null2 = st.columns([3, 1])
    with col_null2:
        show_nulls = st.checkbox("Show rows with nulls", value=True, key="show_nulls")

    if not show_nulls:
        filtered_data = filtered_data.dropna()
        st.write(f"After removing nulls: {len(filtered_data):,} rows")

    # Display dataframe with selection enabled
    selection = st.dataframe(
        filtered_data,
        use_container_width=True,
        selection_mode="multi-row",
        on_select="rerun",
        key="data_table",
    )

    # Store filtered data and selection in session state for use in tab2
    st.session_state["filtered_data"] = filtered_data
    st.session_state["selected_rows"] = (
        selection.selection.rows if selection.selection else []
    )

with tab2:
    st.write("### Time Series Plot")

    # Get data from session state (filtered data from tab1)
    if "filtered_data" not in st.session_state:
        data = load_data(selected_table)
        st.session_state["filtered_data"] = data
    else:
        data = st.session_state["filtered_data"]

    # Check if user selected specific rows
    selected_rows = st.session_state.get("selected_rows", [])
    if selected_rows:
        data = data.iloc[selected_rows]
        st.info(f"📊 Plotting {len(selected_rows)} selected rows from Raw Data tab")

    if data.empty:
        st.warning("No data available to plot")
    else:
        # Identify potential date/time columns (exclude those with all NaT)
        date_columns = []
        for col in data.columns:
            if pd.api.types.is_datetime64_any_dtype(data[col]):
                if data[col].notna().any():  # Check if there are any non-NaT values
                    date_columns.append(col)
            elif data[col].dtype == "object":
                try:
                    parsed = pd.to_datetime(data[col], errors="coerce")
                    if (
                        parsed.notna().any()
                    ):  # Check if parsing succeeded for any values
                        date_columns.append(col)
                except:
                    pass

        if not date_columns:
            st.warning("No date/time columns detected in this table")
        else:
            # User selections
            col1, col2 = st.columns(2)

            with col1:
                time_col = st.selectbox(
                    "Select Time Column", date_columns, key="time_col"
                )

            with col2:
                numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()

                value_cols = st.multiselect(
                    "Select Value Column(s) to Plot",
                    numeric_cols,
                    default=numeric_cols[:1] if numeric_cols else [],
                    key="value_cols",
                )

            if not value_cols:
                st.info("Please select at least one value column to plot")
            else:
                # Convert time column to datetime and remove NaT values
                plot_data = data.copy()
                plot_data[time_col] = pd.to_datetime(
                    plot_data[time_col], errors="coerce"
                )

                # Remove rows where time column is NaT
                plot_data = plot_data[plot_data[time_col].notna()]

                if plot_data.empty:
                    st.warning(f"No valid datetime values found in column '{time_col}'")
                else:
                    # Sort by time
                    plot_data = plot_data.sort_values(time_col)

                    # Optional: Group by for categorical splits
                    categorical_cols = data.select_dtypes(
                        include=["object", "category"]
                    ).columns.tolist()
                    categorical_cols = [
                        col for col in categorical_cols if col != time_col
                    ]

                    color_by = None
                    facet_by = None

                    col3, col4 = st.columns(2)
                    with col3:
                        if categorical_cols:
                            color_by = st.selectbox(
                                "Color by (optional)",
                                ["None"] + categorical_cols,
                                key="color_by",
                            )
                            if color_by == "None":
                                color_by = None

                    with col4:
                        if categorical_cols:
                            facet_by = st.selectbox(
                                "Facet by (optional - creates subplots)",
                                ["None"] + categorical_cols,
                                key="facet_by",
                            )
                            if facet_by == "None":
                                facet_by = None

                    # Create the plot
                    try:
                        fig = px.line(
                            plot_data,
                            x=time_col,
                            y=value_cols,
                            color=color_by,
                            facet_col=facet_by,
                            title=f"Time Series: {', '.join(value_cols)}",
                            labels={time_col: "Time"},
                            template="plotly_white",
                            markers=True if len(plot_data) < 100 else False,
                        )

                        # Update layout
                        fig.update_layout(
                            hovermode="x unified",
                            height=600,
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1,
                            ),
                        )

                        # Make the plot interactive with click events
                        selected_points = plotly_events(
                            fig,
                            click_event=True,
                            hover_event=False,
                            select_event=False,
                            override_height=650,
                            key="time_series_plot",
                        )

                        # Display clicked point information
                        if selected_points:
                            st.write("### Clicked Point Details")
                            clicked_idx = selected_points[0]["pointIndex"]
                            clicked_data = plot_data.iloc[clicked_idx]

                            # Show details in a clean format
                            detail_df = pd.DataFrame(
                                {
                                    "Column": clicked_data.index,
                                    "Value": clicked_data.values,
                                }
                            )
                            st.dataframe(detail_df, use_container_width=True)

                    except Exception as e:
                        st.error(f"Error creating plot: {str(e)}")
                        st.write("Debug info - data types:")
                        st.write(plot_data.dtypes)

                    # Optional: Add aggregation controls
                    with st.expander("📊 Aggregation Options"):
                        agg_col1, agg_col2 = st.columns(2)

                        with agg_col1:
                            agg_freq = st.selectbox(
                                "Aggregate by frequency",
                                [
                                    "None",
                                    "Hour",
                                    "Day",
                                    "Week",
                                    "Month",
                                    "Quarter",
                                    "Year",
                                ],
                                key="agg_freq",
                            )

                        with agg_col2:
                            agg_method = st.selectbox(
                                "Aggregation method",
                                ["mean", "sum", "min", "max", "median", "std", "count"],
                                key="agg_method",
                            )

                        if agg_freq != "None":
                            try:
                                # Perform aggregation
                                freq_map = {
                                    "Hour": "H",
                                    "Day": "D",
                                    "Week": "W",
                                    "Month": "M",
                                    "Quarter": "Q",
                                    "Year": "Y",
                                }

                                agg_data = plot_data.set_index(time_col)

                                if color_by:
                                    agg_data = (
                                        agg_data.groupby(
                                            [
                                                pd.Grouper(freq=freq_map[agg_freq]),
                                                color_by,
                                            ]
                                        )[value_cols]
                                        .agg(agg_method)
                                        .reset_index()
                                    )
                                else:
                                    agg_data = (
                                        agg_data[value_cols]
                                        .resample(freq_map[agg_freq])
                                        .agg(agg_method)
                                        .reset_index()
                                    )

                                # Remove any NaT rows that might have been created
                                agg_data = agg_data[agg_data[time_col].notna()]

                                if not agg_data.empty:
                                    fig_agg = px.line(
                                        agg_data,
                                        x=time_col,
                                        y=value_cols,
                                        color=color_by,
                                        facet_col=facet_by,
                                        title=f"Aggregated ({agg_freq}, {agg_method}): {', '.join(value_cols)}",
                                        template="plotly_white",
                                        markers=True,
                                    )

                                    fig_agg.update_layout(
                                        hovermode="x unified", height=600
                                    )

                                    st.plotly_chart(fig_agg, use_container_width=True)
                                else:
                                    st.warning("No data available after aggregation")

                            except Exception as e:
                                st.error(f"Error during aggregation: {str(e)}")

                    # Export options
                    with st.expander("💾 Export Options"):
                        export_col1, export_col2 = st.columns(2)

                        with export_col1:
                            csv = plot_data.to_csv(index=False)
                            st.download_button(
                                "Download Filtered Data (CSV)",
                                csv,
                                f"{selected_table}_filtered.csv",
                                "text/csv",
                            )

                        with export_col2:
                            # Export plot as HTML
                            html_buffer = fig.to_html()
                            st.download_button(
                                "Download Plot (HTML)",
                                html_buffer,
                                f"{selected_table}_plot.html",
                                "text/html",
                            )
