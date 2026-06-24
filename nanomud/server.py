import asyncio
import logging
from typing import Dict, Optional
from .colors import ansi_format
from .engine import Engine

logger = logging.getLogger(__name__)

class TelnetSession:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, session_id: int, server: "TelnetServer"):
        self.reader = reader
        self.writer = writer
        self.id = session_id
        self.server = server
        self.buffer = bytearray()
        self.just_processed_r = False
        
    def send(self, text: str, echo: Optional[bool] = None):
        try:
            # Handle echo negotiation if requested (TELNET RFC)
            if echo is False:
                # IAC WILL ECHO (tells client to stop local echo)
                self.writer.write(b"\xff\xfb\x01")
            elif echo is True:
                # IAC WONT ECHO (tells client to resume local echo)
                self.writer.write(b"\xff\xfc\x01")
                
            formatted = ansi_format(text)
            # Standard TELNET line endings are \r\n
            formatted = formatted.replace("\r\n", "\n").replace("\n", "\r\n")
            self.writer.write(formatted.encode("utf-8", errors="ignore"))
        except Exception as e:
            logger.error(f"Error sending to session {self.id}: {e}")
            
    def close(self):
        try:
            self.writer.close()
        except Exception:
            pass

    async def run(self):
        self.telnet_state = 0
        try:
            while True:
                data = await self.reader.read(1024)
                if not data:
                    break
                
                i = 0
                while i < len(data):
                    b = data[i]
                    i += 1
                    
                    if self.telnet_state == 0:
                        if b == 255:  # IAC (Interpret As Command)
                            self.telnet_state = 1
                        elif b in (8, 127):  # Backspace or Delete
                            self.just_processed_r = False
                            if self.buffer:
                                self.buffer.pop()
                                self.writer.write(b"\x08 \x08")
                        elif b == 13:  # Carriage Return (\r)
                            line = self.buffer.decode("utf-8", errors="ignore")
                            self.buffer.clear()
                            self.just_processed_r = True
                            self.server.engine.handle_input(self, line)
                        elif b == 10:  # Newline (\n)
                            if not self.just_processed_r:
                                line = self.buffer.decode("utf-8", errors="ignore")
                                self.buffer.clear()
                                self.server.engine.handle_input(self, line)
                            self.just_processed_r = False
                        else:
                            self.just_processed_r = False
                            # Append printable ASCII/UTF-8 characters
                            if 32 <= b < 127 or b >= 128:
                                self.buffer.append(b)
                                
                    elif self.telnet_state == 1:  # Seen IAC
                        if b in (251, 252, 253, 254):  # WILL, WONT, DO, DONT
                            self.telnet_state = 2
                        elif b == 250:  # SB (Subnegotiation Begin)
                            self.telnet_state = 3
                        else:
                            # Other 2-byte commands (e.g. NOP, GA, etc.)
                            self.telnet_state = 0
                            
                    elif self.telnet_state == 2:  # Expected option byte after WILL/WONT/DO/DONT
                        self.telnet_state = 0
                        
                    elif self.telnet_state == 3:  # Inside SB subnegotiation
                        if b == 255:  # IAC inside SB
                            self.telnet_state = 4
                            
                    elif self.telnet_state == 4:  # Seen IAC inside SB
                        if b == 240:  # SE (Subnegotiation End)
                            self.telnet_state = 0
                        else:
                            # Not SE, stay in SB
                            self.telnet_state = 3
                            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Session {self.id} error: {e}")
        finally:
            self.server.engine.handle_disconnect(self)
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass


class TelnetServer:
    def __init__(self, host: str, port: int, data_dir: str, template: Optional[str] = None):
        self.host = host
        self.port = port
        self.engine = Engine(data_dir, template=template)
        self.session_counter = 0
        self.server: Optional[asyncio.AbstractServer] = None

    async def client_handler(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.session_counter += 1
        session_id = self.session_counter
        session = TelnetSession(reader, writer, session_id, self)
        
        addr = writer.get_extra_info("peername")
        logger.info(f"New connection from {addr} (Session {session_id})")
        
        self.engine.handle_connect(session)
        await session.run()

    async def start(self):
        self.server = await asyncio.start_server(self.client_handler, self.host, self.port)
        addr = self.server.sockets[0].getsockname()
        logger.info(f"Server running on {addr}")
        print(f"Nanomud running on telnet://{self.host}:{self.port}")
        print(f"Database directory: {self.engine.world.data_dir}")
        print("Press Ctrl+C to stop.")

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        self.engine.shutdown()
        logger.info("Server stopped.")

    def run(self):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            print("\nShutting down server...")

    async def run_async(self):
        await self.start()
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

