                                           [str], config: dict = None):
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    retry_count = 0
    try:
        extracted = extract_all(files)
    except RetryExceededError:
        retry_count += 3  # all attempts exhausted
        extracted = []
    
    try:
        cleaned, rejects = clean(extracted)
    except RetryExceededError:
        retry_count += 3
        cleaned, rejects = [], []
    
    try:
        report = generate_report(cleaned, rejects, retry_count, files)
    except RetryExceededError:
        retry_count += 3
        report = {"processed_count": 0, "rejected_count": 0, "retry_count": retry_count, "source_files": files}
    
    logger.info("Final Report:")
    logger.info(json.dumps(report, indent=2))</parameter>
<parameter name="new_string">def run(files: List[str], config: dict = None):
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    if config is None:
        config = {}
    # Update global retry config if needed
    if "retry_attempts" in config:
        retries = int(config["retry_attempts"])
        _RETRY_CONFIG["max_attempts"] = retries + 1  # total attempts = retries + 1
    
    retry_count = 0
    try:
        extracted = extract_all(files)
    except RetryExceededError:
        retry_count += _RETRY_CONFIG["max_attempts"]
        extracted = []
    
    try:
        cleaned, rejects = clean(extracted)
    except RetryExceededError:
        retry_count += _RETRY_CONFIG["max_attempts"]
        cleaned, rejects = [], []
    
    try:
        report = generate_report(cleaned, rejects, retry_count, files)
    except RetryExceededError:
        retry_count += _RETRY_CONFIG["max_attempts"]
        report = {"processed_count": 0, "rejected_count": 0, "retry_count": retry_count, "source_files": files}
    
    logger.info("Final Report:")
    logger.info(json.dumps(report, indent=2))
    
    # Write report to file if configured
    output_path = config.get("report_output")
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)</parameter>
</invoke>
</function_calls>