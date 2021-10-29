#! /usr/bin/env python3
import numpy as np
import pandas as pd
import datetime

# from bokeh.io import show
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, RangeTool, Range1d, LinearAxis
from bokeh.plotting import figure, output_file, save
from bokeh.resources import CDN
from bokeh.embed import file_html, components
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.resources import INLINE

from flask import Flask, render_template
app = Flask(__name__)

#pd.options.mode.chained_assignment = None  # default='warn'  #this turns of copy index warnings - careful!

# --------------------------------------------------------
# some helpers


def read_files(url):
    # with open(filename) as data_file:
    df = pd.read_csv(url, skiprows=0)

    df.time = pd.to_datetime(df.time)
    df[['schnee']].astype(float)
    df.dropna(axis=0, inplace=True)
    return df


def fixdatestrings(dt):
    if dt < 10:
        dtS = '0' + str(dt)
    else:
        dtS = str(dt)
    return (dtS)


def assign_wy(row):
    if row.time.month>=10:
        return(pd.datetime(row.time.year+1,1,1).year)
    else:
        return(pd.datetime(row.time.year,1,1).year)


# --------------------------------------------------------
# MAIN script
now = datetime.datetime.now()
end = str(now.year) + '-' + fixdatestrings(now.month)  + '-' +  fixdatestrings(now.day) + '%2000:00'

sid = '15411'  # sonnblick
var = 'schnee,t'
sdate = '1986-10-01%2000:00' #start of SB timeseries
edate = end
filename = 'https://forms.hub.zamg.ac.at/v1/station/e1d81743-60f2-4fa2-be63-3fdc8a7e2822/historical?anonymous=true&parameters='+var+'&start='+sdate+'&end='+edate+'&station_ids='+sid+'&output_format=csv'
# print(filename)
dat_df = read_files(filename)

dat_df['WY'] = dat_df.apply(lambda x: assign_wy(x), axis=1)
dat_df.set_index('time', inplace=True)
dat_df['WY_s'] = pd.to_datetime((dat_df['WY']-1).astype(str)+'10'+'01')
dat_df['WY_doy'] = (dat_df.index - dat_df['WY_s']).dt.days

# make df of normals for snow height
snow = pd.DataFrame(columns=['mean', 'med', 'max', 'min'])
norm_mean = dat_df.groupby([dat_df.WY_doy]).mean()
snow['mean'] = norm_mean['schnee']
norm_max = dat_df.groupby([dat_df.WY_doy]).max()
snow['max'] = norm_max['schnee'].values
snow['min'] = dat_df.groupby([dat_df.WY_doy]).min()['schnee'].values
snow['med'] = dat_df.groupby([dat_df.WY_doy]).median()['schnee'].values

cur_year = dat_df.loc[dat_df['WY_s'].values[-1]:dat_df.index.values[-1]]
cur_year.set_index('WY_doy', inplace=True)

dates = pd.date_range(start='2019/10/01', end='2020/09/30', freq='D')
snow['dates'] = dates

snow = snow.join(cur_year[['schnee', 't']])


def makePlot():
    source = ColumnDataSource(data=snow)

    p = figure(plot_height=500, plot_width=800,
               x_axis_type="datetime", title='Sonnblick typical snow depth (time series:'+str(dat_df.index[0].year)+'-'+str(dat_df.index[-1].year)+')',
               x_axis_location="below",
               background_fill_color="#efefef", x_range=(dates[0], dates[-1]))
               # formatter=DatetimeTickFormatter(days=['%b %d']))
    # tools="xpan", toolbar_location=None
    p.line('dates', 'schnee', source=source, legend_label='current', line_color='tomato')
    p.line('dates', 'mean', source=source, legend_label='time series mean', line_color='black')
    p.line('dates', 'med', source=source, legend_label='ts median', line_color='grey')
    p.line('dates', 'max', source=source, legend_label='ts max', line_color='blue')
    p.line('dates', 'min', source=source, legend_label='ts min', line_color='green')

    p.yaxis.axis_label = 'snow depth (cm)'
    p.legend.location = "top_left"
    p.legend.click_policy = "hide"
    p.xaxis.formatter = DatetimeTickFormatter(months = ['%b'])

    select = figure(title="Drag the selection box to change the range above",
                    plot_height=130, plot_width=800, y_range=p.y_range,
                    x_axis_type="datetime",
                    tools="", toolbar_location=None, background_fill_color="#efefef", x_range=(dates[0], dates[-1]))

    range_tool = RangeTool(x_range=p.x_range)
    range_tool.overlay.fill_color = "navy"
    range_tool.overlay.fill_alpha = 0.2

    select.line('dates', 'schnee', source=source)
    select.line('dates', 'mean', source=source)
    select.yaxis.axis_label = 'cm'
    select.ygrid.grid_line_color = None
    select.add_tools(range_tool)
    select.toolbar.active_multi = range_tool

    return(column(p, select))


def secondPlot():
    dat_df['dates'] = dat_df.index.values
    #print(dat_df)
    source = ColumnDataSource(data=dat_df)
    p1 = figure(plot_height=300, plot_width=800,
                title="Sonnblick daily air temp and snow depth",
               x_axis_type="datetime", x_axis_location="above",
               background_fill_color="#efefef", x_range=(dat_df['dates'].values[-200], dat_df['dates'].values[-1]))
    # tools="xpan", toolbar_location=None
    p1.line('dates', 't', source=source, legend_label = 'Air Temp', line_color="tomato")
    # p.line('dates', 'schnee', source=source, legend = 'Dew Point', line_color="indigo" )
    p1.y_range = Range1d(
        dat_df.t.min() - 2, dat_df.t.max() + 2)

    p1.yaxis.axis_label = 'air temp (celsius)'
    p1.legend.location = "bottom_left"
    p1.legend.click_policy = "hide"

    p1.extra_y_ranges = {"schnee": Range1d(start=0, end=600)}
    p1.add_layout(LinearAxis(y_range_name="schnee", axis_label='snow depth (cm)'), 'right')
    p1.line('dates', 'schnee', source=source, legend_label = 'schnee', line_color="blue" , y_range_name="schnee")


    select1 = figure(title="Drag the selection box to change the range above",
                    plot_height=130, plot_width=800, y_range=p1.y_range,
                    x_axis_type="datetime",
                    tools="", toolbar_location=None, background_fill_color="#efefef", x_range=(dat_df['dates'].values[0], dat_df['dates'].values[-1]))

    range_tool = RangeTool(x_range=p1.x_range)
    range_tool.overlay.fill_color = "navy"
    range_tool.overlay.fill_alpha = 0.2

    select1.line('dates', 't', source=source)
    select1.yaxis.axis_label = 'C'
    select1.ygrid.grid_line_color = None
    select1.add_tools(range_tool)
    select1.toolbar.active_multi = range_tool

    # html = file_html(column(p, select), CDN, "my plot")
    # Html_file= open("plotTest2.html","w")
    # Html_file.write(html)
    # Html_file.close()

    return(column(p1, select1))


@app.route('/')
def Sonnblick():
    # Create the plot
    plot = makePlot()
        
    # Embed plot into HTML via Flask Render
    script, div = components(plot)
    return render_template(
        'Sonnblick.html',
        plot_script=script,
        plot_div=div,
        js_resources=INLINE.render_js(),
        css_resources=INLINE.render_css(),
        ).encode(encoding='UTF-8')

@app.route('/SonnblickTS')
def SonnblickTS():
    # Create the plot
    plot = secondPlot()
        
    # Embed plot into HTML via Flask Render
    script, div = components(plot)
    return render_template(
        'SonnblickTS.html',
        plot_script=script,
        plot_div=div,
        js_resources=INLINE.render_js(),
        css_resources=INLINE.render_css(),
        ).encode(encoding='UTF-8')

if __name__ == '__main__':

    app.run(host='0.0.0.0')
