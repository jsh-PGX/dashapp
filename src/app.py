from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import numpy as np
import pandas as pd
import json

app = Dash(__name__)
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


def company_count(m, df):
    # Get all active rigs at this month
    a_rigs = [df["Rig"][i] for i in list(df['Rig'].index)]
    # Convert to set
    a_rigs = list(set(a_rigs))
    # Get the name of companies
    a_companies = [rig.split('-')[0] for rig in a_rigs]
    # count for every company
    company_count = {i: a_companies.count(i) for i in a_companies if a_companies.count(i) > 5}
    # company_dict = {"Company": list(company_count.keys()), "Count": [company_count[i] for i in company_count]}
    company_count["Other"] = len(a_rigs) - sum(company_count[key] for key in company_count.keys())
    company_count["Total"] = len(a_rigs)
    company_count["Month"] = int(m)
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
this_month = "7"
# Get previous months of that year
other_months = [str(i) for i in range(int(this_month)-1, 0, -1)]
# A list to convert months numbers to names
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# Split Database's Date into Day, Month and Year
main_database[['Month', 'Day', 'Year']] = main_database['Date'].str.split('/', expand=True)
main_database['Field'] = main_database['Well'].str.split('-', expand=True)[0]
# Look for the required Year in the database
year_database = main_database.loc[main_database['Year'] == year]
# Get this month's database
this_month_database = main_database.loc[main_database['Month'] == this_month]
# Get the companies in this month
count_per_comp = company_count(this_month, this_month_database)

# --- Timeline Graph --- #
# Total rig count for every month of the year from the beginning to current month
line_df = pd.DataFrame({k: [v] for k, v in count_per_comp.items()})
for m in other_months:
    month_database = year_database.loc[year_database['Month'] == m]
    count_per_company = company_count(m, month_database)
    m_df = pd.DataFrame({k: [v] for k, v in count_per_company.items()})
    line_df = pd.concat([line_df, m_df])
line_df = line_df.fillna(0)
line_df.sort_values("Month")

# --- Pie Chart of Busiest Fields --- #
field_df = pd.DataFrame(columns=count_per_comp.keys())
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
# Get all active rigs at this month
active_rigs = [this_month_database["Rig"][i] for i in list(this_month_database['Rig'].index)]
# Convert to set
active_rigs = list(set(active_rigs))
# Get the name of companies
companies = [rig.split('-')[0] for rig in active_rigs]
# count for every company
company_count = {i: companies.count(i) for i in companies if companies.count(i) > 2}
company_dict = {"Company": list(company_count.keys()), "Count": [company_count[i] for i in company_count]}

# ---------- Plotly -------------- #
'''
# Plot the field pie chart
df_pie = pd.DataFrame.from_dict(rigs_per_field)
df_pie.loc[df_pie["Rig Count"] < 2, 'Field'] = "Other"
pie_fig = px.pie(df_pie, names="Field", values="Rig Count", hover_data=["Location"])
pie_fig.update_layout(title={'text': 'By Field', 'x': 0.5, 'y': 0, 'pad': {'b': 5}})
pie_fig.update_traces(textposition='inside', textinfo='percent+label')

# Plot the companies' pie chart
df_comp_pie = pd.DataFrame.from_dict(company_dict)
comp_pie_fig = px.pie(df_comp_pie, names="Company", values="Count")
comp_pie_fig.update_layout(title={'text': 'By Company', 'x': 0.5, 'y': 0, 'pad': {'b': 5}})
comp_pie_fig.update_traces(textposition='inside', textinfo='percent+label')

# Plot the bar chart
df_bar = pd.DataFrame.from_dict(rigs_per_field)
df_bar["Location"].replace("", np.NAN, inplace=True)
df_bar = df_bar.dropna(0)
bar_fig = px.bar(df_bar, x="Field", y="Rig Count", color="Location")

# Active map using plotly
lst_of_fields = rigs_per_field["Field"]
lst_of_no_of_rigs = rigs_per_field["Rig Count"]

map_df = pd.DataFrame.from_dict({"name": lst_of_fields, "Rigs": lst_of_no_of_rigs})
with open("J:/Petrogistix/PetroMine/Other/oil_fields.json") as f:
    geojson = json.load(f)
rig_map = px.choropleth_mapbox(map_df, geojson=geojson, color="Rigs", locations="name", featureidkey="properties.name",
                               mapbox_style="carto-positron", zoom=3, center={"lat": 24, "lon": 50})
# rig_map.update_geos(fitbounds="locations")
'''
# ------------------- The App ------------------- #
menu_options = list(line_df)
menu_options.remove("Month")
app.layout = html.Div(children=[
    html.H1(children='Active Rigs Report'),

    html.Div(children='''
        Dash: A web application framework for your data.
    '''),
    dcc.Dropdown(
      options=menu_options, value="Total", id="dropdown", multi=True
    ),
    dcc.Graph(
        id='line'
    ),
    dcc.Graph(
        id='f_pie'
    ),
    dcc.Graph(
        id='map'
    ),
])

# ---------- Plotly -------------- #
# Plot the line chart
@app.callback(
    Output("line", "figure"),
    Input("dropdown", "value"))
def update_line_chart(company):
    line_fig = px.line(line_df, x="Month", y=company)
    return line_fig

# Plot the fields' pie chart
@app.callback(
    Output("f_pie", "figure"),
    Input("dropdown", "value"))
def update_fpie_chart(f):
    field_df.loc[field_df["Total"] < 2, 'Field'] = "Other"
    pie_fig = px.pie(field_df, names="Field", values=f, hover_data=["location"])
    pie_fig.update_layout(title={'text': 'By Field', 'x': 0.5, 'y': 0, 'pad': {'b': 5}})
    pie_fig.update_traces(textposition='inside', textinfo='percent+label')


if __name__ == '__main__':
    app.run_server(debug=True)
