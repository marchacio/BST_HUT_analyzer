import logging
import os

def init_logging(log_file: str, save_file: bool, level=logging.INFO):
    """
    Initializes the logging system.
    This function should be called only once in your main script.

    Args:
        log_file (str): The name of the log file.
        save_file (bool): If True, saves logs to the specified file.
        level (int): The minimum logging level to record.
                     Examples: logging.DEBUG, logging.INFO, logging.WARNING,
                               logging.ERROR, logging.CRITICAL.
    """
        
    # Create a logger instance. It's good practice to use a specific name,
    # as logging.getLogger() with the same name always returns the same instance.
    logger = logging.getLogger('my_tool_logger')
    logger.setLevel(level)

    # To prevent adding handlers multiple times if the function is called again
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create a formatter for log messages
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    if save_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # 1. Handler for the log file
        # 'w' mode overwrites the file if it exists, ensuring a fresh log for each run.
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 2. Handler for the console (standard output)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # This debug message will only be shown if the 'level' is set to DEBUG.
    logger.debug(f"Logging system initialized. Log file: {os.path.abspath(log_file)}")
    return logger