"""
Daily Portfolio Updater
Automatically updates portfolio with latest market prices
Can be run via cron job or scheduled task
"""

import time
import subprocess
import sys
from datetime import datetime, date, timedelta
import logging
from pathlib import Path
import threading

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_updater.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DailyUpdater:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.running = False
        
    def fetch_latest_prices(self):
        """Fetch latest market prices using the daily price tracker"""
        try:
            logger.info("Fetching latest market prices...")
            result = subprocess.run(
                [sys.executable, 'daily_price_tracker.py', '--force'], 
                capture_output=True, 
                text=True, 
                timeout=300,  # 5 minute timeout
                cwd=self.base_dir
            )
            
            if result.returncode == 0:
                logger.info("Price fetching completed successfully")
                logger.debug(f"Price tracker output: {result.stdout}")
                return True
            else:
                logger.error(f"Price fetching failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Price fetching timed out")
            return False
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            return False
    
    def run_portfolio_recompiler(self):
        """Run the portfolio recompiler"""
        try:
            logger.info("Running portfolio recompiler...")
            result = subprocess.run(
                [sys.executable, 'portfolio_recompiler.py'], 
                capture_output=True, 
                text=True, 
                timeout=300,  # 5 minute timeout
                cwd=self.base_dir
            )
            
            if result.returncode == 0:
                logger.info("Portfolio recompiler completed successfully")
                logger.debug(f"Recompiler output: {result.stdout}")
                return True
            else:
                logger.error(f"Portfolio recompiler failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Portfolio recompiler timed out")
            return False
        except Exception as e:
            logger.error(f"Error running portfolio recompiler: {e}")
            return False
    
    def daily_update(self):
        """Perform daily update routine"""
        logger.info("=== Starting Daily Portfolio Update ===")
        
        success = True
        
        # Step 1: Fetch latest prices (this now includes portfolio recompilation)
        if not self.fetch_latest_prices():
            success = False
            # Try to run portfolio recompiler anyway with existing data
            logger.info("Attempting portfolio recompilation with existing price data...")
            if not self.run_portfolio_recompiler():
                logger.error("Portfolio recompilation also failed")
        
        if success:
            logger.info("=== Daily Update Completed Successfully ===")
        else:
            logger.error("=== Daily Update Completed with Errors ===")
        
        return success
    
    def get_next_run_time(self, target_hour=9, target_minute=0):
        """Calculate the next run time (default 9:00 AM)"""
        now = datetime.now()
        target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        
        # If target time has passed today, schedule for tomorrow
        if now >= target_time:
            target_time += timedelta(days=1)
        
        return target_time
    
    def run_scheduler(self):
        """Run the scheduled updater using built-in threading"""
        logger.info("Starting daily updater scheduler...")
        logger.info("Scheduled to run daily at 9:00 AM")
        
        self.running = True
        
        # Run immediately on startup
        logger.info("Running initial update...")
        self.daily_update()
        
        # Schedule next runs
        while self.running:
            next_run = self.get_next_run_time()
            wait_seconds = (next_run - datetime.now()).total_seconds()
            
            logger.info(f"Next update scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Waiting {wait_seconds/3600:.1f} hours until next update...")
            
            # Wait until it's time to run, checking every minute for shutdown signal
            while wait_seconds > 0 and self.running:
                sleep_time = min(60, wait_seconds)  # Sleep in 1-minute chunks
                time.sleep(sleep_time)
                wait_seconds -= sleep_time
            
            if self.running:
                self.daily_update()
    
    def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping daily updater scheduler...")
        self.running = False

def main():
    """Main function"""
    updater = DailyUpdater()
    
    try:
        # Check if running in scheduler mode
        if len(sys.argv) > 1 and sys.argv[1] == '--scheduler':
            updater.run_scheduler()
        else:
            # Run once
            updater.daily_update()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        updater.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
