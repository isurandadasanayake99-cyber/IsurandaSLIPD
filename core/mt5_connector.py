import MetaTrader5 as mt5

def connect_to_mt5():
    """
    Initializes connection to the MetaTrader 5 terminal.
    Make sure your MetaTrader 5 terminal is installed and logged into an account.
    """
    # Initialize connection to the MetaTrader 5 terminal
    if not mt5.initialize():
        print(f"initialize() failed, error code = {mt5.last_error()}")
        return False
        
    print("Connected to MetaTrader 5 successfully!")
    
    # Get terminal info
    terminal_info = mt5.terminal_info()
    if terminal_info is not None:
        print(f"Terminal Info: {terminal_info.name} (Build {terminal_info.build})")
    
    # Get account info
    account_info = mt5.account_info()
    if account_info is not None:
        print(f"Account Number: {account_info.login}")
        print(f"Server: {account_info.server}")
        print(f"Balance: {account_info.balance} {account_info.currency}")
    
    return True

def is_connected():
    """Checks if MT5 terminal connection is active."""
    try:
        return mt5.terminal_info() is not None
    except Exception:
        return False

def get_account_details():
    """
    Returns account information dictionary or a fallback structure.
    """
    try:
        if is_connected():
            acc = mt5.account_info()
            if acc:
                return {
                    "connected": True,
                    "login": acc.login,
                    "server": acc.server,
                    "balance": acc.balance,
                    "equity": acc.equity,
                    "currency": acc.currency
                }
    except Exception:
        pass
    return {
        "connected": False,
        "login": 0,
        "server": "Offline",
        "balance": 5367.50,
        "equity": 5367.50,
        "currency": "USD"
    }

if __name__ == "__main__":
    # Test the connection, then shut down immediately
    print("Attempting to connect to MT5...")
    if connect_to_mt5():
        print("Shutting down connection...")
        mt5.shutdown()
        print("Done.")
