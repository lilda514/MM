import picologging as logging
# import logging
import datetime
import os
import time


# class LoggerInstance(logging.Logger):
#     """
#     Logger instance finetuned to our needs
#     """
    
#     def __init__(self, name: str, debug_mode:bool = False, basepath = None):
#         level = logging.DEBUG if debug_mode else 0
#         logging.Logger(name,level)
#         # super().__init__(self,name,level)
#         self.propagate = False # Prevent propagation to the root logger
#         #Will set path to put logs
#         if basepath is None:
#             date = datetime.datetime.today()
#             datestring = date.strftime("%Y-%m-%d %Hh%M")
#             cwd = os.getcwd()
#             self.basepath = os.path.join(cwd, f'logs\\{datestring}')
#             os.makedirs(self.basepath, exist_ok = True) #making sure there is a file to write to

#         else:
#             self.basepath = basepath
        
#     def createChild(self,child_name:str,debug_mode:bool = False):
#         return LoggerInstance(f"{self.name}.{child_name}",debug_mode,self.basepath)
    
#     def setTopicFilter(self,topic):
#         self.addFilter(TopicFilter(topic))
    
#     def defaultFormatter(self):
#         return logging.Formatter('{asctime} | {levelname} | {topic} | {msg}',style="{" )
    
#     def setHandlers(self):
#         # indiviualfp = os.path.join(self.basepath,*self.name.split("."), ".log") # an individual logfile for each children 
#         # individualFileHandler = logging.FileHandler(indiviualfp, mode = "a")
#         commonfp = os.path.join(self.basepath, self.name.split(".")[0]+".log") # 1 common logfile with the same name as the parent 
        
#         commonFileHandler = logging.FileHandler(commonfp, mode = "a")        
#         commonFileHandler.setLevel(self.level)
#         commonFileHandler.setFormatter(self.defaultFormatter())
#         self.addHandler(commonFileHandler)
        
class LoggerInstance:
    """
    Logger instance with finetuned capabilities
    """
    
    def __init__(self, name: str, debug_mode: bool = False, basepath: str = None):
        self.debug_mode = debug_mode
        level = logging.DEBUG if debug_mode else logging.INFO
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False  # Prevent propagation to the parent logger
        
        # Remove all existing handlers
        if len(self.logger.handlers):
            self.logger.handlers.clear()
        if len(self.logger.filters):
            self.logger.filters.clear()
        
        # Set path to put logs
        if basepath is None:
            date = datetime.datetime.today()
            datestring = date.strftime("%Y-%m-%d %Hh%M")
            cwd = os.getcwd()
            self.basepath = os.path.join(cwd,"logs",f"{datestring}")
            os.makedirs(self.basepath, exist_ok=True)  # Ensure the directory exists
        else:
            self.basepath = basepath

    def createChild(self, child_name: str, debug_mode: bool = None):
        if debug_mode is None:
            debug_mode = self.debug_mode 
        return LoggerInstance(f"{self.logger.name}.{child_name}", debug_mode, self.basepath)

    def setFilters(self, topic):
        self.logger.addFilter(TopicFilter(topic))
        self.logger.addFilter(AsctimeFilter())
        self.topic = topic

    def defaultFormatter(self):
        return logging.Formatter('%(timestamp)s | %(levelname)s | %(topic)s | %(message)s')

    def setHandlers(self):
        # common log file with the same name as the parent
        commonfp = os.path.join(self.basepath, self.logger.name.split(".")[0] + ".log")
        commonFileHandler = logging.FileHandler(commonfp, mode="a")
        commonFileHandler.setLevel(self.logger.level)
        commonFileHandler.setFormatter(self.defaultFormatter())
        self.logger.addHandler(commonFileHandler)
        
        if self.logger.level == logging.DEBUG:
            consoleHandler = logging.StreamHandler()
            consoleHandler.setLevel(self.logger.level)
            consoleHandler.setFormatter(self.defaultFormatter())
            self.logger.addHandler(consoleHandler)
        
    def info(self, msg):
        self.logger.info(msg)
    
    def debug(self, msg):
        self.logger.debug(msg)
    
    def warning(self, msg):
        self.logger.warning(msg)
    
    def error(self, msg):
        self.logger.error(msg)
    
    def critical(self, msg):
        self.logger.critical(msg)
        
    @property
    def name(self):
        return self.logger.name
    
    @property
    def level(self):
        return self.logger.level
    
    @property
    def filters(self):
        return self.logger.filters
    
    def close(self):
        for handler in self.logger.handlers:
            handler.close()
                    
    
    
class TopicFilter(logging.Filter):
    """
    Adds the ".topic" attribute to the log record so it can be formatted
    """
    def __init__(self,topic:str):
        self.topic = topic
    def filter(self, record):
        record.topic = self.topic
        return True
    
class AsctimeFilter(logging.Filter):
    """
    Adds a custom 'asctime' attribute to the log record with milliseconds.
    """
    def __init__(self):
        return
    
    def filter(self, record):
        # Calculate milliseconds and format the timestamp
        milliseconds = int(record.created % 1 * 1000)
        record.timestamp = time.strftime("%H:%M:%S.", time.gmtime(record.created)) + f"{milliseconds:03d}"
        return True
    
    
# log1 = LoggerInstance("test",True)
# log1.logger.addFilter(AsctimeFilter())
# log1.setTopicFilter("exch")
# log1.setHandlers()

# # log2 = logging.Logger("test2",10)
# # log2.addFilter(TopicFilter("exch"))

# # log2.debug("hello")

# log1.debug("hello")
# log1.close()



    
