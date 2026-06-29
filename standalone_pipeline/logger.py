# Standalone replacement for app/utils.py logging (no DB).
# Token usage is printed to stdout instead of being written to the server DB.

def log_gpt_request(user_id, model_name, input_length, output_length):
    print(f"[token usage] model={model_name} input={input_length} output={output_length}")


def is_not_billing_error(e):
    # Return True if the error is not a billable error
    if "Incorrect API key provided" in str(e):
        return True
    if "Invalid Authentication" in str(e):
        return True
