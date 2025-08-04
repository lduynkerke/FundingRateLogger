# Funding Rate Strategy

A system for tracking and analyzing cryptocurrency funding rates to identify trading opportunities.

## Overview

This application monitors cryptocurrency funding rates on the MEXC exchange, collecting data around funding times to enable analysis and strategy development.

## Configuration

The application is configured via `config.yaml` which includes:

- MEXC API credentials
- Logging settings
- Funding rate collection parameters

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

To test the logging functionality:

```
python tests/test_logging.py
```

This will verify that the logger is properly configured and that API client logging is working correctly.

## Troubleshooting

If you encounter issues:

1. Check the log files in the `logs` directory
2. Verify that the `log_dir` exists and is writable
3. Ensure the configuration in `config.yaml` is correct