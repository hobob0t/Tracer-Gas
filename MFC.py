import threading
import logging
import serial.tools.list_ports
import serial
import time
import datetime

class Alicat(threading.Thread):
    def __init__(self, **kwargs: any):
        super(Alicat, self).__init__()
        self.serial_connection = None
        # Serial port
        self.port = kwargs["port"]

        # Name
        self.name = kwargs["name"]

        # Queue
        self.q = kwargs["queue"]

        # Logging
        self.logger = logging.getLogger('__main__')

        # Set logging level
        self.logger.setLevel(kwargs["log_level"])

        # Logging
        self.logger.log(logging.INFO, f"Alicat Thread Created")
        self.stop = False
        self.daemon = True
        self.start()

    def find_and_open(self):
        # TODO: Everything
        pass
        return

    def open(self, port):
        try:
            ser = serial.Serial(port, 19200, timeout=3)
            ser.reset_input_buffer()
        except (serial.SerialException, ValueError) as exp:
            self.logger.log(logging.ERROR, exp.args)
            return False
        else:
            self.logger.log(logging.INFO, f"Alicat {self.name} Opened serial port")
            ser.reset_input_buffer()
            ser.write(b'@@A\r')  # Turn off data streaming
            time.sleep(.1)
            ser.write(b'AS 0\r')  # Set zero flow
            time.sleep(.1)
            ser.reset_input_buffer()
            self.serial_connection = ser
            return True

    def close(self):
        if self.serial_connection is not None:
            self.serial_connection.close()
            self.serial_connection = None
            self.logger.log(logging.INFO, f"Alicat {self.name} Closed serial port")

    def measure(self):
        if self.serial_connection is not None:

            self.serial_connection.write(b'A\r')  # Make a measurement

            self.logger.log(logging.INFO, f"Alicat {self.name} Requesting measurement")

            time.sleep(0.1)
            result = self.serial_connection.read_until(b'\r').decode()
            return result
        else:
            raise IOError(f"Alicat {self.name} Not Connected")

    def parse_measurement(self, string: str) -> dict:
        if isinstance(string, str):
            split_string = string.split()

            keys = ['Abs Pressure', 'Temperature', 'Volume Flow', 'Mass Flow','Setpoint', 'Gas']
            response_dict = {}
            i = 1 # Skip the first element, which is the ID
            for key in keys:
                try:
                    response_dict[key] = split_string[i]
                    i += 1
                except IndexError:
                    self.logger.log(logging.ERROR, "Index Error in Alicat parse_measurement")
                    self.logger.log(logging.ERROR, string)
                    return None
            return response_dict

    def set_flow_rate(self, flow_rate: float):
        self.serial_connection.write(f"AS +{flow_rate}\r".encode())
        self.serial_connection.flush()
        time.sleep(0.5)

    def run(self):
        if self.open(self.port):
            self.logger.log(logging.INFO, f"Alicat {self.name} Connected")
        else:
            self.logger.log(logging.ERROR, f"Alicat {self.name} Not Connected. Check serial port? Check logs?")
            return
        self.serial_connection.reset_input_buffer()
        time.sleep(0.5)
        while True:
            if self.stop:
                self.serial_connection.close()
                break
            # catchall try because we don't want to stop the thread
            try:
                try:
                    time.sleep(0.5)
                    result = (self.parse_measurement(self.measure()))
                    # if mass flow is not in keys don't bother
                    if 'Mass Flow' not in result.keys():
                        self.logger.log(logging.WARNING, f"Alicat {self.name} Mass Flow not found in result")
                        continue
                    result['Timestamp'] = datetime.datetime.now()
                    result['Name'] = self.name

                    # Convert mass flow to float
                    result['Mass Flow'] = float(result['Mass Flow'])
                    result['Source'] = 'Alicat'

                    self.q.put(result)
                except Exception as exp:
                    self.logger.log(logging.ERROR, f"TypeError in Alicat run: {exp.args}")
                    # Pass a result to the queue so the ViewModel knows something went wrong
                    result = {'Source': 'Alicat', 'Name': self.name, 'Timestamp': datetime.datetime.now()}
                    self.q.put(result)
                    continue
            except Exception as exp:
                self.logger.log(logging.ERROR, "Error in Alicat run")
                self.logger.log(logging.ERROR, type(exp))
                self.logger.log(logging.ERROR, exp.args)
                self.logger.log(logging.ERROR, exp)
                # Pass a result to the queue so the ViewModel knows something went wrong
                result = {'Source': 'Alicat', 'Name': self.name, 'Timestamp': datetime.datetime.now()}
                self.q.put(result)
                continue
