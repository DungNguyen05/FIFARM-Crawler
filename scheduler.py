import asyncio
import logging
import time
import schedule
from datetime import datetime
from dotenv import load_dotenv
import os

# Import crawlers
from coin98_crawler import Coin98ArticleCrawler
from tapchibitcoin_crawler import TapchiBitcoinCrawler

# Load environment variables
load_dotenv()

# Timing Configuration
SCHEDULE_TYPE = os.getenv("SCHEDULE_TYPE", "interval")
INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", "60"))
DAILY_TIME = os.getenv("DAILY_TIME", "09:00")
CUSTOM_TIMES = os.getenv("CUSTOM_TIMES", "06:00,12:00,18:00")
RUN_IMMEDIATELY = os.getenv("RUN_IMMEDIATELY", "true").lower() == "true"

# Crawler Configuration
ENABLE_COIN98 = os.getenv("ENABLE_COIN98", "true").lower() == "true"
ENABLE_TAPCHIBITCOIN = os.getenv("ENABLE_TAPCHIBITCOIN", "true").lower() == "true"

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "crawler.log")

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CrawlerScheduler:
    def __init__(self):
        self.crawlers = {}
        
        # Initialize enabled crawlers
        if ENABLE_COIN98:
            self.crawlers['coin98'] = Coin98ArticleCrawler()
            logger.info("✅ Coin98 crawler initialized")
            
        if ENABLE_TAPCHIBITCOIN:
            self.crawlers['tapchibitcoin'] = TapchiBitcoinCrawler()
            logger.info("✅ TapchiBitcoin crawler initialized")
        
        if not self.crawlers:
            logger.error("❌ No crawlers enabled! Check your .env configuration")
            
        logger.info(f"📅 Schedule Type: {SCHEDULE_TYPE}")

    async def run_all_crawlers(self):
        """Run all enabled crawlers concurrently"""
        if not self.crawlers:
            logger.warning("⚠️ No crawlers to run")
            return
            
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"\n⏰ [{current_time}] Starting scheduled crawl for all sources...")
        
        # Create tasks for all crawlers
        tasks = []
        for name, crawler in self.crawlers.items():
            logger.info(f"🚀 Starting {name} crawler...")
            task = asyncio.create_task(
                crawler.run_workflow(),
                name=f"{name}_crawl"
            )
            tasks.append(task)
        
        # Wait for all crawlers to complete
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log results
            for i, (name, result) in enumerate(zip(self.crawlers.keys(), results)):
                if isinstance(result, Exception):
                    logger.error(f"❌ {name} crawler failed: {result}")
                else:
                    logger.info(f"✅ {name} crawler completed successfully")
                    
        except Exception as e:
            logger.error(f"❌ Error running crawlers: {e}")
        
        logger.info("🏁 All crawlers completed")

    def scheduled_crawl(self):
        """Wrapper for scheduled crawl (sync)"""
        # Run async function in new event loop
        asyncio.run(self.run_all_crawlers())

    def setup_schedule(self):
        """Setup scheduler based on configuration"""
        if SCHEDULE_TYPE == "interval":
            if INTERVAL_MINUTES >= 60:
                hours = INTERVAL_MINUTES // 60
                schedule.every(hours).hours.do(self.scheduled_crawl)
                logger.info(f"📅 Scheduled every {hours} hour(s)")
            else:
                schedule.every(INTERVAL_MINUTES).minutes.do(self.scheduled_crawl)
                logger.info(f"📅 Scheduled every {INTERVAL_MINUTES} minute(s)")
                
        elif SCHEDULE_TYPE == "daily":
            schedule.every().day.at(DAILY_TIME).do(self.scheduled_crawl)
            logger.info(f"📅 Scheduled daily at {DAILY_TIME}")
            
        elif SCHEDULE_TYPE == "hourly":
            schedule.every().hour.do(self.scheduled_crawl)
            logger.info("📅 Scheduled every hour")
            
        elif SCHEDULE_TYPE == "custom":
            times = [time.strip() for time in CUSTOM_TIMES.split(',')]
            for time_str in times:
                if ':' in time_str:
                    schedule.every().day.at(time_str).do(self.scheduled_crawl)
                    logger.info(f"📅 Scheduled daily at {time_str}")
        else:
            logger.error(f"❌ Invalid SCHEDULE_TYPE: {SCHEDULE_TYPE}")
            return False
            
        return True

    def start_scheduler(self):
        """Start the scheduler"""
        if not self.setup_schedule():
            return
            
        # Run immediately if configured
        if RUN_IMMEDIATELY:
            logger.info("🚀 Running initial crawl...")
            self.scheduled_crawl()
        
        # Keep the scheduler running
        logger.info("🔄 Scheduler is running... Press Ctrl+C to stop")
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Scheduler stopped by user")

def main():
    
    scheduler = CrawlerScheduler()
    scheduler.start_scheduler()

if __name__ == "__main__":
    main()