import logging
from logging.handlers import RotatingFileHandler
from logging import Formatter
from SBA5 import SBA5
from MFC import Alicat
import ViewModel
import UtilFuncs
import helpers
import queue
from dash_components import *
from dash import Dash, html, callback, Output, Input, State, ctx, dash_table
from dash.exceptions import PreventUpdate
import threading
from dash.dependencies import ALL
import pandas as pd
import dateutil.parser
import dash_bootstrap_components as dbc
import datetime

#global variables
log_file_name = 'runtime.log'
logging_level = logging.WARNING

# create queue
CO2_Sensor_Queue = queue.Queue()
Alicat_Queue = queue.Queue()
ViewModel_Queue = queue.Queue()

# get named logger
logger = logging.getLogger(__name__)

# create handler
handler = RotatingFileHandler(filename=log_file_name, mode='a', maxBytes=1000000, backupCount=2, encoding='utf-8',
                              delay=False)
# create formatter and add to handler
formatter = Formatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
# add the handler to named logger
logger.addHandler(handler)
# also add stream handler
logger.addHandler(logging.StreamHandler())
# set the logging level
logger.setLevel(logging_level)

# define dash app
app = Dash(__name__, external_stylesheets=["/assets/bootstrap.min.css"])
app.enable_dev_tools(dev_tools_silence_routes_logging=True)

# Start ViewModel
ViewModel = ViewModel.ViewModel(ViewModel_Queue=ViewModel_Queue, CO2_Sensor_Queue=CO2_Sensor_Queue,
                                Alicat_Queue=Alicat_Queue, log_level=logging_level)

# Check database file
UtilFuncs.check_or_create_db()


# define layout
def layout():
    return dbc.Container([
        dbc.Tabs(
        [
            dbc.Tab([
                button_row_1,
                graph,
                html.P(id="testing-component"),
                lower_row
            ],label="Main"),
            dbc.Tab([
                dbc.Row([co2_gas_analyzer_input(), alicat_input()]),
                dbc.Row(dbc.Stack([dbc.Label("Active Connections:"),connections])),
                interval,
                interval_connections
                ],label="Serial Connections"),
            dbc.Tab([logger_area],label="Logger")
        ],
        id='main-div'
    )])


app.layout = layout


# Live update graph
@callback(Output('graph', 'figure'),
          Input("graph", "clickData"),
          Input('interval', 'n_intervals'),
          Input('btn-load', 'n_clicks'),
          State('graph', 'figure'),
          State("btn-p1", "color"),
          State("btn-p2", "color"),
          State('date-picker-range', 'start_date'),
          State('date-picker-range', 'end_date'),
          running = [(Output("interval", "disabled"), True, False),
                     (Output("interval-connections", "disabled"), True, False)])
def update_graph_live(clickdata, n, n2, fig, b1_state, b2_state, dt1, dt2):

    button_id = ctx.triggered_id if not None else 'No clicks yet'

    if button_id == 'interval':
        yes_data = False

        if len(ViewModel.CO2data) > 0:
            fig = helpers.add_plot_data(fig, ViewModel.get_CO2_data(), 'CO2 PPM', 'y')
            yes_data = True
        if len(ViewModel.AlicatData) > 0:
            fig = helpers.add_plot_data(fig, ViewModel.get_Alicat_data(), 'Mass Flow', 'y2')
            yes_data = True
        if yes_data:
            return fig
        else:
            raise PreventUpdate

    elif button_id == 'graph':
        return add_vertical_line(b1_state, b2_state, clickdata, fig)

    elif button_id == 'btn-load':
        if dt1 is None or dt2 is None:
            raise PreventUpdate
        else:

            df = UtilFuncs.load_data(dt1, dt2)

            if 'Name' in df.columns:
                groups = df.groupby('Name')
            else:
                raise PreventUpdate
            # Previously, we would append loaded data to existing plots.
            # But that wouldn't clear old data if you wanted to narrow the
            # date range. So now we just clear the data.
            fig['data'] = []
            for node, frame in groups:
                if frame['Source'].iloc[0] == 'Alicat':
                    fig['data'].append({'x': [], 'y': [], 'yaxis': 'y2', 'type': 'scattergl'})
                    fig['data'][-1]['y'] = frame['Mass Flow']
                    fig['data'][-1]['x'] = frame.index
                    fig['data'][-1]['name'] = node
                else:
                    fig['data'].append({'x': [], 'y': [], 'yaxis': 'y', 'type': 'scattergl'})
                    fig['data'][-1]['y'] = frame['CO2 PPM']
                    fig['data'][-1]['x'] = frame.index
                    fig['data'][-1]['name'] = node
            return fig

    else:
        raise PreventUpdate


# Live update connected equipment
@callback(Output('connections', 'children'),
          Output('logger', 'children'),
          Input('interval-connections', 'n_intervals'))
def update_connection_info(n):
    if len(ViewModel.connections) == 0:
        layout = ["No connected equipment"]
    else:
        layout = []
        for connection, values in ViewModel.connections.items():
            try:
                card = connection_card(values, connection)
                layout.append(card)
            except Exception as e:
                logger.log(logging.ERROR, f"Error in update_connection_info: {e.args}")
    try:
        lines = UtilFuncs.LastNlines('runtime.log', 20)[::-1]
    except Exception as e:
        lines = [f"Error reading log file: {e.args}"]
    return dbc.Row(layout),html.Ul([html.Li(x) for x in lines])


@callback(Output('co2-gas-analyzer', 'value'),
          Input('submit-co2-gas-analyzer', 'n_clicks'),
          State('co2-gas-analyzer', 'value'),
          State('GA-port', 'value'))
def add_analyzer(n, name, port):

    if n is None:
        raise PreventUpdate
    else:
        if name is None or name == '' or name == "Please enter a name":
            return "Please enter a name"
        else:
            # Start SBA5 thread which will also connect to the gas analyzer
            SBA5(name=name, port=port, queue=CO2_Sensor_Queue, log_level=logging_level)


@callback(Output('alicat-name', 'value'),
          Input('submit-alicat', 'n_clicks'),
          State('alicat-name', 'value'),
          State('alicat-port', 'value'))
def add_analyzer(n, name, port):

    if n is None:
        raise PreventUpdate
    else:
        if name is None or name == '' or name == "Please enter a name":
            return "Please enter a name"
        else:
            # Start Alicat thread which will also connect to the serial port
            Alicat(name=name, port=port, queue=Alicat_Queue, log_level=logging_level)


@callback(Input('set-flow', 'n_clicks'),
          Input('stop-flow', 'n_clicks'),
          State('flow-rate', 'value'))
def set_flow(n, n2, flow):
    button_id = ctx.triggered_id if not None else 'No clicks yet'
    if button_id == 'set-flow':
        ViewModel.alicat_flow_rate = flow
    if button_id == 'stop-flow':
        ViewModel.alicat_flow_rate = 0


@callback(Input({"type": "btn-stop", "index": ALL}, "n_clicks"))
def disconnect_callback(n):
    button_id = ctx.triggered_id
    name = button_id['index']
    for thread in threading.enumerate():
        if thread.name == name:
            logger.log(logging.INFO, f"Stopping thread {thread.name}")
            thread.stop = True
            ViewModel_Queue.put({'Type': 'Close Connection', 'Name': name})

@app.callback(
    [Output("btn-p1", "color"), Output("btn-p2", "color")],
    [Input("btn-p1", "n_clicks"), Input("btn-p2", "n_clicks")],
    [State("btn-p1", "color"), State("btn-p2", "color")])
def active_point(b1, b2, b1_state, b2_state):
    button_id = ctx.triggered_id if not None else 'No clicks yet'

    # all this does is change the color of the button
    # as feedback to the user for which one is active
    if button_id == "btn-p1":
        if b1_state == "secondary":
            b1_state = "primary"
            b2_state = "secondary"
        else:
            b1_state = "secondary"
    if button_id == "btn-p2":
        if b2_state == "secondary":
            b2_state = "primary"
            b1_state = "secondary"
        else:
            b2_state = "secondary"
    return b1_state, b2_state

@app.callback(
    Output("testing-component", "children"),
    Input("btn-avg", "n_clicks"),
    State("graph", "figure"))
def avg_and_report(b1, fig):
    # If there are shapes
    if "shapes" in fig["layout"]:
        # We want there to be 2 lines so we can get the points
        if len(fig["layout"]["shapes"]) > 1:
            point_one = fig["layout"]["shapes"][0]["x0"]
            point_two = fig["layout"]["shapes"][1]["x0"]
            try:
                point_one = datetime.datetime.strptime(point_one, "%Y-%m-%d %H:%M:%S.%f")
                point_two = datetime.datetime.strptime(point_two, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                point_one = dateutil.parser.parse(point_one)
                point_two = dateutil.parser.parse(point_two)
            if point_one > point_two:
                point_one, point_two = point_two, point_one

            nodes = get_plot_names(fig["data"])

            avg_results = {}
            for node in nodes:
                idx = get_plot_index(fig["data"], node)
                df = pd.DataFrame(fig["data"][idx])
                df["x"] = pd.to_datetime(df["x"])

                df = df.loc[(df["x"] >= point_one) & (df["x"] <= point_two)]



                avg_results[node] = df.mean(numeric_only=True)['y']
            columns = []
            for key in avg_results.keys():
                columns.append({'id': key, 'name': key, 'type': 'numeric', 'format': dash_table.Format.Format(precision=2,scheme=dash_table.Format.Scheme.fixed)})
            return dash_table.DataTable([avg_results],columns = columns)
    else:
        raise PreventUpdate

@app.callback(
    Output("SCFM", "children"),
    Input("SLPM", "value"),
    Input("injection", "value"),
    Input("baseline", "value"))
def calculate_SCFM(slpm, injection, baseline):

    slTOcf = 0.0348544
    logger.log(logging.INFO, f"Calculating SCFM with SLPM: {slpm}, Injection: {injection}, Baseline: {baseline}")
    mDotAir = ((slpm * slTOcf * (10 ** 6 - baseline)) / (injection - baseline)) - (slpm * slTOcf)
    return mDotAir

if __name__ == '__main__':
    app.run(debug=False)
