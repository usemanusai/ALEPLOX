#!/usr/bin/env python3
"""
VoiceGuard Event Logger
Comprehensive event logging system for VoiceGuard
"""

import logging
import logging.handlers
import json
import sqlite3
import win32evtlog
import win32evtlogutil
import win32con
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import threading


class EventLogger:
    """Comprehensive event logging system for VoiceGuard"""
    
    def __init__(self):
        self.logger = logging.getLogger("EventLogger")
        self.db_path = Path("C:/ProgramData/VoiceGuard/config.db")
        self.log_lock = threading.Lock()
        
        # Event categories and IDs
        self.event_categories = {
            'security': {
                'event_ids': {
                    1001: 'Service Started',
                    1002: 'Service Stopped', 
                    1003: 'Configuration Changed',
                    1004: 'Emergency Disable Activated',
                    1005: 'Unauthorized Access Attempt'
                },
                'severity': 'High',
                'retention': '1 year'
            },
            'operational': {
                'event_ids': {
                    2001: 'Voice Command Detected',
                    2002: 'System Shutdown Initiated',
                    2003: 'Test Mode Activated',
                    2004: 'API Key Rotation',
                    2005: 'Watchdog Recovery Action'
                },
                'severity': 'Medium',
                'retention': '90 days'
            },
            'performance': {
                'event_ids': {
                    3001: 'High CPU Usage Detected',
                    3002: 'Memory Threshold Exceeded',
                    3003: 'API Response Time Degraded',
                    3004: 'Audio Processing Latency High'
                },
                'severity': 'Low',
                'retention': '30 days'
            }
        }
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup comprehensive logging system"""
        log_dir = Path("C:/ProgramData/VoiceGuard/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        json_formatter = JsonFormatter()
        
        # File handlers
        handlers = []
        
        # Main log file
        main_handler = logging.handlers.RotatingFileHandler(
            log_dir / "voiceguard.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        main_handler.setFormatter(detailed_formatter)
        handlers.append(main_handler)
        
        # JSON structured log
        json_handler = logging.handlers.RotatingFileHandler(
            log_dir / "voiceguard_structured.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        json_handler.setFormatter(json_formatter)
        handlers.append(json_handler)
        
        # Security events log
        security_handler = logging.handlers.RotatingFileHandler(
            log_dir / "security.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=10
        )
        security_handler.setFormatter(detailed_formatter)
        security_handler.setLevel(logging.WARNING)
        handlers.append(security_handler)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        for handler in handlers:
            root_logger.addHandler(handler)
            
    def log_security_event(self, event_id: int, message: str, context: Dict = None):
        """Log security-related events"""
        self._log_event('security', event_id, message, context, logging.WARNING)
        
    def log_operational_event(self, event_id: int, message: str, context: Dict = None):
        """Log operational events"""
        self._log_event('operational', event_id, message, context, logging.INFO)
        
    def log_performance_event(self, event_id: int, message: str, context: Dict = None):
        """Log performance-related events"""
        self._log_event('performance', event_id, message, context, logging.INFO)
        
    def _log_event(self, category: str, event_id: int, message: str, 
                   context: Dict = None, level: int = logging.INFO):
        """Internal method to log events"""
        try:
            with self.log_lock:
                # Get event details
                event_details = self.event_categories.get(category, {})
                event_name = event_details.get('event_ids', {}).get(event_id, 'Unknown Event')
                
                # Create structured log entry
                log_entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'category': category,
                    'event_id': event_id,
                    'event_name': event_name,
                    'message': message,
                    'context': context or {},
                    'severity': event_details.get('severity', 'Unknown')
                }
                
                # Log to Python logging system
                self.logger.log(level, f"[{category.upper()}:{event_id}] {event_name}: {message}", 
                              extra={'structured_data': log_entry})
                
                # Log to database
                self._log_to_database(log_entry)
                
                # Log to Windows Event Log (for critical events)
                if category == 'security' or event_id in [2002, 1001, 1002]:
                    self._log_to_windows_event_log(log_entry)
                    
        except Exception as e:
            self.logger.error(f"Failed to log event: {e}")
            
    def _log_to_database(self, log_entry: Dict):
        """Log event to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO event_log (event_type, event_data, confidence_score, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (
                    f"{log_entry['category']}:{log_entry['event_id']}",
                    json.dumps(log_entry),
                    log_entry['context'].get('confidence', None),
                    log_entry['timestamp']
                ))
        except Exception as e:
            self.logger.error(f"Database logging failed: {e}")
            
    def _log_to_windows_event_log(self, log_entry: Dict):
        """Log critical events to Windows Event Log"""
        try:
            # Map severity to Windows event type
            event_type_map = {
                'High': win32evtlog.EVENTLOG_ERROR_TYPE,
                'Medium': win32evtlog.EVENTLOG_WARNING_TYPE,
                'Low': win32evtlog.EVENTLOG_INFORMATION_TYPE
            }
            
            event_type = event_type_map.get(log_entry['severity'], win32evtlog.EVENTLOG_INFORMATION_TYPE)
            
            # Create event message
            event_message = f"{log_entry['event_name']}: {log_entry['message']}"
            if log_entry['context']:
                event_message += f"\nContext: {json.dumps(log_entry['context'], indent=2)}"
                
            # Log to Windows Event Log
            win32evtlogutil.ReportEvent(
                "VoiceGuard",
                log_entry['event_id'],
                eventType=event_type,
                strings=[event_message]
            )
            
        except Exception as e:
            self.logger.debug(f"Windows Event Log failed: {e}")
            
    def get_recent_events(self, category: str = None, limit: int = 100) -> List[Dict]:
        """Get recent events from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if category:
                    cursor = conn.execute("""
                        SELECT event_type, event_data, timestamp
                        FROM event_log
                        WHERE event_type LIKE ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (f"{category}:%", limit))
                else:
                    cursor = conn.execute("""
                        SELECT event_type, event_data, timestamp
                        FROM event_log
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (limit,))
                    
                events = []
                for row in cursor.fetchall():
                    try:
                        event_data = json.loads(row[1])
                        events.append(event_data)
                    except json.JSONDecodeError:
                        # Fallback for non-JSON data
                        events.append({
                            'event_type': row[0],
                            'message': row[1],
                            'timestamp': row[2]
                        })
                        
                return events
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve events: {e}")
            return []
            
    def get_event_statistics(self, days: int = 7) -> Dict:
        """Get event statistics for the last N days"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT event_type, COUNT(*) as count
                    FROM event_log
                    WHERE timestamp > ?
                    GROUP BY event_type
                    ORDER BY count DESC
                """, (cutoff_date.isoformat(),))
                
                stats = {}
                total_events = 0
                
                for row in cursor.fetchall():
                    event_type = row[0]
                    count = row[1]
                    stats[event_type] = count
                    total_events += count
                    
                return {
                    'total_events': total_events,
                    'event_breakdown': stats,
                    'period_days': days
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get event statistics: {e}")
            return {'total_events': 0, 'event_breakdown': {}, 'period_days': days}
            
    def cleanup_old_events(self):
        """Cleanup old events based on retention policies"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for category, config in self.event_categories.items():
                    retention = config['retention']
                    
                    # Parse retention period
                    if 'year' in retention:
                        days = 365
                    elif 'day' in retention:
                        days = int(retention.split()[0])
                    else:
                        days = 30  # Default
                        
                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                    
                    # Delete old events
                    cursor = conn.execute("""
                        DELETE FROM event_log
                        WHERE event_type LIKE ? AND timestamp < ?
                    """, (f"{category}:%", cutoff_date.isoformat()))
                    
                    deleted_count = cursor.rowcount
                    if deleted_count > 0:
                        self.logger.info(f"Cleaned up {deleted_count} old {category} events")
                        
        except Exception as e:
            self.logger.error(f"Event cleanup failed: {e}")
            
    def export_events(self, output_file: Path, category: str = None, 
                     start_date: datetime = None, end_date: datetime = None):
        """Export events to file"""
        try:
            events = self.get_recent_events(category, limit=10000)
            
            # Filter by date range if specified
            if start_date or end_date:
                filtered_events = []
                for event in events:
                    event_time = datetime.fromisoformat(event['timestamp'])
                    
                    if start_date and event_time < start_date:
                        continue
                    if end_date and event_time > end_date:
                        continue
                        
                    filtered_events.append(event)
                    
                events = filtered_events
                
            # Export to JSON
            with open(output_file, 'w') as f:
                json.dump(events, f, indent=2, default=str)
                
            self.logger.info(f"Exported {len(events)} events to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Event export failed: {e}")


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add structured data if available
        if hasattr(record, 'structured_data'):
            log_entry.update(record.structured_data)
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)
