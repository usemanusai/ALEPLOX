#!/usr/bin/env python3
"""
VoiceGuard IPC Communication
Named Pipes IPC implementation for service-to-helper communication
"""

import asyncio
import json
import uuid
import win32pipe
import win32file
import win32security
import ntsecuritycon
import threading
import queue
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import struct


class IPCMessage:
    """IPC message structure"""
    
    def __init__(self, msg_type: str, payload: Dict, correlation_id: str = None):
        self.type = msg_type
        self.payload = payload
        self.timestamp = datetime.now(timezone.utc)
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.message_id = str(uuid.uuid4())
        
    def to_bytes(self) -> bytes:
        """Serialize message to bytes"""
        data = {
            'type': self.type,
            'payload': self.payload,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'message_id': self.message_id
        }
        json_str = json.dumps(data)
        json_bytes = json_str.encode('utf-8')
        
        # Prepend length header (4 bytes)
        length = len(json_bytes)
        return struct.pack('<I', length) + json_bytes
        
    @classmethod
    def from_bytes(cls, data: bytes) -> 'IPCMessage':
        """Deserialize message from bytes"""
        json_str = data.decode('utf-8')
        data_dict = json.loads(json_str)
        
        msg = cls(
            data_dict['type'],
            data_dict['payload'],
            data_dict['correlation_id']
        )
        msg.timestamp = datetime.fromisoformat(data_dict['timestamp'])
        msg.message_id = data_dict['message_id']
        
        return msg


class IPCServer:
    """Named pipe server for service-to-helper communication"""
    
    def __init__(self):
        self.pipe_name = r'\\.\pipe\VoiceGuardIPC'
        self.is_running = False
        self.clients = []
        self.message_queue = queue.Queue()
        self.logger = logging.getLogger("IPCServer")
        
    def create_security_descriptor(self):
        """Create security descriptor for named pipe"""
        # Create security descriptor
        sd = win32security.SECURITY_DESCRIPTOR()
        
        # Create DACL
        dacl = win32security.ACL()
        
        # Add SYSTEM full control
        system_sid = win32security.LookupAccountName(None, "NT AUTHORITY\\SYSTEM")[0]
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            ntsecuritycon.GENERIC_ALL,
            system_sid
        )
        
        # Add Administrators full control
        admin_sid = win32security.LookupAccountName(None, "BUILTIN\\Administrators")[0]
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            ntsecuritycon.GENERIC_ALL,
            admin_sid
        )
        
        # Add current user read/write
        try:
            current_user = win32security.GetUserName()
            user_sid = win32security.LookupAccountName(None, current_user)[0]
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                ntsecuritycon.GENERIC_READ | ntsecuritycon.GENERIC_WRITE,
                user_sid
            )
        except Exception as e:
            self.logger.warning(f"Could not add current user to DACL: {e}")
            
        # Set DACL
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        
        # Create security attributes
        sa = win32security.SECURITY_ATTRIBUTES()
        sa.SECURITY_DESCRIPTOR = sd
        sa.bInheritHandle = 0
        
        return sa
        
    def start(self):
        """Start the IPC server"""
        self.is_running = True
        self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
        self.server_thread.start()
        self.logger.info("IPC Server started")
        
    def stop(self):
        """Stop the IPC server"""
        self.is_running = False
        if hasattr(self, 'server_thread'):
            self.server_thread.join(timeout=5)
        self.logger.info("IPC Server stopped")
        
    def _server_loop(self):
        """Main server loop"""
        while self.is_running:
            try:
                # Create security attributes
                sa = self.create_security_descriptor()
                
                # Create named pipe
                pipe_handle = win32pipe.CreateNamedPipe(
                    self.pipe_name,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES,
                    65536,  # Output buffer size
                    65536,  # Input buffer size
                    0,      # Default timeout
                    sa      # Security attributes
                )
                
                self.logger.info("Waiting for client connection...")
                
                # Wait for client connection
                win32pipe.ConnectNamedPipe(pipe_handle, None)
                self.logger.info("Client connected to IPC pipe")
                
                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(pipe_handle,),
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                self.logger.error(f"IPC server error: {e}")
                if self.is_running:
                    import time
                    time.sleep(1)
                    
    def _handle_client(self, pipe_handle):
        """Handle individual client connection"""
        try:
            while self.is_running:
                # Read message length
                try:
                    length_data = win32file.ReadFile(pipe_handle, 4)[1]
                    if len(length_data) != 4:
                        break
                        
                    message_length = struct.unpack('<I', length_data)[0]
                    
                    # Read message data
                    message_data = win32file.ReadFile(pipe_handle, message_length)[1]
                    
                    # Parse message
                    message = IPCMessage.from_bytes(message_data)
                    
                    # Add to message queue
                    self.message_queue.put(message)
                    
                    # Send acknowledgment
                    ack = IPCMessage("ACK", {"message_id": message.message_id})
                    ack_bytes = ack.to_bytes()
                    win32file.WriteFile(pipe_handle, ack_bytes)
                    
                except Exception as e:
                    self.logger.error(f"Client communication error: {e}")
                    break
                    
        finally:
            try:
                win32file.CloseHandle(pipe_handle)
            except:
                pass
            self.logger.info("Client disconnected from IPC pipe")
            
    async def get_pending_messages(self) -> List[IPCMessage]:
        """Get all pending messages from queue"""
        messages = []
        while not self.message_queue.empty():
            try:
                message = self.message_queue.get_nowait()
                messages.append(message)
            except queue.Empty:
                break
        return messages
        
    async def send_message(self, message: IPCMessage):
        """Send message to connected clients (placeholder)"""
        # In a full implementation, you'd maintain client connections
        # and send messages to them
        pass


class IPCClient:
    """Named pipe client for helper-to-service communication"""
    
    def __init__(self):
        self.pipe_name = r'\\.\pipe\VoiceGuardIPC'
        self.pipe_handle = None
        self.is_connected = False
        self.logger = logging.getLogger("IPCClient")
        
    async def connect(self, timeout: int = 30):
        """Connect to the IPC server"""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                # Try to open the named pipe
                self.pipe_handle = win32file.CreateFile(
                    self.pipe_name,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )
                
                # Set pipe mode
                win32pipe.SetNamedPipeHandleState(
                    self.pipe_handle,
                    win32pipe.PIPE_READMODE_MESSAGE,
                    None,
                    None
                )
                
                self.is_connected = True
                self.logger.info("Connected to IPC server")
                return True
                
            except Exception as e:
                self.logger.debug(f"Connection attempt failed: {e}")
                await asyncio.sleep(1)
                
        self.logger.error("Failed to connect to IPC server")
        return False
        
    async def send_message(self, message: IPCMessage) -> bool:
        """Send message to server"""
        if not self.is_connected or not self.pipe_handle:
            return False
            
        try:
            # Send message
            message_bytes = message.to_bytes()
            win32file.WriteFile(self.pipe_handle, message_bytes)
            
            # Wait for acknowledgment
            length_data = win32file.ReadFile(self.pipe_handle, 4)[1]
            message_length = struct.unpack('<I', length_data)[0]
            ack_data = win32file.ReadFile(self.pipe_handle, message_length)[1]
            
            ack_message = IPCMessage.from_bytes(ack_data)
            
            if ack_message.type == "ACK":
                return True
                
        except Exception as e:
            self.logger.error(f"Send message error: {e}")
            self.is_connected = False
            
        return False
        
    def disconnect(self):
        """Disconnect from server"""
        if self.pipe_handle:
            try:
                win32file.CloseHandle(self.pipe_handle)
            except:
                pass
            self.pipe_handle = None
            
        self.is_connected = False
        self.logger.info("Disconnected from IPC server")
