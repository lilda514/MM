import os
from src.sharedstate import SharedState
from src.tools.log import LoggerInstance


class MMSharedState(SharedState):
    required_keys = {"max_position", "total_orders"}

    def __init__(self,debug: bool, logger: LoggerInstance) -> None:
        self.logging = logger
        super().__init__(debug)
    
    def set_parameters_path(self):
        current_folder = os.path.dirname(os.path.abspath(__file__))
        while current_folder.split('\\')[-1] != "src":
            current_folder = os.path.dirname(current_folder)
        
        return os.path.join(current_folder, 'marketmaking', 'parameters.yaml')
    
    def process_parameters(self, parameters: dict, reload: bool): 
        try:
            if not reload:
                self.quote_generator: str = parameters["quote_generator"]
                for exchange in parameters["exchanges"].keys():
                    self.exchanges[exchange.lower()] = parameters["exchanges"][exchange]
              
                for exchange_name,exchange_params in self.exchanges.items():
                    self.generate_data_dict(exchange_name)
                    self.load_exchange(exchange_name ,exchange_params["type"],exchange_params["symbol"])

            self.parameters: dict = parameters["parameters"]

            if self.required_keys > self.parameters.keys():
                for key in self.required_keys:
                    if key in self.parameters:
                        continue

                    raise Exception(
                        f"Missing '{key}' in {self.quote_generator}'s parameters!"
                    )
                
        except Exception as e:
            raise e
               