from collections import OrderedDict
from math import log, sqrt

import numpy as np
import pandas as pd
import requests
import json
import io

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
    HoverTool
)
from bokeh.models.widgets import Slider, Button, Select
from bokeh.layouts import column, row, widgetbox, Spacer
from bokeh.embed import file_html
from bokeh.palettes import brewer

states = ['Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','District of Columbia','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming']

stabr = ['AL','AK','AZ','AR','CA','CO','CT','DE','DC','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']

states_df = pd.DataFrame(list(zip(states, stabr)), 
               columns =['state', 'stabr']) 

income = pd.read_csv('../data_tables/median_household_income.csv')
state_pop = pd.read_csv('../data_tables/state_population.csv')
print(state_pop.columns)

def testing_per_state_plot(width, height, out_file):
    s = requests.get(
        "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports_us/04-12-2020.csv",
        verify=False,
    ).content
    data = pd.read_csv(io.StringIO(s.decode("utf-8")))
    data = data.merge(states_df, left_on="Province_State", right_on="state", sort=False)
    data = data.merge(income, left_on="state", right_on="State", sort=False)
    data = data.merge(state_pop, left_on="state", right_on="State", sort=False)
    data = data.sort_values(by=["People_Tested"]).reset_index()

    ppl_tested = data['People_Tested']

    palette = brewer["YlOrBr"][8]
    palette = palette[::-1]

    rng = 600
    outer_radius = 400
    inner_radius = outer_radius/5
    #color_by = data['Deaths']
    #color_mapper = LogColorMapper(palette=palette, low=min(color_by), high=max(color_by)+max(color_by)/2)

    #color_by = data['HouseholdIncome']
    #color_mapper = LinearColorMapper(palette=palette, low=min(color_by), high=max(color_by))

    color_by = data['Pop']
    print(max(color_by))
    color_mapper = LogColorMapper(palette=palette, low=min(color_by), high=max(color_by))

    inner_radius = inner_radius
    outer_radius = outer_radius

    maxr = sqrt(log(min(ppl_tested)))
    minr = sqrt(log(max(ppl_tested)))

    a = (outer_radius - inner_radius) / (minr - maxr)
    b = inner_radius - a * maxr

    def rad(mic):
        return a * np.sqrt(np.log(mic)) + b

    big_angle = 2.0 * np.pi / (len(data) + 1)
    small_angle = big_angle / 50

    #TOOLS = "hover"
    TOOLS = ''

    p = figure(plot_width=width, plot_height=height, title="",
        toolbar_location=None,
        x_axis_location=None,
        y_axis_location=None,
        x_range=(-rng, rng), y_range=(-rng, rng),
        min_border=0, outline_line_color=None,
        background_fill_color="white",
        tools=TOOLS)

    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None

    # annular wedges
    angles = np.pi/2 - big_angle/2 - data.index.to_series()*big_angle

    # state wedges
    source = ColumnDataSource(
        data=dict(
            radius=list(rad(ppl_tested)),
            ppl_tested=list(ppl_tested),
            state=list(data['state']),
            start_angle=-big_angle+angles+1*small_angle,
            end_angle=-big_angle+angles+35*small_angle,
            deaths=list(data['Deaths']),
            income=list(data['HouseholdIncome']),
            pop=list(data['Pop'])
        )
    )

    wedge = p.annular_wedge(x=0, y=0, inner_radius=inner_radius, outer_radius='radius',
                    start_angle='start_angle', end_angle='end_angle',
                    color={"field": "pop", "transform": color_mapper}, 
                    alpha=0.9, source=source)

    hover = HoverTool(renderers=[wedge],
                         tooltips=[
        ('', '@state'),
        ('Total tested', '@ppl_tested{0,}'),
        #('Deaths', '@deaths{0,}'),
        ('State pop', '@pop{0,}'),
        ])
    p.add_tools(hover)
    '''
    hover = p.select(dict(type=HoverTool))
    hover.tooltips = [
        ('', '@state'),
        ('Total tested', '@ppl_tested{0,}'),
        #('Deaths', '@deaths{0,}'),
        ('State pop', '@pop{0,}'),
    ]
    '''
    ticker = FixedTicker(ticks=[1E6,10E6,20E6,30E6]) # DEATHS Color bar axis markers
    #ticker = FixedTicker(ticks=[10,100,1000,10000]) # DEATHS Color bar axis markers
    #ticker = FixedTicker(ticks=[40000,60000,80000]) # INCOME Color bar axis markers

    color_bar = ColorBar(
        color_mapper=color_mapper,
        border_line_color=None,
        width=20,
        height=100,
        location=(150, rng-200),
        orientation="vertical",
        ticker=ticker, 
        formatter=NumeralTickFormatter(format="0,0"),
        major_tick_out=0,
        major_label_text_align='left',
    )
    p.add_layout(color_bar, 'left')

    radii = rad(ppl_tested)

    y_scalar = (inner_radius+radii/4.75+radii+np.sqrt(np.log(ppl_tested)))
    xr = (radii + radii/11)*np.cos(np.array(-big_angle+angles+10*small_angle)) # make integer bigger, moves left around circ
    yr = y_scalar*np.sin(np.array(-big_angle+angles+25*small_angle))


    label_angle=np.array(-big_angle/2+angles)
    label_angle[label_angle < -np.pi/2] += np.pi # easier to read labels on the left side

    p.text(xr, yr, data['stabr'], angle=label_angle, text_font_size="6pt", text_align="center", text_baseline="middle")


    layout = column(p)
    html = file_html(layout, CDN, "covid_plot_testing_by_state")
    f = open(out_file, "w")
    print(
        f"\nUS TESTING PER STATE PLOT COMPLETE: html file written to {out_file}"
    )
    f.write(html)
    f.close()


############## DESKTOP VERSION ##############
width = 850
height = 550

out_file = f"../visuals/choropleth/covid_plot_testing_per_state_DESKTOP.html"
testing_per_state_plot(width, height, out_file)