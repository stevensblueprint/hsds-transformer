"""
Simple logging system for the transformer.
Collects metrics about the transformation process.
"""

class TransformerLog:
    """Accumulates log entries during the transformation"""
    
    def __init__(self):
        self.entries = []
    
    def log(self, message: str):
        """Add a log entry"""
        self.entries.append(message)
    
    def section(self, title: str):
        """Add a section header"""
        self.entries.append("")
        self.entries.append(f"=== {title} ===")
    
    def get_log(self) -> str:
        """Return all log entries as a single string"""
        return "\n".join(self.entries)
    
    def clear(self):
        """Clear all log entries"""
        self.entries = []


# Global logger instance for use across the transformer
transformer_log = TransformerLog()
