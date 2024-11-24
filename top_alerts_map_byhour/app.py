from shiny import App, reactive, render, ui
import pandas as pd
import altair as alt
from datetime import date
import numpy as np
import json
from shinywidgets import render_altair, output_widget

data_path = "hour_alert_counts.csv"
df_alert_counts = pd.read_csv(data_path)
file_path = "chicago_boundaries.geojson"
# ----
with open(file_path) as f:
    chicago_geojson = json.load(f)
geo_data = alt.Data(values=chicago_geojson["features"])


# Generate dropdown options sorted by their keys
dropdown_options = {
    f"{row['updated_type']} - {row['updated_subtype']} - {row['updated_subsubtype']}": f"{row['updated_type']} - {row['updated_subtype']} - {row['updated_subsubtype']}"
    for _, row in df_alert_counts[["updated_type", "updated_subtype", "updated_subsubtype"]]
    .drop_duplicates()
    .sort_values(["updated_type", "updated_subtype", "updated_subsubtype"])
    .iterrows()
}

# I ask ChatGPT how to add a slider to pick the hour in the shiny app, below is the code.

# Define the Shiny app UI
app_ui = ui.page_fluid(
    ui.panel_title("Top Alerts by Hour"),
    ui.input_slider(
        "hour_slider",  # Input ID
        "Pick an Hour:",  # Label
        min=00,  # Minimum value
        max=23,  # Maximum value
        value=12,  # Default value
        step=1,  # Step size
    ),
    ui.input_select(
        id="alert_type",
        label="Choose the alert type and subtype:",
        choices=dropdown_options,
    ),
    output_widget("my_hist")
)


def server(input, output, session):
    @render.text
    def selected_alert():
        return f"Your choice: {input.alert_type()}"

    @render.text
    def selected_hour():
        return f"You selected hour: {input.hour_slider()}"

    @render_altair
    def my_hist():
        selected = input.alert_type().split(" - ")
        if len(selected) == 3:
            selected_type, selected_subtype, selected_subsubtype = selected
            # Filter the data based on the selected type and subtype
            filtered_data = df_alert_counts[
                (df_alert_counts["updated_type"] == selected_type) &
                (df_alert_counts["updated_subtype"] == selected_subtype) &
                (df_alert_counts["updated_subsubtype"] == selected_subsubtype) &
                (df_alert_counts["hour"] == input.hour_slider())
            ]
            # Get the top 10 locations by count
            aggregated_data = (
                filtered_data
                .sort_values(by="alert_count", ascending=False)
            )
            top_10 = aggregated_data.head(10)

            points = alt.Chart(top_10).mark_circle().encode(
                longitude='binned_longitude:Q',
                latitude='binned_latitude:Q',
                size=alt.Size('alert_count', scale=alt.Scale(range=[10, 100])),
                tooltip=["binned_latitude", "binned_longitude", "alert_count"]
            )
            map_layer = (
                alt.Chart(geo_data).mark_geoshape(
                    fill="lightgray",
                    stroke="white",
                    strokeWidth=1
                )
                .properties(
                    width=400,
                    height=600
                )
                .project("identity", reflectY=True)
            )

            combined_plot = (
                map_layer + points
            ).properties(title="Top 10")

            return combined_plot

        return pd.DataFrame({"Message": ["No data for the selected alert type and subtype"]})

    # Link the output elements to the server functions
    output.selected_alert = selected_alert
    output.selected_hour = selected_hour
    output.my_hist = my_hist


# Create the app
app = App(app_ui, server)
