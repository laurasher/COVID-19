# myapp.py

from random import random
import numpy as np
import pandas as pd
import math
import json
import io
import requests

from bokeh.palettes import RdYlBu3
from bokeh.models.graphs import from_networkx
from bokeh.plotting import figure, curdoc
from bokeh.resources import CDN
from bokeh.embed import autoload_static, json_item, file_html
from bokeh.tile_providers import get_provider, Vendors
from bokeh.models import (
    ColumnDataSource,
    CustomJS,
    LabelSet,
    Plot,
    WheelZoomTool,
    FuncTickFormatter,
    Legend,
    CategoricalColorMapper,
    Range1d,
    MultiLine,
    Circle,
    HoverTool,
    PanTool,
    ResetTool,
    LogColorMapper,
    LinearAxis,
    Grid,
    Label,
    Title,
)
from bokeh.models.widgets import Slider, Button, TextInput
from bokeh.models.glyphs import Patches
from bokeh.layouts import column, row, widgetbox, Spacer
from bokeh.palettes import Spectral4
from bokeh.palettes import Viridis6 as palette
from bokeh.io import output_notebook, show, export_svgs
from bokeh.resources import CDN
from bokeh.embed import autoload_static, json_item
from bokeh.layouts import gridplot
from bokeh.embed import file_html

import geopandas as gpd
from bokeh.models import GeoJSONDataSource, HoverTool, LinearColorMapper, ColorBar
from bokeh.palettes import Viridis6
from bokeh.palettes import brewer
import urllib


def merc_from_arrays(lats, lons):
    r_major = 6378137.000
    x = r_major * np.radians(lons)
    scale = x / lons
    y = (
        180.0
        / np.pi
        * np.log(np.tan(np.pi / 4.0 + lats * (np.pi / 180.0) / 2.0))
        * scale
    )
    return (x, y)


shapefile = "../data/countries_110m/ne_110m_admin_0_countries.shp"

# Read shapefile using Geopandas
gdf = gpd.read_file(shapefile)[["ADMIN", "ADM0_A3", "geometry"]]

# Rename columns.
gdf.columns = ["country", "country_code", "geometry"]

# Drop row corresponding to 'Antarctica'
gdf = gdf.drop(gdf.index[159])
grid_crs = gdf.crs


#################################################### GET AND CLEAN DATA ####################################################
skipCols = 3  # columns at head (Province, Country, Lat, Long)
skipColsTail = 1  # status and color

s = requests.get(
    "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv",
    verify=False,
).content
confirmed = pd.read_csv(io.StringIO(s.decode("utf-8")))
confirmed["status"] = "confirmed"

s = requests.get(
    "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv",
    verify=False,
).content
recovered = pd.read_csv(io.StringIO(s.decode("utf-8")))
recovered["status"] = "recovered"

s = requests.get(
    "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv",
    verify=False,
).content
deaths = pd.read_csv(io.StringIO(s.decode("utf-8")))
deaths["status"] = "deaths"

total = confirmed
total.loc[total["Country/Region"] == "US", "Country/Region"] = "United States of America"
total.loc[total["Country/Region"] == "Congo (Brazzaville)", "Country/Region"] = "Republic of the Congo"
total.loc[total["Country/Region"] == "Congo (Kinshasa)", "Country/Region"] = "Democratic Republic of the Congo"
total = total.sort_values(by=["Country/Region"])

print("-------------------------DATA-------------------------")
print(total)

print('---------------------- GROUP ALL COUNTRIES')
total =  total.groupby('Country/Region').sum().reset_index()
total = total.sort_values(by=["Country/Region"])
print(total)
print(total[total['Country/Region'] =='China'])
print(total[total['Country/Region'] =='United States of America'])

dates = list(total.columns)
dates = dates[skipCols + 1 : len(total.columns) - skipColsTail]
numDays = total.shape[1] - (skipCols + skipColsTail + 1)

#print(f"Num days: {numDays}")
latestDateCol = total.columns[numDays + skipCols]
#print(f"Latest date: {latestDateCol}")

# Read data to json.
gdf_json = json.loads(gdf.to_json())
# Convert to String like object.
grid = json.dumps(gdf_json)

# Input GeoJSON source that contains features for plotting.
geosource = GeoJSONDataSource(geojson=grid)

# DROP DIAMOND PRINCESS
total.drop(total[total["Country/Region"] == "Diamond Princess"].index, axis=0, inplace=True)

print('---------------- MERGE ----------------')
total_latest = total.iloc[:, 0:3].join(total[latestDateCol])
total_latest.columns = ["Country/Region", "Lat", "Long", "latest_cases"]


print("--------- total latest")
print(total_latest)
print(total_latest[total_latest['Country/Region'] =='China'])
print(total_latest[total_latest['Country/Region'] =='United States of America'])

print("--------- gdf")
print(gdf)

total_merged_to_mat = gdf.merge(total, right_on="Country/Region", left_on="country", sort=False)
total_merged_to_mat = total_merged_to_mat.drop(columns=['country_code', 'geometry', 'country'])
total_merged_to_mat = total_merged_to_mat.sort_values(by=["Country/Region"])
print('---------- ADJUSTING MATRIX')
print(total_merged_to_mat)
#total_mat = total.as_matrix().transpose()
total_mat = total_merged_to_mat.as_matrix().transpose()
print(total_mat)

merged = gdf.merge(total_latest, right_on="Country/Region", left_on="country", sort=False)
merged = merged.sort_values(by=["Country/Region"])

print("---------")
print(merged)
print(merged[merged['Country/Region'] =='China'])
print(merged[merged['Country/Region'] =='United States of America'])

merged_json = json.loads(merged.to_json())

# Convert to String like object.
json_data = json.dumps(merged_json)
geosource_json = GeoJSONDataSource(geojson=json_data)

date_label_source = ColumnDataSource(data=dict(names=[latestDateCol]))


TOOLS = "pan,wheel_zoom,reset,hover,save"
p = figure(
    tools=TOOLS,
    toolbar_location=None,
    x_axis_location=None,
    y_axis_location=None,
    width=640,
    height=300,
    x_axis_type="mercator",
    y_axis_type="mercator",
)

p.border_fill_color = "white"
p.background_fill_color = "white"
p.outline_line_color = None
p.grid.grid_line_color = None
p.grid.grid_line_color = None

tile_provider = get_provider(Vendors.CARTODBPOSITRON)
# tile_provider = get_provider(Vendors.STAMEN_TONER)
# p.add_tile(tile_provider)
p.toolbar.active_scroll = p.select_one(WheelZoomTool)
p.title.text_font_size = "14pt"
p.toolbar.logo = None
p.toolbar_location = None


# Add patch renderer to figure.
# Define a sequential multi-hue color palette.
palette = brewer["Reds"][8]

# Reverse color order so that dark blue is highest obesity.
palette = palette[::-1]

# Instantiate LinearColorMapper that linearly maps numbers in a range, into a sequence of colors.
color_mapper = LinearColorMapper(palette=palette, low=0, high=40)

# Define custom tick labels for color bar.
# tick_labels = {'0': '0%', '5': '5%', '10':'10%', '15':'15%', '20':'20%', '25':'25%', '30':'30%','35':'35%', '40': '>40%'}

# Create color bar.
color_bar = ColorBar(
    color_mapper=color_mapper,
    border_line_color=None,
    height=300,
    location=(0, 0),
    orientation="vertical",
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
    line_color='lightgray',
    line_width=0.5,
    fill_alpha=1,
)

timeslider = Slider(
    start=1, end=numDays, value=numDays, step=1, title="", show_value=False
)

updateData = CustomJS(
    args=dict(
        geosource_json=geosource_json,
        date_label_source=date_label_source,
        color_frames=total_mat,  # need to make this a matrix
        dates=dates,
    ),
    code="""
            var f = cb_obj.value
            console.log(f)
            console.log(geosource_json)
            console.log(dates[f-1])

            date_label_source.data.names[0] = dates[f-1]
            date_label_source.change.emit()

            geosource_json.data.latest_cases = color_frames[f+3]
            geosource_json.change.emit()
            console.log(color_frames)
            """,
)
timeslider.js_on_change("value", updateData)
playbutton = Button(label="► Play", button_type="default")
timeline = range(timeslider.end)


labels = LabelSet(
    x=0,
    y=0,
    x_units="screen",
    y_units="screen",
    text="names",
    level="glyph",
    x_offset=5,
    y_offset=5,
    source=date_label_source,
    render_mode="css",
    border_line_color="white",
    border_line_alpha=0.0,
    text_font_size="20px",
    background_fill_color="white",
    background_fill_alpha=0.0,
)

p.add_layout(labels)
p.add_layout(color_bar, 'right')
p.toolbar.active_inspect = None

animateSlider = CustomJS(
    args=dict(timeslider=timeslider, end=numDays),
    code="""
            console.log("Clicked button")
            timeslider.value = timeslider.start
            console.log("Set to beginning")
            step_length_ms = 300
            num_steps = end-1
            inc = 1
            
            playback_interval = setInterval(function(){
                timeslider.value = timeslider.value+inc;
                console.log(timeslider.value);
            }, step_length_ms)
            setTimeout(function(){clearInterval(playback_interval)}, step_length_ms*num_steps)

        """,
)

playbutton.js_on_click(animateSlider)


#################################################### LAYOUT AND ADD TO HMTL DOC ####################################################

# m_layout = column(p, timeslider, widgetbox(playbutton, width=100), row(barplot))
m_layout = column(p, timeslider, widgetbox(playbutton, width=100))
html = file_html(m_layout, CDN, "choropleth_covid_plot")
f = open("../choropleth_covid_plot.html", "w")
print('------ New html file written')
f.write(html)
f.close()
