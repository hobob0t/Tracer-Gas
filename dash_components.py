from dash import dcc, html
import datetime
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from helpers import *

init_layout = {"showlegend": True, "uirevision": True, "hoverdistance": -1,
               'xaxis': {'title_text': 'Time'},
               'yaxis': {'title_text': 'CO2 Concentration [PPM]'},
               'yaxis2': {'anchor': 'x','overlaying': 'y','side': 'right'},
               'margin': {'b': 0, 'l': 0, 'r': 0, 't': 30},}

# define drop down component with list of serial ports
def serial_port_dropdown(id):
    return dcc.Dropdown(
        id=id,
        options=[{"label": port, "value": port} for port in get_serial_ports()],
        value=None)

connections = html.Div(
    id="connections",
    children=[]
)


# define graph div
graph = html.Div(
    id="graph-div",
    children=[
        dcc.Graph(id="graph",figure=go.Figure(layout=init_layout,data=[go.Scattergl(x=[], y=[])]))
    ]
)

# define interval component for updating graph
interval = dcc.Interval(
    id="interval",
    interval=1000,
    n_intervals=0
)

# define logger text area
logger_area = html.Div(id="logger")

# define interval component for showing connected equipment
interval_connections = dcc.Interval(
    id="interval-connections",
    interval=1000,
    n_intervals=0
)

# update serial ports dropdown button
def update_ports_list():
    return dbc.Toast([
         dbc.Button("Update Serial Port List", id="btn-update-serial-port-list")
         ],
        id="update_group",
        header="Update Ports",
    )


# CO2 connect input
def co2_gas_analyzer_input():
    return dbc.Toast(
        [html.Label("Name"),
         dcc.Input(id="co2-gas-analyzer", type="text", value=""),
         serial_port_dropdown("GA-port"),
         dbc.Button("Connect", id="submit-co2-gas-analyzer")
         ],
        id="co2-gas-analyzer-group",
        header="Connect To CO2 Gas Analyzer",
    )

# Alicat connect input
def alicat_input():
    return dbc.Toast(
        [html.Label("Name"),
         dcc.Input(id="alicat-name", type="text", value=""),
         serial_port_dropdown("alicat-port"),
         dbc.Button("Connect", id="submit-alicat")
         ],
        id="alicat-group",
        header="Connect To Mass Flow Controller",
    )

button_row_1 = dbc.Row([dbc.Col(dcc.DatePickerRange(id='date-picker-range'), width='auto'),
                 dbc.Col(dbc.Button("Load Dates", id="btn-load", color="primary"), width='auto'),
                 dbc.Col(dbc.Button("Select Point 1", id="btn-p1", color="secondary"), width='auto'),
                 dbc.Col(dbc.Button("Select Point 2", id="btn-p2", color="secondary"), width='auto'),
                 dbc.Col(dbc.Button("Get Avg", id="btn-avg"), width='auto'),
                 dbc.Col(html.Div([dbc.Button("Download csv", id="btn"), dcc.Download(id="download")]))
                 ], justify='start')

# Flow rate input
flow_input = dbc.Toast(
    [html.Label("Flow Rate [SLPM]"),
     dcc.Input(id="flow-rate", type="text", value=""),
     dbc.Button("Set", id="set-flow"),
     dbc.Button("STOP", id="stop-flow"),
    ],
    id="flow-group",
    header="Flow Rate",
)

calculator_card = dbc.Card([
    dbc.CardHeader("Calculate SCFM"),
    dbc.CardBody([dbc.FormText("SLPM"),dbc.Input(id='SLPM', type='number'),
                  dbc.FormText("Injection CO2 PPM"),dbc.Input(id='injection', type='number'),
                  dbc.FormText("Baseline CO2 PPM"),dbc.Input(id='baseline', type='number'),
                  dbc.FormText("SCFM"),dbc.Alert(id="SCFM")
                  ])
    ])

lower_row = dbc.Row([dbc.Col(calculator_card, width='auto'),
                     dbc.Col(flow_input, width='auto')])

def connection_card(values,connection):
    if values['Source'] == 'SBA5':
        try:
            if values['Zeroing']:
                return dbc.Col([
                    dbc.Card([
                    dbc.CardHeader(f"{values['Source']} {connection}"),
                    dbc.CardBody([html.P(f"Zeroing"),
                                  html.P(f"Time: {datetime.datetime.strftime(values['Timestamp'], '%Y-%m-%d %H:%M:%S')}"),
                                  dbc.Button(f"Disconnect", id={"type": "btn-stop", "index": connection}, value=connection)
                                  ])])])
            elif values['Warming Up']:
                return dbc.Col([
                    dbc.Card([
                    dbc.CardHeader(f"{values['Source']} {connection}"),
                    dbc.CardBody([html.P(f"Warming Up"),
                                  html.P(f"Time: {datetime.datetime.strftime(values['Timestamp'], '%Y-%m-%d %H:%M:%S')}"),
                                  dbc.Button(f"Disconnect", id={"type": "btn-stop", "index": connection}, value=connection)
                                  ])])])
            else:
                return dbc.Col([
                dbc.Card([
                    dbc.CardHeader(f"{values['Source']} {connection}"),
                    dbc.CardBody([html.P(f"CO2: {values['CO2 PPM']} PPM"),
                                  html.P(f"Time: {datetime.datetime.strftime(values['Timestamp'], '%Y-%m-%d %H:%M:%S')}"),
                                  dbc.Button(f"Disconnect", id={"type": "btn-stop", "index": connection}, value=connection)
                                  ])])])
        except Exception as exp:
            return dbc.Col([
                dbc.Card([
                    dbc.CardHeader(f"{values['Source']} {connection}"),
                    dbc.CardBody([html.P("Error in Result, check logs")]),
                    html.P(f"Time: {datetime.datetime.strftime(values['Timestamp'], '%Y-%m-%d %H:%M:%S')}"),
                    dbc.Button(f"Disconnect", id={"type": "btn-stop", "index": connection}, value=connection)])])
    elif values['Source'] == 'Alicat':
        try:
            card = dbc.Col([
                dbc.Card([
                dbc.CardHeader(f"{values['Source']} {connection}"),
                dbc.CardBody([html.P(f"Mass Flow: {values['Mass Flow']} SLPM"),
                              html.P(f"Setpoint: {values['Setpoint']} SLPM"),
                              html.P(f"Time: {datetime.datetime.strftime(values['Timestamp'], '%Y-%m-%d %H:%M:%S')}"),
                              dbc.Button(f"Disconnect", id={"type": "btn-stop","index":connection},value=connection)
                              ])])])
        except Exception as exp:
            card = dbc.Col([
                dbc.Card([
                    dbc.CardHeader(f"{values['Source']} {connection}"),
                    dbc.CardBody([html.P("Error in Result, check logs")]),
                    html.P(f"Time: {datetime.datetime.strftime(values['Timestamp'], '%Y-%m-%d %H:%M:%S')}"),
                    dbc.Button(f"Disconnect", id={"type": "btn-stop", "index": connection}, value=connection)])])
        return card
