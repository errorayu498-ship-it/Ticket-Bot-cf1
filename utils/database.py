import json
import aiofiles
import asyncio
from typing import Dict, List, Any
from datetime import datetime
from .logger import logger

class Database:
    def __init__(self, memory_file: str = "memory.json"):
        self.memory_file = memory_file
        self.data = None
        self.lock = asyncio.Lock()
    
    async def load_data(self):
        """Load data from memory file"""
        try:
            async with aiofiles.open(self.memory_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                self.data = json.loads(content)
                logger.info("Database loaded successfully")
        except FileNotFoundError:
            logger.warning("Memory file not found, creating new one")
            await self.create_default_data()
        except json.JSONDecodeError:
            logger.error("Error decoding memory file, creating new one")
            await self.create_default_data()
    
    async def create_default_data(self):
        """Create default data structure"""
        self.data = {
            "tickets": {},
            "temp_removed_options": [],
            "ticket_counter": 0,
            "blacklisted_users": [],
            "panel_message_id": None,
            "panel_channel_id": None
        }
        await self.save_data()
    
    async def save_data(self):
        """Save data to memory file"""
        async with self.lock:
            try:
                async with aiofiles.open(self.memory_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(self.data, indent=4, ensure_ascii=False))
                logger.debug("Data saved successfully")
            except Exception as e:
                logger.error(f"Error saving data: {e}")
    
    async def get_ticket(self, ticket_id: str) -> Dict:
        """Get ticket by ID"""
        return self.data["tickets"].get(ticket_id)
    
    async def get_all_tickets(self) -> Dict:
        """Get all tickets"""
        return self.data["tickets"]
    
    async def add_ticket(self, ticket_id: str, ticket_data: Dict):
        """Add a new ticket"""
        self.data["tickets"][ticket_id] = ticket_data
        await self.save_data()
    
    async def remove_ticket(self, ticket_id: str):
        """Remove a ticket"""
        if ticket_id in self.data["tickets"]:
            del self.data["tickets"][ticket_id]
            await self.save_data()
    
    async def update_ticket(self, ticket_id: str, update_data: Dict):
        """Update ticket data"""
        if ticket_id in self.data["tickets"]:
            self.data["tickets"][ticket_id].update(update_data)
            await self.save_data()
    
    async def get_next_ticket_number(self) -> int:
        """Get next ticket number"""
        self.data["ticket_counter"] += 1
        await self.save_data()
        return self.data["ticket_counter"]
    
    async def add_temp_removed_option(self, option_data: Dict):
        """Add temporarily removed option"""
        self.data["temp_removed_options"].append(option_data)
        await self.save_data()
    
    async def remove_temp_removed_option(self, option_name: str):
        """Remove temporarily removed option"""
        self.data["temp_removed_options"] = [opt for opt in self.data["temp_removed_options"] if opt.get("name") != option_name]
        await self.save_data()
    
    async def get_temp_removed_options(self) -> List:
        """Get temporarily removed options"""
        return self.data["temp_removed_options"]
    
    async def add_blacklisted_user(self, user_id: int):
        """Add user to blacklist"""
        if user_id not in self.data["blacklisted_users"]:
            self.data["blacklisted_users"].append(user_id)
            await self.save_data()
    
    async def remove_blacklisted_user(self, user_id: int):
        """Remove user from blacklist"""
        if user_id in self.data["blacklisted_users"]:
            self.data["blacklisted_users"].remove(user_id)
            await self.save_data()
    
    async def is_blacklisted(self, user_id: int) -> bool:
        """Check if user is blacklisted"""
        return user_id in self.data["blacklisted_users"]
    
    async def update_panel_info(self, channel_id: int, message_id: int):
        """Update panel message info"""
        self.data["panel_channel_id"] = channel_id
        self.data["panel_message_id"] = message_id
        await self.save_data()
    
    async def get_panel_info(self) -> tuple:
        """Get panel message info"""
        return self.data.get("panel_channel_id"), self.data.get("panel_message_id")
