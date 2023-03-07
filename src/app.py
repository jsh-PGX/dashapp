import json
from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import pandas as pd


dashboard_name1 = 'dash_1'
app = Dash(__name__)
# Expose Flask instance
server = app.server

# Data Extraction
def sort_list(e):
    return e["Count"]


def create_df(x_label: str, x_axis: list, y_label: str, y_axis: list):
    """
    Creates a dataframe to be used in plotly charts

    :param x_label: label of the x-axis
    :param x_axis: data for the x-axis
    :param y_label: label for the y-axis
    :param y_axis: data for the y-axis
    :return: DataFrame
    """
    dict_line = {x_label: x_axis, y_label: y_axis}
    df = pd.DataFrame.from_dict(dict_line)
    return df


def company_count(y, m, df):
    # Get all active rigs at this month
    a_rigs = [df["Rig"][i] for i in list(df['Rig'].index)]
    # Convert to set
    a_rigs = list(set(a_rigs))
    # Get the name of companies
    a_companies = [rig.split('-')[0] for rig in a_rigs]
    # count for every company
    company_count = {i: a_companies.count(i) for i in a_companies}
    # company_dict = {"Company": list(company_count.keys()), "Count": [company_count[i] for i in company_count]}
    #company_count["Other"] = len(a_rigs) - sum(company_count[key] for key in company_count.keys())
    company_count["Total"] = len(a_rigs)
    company_count["Month"] = int(m)
    company_count['Year'] = int(y)
    return company_count


def field_count(f, df, comps):
    # Get all active rigs at this month
    a_rigs = [df["Rig"][i] for i in list(df['Rig'].index)]
    # Convert to set
    a_rigs = list(set(a_rigs))
    # Get the name of companies
    a_companies = [rig.split('-')[0] for rig in a_rigs]
    # count for every company
    company_count = {i: a_companies.count(i) for i in a_companies}
    company_count["Total"] = len(a_rigs)
    company_count["Field"] = f
    # Check to see if the field is onshore or offshore
    location_df = field_database.loc[field_database["Field"] == field]
    if not location_df.empty:
        company_count["location"] = location_df["Location"].values[0]
    else:
        company_count["location"] = ""
    return company_count


# Main database file
database_path = "index.csv"
# Read and store the main database
main_database = pd.read_csv(database_path)
# Get the field database to check onshore vs offshore fields
field_database = pd.read_csv("Fields.csv")
# Ask the user to input the year and month
year = "2022"
this_month = "2"
# Get previous months of that year
other_months = [str(i) for i in range(int(this_month)-1, 0, -1)]
# Get previous months of last year
last_year = str(int(year) - 1)
last_year_months = [str(12 - i) for i in range(12 - int(this_month))]
# A list to convert months numbers to names
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# Split Database's Date into Day, Month and Year
main_database[['Month', 'Day', 'Year']] = main_database['Date'].str.split('/', expand=True)
main_database['Field'] = main_database['Well'].str.split('-', expand=True)[0]
# Look for the required Year in the database
year_database = main_database.loc[main_database['Year'] == year]
# Get this month's database
this_month_database = year_database.loc[main_database['Month'] == this_month]
# Get the companies in this month
count_per_comp = company_count(year, this_month, this_month_database)

# --- Timeline Graph --- #
# Total rig count for every month of the year from the beginning to current month
line_df = pd.DataFrame({k: [v] for k, v in count_per_comp.items()})
for m in other_months:
    month_database = year_database.loc[year_database['Month'] == m]
    count_per_company = company_count(year, m, month_database)
    m_df = pd.DataFrame({k: [v] for k, v in count_per_company.items()})
    line_df = pd.concat([line_df, m_df])
# Look for months in the previous year
last_year_database = main_database.loc[main_database['Year'] == last_year]
for m_p in last_year_months:
    month_database = last_year_database.loc[last_year_database['Month'] == m_p]
    count_per_company = company_count(last_year, m_p, month_database)
    m_df = pd.DataFrame({k: [v] for k, v in count_per_company.items()})
    line_df = pd.concat([line_df, m_df])
line_df = line_df.fillna(0)
line_df = line_df.sort_values(["Year", "Month"])
line_df = line_df.set_index(pd.Index([i for i in range(12)]))
line_df['Date'] = [months[int(line_df["Month"][i]) - 1] + ' ' + str(line_df["Year"][i]) for i in list(line_df.index)]
line_df = line_df.drop(['Month', 'Year'], axis=1)
# --- Pie Chart of Busiest Fields --- #
columns_keys = count_per_comp
columns_keys.pop('Month')
columns_keys.pop('Year')

field_df = pd.DataFrame(columns=columns_keys.keys())
# Get all active fields of that month
fields = [this_month_database["Field"][i] for i in list(this_month_database['Field'].index)]
# Convert to set
fields = list(set(fields))

for field in fields:
    # Get the occurrences of current field in this month
    database = this_month_database.loc[this_month_database["Field"] == field]
    # Count for every company
    count_per_field = field_count(field, database, count_per_comp.keys())
    f_df = pd.DataFrame({k: [v] for k, v in count_per_field.items()})
    # Add to the main DF
    field_df = pd.concat([field_df, f_df])
field_df = field_df.fillna(0)

# --- Pie Chart of companies market share --- #
comp_df = field_df.transpose()
comp_df.columns = comp_df.loc['Field']
comp_df = comp_df.iloc[:-3]
comp_df['Total'] = [count_per_comp[k] for k in list(columns_keys.keys())[:-1]]
comp_df['Company'] = list(comp_df.index)

# ---------- Plotly -------------- #
# Plot the line chart
line_fig = px.line(line_df, x="Date", y=line_df.columns[:-1])
line_fig.update_layout(legend_title='Company')
line_fig.for_each_trace(lambda trace: trace.update(visible="legendonly")
                        if trace.name != "Total" else ())

# Plot the Map
with open('oil_fields.json') as f:
    map_fields = json.load(f)

rig_count = field_df[["Field", "Total"]]
map_fig = px.choropleth_mapbox(rig_count, geojson=map_fields, locations='Field', color="Total",
                               color_continuous_scale="Viridis",
                               mapbox_style="carto-positron",
                               featureidkey="properties.name",
                               center={"lat": 25.316737, "lon": 49.258831},
                               zoom=5)
# ------------------- The App ------------------- #
menu_options = list(line_df)
menu_options.remove('Date')
title_style = {"font-family": "Arial,Helvetica,sans-serif",
               "font-size": "250%", "color": "#1055a9",
               "padding": "0 0 0 1em",
               "margin": "0 0 0px 8px",
               "border-style": "none none none solid",
               "border-color": "#1055a9"}
app.layout = html.Div(children=[
    html.H1(children='Rig', style=title_style),
    html.H1(children='Activity', style=title_style),
    html.H1(children='Report', style=title_style),

    html.H2(children=months[int(this_month)-1] + ', ' + year,
            style={"font-family": "Arial,Helvetica,sans-serif",
                   "font-size": "150%", "color": "white",
                   "padding": "10px 20px 10px 20px", "margin": "24px 0 24px 8px",
                   "border-radius": "15px", "width": "20%", "text-align": "center",
                   "background": "#619c54"}),

    html.H2(children='Total Active Rigs', style={"font-family": "Arial,Helvetica,sans-serif",
                                                 "font-size": "150%", "color": "black",
                                                 "padding": "0 0 0 1em",
                                                 "margin": "12px 0 0 8px",
                                                 "border-style": "none none none solid",
                                                 "border-color": "#1055a9"}),

    dcc.Graph(
        figure=line_fig
    ),

    html.H2(children='Market Shares', style={"font-family": "Arial,Helvetica,sans-serif",
                                             "font-size": "150%", "color": "black",
                                             "padding": "0 0 0 1em",
                                             "margin": "12px 0 8px 8px",
                                             "border-style": "none none none solid",
                                             "border-color": "#1055a9"}),

    html.Div(
        children=[dcc.Graph(id='f_pie', style={'width': '49%', 'display': 'inline-block'}),
                  dcc.Graph(id='c_pie', style={'width': '49%', 'display': 'inline-block'})
                  ], className="row"
    ),
    html.Div(children=[
        html.H3(children="Select a Company for more details",
                style={"font-family": "Arial,Helvetica,sans-serif",
                       "font-size": "100%", "color": "black",
                       "margin": "0px 0 8px 8px", 'width': '49%',
                       "border-style": "none none none none",
                       "border-color": "#1055a9", 'display': 'inline-block'}),
        html.H3(children="Select a Field for more details",
                style={"font-family": "Arial,Helvetica,sans-serif",
                       "font-size": "100%", "color": "black",
                       "margin": "0px 0px 8px 8px", 'width': '49%',
                       "border-style": "none none none none",
                       "border-color": "#1055a9", 'display': 'inline-block'})
    ]),
    html.Div(children=[
        dcc.Dropdown(options=menu_options, value="Total", id="ddlist_f",
                     style={'width': '50%', 'display': 'inline-block'}),
        dcc.Dropdown(options=comp_df.columns.to_list()[:-1], value="Total", id="ddlist_c",
                     style={'width': '50%', 'display': 'inline-block'})
    ]),

    html.H2(children='Active Map', style={"font-family": "Arial,Helvetica,sans-serif",
                                          "font-size": "150%", "color": "black",
                                          "padding": "0 0 0 1em",
                                          "margin": "12px 0 0 8px",
                                          "border-style": "none none none solid",
                                          "border-color": "#1055a9"}),

    dcc.Graph(
        figure=map_fig
    )
])

# ---------- Plotly -------------- #

# Plot the fields' pie chart
@app.callback(
    Output("f_pie", "figure"),
    Input("ddlist_f", "value"))
def update_fpie_chart(f):
    df = field_df
    # if f == 'Total':
    #     df.loc[df["Total"] < 5, 'Field'] = "Other"
    df['values'] = df[f] if type(f) == str else df[f].sum(axis=1)
    pie_fig = px.pie(df, names="Field", values=f, hover_data=["location"])
    pie_fig.update_layout(title={'text': 'By Field', 'x': 0.45, 'y': 0.95, 'pad': {'b': 5}})
    pie_fig.update_traces(textposition='inside', textinfo='percent+label')
    return pie_fig

# Plot the companies' pie chart
@app.callback(
    Output("c_pie", "figure"),
    Input("ddlist_c", "value"))
def update_cpie_chart(f):
    df = comp_df
    # if f == 'Total':
    #     df.loc[df["Total"] < 3, 'Company'] = "Other"
    df['values'] = df[f] if type(f) == str else df[f].sum(axis=1)
    pie_fig = px.pie(df, names="Company", values=f)
    pie_fig.update_layout(title={'text': 'By Company', 'x': 0.45, 'y': 0.95, 'pad': {'b': 5}})
    pie_fig.update_traces(textposition='inside', textinfo='percent+label')
    return pie_fig

if __name__ == '__main__':
    app.run_server(debug=True)
