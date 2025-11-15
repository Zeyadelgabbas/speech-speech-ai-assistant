import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from collections import Counter
from ..utils import get_logger, config ,estimate_cost

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
            "prompt_tokens": 0,
            "completion_tokens": 0,
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
            "prompt_tokens": 0,
            "completion_tokens": 0,
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
    
    def log_tokens(self, tokens):
        """Log token usage."""

        pricing = estimate_cost(tokens)
        prompt_tokens = pricing.get("prompt_tokens",0)
        completion_tokens = pricing.get("completion_tokens",0)


        self.session_data["prompt_tokens"] += prompt_tokens
        self.session_data["completion_tokens"] += completion_tokens
        self.session_data["total_tokens"] += (prompt_tokens + completion_tokens)
        
        # Estimate cost (update pricing as needed)
        # gpt-4-turbo: $10/1M input, $30/1M output
        estimated_total_cost = pricing['total_cost_usd']
        self.session_data["estimated_cost"] +=estimated_total_cost
        logger.info("Logged tokens to stats")
    
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
            total_prompt_tokens = sum(r.get("prompt_tokens", 0) for r in records)
            total_completion_tokens = sum(r.get("completion_tokens", 0) for r in records)
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
            avg_tokens_per_session = total_tokens / total_sessions if total_sessions > 0 else 0
            error_rate = (total_errors / total_messages * 100) if total_messages > 0 else 0
            
            # Build report
            report = "╔══════════════════════════════════════════════════════════════╗\n"
            report += "║                    📊 USAGE STATISTICS                       ║\n"
            report += "╠══════════════════════════════════════════════════════════════╣\n"
            report += f"║  Total Sessions:       {total_sessions:<35}║\n"
            report += f"║  Total Messages:       {total_messages:<35}║\n"
            report += f"║  Total Duration:       {self._format_duration(total_duration):<35}║\n"
            report += "╠══════════════════════════════════════════════════════════════╣\n"
            report += "║  💰 Token Usage & Costs:                                     ║\n"
            report += f"║    • Prompt Tokens:    {total_prompt_tokens:<35}║\n"
            report += f"║    • Completion Tokens:{total_completion_tokens:<35}║\n"
            report += f"║    • Total Tokens:     {total_tokens:<35}║\n"
            report += f"║    • Estimated Cost:   ${total_cost:.4f}{' ' * (31 - len(f'${total_cost:.4f}'))}║\n"
            report += "╠══════════════════════════════════════════════════════════════╣\n"
            
            if most_used:
                report += "║  🔧 Most Used Tools:                                         ║\n"
                for i, (tool, count) in enumerate(most_used, 1):
                    line = f"║    {i}. {tool}"
                    spaces = 45 - len(line)
                    report += f"{line}{' ' * spaces}({count} times){' ' * (62 - len(line) - spaces - len(f'({count} times)'))}║\n"
                report += "╠══════════════════════════════════════════════════════════════╣\n"
            
            report += "║  ⚡ Performance Metrics:                                      ║\n"
            report += f"║    • Avg Session:      {self._format_duration(avg_session_length):<35}║\n"
            report += f"║    • Avg Messages:     {avg_messages:.1f} msgs/session{' ' * (23 - len(f'{avg_messages:.1f}'))}║\n"
            report += f"║    • Avg Tokens:       {avg_tokens_per_session:.0f} tokens/session{' ' * (20 - len(f'{avg_tokens_per_session:.0f}'))}║\n"
            report += f"║    • Error Rate:       {error_rate:.1f}%{' ' * (34 - len(f'{error_rate:.1f}%'))}║\n"
            report += f"║    • Tool Calls:       {len(all_tools)} total{' ' * (29 - len(f'{len(all_tools)}'))}║\n"
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
            total_prompt_tokens = sum(r.get("prompt_tokens", 0) for r in records)
            total_completion_tokens = sum(r.get("completion_tokens", 0) for r in records)
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
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens,
                "total_tokens": total_tokens,
                "last_7_days_cost": recent_cost,
                "sessions_count": len(records)
            }
        
        except Exception as e:
            logger.error(f"Failed to get cost summary: {e}")
            return {
                "total_cost": 0.0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "last_7_days_cost": 0.0,
                "sessions_count": 0
            }

    def reset_stats(self):
        try:
            with open(self.log_file, "w") as f:
                pass
            logger.info("Stats are cleared")

        except Exception as e:
            error_msg = f"Error clearing stats : {str(e)}"
            logger.error(error_msg)
            print(error_msg)
