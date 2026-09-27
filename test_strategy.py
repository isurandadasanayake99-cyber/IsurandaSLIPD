import MetaTrader5 as mt5
import time
from database.db_manager import DatabaseLogger
from strategy.grid_bot import GridBot
from core.mt5_connector import connect_to_mt5

def main():
    print("Testing Phase 2: Core Trading Logic")
    if not connect_to_mt5():
        return

    db_logger = DatabaseLogger()
    
    # Create grid bots for EURUSD and GBPJPY, 
    # testing the concurrent threading requirement.
    bot_eurusd = GridBot(
        symbol="EURUSD",
        lot_size=0.01,
        grid_spacing_pips=10,
        num_levels=3, # Place 3 buy limits and 3 sell limits
        db_logger=db_logger
    )
    
    bot_gbpjpy = GridBot(
        symbol="GBPJPY",
        lot_size=0.01,
        grid_spacing_pips=15,
        num_levels=3,
        db_logger=db_logger
    )
    
    print("\nStarting Grid Bots in parallel...")
    bot_eurusd.start()
    bot_gbpjpy.start()
    
    try:
        # Keep main thread alive
        print("Bots are running concurrently. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received.")
    finally:
        print("Stopping bots and shutting down...")
        bot_eurusd.stop()
        bot_gbpjpy.stop()
        
        # Wait for threads to finish cleanly
        bot_eurusd.join()
        bot_gbpjpy.join()
        
        mt5.shutdown()
        print("Application closed.")

if __name__ == "__main__":
    main()
