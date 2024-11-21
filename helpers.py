from serial.tools import list_ports
import serial

def get_plot_index(data, node):
    """function to get what index a node is within a plotly figure
    data is a plotly figure data list, node is the sensor node we're looking for"""
    i = 0
    for item in data:
        # the "name" key may or may not be in the item
        if "name" in item:
            if item["name"] == node:
                return i
        i = i + 1
    # Return None if not found
    return None

def get_plot_names(data):
    """function to get all the names of the traces in a plotly figure
    in this case it will get all the sensors currently plotted on screen"""
    names = []
    for item in data:
        # the "name" key may or may not be in the item
        if "name" in item:
            names.append(item["name"])
    return names

def get_serial_ports():
    """function to get all the serial ports on the system"""
    ports = []
    for port in list_ports.comports():
        ports.append(port.device)
    return ports

def add_plot_data(fig,new_data,key,y_axis):
    for i, data in enumerate(new_data):
        idx = get_plot_index(fig['data'], data['Name'])
        if idx is not None:
            # If we find it in the list of plots we append the new datapoint to the correct plot
            fig['data'][idx]['y'].append(data[key])
            fig['data'][idx]['x'].append(data['Timestamp'])
        else:
            # if we don't find the trace we create a new plot and add it to the graph
            fig['data'].append({'x': [], 'y': [], 'yaxis':y_axis,'type': 'scattergl'})
            fig['data'][-1]['y'].append(data[key])
            fig['data'][-1]['x'].append(data['Timestamp'])
            fig['data'][-1]['name'] = data['Name']
    return fig

def add_vertical_line(b1_state, b2_state, clickdata, fig):
    # The x axis location of the datapoint that was clicked
    x_point = clickdata["points"][0]["x"]
    # If the "Select Point 1" button is highlighted
    if b1_state == "primary":
        # If there are already shapes on the graph
        if "shapes" in fig["layout"]:
            # Set shape 0 to a vertical line at the x_point
            fig["layout"]["shapes"][0] = {"type": "line", "x0": x_point, "x1": x_point, "xref": "x", "y0": 0,
                                          "y1": 1,
                                          "yref": "y domain"}
        else:
            # if there are no shapes, make the first shape as a vertical line at the x_point
            fig["layout"]["shapes"] = [
                {"type": "line", "x0": x_point, "x1": x_point, "xref": "x", "y0": 0, "y1": 1, "yref": "y domain"}]
    # If the "Select Point 2" button is highlighted
    if b2_state == "primary":
        # If there are already shapes on the graph
        if "shapes" in fig["layout"]:
            # If there are already two shapes on the graph...
            if len(fig["layout"]["shapes"]) > 1:
                # We want the second one to be a vertical line at the x_point
                fig["layout"]["shapes"][1] = {"type": "line", "x0": x_point, "x1": x_point, "xref": "x", "y0": 0,
                                              "y1": 1,
                                              "yref": "y domain"}
            else:
                # Else there must only be one shape, so we append the list
                fig["layout"]["shapes"].append(
                    {"type": "line", "x0": x_point, "x1": x_point, "xref": "x", "y0": 0, "y1": 1,
                     "yref": "y domain"})
        else:
            # Else there are no shapes we create the point 2 shape as a vertical line at the x_point
            fig["layout"]["shapes"] = [{},
                                       {"type": "line", "x0": x_point, "x1": x_point, "xref": "x", "y0": 0, "y1": 1,
                                        "yref": "y domain"}]
    return fig