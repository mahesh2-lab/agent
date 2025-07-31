import sys
import platform
import os
from dotenv import load_dotenv

def check_python_version(min_version=(3, 7)):
    if sys.version_info < min_version:
        print(f"Python {min_version[0]}.{min_version[1]}+ is required.")
        return False
    print(f"Python version: {platform.python_version()}")
    return True

def check_env_var(var_name):
    value = os.environ.get(var_name)
    if value is None:
        print(f"Environment variable '{var_name}' is not set.")
        return False
    print(f"{var_name}={value}")
    return True

def main():
    print("Loading environment variables from .env file...")
    load_dotenv()
    print("Checking environment...")
    python_ok = check_python_version()
    env_ok = check_env_var("GOOGLE_API_KEY") 
    if python_ok and env_ok:
        print("Environment check passed.")
    else:
        print("Environment check failed.")

if __name__ == "__main__":
    main()