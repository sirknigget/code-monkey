def suppress_noisy_loggers():
    import logging

    # Suppress low-level HTTP transport noise during tests
    for _noisy_logger in (
        "httpx",
        "httpcore",
        "urllib3",
        "openai._base_client",
        "langsmith",
    ):
        logging.getLogger(_noisy_logger).setLevel(logging.WARNING)
