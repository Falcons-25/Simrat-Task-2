import dash
from dash import dcc, html
from dash.dependencies import Output, Input, State
import plotly.graph_objs as go
import serial
import time
import pandas as pd
import sys

# Initialize the Dash app
app = dash.Dash(__name__)

# Initialize the Arduino serial port
try:
    ser = serial.Serial('COM6', 9600)
    print("Serial port opened successfully.")
except serial.SerialException as e:
    ser = None
    print(f"Error opening the serial port: {e}")

# Define the layout of the app
app.layout = html.Div(
    [
        html.H2("Live Graph"),
        dcc.Graph(id="live-graph", animate=True),
        dcc.Interval(id="graph-update", interval=1000, n_intervals=0),
        html.Button("Stop", id="stop-button", n_clicks=0),
        dcc.ConfirmDialog(
            id='confirm-dialog',
            message='Are you sure you want to terminate the program?'
        ),
        dcc.Store(id='terminate', data=False)  # Hidden div to store termination status
    ]
)

# List to store data points
x_data = []
y_data = []

# CSV file path
csv_file_path = 'Ultrasonic.csv'

# Function to save data to CSV
def save_to_csv(x, y, file_path):
    # Create a DataFrame from the data lists
    df = pd.DataFrame({'Timestamp': x, 'Value': y})
    
    # Append data to CSV file, creating it if it does not exist
    try:
        df.to_csv(file_path, mode='a', header=not pd.io.common.file_exists(file_path), index=False)
    except Exception as e:
        print(f"Error saving to CSV: {e}")

# Callback function to update the graph
@app.callback(
    Output("live-graph", "figure"),
    [Input("graph-update", "n_intervals")],
    [State('terminate', 'data')]
)
def update_graph(n, terminate):
    global x_data, y_data

    if terminate:
        return {"data": [], "layout": go.Layout(title="Program Terminated")}

    if ser and ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').strip()
        print(f"Received line: {line}")  # Debug: Print the raw line received
        try:
            # Assuming data format is int,int.float and we need the float part
            _, y_value_str = line.split(',')
            y_value = float(y_value_str)
            print(f"Converted value: {y_value}")  # Debug: Print the converted float value
            
            # Add the new data point to the lists
            current_time = time.time()
            x_data.append(current_time)  # Current timestamp
            y_data.append(y_value)

            # Limit the size of data lists (e.g., last 100 points)
            if len(x_data) > 100:
                x_data.pop(0)
                y_data.pop(0)
            
            # Save the new data point to CSV
            save_to_csv([current_time], [y_value], csv_file_path)
            
        except ValueError as e:
            print(f"Error converting data: {line} - {e}")

    # Create the graph trace
    trace = go.Scatter(
        x=x_data,
        y=y_data,
        mode="lines+markers",
        name="Data",
        line={"color": "rgb(0, 255, 0)"},
        marker={"color": "rgb(0, 255, 0)", "size": 8},
    )

    # Create the graph layout
    layout = go.Layout(
        title="Live Graph",
        xaxis=dict(range=[min(x_data) if x_data else 0, max(x_data) if x_data else 1]),
        yaxis=dict(range=[min(y_data) if y_data else 0, max(y_data) if y_data else 1]),
    )

    # Return the graph figure
    return {"data": [trace], "layout": layout}

# Callback to show confirmation dialog
@app.callback(
    Output('confirm-dialog', 'displayed'),
    [Input('stop-button', 'n_clicks')]
)
def display_confirm(n_clicks):
    if n_clicks > 0:
        return True
    return False

# Callback to handle confirmation dialog response
@app.callback(
    Output('terminate', 'data'),
    [Input('confirm-dialog', 'submit_n_clicks')],
    [State('terminate', 'data')]
)
def set_terminate(submit_n_clicks, terminate):
    if submit_n_clicks:
        return True
    return terminate

if __name__ == "_main_":
    app.run(debug=False, port=8051, use_reloader=False)