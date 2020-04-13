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
    FuncTickFormatter,
    RadioButtonGroup,
)
from bokeh.models.widgets import Slider, Button, Select
from bokeh.layouts import column, row, widgetbox, Spacer
from bokeh.embed import file_html
from bokeh.palettes import brewer

import geopandas as gpd


def main():
    ############## USER PARAMS ##############
    # Write output file to...
    out_file = "../visuals/choropleth/choropleth_covid_plot_US_data_availability.html"

    # Styling parameters
    map_width = 650
    map_height = 350
    title_font_size = "9pt"
    title_font_style = "italic"
    date_font_size = "12pt"
    title_font = "tahoma"
    ticker = FixedTicker(
        ticks=[10, 100, 1000, 10000, 100000, 300000]
    )  # Color bar axis markers

    # More palettes to choose from here https://docs.bokeh.org/en/latest/docs/reference/palettes.html
    # palette = brewer["YlOrBr"][8]
    # palette = palette[::-1]

    palette = ["lightgray", "#002d72"]
    #palette = ["lightgray", "#F1C402"]

    ############## END USER PARAMS ##############

    # Data parameters
    skipCols = 3  # columns at head (Province, Country, Lat, Long)
    skipColsTail = 1  # status and color

    s = requests.get(
        "https://raw.githubusercontent.com/govex/COVID-19/master/data_tables/COVID19%20Dashboards%20-%20Cases%20and%20Hospitals%20-%20States.csv",
        verify=False,
    ).content
    total = pd.read_csv(io.StringIO(s.decode("utf-8")))
    total = total.replace("Yes", 1).replace("No", 0)

    total.columns = [c.replace("-", " ") for c in total.columns]

    # Clean column names
    total["State"] = total["State"].str.replace(r"\(.*\)", "")
    total["State"] = [s.strip() for s in total["State"]]

    # Get and clean data
    # shapefile = "../geo_data/ne_110m_admin_1_states_provinces/ne_110m_admin_1_states_provinces.shp"
    shapefile = "../geo_data/ne_110m_admin_1_states_provinces_lakes/ne_110m_admin_1_states_provinces_lakes.shp"

    # Read shapefile using Geopandas
    gdf = gpd.read_file(shapefile)[["name", "geometry"]]

    gdf_hawaii = gdf[gdf["name"] == "Hawaii"]
    gdf_alaska = gdf[gdf["name"] == "Alaska"]

    gdf.drop(gdf[gdf["name"] == "Alaska"].index, inplace=True)
    gdf.drop(gdf[gdf["name"] == "Hawaii"].index, inplace=True)

    # Read data to json.
    gdf_json = json.loads(gdf.to_json())
    gdf_json_alaska = json.loads(gdf_alaska.to_json())
    gdf_json_hawaii = json.loads(gdf_hawaii.to_json())

    # Convert to String like object.
    grid = json.dumps(gdf_json)
    grid_alaska = json.dumps(gdf_json_alaska)
    grid_hawaii = json.dumps(gdf_json_hawaii)

    # Input GeoJSON source that contains features for plotting.
    geosource = GeoJSONDataSource(geojson=grid)
    geosource_alaska = GeoJSONDataSource(geojson=grid_alaska)
    geosource_hawaii = GeoJSONDataSource(geojson=grid_hawaii)

    # Join data to GeoJSON
    data_merged = gdf.merge(total, right_on="State", left_on="name", sort=False).drop(
        columns=["Main Dashboard"]
    )
    data_merged_alaska = gdf_alaska.merge(
        total, right_on="State", left_on="name", sort=False
    ).drop(columns=["Main Dashboard"])
    data_merged_hawaii = gdf_hawaii.merge(
        total, right_on="State", left_on="name", sort=False
    ).drop(columns=["Main Dashboard"])

    # Rename columns to enable programmatic selection
    df_to_mat = data_merged.drop(columns=["geometry", "name", "State"])
    df_to_mat_alaska = data_merged_alaska.drop(columns=["geometry", "name", "State"])
    df_to_mat_hawaii = data_merged_hawaii.drop(columns=["geometry", "name", "State"])
    column_names_list = list(df_to_mat.columns)
    df_to_mat.columns = [item for item in range(len(column_names_list))]
    df_to_mat_alaska.columns = [item for item in range(len(column_names_list))]
    df_to_mat_hawaii.columns = [item for item in range(len(column_names_list))]
    #merged_mat = df_to_mat.as_matrix().transpose()
    merged_mat = df_to_mat.values.transpose()
    #merged_mat_alaska = df_to_mat_alaska.as_matrix().transpose()
    #merged_mat_hawaii = df_to_mat_hawaii.as_matrix().transpose()
    merged_mat_alaska = df_to_mat_alaska.values.transpose()
    merged_mat_hawaii = df_to_mat_hawaii.values.transpose()

    # Convert to GeoJSONDataSource
    data_merged.rename(columns={data_merged.columns[4]: "datatype"}, inplace=True)
    json_data = json.dumps(json.loads(data_merged.to_json()))
    geosource_json = GeoJSONDataSource(geojson=json_data)

    data_merged_alaska.rename(
        columns={data_merged_alaska.columns[4]: "datatype"}, inplace=True
    )
    json_data_alaska = json.dumps(json.loads(data_merged_alaska.to_json()))
    geosource_json_alaska = GeoJSONDataSource(geojson=json_data_alaska)

    data_merged_hawaii.rename(
        columns={data_merged_hawaii.columns[4]: "datatype"}, inplace=True
    )
    json_data_hawaii = json.dumps(json.loads(data_merged_hawaii.to_json()))
    geosource_json_hawaii = GeoJSONDataSource(geojson=json_data_hawaii)

    ############## BUILD PLOT ##############
    TOOLS = ""

    p = figure(
        tools=TOOLS,
        toolbar_location=None,
        x_axis_location=None,
        y_axis_location=None,
        width=map_width,
        height=map_height,
    )

    p.border_fill_color = "white"
    p.background_fill_color = "white"
    p.outline_line_color = None
    p.grid.grid_line_color = None
    p.grid.grid_line_color = None

    p.title.text_font = title_font
    p.title.text_font_size = title_font_size
    p.title.text_font_style = title_font_style
    p.toolbar.logo = None
    p.toolbar_location = None

    color_mapper = LinearColorMapper(palette=palette, low=0, high=1)

    p.patches(
        "xs",
        "ys",
        fill_alpha=0.9,
        fill_color={"field": "datatype", "transform": color_mapper},
        line_color=None,
        source=geosource_json,
    )
    p.patches(
        "xs",
        "ys",
        source=geosource,
        fill_color=None,
        line_color="white",
        line_width=0.5,
        fill_alpha=1,
    )

    p.toolbar.active_inspect = None

    ###### ALASKA
    p_alaska = figure(
        tools=TOOLS,
        toolbar_location=None,
        x_axis_location=None,
        y_axis_location=None,
        width=130,
        height=100,
    )

    p_alaska.border_fill_color = "white"
    p_alaska.background_fill_color = "white"
    p_alaska.outline_line_color = None
    p_alaska.grid.grid_line_color = None
    p_alaska.grid.grid_line_color = None

    p_alaska.title.text_font = title_font
    p_alaska.title.text_font_size = title_font_size
    p_alaska.title.text_font_style = title_font_style
    p_alaska.toolbar.logo = None
    p_alaska.toolbar_location = None

    color_mapper = LinearColorMapper(palette=palette, low=0, high=1)

    p_alaska.patches(
        "xs",
        "ys",
        fill_alpha=0.9,
        fill_color={"field": "datatype", "transform": color_mapper},
        line_color=None,
        source=geosource_json_alaska,
    )
    p_alaska.patches(
        "xs",
        "ys",
        source=geosource_alaska,
        fill_color=None,
        line_color="white",
        line_width=0.5,
        fill_alpha=1,
    )

    p_alaska.toolbar.active_inspect = None

    ###### HAWAII
    p_hawaii = figure(
        tools=TOOLS,
        toolbar_location=None,
        x_axis_location=None,
        y_axis_location=None,
        width=130,
        height=100,
    )

    p_hawaii.border_fill_color = "white"
    p_hawaii.background_fill_color = "white"
    p_hawaii.outline_line_color = None
    p_hawaii.grid.grid_line_color = None
    p_hawaii.grid.grid_line_color = None

    p_hawaii.title.text_font = title_font
    p_hawaii.title.text_font_size = title_font_size
    p_hawaii.title.text_font_style = title_font_style
    p_hawaii.toolbar.logo = None
    p_hawaii.toolbar_location = None

    color_mapper = LinearColorMapper(palette=palette, low=0, high=1)

    p_hawaii.patches(
        "xs",
        "ys",
        fill_alpha=0.9,
        fill_color={"field": "datatype", "transform": color_mapper},
        line_color=None,
        source=geosource_json_hawaii,
    )
    p_hawaii.patches(
        "xs",
        "ys",
        source=geosource_hawaii,
        fill_color=None,
        line_color="white",
        line_width=0.5,
        fill_alpha=1,
    )

    p_hawaii.toolbar.active_inspect = None

    ############## INTERACTIVE ELEMENTS ##############

    radio_button_group = RadioButtonGroup(
            labels=["Confirmed", "Deaths", "Testing"], active=0)

    select1 = Select(title="", value="Test", options=["Test", "Confirmed", "Death"])
    select2 = Select(
        title="", value="Race", options=["Race", "Age", "Gender", "Co Morbidities"]
    )

    select_update = CustomJS(
        args=dict(
            select=select1,
            demoselect=select2,
            geosource_json=geosource_json,
            matrix_values=merged_mat,
            geosource_json_alaska=geosource_json_alaska,
            matrix_values_alaska=merged_mat_alaska,
            geosource_json_hawaii=geosource_json_hawaii,
            matrix_values_hawaii=merged_mat_hawaii,
            cols=column_names_list,
        ),
        code="""
                if (select.value == "Confirmed") {
                    var datatype = "Case";
                } else {
                    var datatype = select.value;
                }

                function findDataType(element) {

                  if ( element.includes(demoselect.value) && element.includes(datatype) ){
                    return element;
                  }
                }

                data_type_ind = cols.findIndex(findDataType);

                geosource_json.data.datatype = matrix_values[data_type_ind]
                geosource_json.change.emit()

                geosource_json_alaska.data.datatype = matrix_values_alaska[data_type_ind]
                geosource_json_alaska.change.emit()

                geosource_json_hawaii.data.datatype = matrix_values_hawaii[data_type_ind]
                geosource_json_hawaii.change.emit()
            """,
    )

    radio_button_update = CustomJS(
        args=dict(
            radio_button_group=radio_button_group,
            geosource_json=geosource_json,
            matrix_values=merged_mat,
            geosource_json_alaska=geosource_json_alaska,
            matrix_values_alaska=merged_mat_alaska,
            geosource_json_hawaii=geosource_json_hawaii,
            matrix_values_hawaii=merged_mat_hawaii,
            cols=column_names_list,
        ),
        code="""
                console.log(radio_button_group)
                console.log(radio_button_group.labels[radio_button_group.active])
                
                if (radio_button_group.labels[radio_button_group.active] == "Confirmed") {
                    var datatype = "Case";
                }
                if (radio_button_group.labels[radio_button_group.active] == "Deaths") {
                    var datatype = "Death";
                } 
                if (radio_button_group.labels[radio_button_group.active] == "Testing") {
                    var datatype = "Test";
                }
                
                function findDataType(element) {

                  if ( element.includes(datatype) ){
                    return element;
                  }
                }

                data_type_ind = cols.findIndex(findDataType);

                geosource_json.data.datatype = matrix_values[data_type_ind]
                geosource_json.change.emit()

                geosource_json_alaska.data.datatype = matrix_values_alaska[data_type_ind]
                geosource_json_alaska.change.emit()

                geosource_json_hawaii.data.datatype = matrix_values_hawaii[data_type_ind]
                geosource_json_hawaii.change.emit()
                
            """,
    )
    select1.js_on_change("value", select_update)
    select2.js_on_change("value", select_update)
    radio_button_group.js_on_change("active", radio_button_update)

    ############## Write html to output file
    """
    layout = column(row(widgetbox(select1, width=math.floor(map_width/3)),
        widgetbox(select2, width=math.floor(map_width/2.5))), 
        row(column(p_alaska, p_hawaii), p))
    """
    layout = column(
        widgetbox(radio_button_group, width=math.floor(map_width / 3)),
        row(column(p_alaska, p_hawaii), p),
    )
    html = file_html(layout, CDN, "choropleth_covid_plot_US_data_availability")
    f = open(out_file, "w")
    print(
        f"\nUS DATA AVAILABILITY CHOROPLETH PLOT COMPLETE: html file written to {out_file}"
    )
    f.write(html)
    f.close()


main()
