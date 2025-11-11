"""
Usage analytics tracker for voice assistant.
Logs session metrics and generates reports.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from collections import Counter
from ..utils import get_logger, config

logger = get_logger(__name__)


class Analytics:
    """
    Tracks usage statistics and generates reports.
    
    Storage format: JSON lines (one object per session)
    File: ./data/analytics.jsonl
    """
    
    def __init__(self, log_file: Path = None):
        """
        Initialize analytics tracker.
        
        Args:
            log_file: Path to analytics log file
        """
        self.log_file = log_file or (config.DATA_DIR / "analytics.jsonl")
        
        # Ensure file exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists():
            self.log_file.touch()
        
        # Current session tracking
        self.session_start = None
        self.session_data = {
            "messages_count": 0,
            "tools_used": [],
            "total_tokens": 0,
            "errors": 0,
            "estimated_cost": 0.0
        }
        
        logger.info(f"Analytics initialized: {self.log_file}")
    
    def start_session(self):
        """Start tracking a new session."""
        self.session_start = datetime.now()
        self.session_data = {
            "messages_count": 0,
            "tools_used": [],
            "total_tokens": 0,
            "errors": 0,
            "estimated_cost": 0.0
        }
        logger.debug("Analytics session started")
    
    def log_message(self):
        """Increment message count."""
        self.session_data["messages_count"] += 1
    
    def log_tool_use(self, tool_name: str):
        """Log a tool execution."""
        self.session_data["tools_used"].append(tool_name)
    
    def log_tokens(self, prompt_tokens: int, completion_tokens: int):
        """Log token usage."""
        self.session_data["total_tokens"] += (prompt_tokens + completion_tokens)
        
        # Estimate cost (update pricing as needed)
        # gpt-4-turbo: $10/1M input, $30/1M output
        cost = (prompt_tokens / 1_000_000) * 10.0
        cost += (completion_tokens / 1_000_000) * 30.0
        self.session_data["estimated_cost"] += cost
    
    def log_error(self):
        """Increment error count."""
        self.session_data["errors"] += 1
    
    def end_session(self):
        """
        End current session and write to log file.
        """
        if not self.session_start:
            return
        
        duration = (datetime.now() - self.session_start).total_seconds()
        
        # Build session record
        record = {
            "timestamp": self.session_start.isoformat(),
            "duration": round(duration, 2),
            **self.session_data
        }
        
        # Append to log file (JSON lines format)
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(record) + '\n')
            
            logger.info(f"Analytics saved: {record['messages_count']} msgs, "
                       f"{record['total_tokens']} tokens, ${record['estimated_cost']:.4f}")
        
        except Exception as e:
            logger.error(f"Failed to write analytics: {e}")
        
        # Reset for next session
        self.session_start = None
    
    def generate_report(self) -> str:
        """
        Generate usage statistics report.
        
        Returns:
            Formatted report string
        """
        try:
            # Read all session records
            records = []
            
            with open(self.log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
            
            if not records:
                return "📊 No usage data yet. Start using the assistant to see statistics!"
            
            # Calculate statistics
            total_sessions = len(records)
            total_messages = sum(r.get("messages_count", 0) for r in records)
            total_tokens = sum(r.get("total_tokens", 0) for r in records)
            total_cost = sum(r.get("estimated_cost", 0.0) for r in records)
            total_errors = sum(r.get("errors", 0) for r in records)
            total_duration = sum(r.get("duration", 0) for r in records)
            
            # Tool usage
            all_tools = []
            for r in records:
                all_tools.extend(r.get("tools_used", []))
            
            tool_counts = Counter(all_tools)
            most_used = tool_counts.most_common(5)
            
            # Average metrics
            avg_session_length = total_duration / total_sessions if total_sessions > 0 else 0
            avg_messages = total_messages / total_sessions if total_sessions > 0 else 0
            error_rate = (total_errors / total_messages * 100) if total_messages > 0 else 0
            
            # Build report
            report = "╔══════════════════════════════════════════════════════════════╗\n"
            report += "║                    📊 USAGE STATISTICS                       ║\n"
            report += "╠══════════════════════════════════════════════════════════════╣\n"
            report += f"║  Total Sessions:       {total_sessions:<35}║\n"
            report += f"║  Total Messages:       {total_messages:<35}║\n"
            report += f"║  Total Duration:       {self._format_duration(total_duration):<35}║\n"
            report += "╠══════════════════════════════════════════════════════════════╣\n"
            report += "║  💰 API Usage:                                               ║\n"
            report += f"║    • OpenAI Tokens:    {total_tokens:<35}║\n"
            report += f"║    • Estimated Cost:   ${total_cost:.2f}{' ' * (33 - len(f'${total_cost:.2f}'))}║\n"
            report += f"║    • Tool Calls:       {len(all_tools):<35}║\n"
            report += "╠══════════════════════════════════════════════════════════════╣\n"
            
            if most_used:
                report += "║  🔧 Most Used Tools:                                         ║\n"
                for i, (tool, count) in enumerate(most_used, 1):
                    line = f"║    {i}. {tool}"
                    spaces = 45 - len(line)
                    report += f"{line}{' ' * spaces}({count} times){' ' * (62 - len(line) - spaces - len(f'({count} times)'))}║\n"
                report += "╠══════════════════════════════════════════════════════════════╣\n"
            
            report += "║  ⚡ Performance:                                              ║\n"
            report += f"║    • Avg Session:      {avg_session_length:.1f}s{' ' * (34 - len(f'{avg_session_length:.1f}s'))}║\n"
            report += f"║    • Avg Messages:     {avg_messages:.1f}{' ' * (35 - len(f'{avg_messages:.1f}'))}║\n"
            report += f"║    • Error Rate:       {error_rate:.1f}%{' ' * (34 - len(f'{error_rate:.1f}%'))}║\n"
            report += "╚══════════════════════════════════════════════════════════════╝\n"
            
            return report
        
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return f"❌ Error generating report: {str(e)}"
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} min"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hrs"
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get cost breakdown.
        
        Returns:
            Dictionary with cost metrics
        """
        try:
            records = []
            
            with open(self.log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
            
            total_cost = sum(r.get("estimated_cost", 0.0) for r in records)
            total_tokens = sum(r.get("total_tokens", 0) for r in records)
            
            # Last 7 days cost
            from datetime import timedelta
            now = datetime.now()
            week_ago = now - timedelta(days=7)
            
            recent_cost = sum(
                r.get("estimated_cost", 0.0) 
                for r in records 
                if datetime.fromisoformat(r["timestamp"]) >= week_ago
            )
            
            return {
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "last_7_days_cost": recent_cost,
                "sessions_count": len(records)
            }
        
        except Exception as e:
            logger.error(f"Failed to get cost summary: {e}")
            return {
                "total_cost": 0.0,
                "total_tokens": 0,
                "last_7_days_cost": 0.0,
                "sessions_count": 0
            }


# ============================================================================
# MODULE TEST
# ============================================================================
if __name__ == "__main__":
    import tempfile
    import time
    
    print("=" * 70)
    print("ANALYTICS TEST")
    print("=" * 70)
    
    # Create temp file
    temp_file = Path(tempfile.mktemp(suffix=".jsonl"))
    
    try:
        # Test 1: Initialize
        print("\n📝 Test 1: Initialize analytics")
        analytics = Analytics(log_file=temp_file)
        print("✅ Initialized")
        
        # Test 2: Track a session
        print("\n📝 Test 2: Track session")
        analytics.start_session()
        
        # Simulate activity
        for i in range(5):
            analytics.log_message()
            analytics.log_tool_use("web_search")
            analytics.log_tokens(100, 50)
        
        analytics.log_tool_use("rag_query")
        analytics.log_error()
        
        time.sleep(0.5)  # Simulate duration
        analytics.end_session()
        
        print("✅ Session logged")
        
        # Test 3: Generate report
        print("\n📝 Test 3: Generate report")
        
        # Log another session
        analytics.start_session()
        analytics.log_message()
        analytics.log_message()
        analytics.log_tool_use("gmail_draft")
        analytics.log_tokens(200, 100)
        time.sleep(0.3)
        analytics.end_session()
        
        report = analytics.generate_report()
        print(report)
        
        # Test 4: Cost summary
        print("\n📝 Test 4: Cost summary")
        cost = analytics.get_cost_summary()
        print(f"Total cost: ${cost['total_cost']:.4f}")
        print(f"Total tokens: {cost['total_tokens']}")
        print(f"Sessions: {cost['sessions_count']}")
        
        print("\n✅ All analytics tests passed!")
    
    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()
            print(f"\n🧹 Cleaned up: {temp_file}")