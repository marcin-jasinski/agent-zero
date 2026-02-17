"""Agent Zero (L.A.B.) - Main Chainlit Application Entry Point.

This is the A.P.I. (AI Playground Interface) - the web-based dashboard
for Agent Zero, the Local Agent Builder.

Phase 6b: Migrated from Streamlit to Chainlit for production-grade async architecture.
"""

import logging
import sys
from pathlib import Path

# Add project root to Python path for module imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import chainlit as cl

from src.config import get_config
from src.logging_config import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Load configuration
config = get_config()

logger.info("Starting Agent Zero UI (Chainlit)")


@cl.on_chat_start
async def start():
    """Initialize agent when chat session starts."""
    logger.info("New chat session started")
    
    # Welcome message
    welcome_msg = """# 👋 Welcome to Agent Zero (L.A.B.)

**Local Agent Builder** - Your production-grade AI agent development platform.

🔥 **New**: Now powered by Chainlit for better performance and async support!

## What can I help you with?

- 💬 **Chat**: Ask me anything using the knowledge base
- 📄 **Upload Documents**: Build your knowledge base (PDF, TXT, MD, CSV)
- ⚙️ **System Status**: View service health and metrics

**Note**: This is Step 23 of Phase 6b (Chainlit Migration). Full features coming in Steps 24-28!

---

Try asking me a question or upload a document to get started!
"""
    
    await cl.Message(content=welcome_msg).send()
    
    # Store session info
    cl.user_session.set("initialized", True)
    
    logger.info("Chat session initialized successfully")


@cl.on_message
async def main(message: cl.Message):
    """Process user messages."""
    logger.info(f"Received message: {message.content}")
    
    # Temporary response until we migrate the full agent (Step 24)
    response = f"""🚧 **Migration in Progress** 🚧

You said: "{message.content}"

The full chat functionality will be available in **Step 24: Migrate Chat Interface**.

For now, I'm just a friendly placeholder showing that Chainlit is working! 

**Current Status**: Step 23 Complete ✅
**Next Steps**: 
- Step 24: Migrate Chat Interface (agent integration)
- Step 25: Migrate Knowledge Base (document upload)
- Step 26: Create Admin Dashboard (system monitoring)
"""
    
    await cl.Message(content=response).send()


@cl.on_chat_end
async def end():
    """Cleanup when chat ends."""
    logger.info("Chat session ended")
    await cl.Message(content="👋 Goodbye! Thanks for using Agent Zero!").send()


if __name__ == "__main__":
    logger.info(f"Agent Zero {config.app_version} - {config.env} environment")
