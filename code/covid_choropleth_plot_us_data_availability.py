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
    map_height = 250
    map_width = math.floor(map_height*1.5)
    title_font_size = "9pt"
    title_font_style = "italic"
    date_font_size = "12pt"
    title_font = "tahoma"
    ticker = FixedTicker(ticks=[10,100,1000,10000,100000,300000]) # Color bar axis markers

    # More palettes to choose from here https://docs.bokeh.org/en/latest/docs/reference/palettes.html
    #palette = brewer["YlOrBr"][8]
    #palette = palette[::-1]

    palette = ["#fc8d62", "#66c2a5"]

    ############## END USER PARAMS ##############

    # Data parameters
    skipCols = 3  # columns at head (Province, Country, Lat, Long)
    skipColsTail = 1  # status and color

    s = requests.get(
        "https://raw.githubusercontent.com/govex/COVID-19/master/data_tables/COVID19%20Dashboards%20-%20Cases%20and%20Hospitals%20-%20States.csv",
        verify=False,
    ).content
    total = pd.read_csv(io.StringIO(s.decode("utf-8")))
    total = total.replace('Yes', 1).replace('No', 0)

    total.columns = [c.replace("-"," ") for c in total.columns]

    # Clean column names
    total["State"] = total["State"].str.replace(r"\(.*\)","")
    total["State"] = [s.strip() for s in total["State"]]
    print(total)

    # Get and clean data
    #shapefile = "../geo_data/ne_110m_admin_1_states_provinces/ne_110m_admin_1_states_provinces.shp"
    shapefile = "../geo_data/ne_110m_admin_1_states_provinces_lakes/ne_110m_admin_1_states_provinces_lakes.shp"

    # Read shapefile using Geopandas
    gdf = gpd.read_file(shapefile)[["name", "geometry"]]

    # Read data to json.
    gdf_json = json.loads(gdf.to_json())

    # Convert to String like object.
    grid = json.dumps(gdf_json)

    # Input GeoJSON source that contains features for plotting.
    geosource = GeoJSONDataSource(geojson=grid)

    # Join data to GeoJSON
    data_merged = gdf.merge(total, right_on="State", left_on="name", sort=False).drop(columns=['Main Dashboard'])

    # Rename columns to enable programmatic selection
    df_to_mat = data_merged.drop(columns=['geometry', 'name', 'State'])
    column_names_list = list(df_to_mat.columns)
    df_to_mat.columns = [item for item in range(len(column_names_list))]
    merged_mat = df_to_mat.as_matrix().transpose()

    # Convert to GeoJSONDataSource
    #print(data_merged)
    data_merged.rename(columns={data_merged.columns[3]:'datatype'}, inplace=True)
    json_data = json.dumps(json.loads(data_merged.to_json()))
    geosource_json = GeoJSONDataSource(geojson=json_data)


    ############## BUILD PLOT ##############
    TOOLS = "pan,wheel_zoom"

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

    p.toolbar.active_scroll = p.select_one(WheelZoomTool)
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
        line_color="lightgray",
        line_width=0.5,
        fill_alpha=1,
    )

    p.toolbar.active_inspect = None

    ############## INTERACTIVE ELEMENTS ##############
    select1 = Select(title="", value="Test", options=["Test", "Confirmed", "Death"])
    select2 = Select(title="", value="Race", options=["Race", "Age", "Gender", "Co Morbidities"])

    select_update = CustomJS(
        args=dict(select=select1,demoselect=select2, geosource_json=geosource_json, matrix_values=merged_mat, cols=column_names_list),
        code="""
                console.log(select.value)
                console.log(demoselect.value)
                console.log('geo json source')
                console.log(geosource_json)
                console.log(cols)

                if (select.value == "Confirmed") {
                    var datatype = "Case";
                } else {
                    var datatype = select.value;
                }

                function findDataType(element) {
                  console.log('---------')
                  console.log(element)
                  console.log('includes case type: ', datatype, element.includes(datatype))
                  console.log('includes demo type: ', demoselect.value, element.includes(demoselect.value))

                  if ( element.includes(demoselect.value) && element.includes(datatype) ){
                    return element;
                  }
                }

                console.log(cols.findIndex(findDataType));
                data_type_ind = cols.findIndex(findDataType);
                console.log(matrix_values[data_type_ind])

                geosource_json.data.datatype = matrix_values[data_type_ind]
                geosource_json.change.emit()
            """,
    )
    select1.js_on_change('value', select_update)
    select2.js_on_change('value', select_update)

    ############## Write html to output file
    layout = column(row(widgetbox(select1, width=math.floor(map_width/2.5)), widgetbox(select2, width=math.floor(map_width/2.5))), p)
    #layout = column(p)
    html = file_html(layout, CDN, "choropleth_covid_plot_US_data_availability")
    f = open(out_file, "w")
    print(f"\nUS DATA AVAILABILITY CHOROPLETH PLOT COMPLETE: html file written to {out_file}")
    f.write(html)
    f.close()

main()
