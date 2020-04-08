import json
import io
import pandas as pd
import requests
import math

from bokeh.plotting import figure
from bokeh.resources import CDN
from bokeh.models import (
    ColumnDataSource,
    CustomJS,
    LabelSet,
    WheelZoomTool,
    GeoJSONDataSource,
    LinearColorMapper,
    LogColorMapper,
    ColorBar,
    NumeralTickFormatter,
    FixedTicker,
    FuncTickFormatter
)
from bokeh.models.widgets import Slider, Button
from bokeh.layouts import column, row, widgetbox, Spacer
from bokeh.embed import file_html
from bokeh.palettes import brewer

import geopandas as gpd


def main():
    ############## USER PARAMS ##############
    # Write output file to...
    out_file_new_daily_cases = "../visuals/choropleth/choropleth_covid_plot_new_daily_cases.html"
    moving_window = 5

    # Styling parameters
    map_width = 650
    map_height = 350
    colorbar_height = 20
    title_font_size = "9pt"
    title_font_style = "italic"
    date_font_size = "12pt"
    title_font = "tahoma"
    ticker_new_cases = FixedTicker(ticks=[10,100,1000,10000,100000]) # Color bar axis markers

    # More palettes to choose from here https://docs.bokeh.org/en/latest/docs/reference/palettes.html
    palette = brewer["YlOrBr"][8]
    palette = palette[::-1]

    ############## END USER PARAMS ##############

    # Data parameters
    skipCols = 3  # columns at head (Province, Country, Lat, Long)
    skipColsTail = 1  # status and color

    s = requests.get(
        "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv",
        verify=False,
    ).content
    confirmed = pd.read_csv(io.StringIO(s.decode("utf-8")))
    confirmed["status"] = "confirmed"
    total = confirmed

    # Fix labeling inconsistencies
    total.loc[
        total["Country/Region"] == "US", "Country/Region"
    ] = "United States of America"
    total.loc[
        total["Country/Region"] == "Congo (Brazzaville)", "Country/Region"
    ] = "Republic of the Congo"
    total.loc[
        total["Country/Region"] == "Congo (Kinshasa)", "Country/Region"
    ] = "Democratic Republic of the Congo"
    total.loc[
        total["Country/Region"] == "Korea, South", "Country/Region"
    ] = "South Korea"
    total.loc[total["Country/Region"] == "Taiwan*", "Country/Region"] = "Taiwan"
    total.loc[total["Country/Region"] == "Burma", "Country/Region"] = "Myanmar"
    total.loc[
        total["Country/Region"] == "Tanzania", "Country/Region"
    ] = "United Republic of Tanzania"
    total.loc[total["Province/State"] == "Greenland", "Country/Region"] = "Greenland"

    total = total.sort_values(by=["Country/Region"])
    total = total.groupby("Country/Region").sum().reset_index()
    total = total.sort_values(by=["Country/Region"])

    # Get dates for date label
    dates = list(total.columns)
    dates = dates[skipCols + 1 : len(total.columns) - skipColsTail]
    num_days = total.shape[1] - (skipCols + skipColsTail + 1)
    latest_date_col = total.columns[num_days + skipCols]

    # Get and clean data
    shapefile = "../geo_data/countries_110m/ne_110m_admin_0_countries.shp"

    # Read shapefile using Geopandas
    gdf = gpd.read_file(shapefile)[["ADMIN", "ADM0_A3", "geometry"]]

    # Rename columns.
    gdf.columns = ["country", "country_code", "geometry"]

    # Drop row corresponding to 'Antarctica'
    gdf = gdf.drop(gdf.index[159])

    # Read data to json.
    gdf_json = json.loads(gdf.to_json())

    # Convert to String like object.
    grid = json.dumps(gdf_json)

    # Input GeoJSON source that contains features for plotting.
    geosource = GeoJSONDataSource(geojson=grid)

    # Drop Diamond Princess
    total.drop(
        total[total["Country/Region"] == "Diamond Princess"].index, axis=0, inplace=True
    )

    # New cases daily
    new_cases = total.iloc[:, :3].join(
        total.iloc[:, 3:].diff(axis=1).fillna(0).astype(int)
    )
    diff_cases = total.iloc[:, 3:].diff(axis=1).fillna(0).astype(int)
    diff_cases = diff_cases.rolling(moving_window, axis=1).mean().fillna(0).astype(int)
    new_cases = total.iloc[:, :3].join(diff_cases)

    # Find max cases so far for color scaling
    max_cases_ever = max(total.iloc[:, 3:].max())
    max_cases_new_daily = max(new_cases.iloc[:, 3:].max())

    # Join cumulative cases to GeoJSON
    total_latest = total.iloc[:, 0:3].join(total[latest_date_col])
    total_latest.columns = ["Country/Region", "Lat", "Long", "latest_cases"]
    total_merged_to_mat = gdf.merge(
        total, right_on="Country/Region", left_on="country", sort=False
    )
    total_merged_to_mat = total_merged_to_mat.drop(
        columns=["country_code", "geometry", "country"]
    )
    total_merged_to_mat = total_merged_to_mat.sort_values(by=["Country/Region"])
    total_mat = total_merged_to_mat.as_matrix().transpose()
    merged = gdf.merge(
        total_latest, right_on="Country/Region", left_on="country", sort=False
    )
    merged = merged.sort_values(by=["Country/Region"])

    # Join new daily cases to GeoJSON
    new_cases_latest = new_cases.iloc[:, 0:3].join(new_cases[latest_date_col])
    new_cases_latest.columns = ["Country/Region", "Lat", "Long", "latest_cases"]
    new_cases_merged_to_mat = gdf.merge(
        new_cases, right_on="Country/Region", left_on="country", sort=False
    )
    new_cases_merged_to_mat = new_cases_merged_to_mat.drop(
        columns=["country_code", "geometry", "country"]
    )
    new_cases_merged_to_mat = new_cases_merged_to_mat.sort_values(by=["Country/Region"])
    new_cases_mat = new_cases_merged_to_mat.as_matrix().transpose()
    merged_new_cases = gdf.merge(
        new_cases_latest, right_on="Country/Region", left_on="country", sort=False
    )
    merged_new_cases = merged_new_cases.sort_values(by=["Country/Region"])

    # Convert to json
    merged_json = json.loads(merged.to_json())
    new_cases_merged_json = json.loads(merged_new_cases.to_json())

    # Convert to GeoJSONDataSource
    json_data = json.dumps(merged_json)
    geosource_json = GeoJSONDataSource(geojson=json_data)

    new_cases_json_data = json.dumps(new_cases_merged_json)
    new_cases_geosource_json = GeoJSONDataSource(geojson=new_cases_json_data)

    date_label_source_cumulative = ColumnDataSource(data=dict(names=[latest_date_col]))
    date_label_source_new_daily_cases = ColumnDataSource(data=dict(names=[latest_date_col]))

    ############## BUILD NEW DAILY CASES PLOT ##############
    TOOLS = "pan,wheel_zoom"
    p2 = figure(
        tools=TOOLS,
        toolbar_location=None,
        x_axis_location=None,
        y_axis_location=None,
        width=map_width,
        height=map_height + colorbar_height,
        #title=f"New Daily Cases, {moving_window} day moving average",
    )

    color_mapper_new_cases = LogColorMapper(palette=palette, low=0, high=max_cases_new_daily)

    color_bar_new_cases = ColorBar(
        color_mapper=color_mapper_new_cases,
        border_line_color=None,
        width=map_width - 30,
        height=colorbar_height,
        location=(0, 0),
        orientation="horizontal",
        ticker=ticker_new_cases, 
        formatter=NumeralTickFormatter(format="0,0"),
    )

    p2.border_fill_color = "white"
    p2.background_fill_color = "white"
    p2.outline_line_color = None
    p2.grid.grid_line_color = None
    p2.grid.grid_line_color = None

    p2.toolbar.active_scroll = p2.select_one(WheelZoomTool)
    p2.title.text_font_size = title_font_size
    p2.title.text_font_style = title_font_style
    p2.title.text_font = title_font
    p2.toolbar.logo = None
    p2.toolbar_location = None

    p2.patches(
        "xs",
        "ys",
        fill_alpha=0.9,
        fill_color={"field": "latest_cases", "transform": color_mapper_new_cases},
        line_color=None,
        source=new_cases_geosource_json,
    )
    p2.patches(
        "xs",
        "ys",
        source=geosource,
        fill_color=None,
        line_color="lightgray",
        line_width=0.5,
        fill_alpha=1,
    )

    labels_new_daily_cases = LabelSet(
        x=0,
        y=0,
        x_units="screen",
        y_units="screen",
        text="names",
        level="glyph",
        x_offset=5,
        y_offset=5,
        source=date_label_source_new_daily_cases,
        render_mode="css",
        border_line_color="white",
        border_line_alpha=0.0,
        text_font_size=date_font_size,
        background_fill_color="white",
        background_fill_alpha=0.0,
    )

    p2.add_layout(labels_new_daily_cases)
    p2.add_layout(color_bar_new_cases, "above")
    p2.toolbar.active_inspect = None


    ############## INTERACTIVE ELEMENTS ##############
    timeslider_new_daily_cases = Slider(
        start=1, end=num_days, value=num_days, step=1, title="", show_value=False
    )

    update_data_new_daily_cases = CustomJS(
        args=dict(
            geosource_json_new_cases=new_cases_geosource_json,
            date_label_source=date_label_source_new_daily_cases,
            color_frames_new_cases=new_cases_mat,
            dates=dates,
        ),
        code="""
                var f = cb_obj.value

                date_label_source.data.names[0] = dates[f-1]
                date_label_source.change.emit()

                geosource_json_new_cases.data.latest_cases = color_frames_new_cases[f+3]
                geosource_json_new_cases.change.emit()
                """,
    )

    timeslider_new_daily_cases.js_on_change("value", update_data_new_daily_cases)
    playbutton_new_daily_cases = Button(label="► Play", button_type="default")

    animate_slider_new_daily_cases = CustomJS(
        args=dict(timeslider=timeslider_new_daily_cases, end=num_days),
        code="""
                timeslider.value = timeslider.start
                step_length_ms = 500
                num_steps = end
                inc = 1
                
                playback_interval = setInterval(function(){
                    if (timeslider.value+inc <= num_steps){
                      timeslider.value = timeslider.value+inc;
                    }
                }, step_length_ms)
                setTimeout(function(){clearInterval(playback_interval)}, step_length_ms*num_steps)

            """,
    )
    playbutton_new_daily_cases.js_on_click(animate_slider_new_daily_cases)

    ############## Write html to output file ##############

    layout_new_daily_cases = column(p2, timeslider_new_daily_cases, widgetbox(playbutton_new_daily_cases, width=100))
    html = file_html(layout_new_daily_cases, CDN, "choropleth_covid_plot_new_daily_cases")
    f = open(out_file_new_daily_cases, "w")
    print(f"\nCHOROPLETH NEW DAILY CASES PLOT COMPLETE: html file written to {out_file_new_daily_cases}")
    f.write(html)
    f.close()


main()
