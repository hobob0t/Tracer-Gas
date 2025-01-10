import threading
import logging
import serial.tools.list_ports
import serial
import time
import datetime


class SBA5(threading.Thread):
    def __init__(self, **kwargs: any):
        super(SBA5, self).__init__()
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
        self.logger.log(logging.INFO, f"SBA5 Thread Created")

        self.stop = False
        self.daemon = True
        self.start()

    def find_and_open(self):
        '''todo: doesn't work if SBA-5 is warming up. Need to check for more cases just use open() method for now.'''
        ports = serial.tools.list_ports.comports()
        for port in ports:
            print(port.device)
            try:
                ser = serial.Serial(port.device, 19200, timeout=2)
            except serial.SerialException as exp:
                print('..going to next COM port')
                pass
            else:
                ser.reset_input_buffer()
                ser.write(b'!\r')  # Turn off data streaming
                time.sleep(.1)
                stuff = ser.read_until(b'\r\n')  # Read response
                print(stuff)
                if stuff == b'!\x00 Ok\r\n':  # This is the expected response
                    print("Found SBA-5")
                    self.serial_connection = ser
                    return
                else:
                    print('Found something that did not respond like the SBA-5')
        raise IOError(f"SBA5 {self.name} Not found")

    def open(self, port):
        try:
            ser = serial.Serial(port, 19200, timeout=3)
            ser.flush()
        except (serial.SerialException, ValueError) as exp:
            self.logger.log(logging.ERROR, exp.args)
            return False
        else:
            self.logger.log(logging.INFO, f"SBA5 {self.name} Opened serial port")
            ser.write(b'@\r')  # Turn ON data streaming
            time.sleep(.5)
            ser.write(b'F255\r')  # Set format to all data
            time.sleep(.5)

            self.serial_connection = ser
            return True

    def close(self):
        if self.serial_connection is not None:
            self.serial_connection.close()
            self.serial_connection = None
            self.logger.log(logging.INFO, f"SBA5 {self.name} Closed serial port")

    def streaming_mode(self):
        if self.serial_connection is not None:
            try:
                response = self.serial_connection.read_until(b'\r\n').decode()
                if len(response) == 0:
                    self.logger.log(logging.WARNING, f"SBA5 {self.name} No Response")
                    return None
                char = response[0]
                if char == '\0':
                    char = response[1]

            except Exception as exp:
                self.logger.log(logging.ERROR, type(exp))
                self.logger.log(logging.ERROR, exp.args)
                self.logger.log(logging.ERROR, f"SBA5 {self.name} Error in streaming mode")
                self.logger.log(logging.ERROR, response)
                response = None
                char = ''
            if char == 'Z':
                self.logger.log(logging.INFO, f"SBA5 {self.name} Zeroing")
                self.logger.log(logging.INFO, response)
                return {'Name': self.name, 'Zeroing': True, 'Warming Up': False, 'Source': 'SBA5'}
            elif char == 'W':
                self.logger.log(logging.INFO, f"SBA5 {self.name} Warming Up")
                self.logger.log(logging.INFO, response)
                return {'Name': self.name, 'Zeroing': False, 'Warming Up': True, 'Source': 'SBA5'}
            elif char == 'M':
                self.logger.log(logging.INFO, f"SBA5 {self.name} Parsing Measurement")
                return self.parse_measurement(response)
            elif char == '':
                return None
            else:
                self.logger.log(logging.INFO, f"SBA5 {self.name} Not Zeroing or Warming up or Invalid Response")
                self.logger.log(logging.INFO, response)
                return None


    def polling_measurement(self):
        if self.serial_connection is not None:
            self.serial_connection.reset_input_buffer()
            self.serial_connection.write(b'M\r')  # Make a measurement
            self.logger.log(logging.INFO, f"SBA5 {self.name} Requesting measurement")
            try:
                result = self.serial_connection.read_until(b'\r\n').decode()
            except ValueError as err:
                self.logger.log(logging.ERROR, err.args)
                return None
            except serial.SerialException as err:
                self.logger.log(logging.ERROR, err.args)
                return None
            else:
                return result
        else:
            raise IOError(f"SBA5 {self.name} Not Connected")

    def parse_measurement(self, string: str) -> dict:
        if isinstance(string, str):
            split_string = string.split()

            if len(split_string) < 10:
                string = string.replace('\n', '')
                string = string.replace('\r', '')
                self.logger.warning(f'SBA5 {self.name} value missing in measurement response.')
                return None

            keys = ['counts since last Zero', 'current counts', 'CO2 PPM', 'average IGRA Temp [C]', 'RH',
                    'RH Sensor Temp [C]', 'pressure [mbar]', 'IGRA detector temp [C]',
                    'IGRA source temp [C]']
            response_dict = {}
            response_dict['Warming Up'] = False
            response_dict['Zeroing'] = False
            i = 1  # Skip the first element which is the 'M' character
            for key in keys:
                try:
                    response_dict[key] = split_string[i]
                    i += 1
                except IndexError:
                    string = string.replace('\n', '')
                    string = string.replace('\r', '')
                    self.logger.warning(f'SBA5 {self.name} value missing in measurement response.')
                    self.logger.warning(f'SBA5 {self.name} Response was: {string} <--(if that says "OK" ignore this message)')

                    # # try resetting F255
                    # self.serial_connection.write(b'F255\r')  # Set format to all data
                    # time.sleep(1)
                    # # try resetting to streaming mode
                    # self.serial_connection.write(b'@\r')
                    # time.sleep(1)
                    #
                    # self.serial_connection.reset_input_buffer()
                    # time.sleep(0.1)

                    return response_dict
            return response_dict

    def zero(self):
        if self.serial_connection is not None:
            self.logger.log(logging.INFO, f"SBA5 {self.name} Sending Zeroing Command to SBA5")
            self.serial_connection.write(b'Z\r')

    def run(self):
        if self.open(self.port):
            self.logger.log(logging.INFO, f"SBA5 {self.name} Connected")
        else:
            self.logger.log(logging.ERROR, f"SBA5 {self.name} Not Connected. Check serial port? Check logs?")
            return

        time.sleep(0.5)

        while self.stop == False:
            try:
                result = self.streaming_mode()
                if result is not None:
                    result['Timestamp'] = datetime.datetime.now()
                    result['Name'] = self.name
                    result['Source'] = 'SBA5'
                    if result['Warming Up'] == False and result['Zeroing'] == False:
                        # if the result does not contain the CO2 PPM key, then don't bother saving it
                        if 'CO2 PPM' not in result.keys():
                            self.logger.log(logging.WARNING, f"SBA5 {self.name} CO2 PPM not found in result")
                            continue

                        # that's not a string!
                        result['CO2 PPM'] = int(result['CO2 PPM'])

                        self.logger.log(logging.INFO, f"SBA5 {self.name} Measurement: {result}")
                    self.q.put(result)
            except Exception as exp:
                self.logger.log(logging.ERROR, "Error in SBA5 run")
                self.logger.log(logging.ERROR, exp.args)
                self.logger.log(logging.ERROR, type(exp))
                # Pass a result to the queue so the ViewModel knows something went wrong
                result = {'Source': 'SBA5', 'Name': self.name, 'Timestamp': datetime.datetime.now()}
                self.q.put(result)
                continue
