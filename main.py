"""
Main entry point for the Funding Rate Strategy application.

This module initializes the application components and sets up a scheduler to
periodically collect funding rate data from the MEXC exchange. It handles:

1. Setting up the logging system
2. Initializing the MEXC API client
3. Scheduling periodic funding rate snapshots
4. Running the main application loop with error handling

The application runs continuously, checking for upcoming funding events and
collecting data at strategic times before each funding rate payout.
"""

import time
import schedule
from datetime import datetime, timezone
from api.contract_client import MEXCContractClient
from pipeline.funding_rate_logger import log_funding_snapshot, get_next_funding_times
from utils.config_loader import load_config
from utils.logger import setup_logger, get_logger

def main():
    """
    Initializes the MEXC API client and periodically schedules the funding snapshot logger.

    The logger is triggered every 10 minutes, and internally decides whether to log based
    on proximity to funding times. This ensures resilience in case of minor time drift or delays.
    """
    # Initialize the logger
    logger = setup_logger()
    logger.info("Starting Funding Rate Strategy application")
    
    try:
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        client = MEXCContractClient(config=config['mexc'])
        logger.info("MEXC client initialized")

        logger.info(f"Scheduler initialized at: {datetime.now(timezone.utc).isoformat()}")
        logger.info("Upcoming funding times (UTC):")
        for t in get_next_funding_times()[:5]:
            logger.info(f"  {t.isoformat()}")

        # Run every 5 minutes and internally check if it's within funding window
        schedule.every(5).minutes.do(run_snapshot_safely, client)
        logger.info("Scheduler set to run every 5 minutes")

        logger.info("Entering main loop")
        while True:
            schedule.run_pending()
            time.sleep(60)
    except Exception as e:
        logger.critical(f"Fatal error in main application: {e}", exc_info=True)
        raise

def run_snapshot_safely(client):
    """
    Wraps the snapshot logger in try-except for resilience.

    :param client: Initialized MEXCContractClient.
    :type client: MEXCContractClient
    """
    logger = get_logger()
    try:
        logger.debug("Starting funding snapshot execution")
        log_funding_snapshot(client)
        logger.info(f"Snapshot executed successfully at {datetime.now(timezone.utc).isoformat()}")
    except Exception as e:
        logger.error(f"Error during snapshot execution: {e}", exc_info=True)


if __name__ == "__main__":
    main()