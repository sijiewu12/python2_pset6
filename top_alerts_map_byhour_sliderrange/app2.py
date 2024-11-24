from shiny import App, reactive, render, ui
import pandas as pd
import altair as alt
import json
from shinywidgets import render_altair, output_widget

# Load data
data_path = "hour_alert_counts.csv"
df_alert_counts = pd.read_csv(data_path)

file_path = "chicago_boundaries.geojson"
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

# Define the Shiny app UI
app_ui = ui.page_fluid(
    ui.panel_title("Hour Selector with Toggle"),
    ui.input_switch(
        "toggle_hour_mode",
        "Toggle Single Hour / Hour Range:",
        value=False,  # Default to "Hour Range"
    ),
    ui.output_ui("hour_selector"),
    ui.output_text_verbatim("hour_output"),
    ui.input_select(
        id="alert_type",
        label="Choose the alert type and subtype:",
        choices=dropdown_options,
    ),
    output_widget("my_hist")
)


def server(input, output, session):
    # Reactive UI for hour selection based on toggle state
    @output
    @render.ui
    def hour_selector():
        if input.toggle_hour_mode():
            # Single hour selection slider
            return ui.input_slider(
                "hour_slider",
                "Select Single Hour:",
                min=0,
                max=23,
                value=8,  # Default selected hour
                step=1,
                animate=False
            )
        else:
            # Hour range selection slider
            return ui.input_slider(
                "hour_range",
                "Select Hour Range:",
                min=0,
                max=23,
                value=[8, 17],  # Default selected range (8 AM to 5 PM)
                step=1,
                animate=False
            )

    # Output the selected hour or range
    @output
    @render.text
    def hour_output():
        if input.toggle_hour_mode():
            return f"Selected Single Hour: {input.hour_slider()}"
        else:
            return f"Selected Hour Range: {input.hour_range()}"

    # Render the Altair chart
    @render_altair
    def my_hist():
        selected = input.alert_type().split(" - ")
        if len(selected) == 3:
            selected_type, selected_subtype, selected_subsubtype = selected

            if input.toggle_hour_mode():
                # Filter for single hour
                filtered_data = df_alert_counts[
                    (df_alert_counts["updated_type"] == selected_type) &
                    (df_alert_counts["updated_subtype"] == selected_subtype) &
                    (df_alert_counts["updated_subsubtype"] == selected_subsubtype) &
                    (df_alert_counts["hour"] == input.hour_slider())
                ]
            else:
                # Filter for hour range
                filtered_data = df_alert_counts[
                    (df_alert_counts["updated_type"] == selected_type) &
                    (df_alert_counts["updated_subtype"] == selected_subtype) &
                    (df_alert_counts["updated_subsubtype"] == selected_subsubtype) &
                    (df_alert_counts["hour"] >= input.hour_range()[0]) &
                    (df_alert_counts["hour"] < input.hour_range()[1])
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
    output.hour_output = hour_output
    output.my_hist = my_hist


# Create the app
app = App(app_ui, server)
