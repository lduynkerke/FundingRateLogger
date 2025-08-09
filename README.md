# Funding Rate Logger

A system for tracking and analyzing cryptocurrency funding rates to identify trading opportunities.

## Overview

This application monitors cryptocurrency funding rates on the MEXC exchange, collecting data around funding times to enable analysis and strategy development. It automatically identifies symbols with the highest funding rates before each funding event and collects detailed price data at various timeframes to support trading strategy development.

## Features

- Automatic monitoring of funding rate events on MEXC exchange
- Identification of top symbols with highest funding rates
- Collection of OHLCV data at multiple timeframes (1m, 10m, 1h, 1d)
- Comprehensive logging system
- Configurable data collection parameters
- CSV export of collected data for analysis

## Installation

### Prerequisites

- Python 3.8 or higher
- MEXC API credentials (obtain from [MEXC Exchange](https://www.mexc.com/))

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/FundingRateLogger.git
   cd FundingRateLogger
   ```

2. Install dependencies:
   ```
   pip install schedule requests pyyaml
   ```

3. Configure your MEXC API credentials in `config.yaml`:
   ```yaml
   mexc:
     api_key: "your_api_key_here"
     secret_key: "your_secret_key_here"
   ```

## Configuration

The application is configured via `config.yaml` which includes:

- MEXC API credentials
- Logging settings
- Funding rate collection parameters

### Full Configuration Example

```yaml
mexc:
  api_key: "your_api_key_here"
  secret_key: "your_secret_key_here"
  base_urls:
    spot: "https://api.mexc.com"
    contract: "https://contract.mexc.com"
  timeout: 10

logging:
  log_dir: "logs"
  log_file: "funding_log.csv"
  log_level: "INFO"
  console_log_level: "WARNING"
  file_log_level: "INFO"
  log_format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  max_log_files: 30

funding:
  snapshot_window_minutes: 10
  log_interval_hours: 4
  top_n_symbols: 3
  time_windows:
    daily_days_back: 3
    hourly_hours_back: 8
    ten_min_hours_before: 1
    one_min_minutes_before: 10
    one_min_minutes_after: 10
```

### Funding Configuration

The `funding` section controls how data is collected:

- `snapshot_window_minutes`: Time window around funding events to collect data
- `log_interval_hours`: How often to log funding rates
- `top_n_symbols`: Number of top funding rate symbols to track
- `time_windows`: Configuration for different timeframe data collection
  - `daily_days_back`: Number of days of daily candles to collect
  - `hourly_hours_back`: Number of hours of hourly candles to collect
  - `ten_min_hours_before`: Hours of 10-minute candles to collect before funding
  - `one_min_minutes_before`: Minutes of 1-minute candles to collect before funding
  - `one_min_minutes_after`: Minutes of 1-minute candles to collect after funding

### Logging Configuration

The application uses Python's built-in logging module with the following configuration options in `config.yaml`:

```yaml
logging:
  log_dir: "logs"                # Directory where log files are stored
  log_file: "funding_log.csv"    # CSV file for funding rate data
  log_level: "INFO"              # Overall logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  console_log_level: "WARNING"   # Level for console output
  file_log_level: "INFO"         # Level for file output
  log_format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # Log message format
  max_log_files: 30              # Maximum number of log files to keep
```

## Usage

### Running the Application

To start the funding rate logger:

```
python main.py
```

The application will run continuously, checking for upcoming funding events and collecting data at strategic times before each funding rate payout.

### Data Collection Process

The application follows this process:

1. Runs every 5 minutes to check for upcoming funding events
2. At 15 minutes before funding time: Identifies and caches top symbols with highest funding rates
3. At 10 minutes before funding time: Collects OHLCV data for the cached symbols
4. Saves collected data to CSV files for later analysis

### Output Files

Data is saved to CSV files with the naming pattern:
```
funding_data_{symbol}_{timestamp}.csv
```

Each CSV file contains the following columns:
- Symbol
- FundingTime
- Interval (1m, 10m, 1h, 1d)
- Timestamp
- Open
- High
- Low
- Close
- Volume

## Project Structure

```
FundingRateLogger/
├── api/                      # API client implementations
│   ├── __init__.py
│   ├── base_client.py        # Base API client class
│   ├── contract_client.py    # MEXC contract API client
│   └── spot_client.py        # MEXC spot API client
├── pipeline/                 # Data processing pipeline
│   ├── __init__.py
│   └── funding_rate_logger.py # Core funding rate collection logic
├── utils/                    # Utility functions
│   ├── __init__.py
│   ├── config_loader.py      # Configuration loading
│   ├── funding_rate_cache.py # Symbol caching utilities
│   └── logger.py             # Logging setup
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_funding_logger.py
│   ├── test_implementation.py
│   └── test_logging.py
├── logs/                     # Log files directory
├── .gitignore                # Git ignore file for Python projects
├── config.yaml               # Configuration file
├── conftest.py               # Pytest configuration
├── main.py                   # Application entry point
├── pytest.ini                # Pytest settings
└── README.md                 # This documentation
```

## Logging System

The application implements comprehensive logging throughout all components:

1. **API Clients**: Logs API requests, responses, and errors
2. **Pipeline Components**: Logs data processing steps and outcomes
3. **Main Application**: Logs application startup, scheduling, and execution

### Log Levels

- **DEBUG**: Detailed information for diagnosing problems
- **INFO**: Confirmation that things are working as expected
- **WARNING**: Indication that something unexpected happened
- **ERROR**: Due to a more serious problem, the software couldn't perform some function
- **CRITICAL**: A serious error indicating the program may be unable to continue running

### Log Files

Log files are stored in the `logs` directory with filenames including the date (e.g., `app_20250802.log`).

## Running Tests

To run all tests:

```
pytest
```

To test specific components:

```
python tests/test_logging.py
python tests/test_api.py
python tests/test_funding_logger.py
```

This will verify that the logger is properly configured and that API client logging is working correctly.

## Deployment

### Prerequisites

- Linux server with systemd
- Python 3.8 or higher
- sudo privileges

### Deployment Steps

1. Clone the repository to your server:
   ```bash
   git clone https://github.com/yourusername/FundingRateLogger.git
   cd FundingRateLogger
   ```

2. Update the configuration file with your MEXC API credentials:
   ```bash
   nano config.yaml
   ```
   
   Update the following lines with your actual API credentials:
   ```yaml
   mexc:
     api_key: "your_api_key_here"
     secret_key: "your_secret_key_here"
   ```

3. Make the deployment script executable:
   ```bash
   chmod +x deploy.sh
   ```

4. Run the deployment script:
   ```bash
   ./deploy.sh
   ```

   The script will:
   - Check if Python 3.8+ is installed
   - Create a Python virtual environment
   - Install all required dependencies
   - Create a systemd service for the application
   - Start the service

5. Verify the service is running:
   ```bash
   sudo systemctl status fundingratelogger.service
   ```

### Managing the Service

- **Check service status**:
  ```bash
  sudo systemctl status fundingratelogger.service
  ```

- **View logs**:
  ```bash
  sudo journalctl -u fundingratelogger.service
  ```

- **Restart the service**:
  ```bash
  sudo systemctl restart fundingratelogger.service
  ```

- **Stop the service**:
  ```bash
  sudo systemctl stop fundingratelogger.service
  ```

### Application Logs

Application logs are stored in the `logs` directory. The log files are named with the date format `app_YYYYMMDD.log`.

### Troubleshooting

1. **Service fails to start**:
   - Check the logs: `sudo journalctl -u fundingratelogger.service`
   - Verify your API credentials in `config.yaml`
   - Ensure Python 3.8+ is installed: `python3 --version`

2. **Missing dependencies**:
   - Manually install dependencies: `pip install -r requirements.txt`

3. **Permission issues**:
   - Ensure the user has write permissions to the application directory
   - Check if the logs directory exists and is writable