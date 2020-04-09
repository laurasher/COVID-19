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
from bokeh.models.widgets import Slider, Button, Toggle
from bokeh.layouts import column, row, widgetbox
from bokeh.embed import file_html
from bokeh.palettes import brewer

import geopandas as gpd


def main():
    ############## USER PARAMS ##############
    # Write output file to...
    out_file_cumulative = "../visuals/choropleth/choropleth_covid_plot_cumulative_650px.html"

    # Styling parameters
    map_width = 650
    map_height = 350
    colorbar_height = 20
    title_font_size = "9pt"
    title_font_style = "italic"
    date_font_size = "12pt"
    title_font = "tahoma"
    ticker = FixedTicker(ticks=[10,100,1000,10000,100000,300000]) # Color bar axis markers

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

    # Find max cases so far for color scaling
    max_cases_ever = max(total.iloc[:, 3:].max())

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

    # Convert to json
    merged_json = json.loads(merged.to_json())

    # Convert to GeoJSONDataSource
    json_data = json.dumps(merged_json)
    geosource_json = GeoJSONDataSource(geojson=json_data)

    date_label_source_cumulative = ColumnDataSource(data=dict(names=[latest_date_col]))

    ############## BUILD CUMULATIVE CASES PLOT ##############
    TOOLS = ""

    p = figure(
        tools=TOOLS,
        toolbar_location=None,
        x_axis_location=None,
        y_axis_location=None,
        width=map_width,
        height=map_height + colorbar_height,
        #title="Cumulative Cases",
    )

    p.border_fill_color = "white"
    p.background_fill_color = "white"
    p.outline_line_color = None
    p.grid.grid_line_color = None
    p.grid.grid_line_color = None

    p.toolbar.active_scroll = p.select_one(WheelZoomTool)
    p.title.text_font = title_font
    p.title.text_font_size = title_font_size
    p.title.text_font_style = title_font_style
    p.toolbar.logo = None
    p.toolbar_location = None

    color_mapper = LogColorMapper(palette=palette, low=0, high=max_cases_ever)

    color_bar_cumulative = ColorBar(
        color_mapper=color_mapper,
        border_line_color=None,
        width=map_width - 30,
        height=colorbar_height,
        location=(0, 0),
        orientation="horizontal",
        ticker=ticker, 
        formatter=NumeralTickFormatter(format="0,0"),
    )

    p.patches(
        "xs",
        "ys",
        fill_alpha=0.9,
        fill_color={"field": "latest_cases", "transform": color_mapper},
        line_color=None,
        source=geosource_json,
    )
    p.patches(
        "xs",
        "ys",
        source=geosource,
        fill_color=None,
        line_color="lightgray",
        line_width=0.5,
        fill_alpha=1,
    )

    labels_cumulative = LabelSet(
        x=0,
        y=0,
        x_units="screen",
        y_units="screen",
        text="names",
        level="glyph",
        x_offset=5,
        y_offset=5,
        source=date_label_source_cumulative,
        render_mode="css",
        border_line_color="white",
        border_line_alpha=0.0,
        text_font_size=date_font_size,
        text_font=title_font,
        background_fill_color="white",
        background_fill_alpha=0.0,
    )

    p.toolbar.active_inspect = None
    p.add_layout(labels_cumulative)
    p.add_layout(color_bar_cumulative, 'above')


    ############## INTERACTIVE ELEMENTS ##############
    timeslider_cumulative = Slider(
        start=1, end=num_days, value=num_days, step=1, title="", show_value=False
    )

    update_data_cumulative = CustomJS(
        args=dict(
            geosource_json=geosource_json,
            date_label_source=date_label_source_cumulative,
            color_frames=total_mat,
            dates=dates,
        ),
        code="""
                var f = cb_obj.value

                date_label_source.data.names[0] = dates[f-1]
                date_label_source.change.emit()

                geosource_json.data.latest_cases = color_frames[f+3]
                geosource_json.change.emit()
                """,
    )

    timeslider_cumulative.js_on_change("value", update_data_cumulative)
    playbutton_cumulative = Button(label="► Play", button_type="default")

    animate_slider_cumulative = CustomJS(
        args=dict(timeslider=timeslider_cumulative, end=num_days),
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

    # Set up Play/Pause button/toggle JS
    toggl_js = CustomJS(args=dict(slider=timeslider_cumulative, end=[i for i in range(1, num_days)]),
        code="""
        // A little lengthy but it works for me, for this problem, in this version.
            step_length_ms = 300
            
            var check_and_iterate = function(index){
                var slider_val = slider.value;
                var toggle_val = cb_obj.active;
                if(toggle_val == false) {
                    cb_obj.label = '► Play';
                    clearInterval(looop);
                    } 
                else if(slider_val == index[index.length - 1]) {
                    cb_obj.label = '► Play';
                    slider.value = index[0];
                    cb_obj.active = false;
                    clearInterval(looop);
                    }
                else if(slider_val !== index[index.length - 1]){
                    slider.value = index.filter((item) => item > slider_val)[0];
                    }
                else {
                clearInterval(looop);
                    }
            }
            if(cb_obj.active == false){
                cb_obj.label = '► Play';
                clearInterval(looop);
            }
            else {
                cb_obj.label = '❚❚ Pause';
                var looop = setInterval(check_and_iterate, step_length_ms, end);
            };
            
        """)

    toggl = Toggle(label='► Play',active=False)
    toggl.js_on_change('active',toggl_js)

    playbutton_cumulative.js_on_click(animate_slider_cumulative)

    ############## Write html to output file
    #layout_cumulative = column(p, timeslider_cumulative, widgetbox(playbutton_cumulative, width=100))
    layout_cumulative = column(p, timeslider_cumulative, widgetbox(toggl, width=100))
    html = file_html(layout_cumulative, CDN, "choropleth_covid_plot_cumulative")
    f = open(out_file_cumulative, "w")
    print(f"\nCHOROPLETH CUMULATIVE PLOT COMPLETE: html file written to {out_file_cumulative}")
    f.write(html)
    f.close()




    ############## USER PARAMS ##############
    # Write output file to...
    out_file_cumulative = "../visuals/choropleth/choropleth_covid_plot_cumulative_320px.html"

    # Styling parameters
    map_width = 320
    map_height = 173

    colorbar_height = 10
    title_font_size = "9pt"
    title_font_style = "italic"
    date_font_size = "12pt"
    title_font = "tahoma"
    ticker = FixedTicker(ticks=[10,100,1000,10000,300000]) # Color bar axis markers

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

    # Find max cases so far for color scaling
    max_cases_ever = max(total.iloc[:, 3:].max())

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

    # Convert to json
    merged_json = json.loads(merged.to_json())

    # Convert to GeoJSONDataSource
    json_data = json.dumps(merged_json)
    geosource_json = GeoJSONDataSource(geojson=json_data)

    date_label_source_cumulative = ColumnDataSource(data=dict(names=[latest_date_col]))

    ############## BUILD CUMULATIVE CASES PLOT ##############
    TOOLS = ""

    p = figure(
        tools=TOOLS,
        toolbar_location=None,
        x_axis_location=None,
        y_axis_location=None,
        width=map_width,
        height=map_height + colorbar_height,
        #title="Cumulative Cases",
    )

    p.border_fill_color = "white"
    p.background_fill_color = "white"
    p.outline_line_color = None
    p.grid.grid_line_color = None
    p.grid.grid_line_color = None

    p.toolbar.active_scroll = p.select_one(WheelZoomTool)
    p.title.text_font = title_font
    p.title.text_font_size = title_font_size
    p.title.text_font_style = title_font_style
    p.toolbar.logo = None
    p.toolbar_location = None

    color_mapper = LogColorMapper(palette=palette, low=0, high=max_cases_ever)

    color_bar_cumulative = ColorBar(
        color_mapper=color_mapper,
        border_line_color=None,
        width=map_width - 30,
        height=colorbar_height,
        location=(0, 0),
        orientation="horizontal",
        ticker=ticker, 
        formatter=NumeralTickFormatter(format="0,0"),
    )

    p.patches(
        "xs",
        "ys",
        fill_alpha=0.9,
        fill_color={"field": "latest_cases", "transform": color_mapper},
        line_color=None,
        source=geosource_json,
    )
    p.patches(
        "xs",
        "ys",
        source=geosource,
        fill_color=None,
        line_color="lightgray",
        line_width=0.5,
        fill_alpha=1,
    )

    labels_cumulative = LabelSet(
        x=0,
        y=0,
        x_units="screen",
        y_units="screen",
        text="names",
        level="glyph",
        x_offset=5,
        y_offset=5,
        source=date_label_source_cumulative,
        render_mode="css",
        border_line_color="white",
        border_line_alpha=0.0,
        text_font_size=date_font_size,
        text_font=title_font,
        background_fill_color="white",
        background_fill_alpha=0.0,
    )

    p.toolbar.active_inspect = None
    p.add_layout(labels_cumulative)
    p.add_layout(color_bar_cumulative, 'above')


    ############## INTERACTIVE ELEMENTS ##############
    timeslider_cumulative = Slider(
        start=1, end=num_days, value=num_days, step=1, title="", show_value=False
    )

    update_data_cumulative = CustomJS(
        args=dict(
            geosource_json=geosource_json,
            date_label_source=date_label_source_cumulative,
            color_frames=total_mat,
            dates=dates,
        ),
        code="""
                var f = cb_obj.value

                date_label_source.data.names[0] = dates[f-1]
                date_label_source.change.emit()

                geosource_json.data.latest_cases = color_frames[f+3]
                geosource_json.change.emit()
                """,
    )

    timeslider_cumulative.js_on_change("value", update_data_cumulative)
    playbutton_cumulative = Button(label="► Play", button_type="default")

    animate_slider_cumulative = CustomJS(
        args=dict(timeslider=timeslider_cumulative, end=num_days),
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

    # Set up Play/Pause button/toggle JS
    toggl_js = CustomJS(args=dict(slider=timeslider_cumulative, end=[i for i in range(1, num_days)]),
        code="""
        // A little lengthy but it works for me, for this problem, in this version.
            step_length_ms = 300
            
            var check_and_iterate = function(index){
                var slider_val = slider.value;
                var toggle_val = cb_obj.active;
                if(toggle_val == false) {
                    cb_obj.label = '► Play';
                    clearInterval(looop);
                    } 
                else if(slider_val == index[index.length - 1]) {
                    cb_obj.label = '► Play';
                    slider.value = index[0];
                    cb_obj.active = false;
                    clearInterval(looop);
                    }
                else if(slider_val !== index[index.length - 1]){
                    slider.value = index.filter((item) => item > slider_val)[0];
                    }
                else {
                clearInterval(looop);
                    }
            }
            if(cb_obj.active == false){
                cb_obj.label = '► Play';
                clearInterval(looop);
            }
            else {
                cb_obj.label = '❚❚ Pause';
                var looop = setInterval(check_and_iterate, step_length_ms, end);
            };
            
        """)

    toggl = Toggle(label='► Play',active=False)
    toggl.js_on_change('active',toggl_js)

    playbutton_cumulative.js_on_click(animate_slider_cumulative)

    ############## Write html to output file
    #layout_cumulative = column(p, timeslider_cumulative, widgetbox(playbutton_cumulative, width=100))
    layout_cumulative = column(p, timeslider_cumulative, widgetbox(toggl, width=100))
    html = file_html(layout_cumulative, CDN, "choropleth_covid_plot_cumulative")
    f = open(out_file_cumulative, "w")
    print(f"\nCHOROPLETH CUMULATIVE PLOT COMPLETE: html file written to {out_file_cumulative}")
    f.write(html)
    f.close()


main()
