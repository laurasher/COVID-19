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
    Label,
    LabelSet,
)
from bokeh.models.widgets import Slider, Button, Select
from bokeh.layouts import column, row, widgetbox, Spacer
from bokeh.embed import file_html
from bokeh.palettes import brewer

import geopandas as gpd


def us_data_plot(map_width, map_height, ak_width, ak_height, label_size, out_file, json_outfile):
    ############## USER PARAMS ##############
    title_font_size = "9pt"
    title_font_style = "italic"
    date_font_size = "12pt"
    title_font = "tahoma"
    palette = ["lightgray", "#002d72"]

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
    gdf = gpd.read_file(shapefile)[["name", "geometry", "postal"]]

    gdf["center_lon"] = gdf["geometry"].centroid.x
    gdf["center_lat"] = gdf["geometry"].centroid.y
    gdf_hawaii = gdf[gdf["name"] == "Hawaii"]
    gdf_alaska = gdf[gdf["name"] == "Alaska"]
    gdf.drop(gdf[gdf["name"] == "Alaska"].index, inplace=True)
    gdf.drop(gdf[gdf["name"] == "Hawaii"].index, inplace=True)

    # Create different dataset to correct misaligned labels

    # Read data to json.
    gdf_json = json.loads(gdf.to_json())
    #gdf_json_normal_labels = json.loads(gdf_normal_labels.to_json())
    gdf_json_alaska = json.loads(gdf_alaska.to_json())
    gdf_json_hawaii = json.loads(gdf_hawaii.to_json())

    # Convert to String like object.
    grid = json.dumps(gdf_json)
    #grid_normal_labels = json.dumps(gdf_json_normal_labels)
    grid_alaska = json.dumps(gdf_json_alaska)
    grid_hawaii = json.dumps(gdf_json_hawaii)

    # Input GeoJSON source that contains features for plotting.
    geosource = GeoJSONDataSource(geojson=grid)
    geosource_alaska = GeoJSONDataSource(geojson=grid_alaska)
    geosource_hawaii = GeoJSONDataSource(geojson=grid_hawaii)
    #geosource_normal_labels = GeoJSONDataSource(geojson=gdf_json_normal_labels)

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

    states_race_testing = data_merged.loc[data_merged['Race   Test']==1, 'State'].to_list()
    states_race_confirmed = data_merged.loc[data_merged['Race   Case']==1, 'State'].to_list()
    states_race_death = data_merged.loc[data_merged['Race  Death']==1, 'State'].to_list()
    race_dict = {
      'testing' : states_race_testing,
      'confirmed' : states_race_confirmed,
      'death' : states_race_death
    }

    if map_width > 500:
      with open(json_outfile, 'w') as json_file:
        json.dump(race_dict, json_file)

    # Rename columns to enable programmatic selection
    df_to_mat = data_merged.drop(columns=["geometry", "name", "State"])
    df_to_mat_alaska = data_merged_alaska.drop(columns=["geometry", "name", "State"])
    df_to_mat_hawaii = data_merged_hawaii.drop(columns=["geometry", "name", "State"])
    column_names_list = list(df_to_mat.columns)
    df_to_mat.columns = [item for item in range(len(column_names_list))]
    df_to_mat_alaska.columns = [item for item in range(len(column_names_list))]
    df_to_mat_hawaii.columns = [item for item in range(len(column_names_list))]
    merged_mat = df_to_mat.values.transpose()
    merged_mat_alaska = df_to_mat_alaska.values.transpose()
    merged_mat_hawaii = df_to_mat_hawaii.values.transpose()

    # Convert to GeoJSONDataSource
    data_merged.rename(columns={data_merged.columns[7]: "datatype"}, inplace=True)
    json_data = json.dumps(json.loads(data_merged.to_json()))
    geosource_json = GeoJSONDataSource(geojson=json_data)

    normal_labels = data_merged.copy() 
    normal_labels.drop(normal_labels[normal_labels["name"] == "Maryland"].index, inplace=True)
    normal_labels.drop(normal_labels[normal_labels["name"] == "Delaware"].index, inplace=True)
    normal_labels.drop(normal_labels[normal_labels["name"] == "Rhode Island"].index, inplace=True)
    normal_labels.drop(normal_labels[normal_labels["name"] == "District of Columbia"].index, inplace=True)
    normal_labels.drop(normal_labels[normal_labels["name"] == "Florida"].index, inplace=True)
    normal_labels.drop(normal_labels[normal_labels["name"] == "Michigan"].index, inplace=True)
    normal_labels.drop(normal_labels[normal_labels["name"] == "Massachusetts"].index, inplace=True)
    json_data_normal_labels = json.dumps(json.loads(normal_labels.to_json()))
    label_geosource_json = GeoJSONDataSource(geojson=json_data_normal_labels)
    
    data_merged_alaska.rename(
        columns={data_merged_alaska.columns[7]: "datatype"}, inplace=True
    )
    json_data_alaska = json.dumps(json.loads(data_merged_alaska.to_json()))
    geosource_json_alaska = GeoJSONDataSource(geojson=json_data_alaska)
    data_merged_hawaii.rename(
        columns={data_merged_hawaii.columns[7]: "datatype"}, inplace=True
    )
    json_data_hawaii = json.dumps(json.loads(data_merged_hawaii.to_json()))
    geosource_json_hawaii = GeoJSONDataSource(geojson=json_data_hawaii)

    data_merged_maryland = data_merged.loc[data_merged["name"]=="Maryland"]
    json_data_maryland_label = json.dumps(json.loads(data_merged_maryland.to_json()))
    geosource_json_maryland = GeoJSONDataSource(geojson=json_data_maryland_label)

    data_merged_dc = data_merged.loc[data_merged["name"]=="District of Columbia"].reset_index()
    data_merged_dc = pd.concat([data_merged_dc]*2, ignore_index=True)
    data_merged_dc.at[1,'center_lon'] = data_merged_dc.iloc[1,:]['center_lon'] + 1.5
    data_merged_dc.at[1,'center_lat'] = data_merged_dc.iloc[1,:]['center_lat'] - 1.5
    data_merged_dc.at[1,'postal'] = ''
    data_merged_dc["xs"] = [data_merged_dc.iloc[0,:]['center_lon'], data_merged_dc.iloc[0,:]['center_lon'] + 1.35]
    data_merged_dc["ys"] = [data_merged_dc.iloc[0,:]['center_lat'], data_merged_dc.iloc[0,:]['center_lat'] - 1.35]
    json_data_dc_label = json.dumps(json.loads(data_merged_dc.to_json()))
    geosource_json_dc = GeoJSONDataSource(geojson=json_data_dc_label)

    data_merged_florida = data_merged.loc[data_merged["name"]=="Florida"]
    json_data_florida_label = json.dumps(json.loads(data_merged_florida.to_json()))
    geosource_json_florida = GeoJSONDataSource(geojson=json_data_florida_label)

    data_merged_delaware = data_merged.loc[data_merged["name"]=="Delaware"]
    json_data_delaware_label = json.dumps(json.loads(data_merged_delaware.to_json()))
    geosource_json_delaware = GeoJSONDataSource(geojson=json_data_delaware_label)

    data_merged_ri = data_merged.loc[data_merged["name"]=="Rhode Island"]
    json_data_ri_label = json.dumps(json.loads(data_merged_ri.to_json()))
    geosource_json_ri = GeoJSONDataSource(geojson=json_data_ri_label)

    data_merged_michigan = data_merged.loc[data_merged["name"]=="Michigan"]
    json_data_michigan_label = json.dumps(json.loads(data_merged_michigan.to_json()))
    geosource_json_michigan = GeoJSONDataSource(geojson=json_data_michigan_label)

    data_merged_mass = data_merged.loc[data_merged["name"]=="Massachusetts"]
    json_data_mass_label = json.dumps(json.loads(data_merged_mass.to_json()))
    geosource_json_mass = GeoJSONDataSource(geojson=json_data_mass_label)


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

    #p.circle(x='center_lon', y='center_lat', size=3, color='red', alpha=0.7, source=geosource_json)

    labels_all_states = LabelSet(
        x="center_lon",
        y="center_lat",
        text="postal",
        level="glyph",
        text_font_size=label_size,
        text_color="white",
        text_font_style="bold",
        x_offset=-6,
        y_offset=-8,
        source=label_geosource_json,
        render_mode="css",
    )
    if map_width > 500:
      p.add_layout(labels_all_states)

    p.toolbar.active_inspect = None

    ###### DC
    label_dc = LabelSet(
        x="center_lon",
        y="center_lat",
        text="postal",
        level="glyph",
        text_font_size=label_size,
        text_color="black",
        text_font_style="normal",
        x_offset=13,
        y_offset=-28,
        source=geosource_json_dc,
        render_mode="css",
    )

    if map_width > 500:
      p.add_layout(label_dc)
      #p.line(x=[ data_merged_dc['center_lon'], data_merged_dc['center_lon']+13 ], y=[ data_merged_dc['center_lat'], data_merged_dc['center_lat']-26 ], color='red', line_width=5)
      #p.circle(x='center_lon', y='center_lat', size=3, color='red', alpha=0.7, source=geosource_json_dc)
      p.line(x='xs', y='ys', color='black', line_width = 0.75, source=geosource_json_dc)
    ###### MARYLAND
    label_maryland = LabelSet(
        x="center_lon",
        y="center_lat",
        text="postal",
        level="glyph",
        text_font_size=label_size,
        text_color="black",
        text_font_style="normal",
        x_offset=18,
        y_offset=-20,
        source=geosource_json_maryland,
        render_mode="css",
    )

    if map_width > 500:
      p.add_layout(label_maryland)

    ###### DELAWARE
    label_delaware = LabelSet(
        x="center_lon",
        y="center_lat",
        text="postal",
        level="glyph",
        text_font_size=label_size,
        text_color="black",
        text_font_style="normal",
        x_offset=8,
        y_offset=-10,
        source=geosource_json_delaware,
        render_mode="css",
    )

    if map_width > 500:
      p.add_layout(label_delaware)

    ###### MASSACHUSETTS
    label_mass = LabelSet(
        x="center_lon",
        y="center_lat",
        text="postal",
        level="glyph",
        text_font_size=label_size,
        text_color="white",
        text_font_style="bold",
        x_offset=-6,
        y_offset=-6,
        source=geosource_json_mass,
        render_mode="css",
    )

    if map_width > 500:
      p.add_layout(label_mass)

    ##### RHODE ISLAND
    label_ri = LabelSet(
        x="center_lon",
        y="center_lat",
        text="postal",
        level="glyph",
        text_font_size=label_size,
        text_color="black",
        text_font_style="normal",
        x_offset=1,
        y_offset=-14,
        source=geosource_json_ri,
        render_mode="css",
    )

    if map_width > 500:
      p.add_layout(label_ri)

    ##### MICHIGAN
    label_michigan = LabelSet(
        x="center_lon",
        y="center_lat",
        text="postal",
        level="glyph",
        text_font_size=label_size,
        text_color="white",
        text_font_style="bold",
        x_offset=4,
        y_offset=-22,
        source=geosource_json_michigan,
        render_mode="css",
    )

    if map_width > 500:
      p.add_layout(label_michigan)


    ###### FLORIDA
    label_florida = LabelSet(
        x="center_lon",
        y="center_lat",
        text="postal",
        level="glyph",
        text_font_size=label_size,
        text_color="white",
        text_font_style="bold",
        x_offset=4,
        y_offset=-8,
        source=geosource_json_florida,
        render_mode="css",
    )

    if map_width > 500:
      p.add_layout(label_florida)
      dc_line = ColumnDataSource(data=dict({
        "xs" : [ data_merged_dc['center_lon'], data_merged_dc['center_lon']+13 ],
        "ys" : [ data_merged_dc['center_lat'], data_merged_dc['center_lat']-26 ]}
        ))

      p.circle(
        "xs",
        "ys",
        line_color='red',
        source=dc_line,
      )

    ###### ALASKA
    p_alaska = figure(
        tools=TOOLS,
        toolbar_location=None,
        x_axis_location=None,
        y_axis_location=None,
        width=ak_width,
        height=ak_height,
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

    labels = LabelSet(
        x="center_lon",
        y="center_lat",
        text="postal",
        level="glyph",
        text_font_size="6pt",
        text_color="white",
        text_font_style="bold",
        x_offset=-6,
        y_offset=-8,
        source=geosource_json_alaska,
        render_mode="css",
    )
    if map_width > 500:
      p_alaska.add_layout(labels)
    p_alaska.toolbar.active_inspect = None

    ###### HAWAII
    p_hawaii = figure(
        tools=TOOLS,
        toolbar_location=None,
        x_axis_location=None,
        y_axis_location=None,
        width=ak_width,
        height=ak_height,
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

    labels = LabelSet(
        x="center_lon",
        y="center_lat",
        text="postal",
        level="glyph",
        text_font_size="6pt",
        text_color="white",
        text_font_style="bold",
        x_offset=12,
        y_offset=-20,
        source=geosource_json_hawaii,
        render_mode="css",
    )
    if map_width > 500:
      p_hawaii.add_layout(labels)
    p_hawaii.toolbar.active_inspect = None

    ############## INTERACTIVE ELEMENTS ##############
    radio_button_group = RadioButtonGroup(
        labels=["Confirmed", "Deaths", "Testing"], active=0
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
            labels=labels_all_states,
        ),
        code="""
              console.log('CHANGE')
              console.log(labels)

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


def main():

    ############## MOBILE VERSION ##############
    ratio = 320/173
    #map_width = 342 - math.ceil(342/5)
    map_width = 342 - 55
    map_height = math.ceil(map_width/ratio)
    ratio = 130/100
    #ak_width = math.ceil(map_width/5)
    ak_width = 55
    ak_height = math.ceil(ak_width/ratio)
    label_size = '4pt'
    print(ak_width)
    # Json output
    json_outfile = f"../visuals/choropleth/US_race_data_availability.json"

    # Write output file to...
    out_file = f"../visuals/choropleth/choropleth_covid_plot_US_data_availability_342px.html"
    us_data_plot(map_width, map_height, ak_width, ak_height, label_size, out_file, json_outfile)

    ############## DESKTOP VERSION ##############
    ratio = 650/350

    #map_width = 736 - math.ceil(736/5)
    map_width = 736 - 110
    print(f"MAP WIDTH {map_width}")
    map_height = math.ceil(map_width/ratio)
    ratio = 64/49
    #ak_width = math.ceil(map_width/5)
    ak_width = 110
    print(f"AK WIDTH {ak_width}")
    ak_height = math.ceil(ak_width/ratio)
    label_size = '6pt'

    # Write output file to...
    out_file = f"../visuals/choropleth/choropleth_covid_plot_US_data_availability_736px.html"
    us_data_plot(map_width, map_height, ak_width, ak_height, label_size, out_file, json_outfile)


main()
