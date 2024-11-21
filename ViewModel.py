import threading
import logging
import time

import UtilFuncs

class ViewModel(threading.Thread):
    def __init__(self, **kwargs: any):
        super(ViewModel, self).__init__()
        # Queue
        self.CO2_Queue = kwargs["CO2_Sensor_Queue"]
        self.Alicat_Queue = kwargs["Alicat_Queue"]
        self.ViewModel_Queue = kwargs["ViewModel_Queue"]

        # Logging
        self.logger = logging.getLogger('__main__')

        # Set logging level
        self.logger.setLevel(kwargs["log_level"])

        # Logging
        self.logger.log(logging.INFO, "ViewModel Thread Created")

        # Start the thread
        self.daemon = True
        self.start()


    def process_queue_item(self, item:dict):
        self.logger.debug(f"Processing item: {item}")
        if 'Source' in item:
            # Update connection with new data
            self.connections[item['Name']] = item
            try:
                if item['Source'] == 'SBA5':
                    if not item['Warming Up'] and not item['Zeroing']:
                        self.CO2data.append(item)
                        stmt = self.table.insert().values(item)
                        self.conn.execute(stmt)
                if item['Source'] == 'Alicat':
                    if float(self.alicat_flow_rate) != float(self.previous_flow_rate):
                        self.logger.debug(f"Flow rate changed to {self.alicat_flow_rate}")
                        self.previous_flow_rate = float(self.alicat_flow_rate)
                        self.set_flow_rate(self.alicat_flow_rate, item['Name'])

                    self.AlicatData.append(item)
                    stmt = self.table.insert().values(item)
                    self.conn.execute(stmt)

            except KeyError as exp:
                self.logger.error(f"KeyError in ViewModel while processing item: {exp}")
                self.logger.error(f"Item: {item}")

    def get_CO2_data(self):
        return_value = self.CO2data
        self.CO2data = []
        return return_value

    def get_Alicat_data(self):
        return_value = self.AlicatData
        self.AlicatData = []
        return return_value

    def set_flow_rate(self, flow_rate: float, name: str = None):
        for thread in threading.enumerate():
            if thread.name == name:
                thread.set_flow_rate(flow_rate)

    def run(self):
        # database stuff
        self.engine, self.metadata = UtilFuncs.connect_and_reflect()
        self.conn = self.engine.connect()
        self.table = self.metadata.tables['Data']

        # To keep track of active equipment
        self.connections = {}
        # List of dicts of queued data
        self.CO2data = []
        self.AlicatData = []
        # Desired Flow Rate [slpm]
        self.alicat_flow_rate = 0
        self.previous_flow_rate = float(self.alicat_flow_rate)

        state = 0
        while True:
            try:
                match state:
                    case 0:
                        if not self.CO2_Queue.empty():
                            self.process_queue_item(self.CO2_Queue.get(False))
                        state = 1
                    case 1:
                        if not self.Alicat_Queue.empty():
                            self.process_queue_item(self.Alicat_Queue.get(False))
                        state = 2
                    case 2:
                        if not self.ViewModel_Queue.empty():
                            item = self.ViewModel_Queue.get(False)
                            if item['Type'] == 'Close Connection':
                                removed = self.connections.pop(item['Name'])
                                self.logger.log(logging.DEBUG,f"Connection {item['Name']} removed from list")

                                # Clear the queue of the removed connection
                                if removed['Source'] == 'Alicat':
                                    # Wait five seconds to avoid race conditions with the thread closing
                                    # This time must be longer than the serial timeout
                                    time.sleep(5)
                                    while not self.Alicat_Queue.empty():
                                        self.Alicat_Queue.get(False)
                                        self.logger.log(logging.WARNING, f"Alicat Queue Cleared")
                                if removed['Source'] == 'SBA5':
                                    # Wait five seconds to avoid race conditions with the thread closing
                                    # This time must be longer than the serial timeout
                                    time.sleep(5)
                                    while not self.CO2_Queue.empty():
                                        self.CO2_Queue.get(False)
                                        self.logger.log(logging.WARNING, f"SBA Queue Cleared")
                        state = 3
                    case 3:
                        time.sleep(.1)
                        state = 0
                    case _:
                        state = 0

            except Exception as exp:
                self.logger.error(f"Error in ViewModel: {exp}")
