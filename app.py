from flask import Flask, render_template, request
import pandas as pd
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar
from bokeh.palettes import brewer
from bokeh.models.tools import HoverTool
from bokeh.embed import components
import geopandas as gpd
import numpy as nppi
import json
from datetime import datetime
from datetime import date
from datetime import timedelta

app = Flask(__name__)


def plot_data(_country, _date, typeOfData):
    deaths_url = "https://raw.githubusercontent.com/datasets/covid-19/master/data/countries-aggregated.csv"
    ds = pd.read_csv(deaths_url)

    ds["Date"] = pd.to_datetime(ds["Date"])

    ds.replace(to_replace="US", value="United States of America", inplace=True)
    ds.replace(to_replace="Congo (Kinshasa)", value="Democratic Republic of the Congo", inplace=True)
    ds.replace(to_replace="Congo (Brazzaville)", value="Republic of the Congo", inplace=True)
    ds.replace(to_replace="Cote d'Ivoire", value="Ivory Coast", inplace=True)
    ds.replace(to_replace="Taiwan*", value="Taiwan", inplace=True)
    ds.replace(to_replace="Tanzania", value="United Republic of Tanzania", inplace=True)
    ds.replace(to_replace="Burma", value="Myanmar", inplace=True)
    ds.replace(to_replace="Bahamas", value="The Bahamas", inplace=True)
    ds.replace(to_replace="Serbia", value="Republic of Serbia", inplace=True)
    ds.replace(to_replace="Timor-Leste", value="East Timor", inplace=True)
    ds.replace(to_replace="Korea, South", value="South Korea", inplace=True)
    ds.replace(to_replace="North Macedonia", value="Macedonia", inplace=True)

    countries = ds.Country.values
    countries = np.unique(countries).tolist()

    shapefile = 'Analysis/shapefiles/ne_110m_admin_0_countries.shp'
    gdf = gpd.read_file(shapefile)[['ADMIN', 'ADM0_A3', 'geometry']]

    gdf.columns = ['country', 'country_code', 'geometry']
    gdf = gdf.drop(gdf.index[159])  # Drop Antarctica

    gdfCountries = gdf.country.values

    mask = ds['Country'] == _country
    ds_sub = ds[mask].reset_index()

    dateSub = ds[ds['Date'] == _date]

    sourceDate = ColumnDataSource(data={
        'date': dateSub.Date,
        'country': dateSub.Country,
        'Confirmed': dateSub.Confirmed,
        'Recovered': dateSub.Recovered,
        'Deaths': dateSub.Deaths
    })

    source = ColumnDataSource(data={
        'date': ds_sub.Date,
        'country': ds_sub.Country,
        'confirmed': ds_sub.Confirmed,
        'recovered': ds_sub.Recovered,
        'dead': ds_sub.Deaths
    })

    plot = figure(title=_country, x_axis_label='Dates', y_axis_label='Cases Count', x_axis_type='datetime',
                  plot_width=1200, plot_height=680)

    plot.line(x='date', y='confirmed', source=source, color='blue', line_width=4)
    plot.line(x='date', y='recovered', source=source, color='green', line_width=4)
    plot.line(x='date', y='dead', source=source, color='red', line_width=4)

    plot.toolbar.logo = None
    plot.toolbar_location = None

    hover = HoverTool(tooltips=[('Confirmed', '@confirmed'), ('Recovered', '@recovered'), ('Deceased', '@dead')])
    plot.add_tools(hover)
    plot.left[0].formatter.use_scientific = False

    merged = gdf.merge(dateSub, left_on='country', right_on='Country', how='left')
    merged['Date'] = merged['Date'].dt.strftime('%Y-%m-%d')

    merged_json = json.loads(merged.to_json())  # Read data to JSON
    json_data = json.dumps(merged_json)

    geosource = GeoJSONDataSource(geojson=json_data)

    palette = brewer["YlGnBu"][8]
    palette = palette[::-1]

    color_mapper = LinearColorMapper(palette=palette, low=dateSub[typeOfData].min(),
                                     high=(dateSub[typeOfData].max() / 2.5), nan_color='#d9d9d9')

    if typeOfData == "Confirmed":
        hover = HoverTool(tooltips=[('Country', '@Country'), ('Confirmed Cases', '@Confirmed')])
        titleString = "Number of {} COVID-19 cases - {}".format(typeOfData, _date)
    elif typeOfData == "Recovered":
        hover = HoverTool(tooltips=[('Country', '@Country'), ('Recovered Cases', '@Recovered')])
        titleString = "Number of {} COVID-19 cases - {}".format(typeOfData, _date)
    elif typeOfData == "Deaths":
        hover = HoverTool(tooltips=[('Country', '@Country'), ('Fatalities', '@Deaths')])
        titleString = "Number of COVID-19 fatalities - {}".format(_date)

    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8, width=500, height=20,
                         border_line_color=None, location=(0, 0), orientation='horizontal')

    p = figure(title=titleString, plot_height=680, plot_width=1200, toolbar_location=None, tools=[hover])
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None

    # Add patch renderer to figure.
    p.patches('xs', 'ys', source=geosource, fill_color={'field': typeOfData, 'transform': color_mapper},
              line_color='black', line_width=0.25, fill_alpha=1)

    # Specify layout
    p.add_layout(color_bar, 'below')
    p.axis.visible = False

    return plot, p, countries


@app.route('/')
def index():
    # Determine the selected country
    current_country_name = request.args.get("country_names")
    selectedDate = request.args.get("date")
    typeOfData = request.args.get("typeOfData")

    if current_country_name is None:
        current_country_name = "India"

    if selectedDate is None:
        selectedDate = "2020-07-26"
        selectedDate = datetime.strptime(selectedDate, '%Y-%m-%d')
        selectedDate = datetime.date(selectedDate)
        print(selectedDate)
    else:
        selectedDate = datetime.strptime(selectedDate, '%Y-%m-%d')
        selectedDate = datetime.date(selectedDate)
        print(selectedDate)

    today = date.today()
    yesterday = today - timedelta(days=1)

    if selectedDate > yesterday:
        selectedDate = "2020-07-26"
        print("Date not valid - after")
    elif selectedDate < date(2020, 1, 20):
        selectedDate = "2020-01-22"
        print("Date not valid - before")

    if typeOfData is None:
        typeOfData = "Confirmed"

    # Create the plot
    plot, plot1, name = plot_data(current_country_name, selectedDate, typeOfData)

    # Embed plot into HTML via Flask Render
    script, div = components(plot)
    script1, div1 = components(plot1)
    return render_template("index.html", script_plot=script, div_plot=div,
                           script_active_plot=script1, div_active_plot=div1,
                           country_names=name, current_country_name=current_country_name)


if __name__ == '__main__':
    app.run()
